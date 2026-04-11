"""
chunker.py — Partición del contenido normalizado en fragmentos para el RAG.

Qué hace:
  - Texto narrativo → chunks de ~500 tokens con overlap de 50
  - Tablas → chunks de cabecera + N filas (cabecera repetida en cada chunk)

Por qué estrategias distintas:
  El texto narrativo se puede cortar en cualquier punto con overlap para
  no perder contexto entre chunks adyacentes.
  Las tablas tienen estructura fila×columna: si cortamos sin repetir la
  cabecera, el LLM no sabe qué columna corresponde a cada valor.

Estructura de un chunk:
  {
    "chunk_id":   "folleto_presupuestos_2026_p8_t0_c0",
    "source":     "folleto_presupuestos_2026.pdf",
    "page":       8,
    "type":       "table",          # "text" o "table"
    "content":    "Distribución... | Presupuesto 2025 | ...\nSanidad | ...",
    "token_count": 312
  }

El chunk_id codifica: fuente_página_tipo_índice
  p8   = página 8
  t0   = tabla 0 de esa página (solo en type=table)
  c0   = chunk 0 dentro de esa tabla o bloque de texto
"""

import json
import logging
import re
from pathlib import Path

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Rutas ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# ─── Configuración de chunking ───────────────────────────────────────────────
# Importamos desde config si está disponible, si no usamos defaults
try:
    import sys
    sys.path.insert(0, str(ROOT_DIR))
    from config import CHUNK_SIZE, CHUNK_OVERLAP
except Exception:
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

# Número máximo de filas por chunk de tabla
# Con cabecera repetida, ~8 filas suelen caber en 500 tokens
FILAS_POR_CHUNK_TABLA = 8

# Aproximación de tokens sin dependencias externas de red.
# Para español: 1 token ≈ 4 caracteres (validado empíricamente con GPT-4 y Gemini).
# tiktoken requiere descargar ficheros BPE desde servidores externos —
# en producción se puede sustituir por tiktoken si hay acceso de red.
CHARS_POR_TOKEN = 4


def contar_tokens(texto: str) -> int:
    """
    Estima el número de tokens de un texto.

    Usa la aproximación de 4 caracteres por token, válida para español.
    Error típico: ±10% respecto a tokenizadores reales (GPT-4, Gemini).
    Suficiente para decidir cuándo cortar un chunk.
    """
    return max(1, len(texto) // CHARS_POR_TOKEN)


# ════════════════════════════════════════════════════════════════════════════
# CHUNKING DE TEXTO NARRATIVO
# ════════════════════════════════════════════════════════════════════════════

def chunkear_texto(
    texto: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """
    Divide texto narrativo en chunks de ~chunk_size tokens con overlap.

    Analogía: imagina que el texto es una cinta de papel. La cortamos en
    trozos de tamaño fijo, pero cada trozo comparte los últimos 50 tokens
    con el siguiente. Así, si una frase queda cortada entre dos chunks,
    el contexto necesario para entenderla aparece en ambos.

    Estrategia:
      1. Dividimos por párrafos (doble salto de línea)
      2. Acumulamos párrafos hasta llegar al límite de tokens
      3. Cuando superamos el límite, cerramos el chunk y comenzamos
         el siguiente con los últimos chunk_overlap tokens como semilla

    Args:
        texto:         Texto limpio de una o varias páginas
        chunk_size:    Máximo de tokens por chunk
        chunk_overlap: Tokens de solapamiento entre chunks consecutivos

    Returns:
        Lista de strings, cada uno es un chunk
    """
    if not texto or not texto.strip():
        return []

    # Dividimos por párrafos para no cortar en mitad de una idea
    parrafos = [p.strip() for p in re.split(r"\n\n+", texto) if p.strip()]

    chunks = []
    chunk_actual = []
    tokens_actuales = 0

    for parrafo in parrafos:
        tokens_parrafo = contar_tokens(parrafo)

        # Caso borde: un párrafo solo ya supera el límite
        # Lo añadimos como chunk propio aunque sea grande
        if tokens_parrafo > chunk_size:
            # Primero cerramos el chunk en curso si tiene contenido
            if chunk_actual:
                chunks.append("\n\n".join(chunk_actual))
                chunk_actual = []
                tokens_actuales = 0
            chunks.append(parrafo)
            continue

        # Si añadir este párrafo supera el límite, cerramos el chunk actual
        if tokens_actuales + tokens_parrafo > chunk_size and chunk_actual:
            chunks.append("\n\n".join(chunk_actual))

            # Calculamos el overlap: tomamos párrafos del final del chunk
            # hasta acumular chunk_overlap tokens
            overlap_texto = []
            overlap_tokens = 0
            for p in reversed(chunk_actual):
                t = contar_tokens(p)
                if overlap_tokens + t <= chunk_overlap:
                    overlap_texto.insert(0, p)
                    overlap_tokens += t
                else:
                    break

            chunk_actual = overlap_texto
            tokens_actuales = overlap_tokens

        chunk_actual.append(parrafo)
        tokens_actuales += tokens_parrafo

    # Añadimos el último chunk si tiene contenido
    if chunk_actual:
        chunks.append("\n\n".join(chunk_actual))

    return chunks


# ════════════════════════════════════════════════════════════════════════════
# CHUNKING DE TABLAS
# ════════════════════════════════════════════════════════════════════════════

def chunkear_tabla(
    tabla_texto: str,
    filas_por_chunk: int = FILAS_POR_CHUNK_TABLA
) -> list[str]:
    """
    Divide una tabla en chunks de cabecera + N filas.

    La cabecera (primera fila) se repite en cada chunk para que el LLM
    siempre sepa a qué columna pertenece cada valor.

    Ejemplo con filas_por_chunk=2:
      Chunk 0: "Consejería | 2025 | 2026\nSanidad | 10.459 | 11.009\nEducación | 6.699 | 6.959"
      Chunk 1: "Consejería | 2025 | 2026\nVivienda | 3.290 | 3.292\nFamilia | 2.694 | 2.904"

    Args:
        tabla_texto:    Representación textual de la tabla (de normalizer)
        filas_por_chunk: Número de filas de datos por chunk (sin contar cabecera)

    Returns:
        Lista de strings, cada uno es un chunk de tabla
    """
    if not tabla_texto or not tabla_texto.strip():
        return []

    filas = tabla_texto.strip().split("\n")

    if len(filas) == 0:
        return []

    # La primera fila es la cabecera
    cabecera = filas[0]
    filas_datos = filas[1:]

    # Si la tabla no tiene datos (solo cabecera), la devolvemos como un chunk
    if not filas_datos:
        return [cabecera]

    chunks = []
    for i in range(0, len(filas_datos), filas_por_chunk):
        bloque = filas_datos[i:i + filas_por_chunk]
        # Cabecera repetida + filas de datos
        chunk = cabecera + "\n" + "\n".join(bloque)
        chunks.append(chunk)

    return chunks


# ════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE CHUNKS CON METADATOS
# ════════════════════════════════════════════════════════════════════════════

def construir_chunk_id(
    nombre_base: str,
    num_pagina: int,
    tipo: str,
    indice_chunk: int,
    indice_tabla: int | None = None
) -> str:
    """
    Genera un identificador único y legible para cada chunk.

    Formato:
      texto:  "folleto_presupuestos_2026_p4_text_c2"
      tabla:  "folleto_presupuestos_2026_p8_t0_c1"

    El chunk_id permite trazar un chunk hasta su página y tabla de origen,
    útil para debugging y para construir las citas en las respuestas del RAG.
    """
    base = nombre_base.replace(" ", "_").replace(".", "_")
    pagina_str = f"p{num_pagina}"

    if tipo == "table" and indice_tabla is not None:
        return f"{base}_{pagina_str}_t{indice_tabla}_c{indice_chunk}"
    else:
        return f"{base}_{pagina_str}_text_c{indice_chunk}"


def procesar_pagina(
    pagina: dict,
    nombre_fuente: str,
    nombre_base: str
) -> list[dict]:
    """
    Genera todos los chunks de una página (texto + tablas).

    Args:
        pagina:        Dict de página normalizada {page, text, tables, tables_text}
        nombre_fuente: Nombre del archivo PDF original
        nombre_base:   Nombre base para construir chunk_ids

    Returns:
        Lista de dicts, cada uno es un chunk con metadatos completos
    """
    chunks = []
    num_pagina = pagina["page"]

    # ── Chunks de texto narrativo ────────────────────────────────────────
    texto = pagina.get("text", "")
    if texto.strip():
        fragmentos_texto = chunkear_texto(texto)
        for i, fragmento in enumerate(fragmentos_texto):
            chunk_id = construir_chunk_id(nombre_base, num_pagina, "text", i)
            chunks.append({
                "chunk_id":    chunk_id,
                "source":      nombre_fuente,
                "page":        num_pagina,
                "type":        "text",
                "content":     fragmento,
                "token_count": contar_tokens(fragmento)
            })

    # ── Chunks de tablas ─────────────────────────────────────────────────
    tablas_texto = pagina.get("tables_text", [])
    for idx_tabla, tabla_texto in enumerate(tablas_texto):
        if not tabla_texto.strip():
            continue

        fragmentos_tabla = chunkear_tabla(tabla_texto)
        for i, fragmento in enumerate(fragmentos_tabla):
            chunk_id = construir_chunk_id(
                nombre_base, num_pagina, "table", i, idx_tabla
            )
            chunks.append({
                "chunk_id":    chunk_id,
                "source":      nombre_fuente,
                "page":        num_pagina,
                "type":        "table",
                "content":     fragmento,
                "token_count": contar_tokens(fragmento)
            })

    return chunks


def chunkear_documento(datos_normalizados: dict) -> list[dict]:
    """
    Genera todos los chunks de un documento normalizado.

    Args:
        datos_normalizados: Dict con estructura {source, total_pages, pages}

    Returns:
        Lista de chunks con metadatos, ordenados por página
    """
    nombre_fuente = datos_normalizados["source"]
    # Nombre base: nombre del archivo sin extensión
    nombre_base = Path(nombre_fuente).stem

    logger.info(f"Chunkeando: {nombre_fuente}")

    todos_los_chunks = []
    for pagina in datos_normalizados["pages"]:
        chunks_pagina = procesar_pagina(pagina, nombre_fuente, nombre_base)
        todos_los_chunks.extend(chunks_pagina)

    # Estadísticas
    chunks_texto = [c for c in todos_los_chunks if c["type"] == "text"]
    chunks_tabla = [c for c in todos_los_chunks if c["type"] == "table"]
    tokens_total = sum(c["token_count"] for c in todos_los_chunks)
    tokens_medio = tokens_total // len(todos_los_chunks) if todos_los_chunks else 0

    logger.info(
        f"  Total chunks: {len(todos_los_chunks)} "
        f"({len(chunks_texto)} texto + {len(chunks_tabla)} tabla)"
    )
    logger.info(
        f"  Tokens: {tokens_total:,} total, "
        f"{tokens_medio} media por chunk"
    )

    return todos_los_chunks


def chunkear_desde_json(
    ruta_json: Path | str,
    guardar: bool = True
) -> list[dict]:
    """
    Carga un JSON normalizado, lo chunkea y opcionalmente guarda el resultado.

    El archivo de salida tiene el sufijo "_chunks":
      folleto_presupuestos_2026_normalized.json → folleto_presupuestos_2026_chunks.json

    Args:
        ruta_json: Ruta al JSON normalizado (generado por normalizer.py)
        guardar:   Si True, guarda los chunks en data/processed/

    Returns:
        Lista de chunks con metadatos
    """
    ruta_json = Path(ruta_json)

    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)

    chunks = chunkear_documento(datos)

    if guardar:
        # El nombre de salida elimina el sufijo "_normalized" y añade "_chunks"
        nombre_salida = ruta_json.stem.replace("_normalized", "") + "_chunks.json"
        ruta_salida = PROCESSED_DIR / nombre_salida

        with open(ruta_salida, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"  Chunks guardados en: {ruta_salida}")

    return chunks


# ════════════════════════════════════════════════════════════════════════════
# TEST BLOCK
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Chunkea los JSONs normalizados disponibles en data/processed/.

    Uso:
        python ingestion/chunker.py
        python ingestion/chunker.py data/processed/mi_archivo_normalized.json
    """
    import sys

    if len(sys.argv) > 1:
        jsons = [Path(sys.argv[1])]
    else:
        jsons = list(PROCESSED_DIR.glob("*_normalized.json"))

    if not jsons:
        print(f"No se encontraron JSONs normalizados en {PROCESSED_DIR}")
        print("Ejecuta primero: python ingestion/normalizer.py")
        sys.exit(1)

    for ruta_json in jsons:
        print(f"\n{'='*60}")
        print(f"Chunkeando: {ruta_json.name}")
        print(f"{'='*60}")

        chunks = chunkear_desde_json(ruta_json, guardar=True)

        if not chunks:
            print("No se generaron chunks.")
            continue

        # ── Distribución de tamaños ──────────────────────────────────────
        tokens = [c["token_count"] for c in chunks]
        print(f"\nDistribución de tokens por chunk:")
        print(f"  Mínimo:  {min(tokens)}")
        print(f"  Máximo:  {max(tokens)}")
        print(f"  Media:   {sum(tokens) // len(tokens)}")
        print(f"  >500 tk: {sum(1 for t in tokens if t > 500)} chunks")

        # ── Muestra de chunk de texto ────────────────────────────────────
        chunk_texto = next((c for c in chunks if c["type"] == "text"), None)
        if chunk_texto:
            print(f"\n── CHUNK TEXTO de ejemplo ──")
            print(f"  ID:     {chunk_texto['chunk_id']}")
            print(f"  Página: {chunk_texto['page']}")
            print(f"  Tokens: {chunk_texto['token_count']}")
            print(f"  Contenido (primeros 200 chars):")
            print(f"    {chunk_texto['content'][:200]}...")

        # ── Muestra de chunk de tabla ────────────────────────────────────
        chunk_tabla = next((c for c in chunks if c["type"] == "table"), None)
        if chunk_tabla:
            print(f"\n── CHUNK TABLA de ejemplo ──")
            print(f"  ID:     {chunk_tabla['chunk_id']}")
            print(f"  Página: {chunk_tabla['page']}")
            print(f"  Tokens: {chunk_tabla['token_count']}")
            print(f"  Contenido:")
            for linea in chunk_tabla["content"].split("\n"):
                print(f"    {linea}")

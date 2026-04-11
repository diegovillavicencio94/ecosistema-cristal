"""
normalizer.py — Limpieza de texto y tablas extraídas por pdf_extractor.

Qué hace:
  - Limpia el texto narrativo (espacios, saltos de línea, caracteres extraños)
  - Limpia las celdas de las tablas sin alterar su estructura matricial
  - Convierte cada tabla en una representación textual legible para el chunker

Qué NO hace (por diseño):
  - No elimina columnas ni filas vacías: una celda vacía en un presupuesto
    es un dato semántico (partida sin dotación), no ruido
  - No reordena ni fusiona filas
  - No interpreta los valores numéricos

Por qué importa conservar la matriz:
  Las tablas presupuestarias tienen una relación fila×columna que codifica
  glosas (filas) vs ejercicios o capítulos (columnas). Comprimir una columna
  vacía rompe esa relación y el LLM no puede responder correctamente a
  preguntas como "¿cuánto se destinó a X en el capítulo Y?".
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


# ════════════════════════════════════════════════════════════════════════════
# LIMPIEZA DE TEXTO NARRATIVO
# ════════════════════════════════════════════════════════════════════════════

def limpiar_texto(texto: str) -> str:
    """
    Limpia el texto narrativo extraído de una página PDF.

    Problemas comunes en PDFs presupuestarios:
      - Saltos de línea en mitad de palabras (guiones de partición)
      - Múltiples espacios consecutivos
      - Caracteres de control (tabulaciones, form feeds)
      - Líneas con solo números de página o encabezados repetidos

    Args:
        texto: Texto crudo extraído por pdfplumber

    Returns:
        Texto limpio con espaciado normalizado
    """
    if not texto:
        return ""

    # 1. Unir palabras partidas con guión al final de línea
    #    Ejemplo: "presu-\npuesto" → "presupuesto"
    texto = re.sub(r"-\n(\w)", r"\1", texto)

    # 2. Reemplazar saltos de línea simples por espacio
    #    (los dobles saltos de línea indican párrafos reales, los conservamos)
    texto = re.sub(r"(?<!\n)\n(?!\n)", " ", texto)

    # 3. Normalizar múltiples espacios a uno solo
    texto = re.sub(r" {2,}", " ", texto)

    # 4. Normalizar múltiples saltos de línea a máximo dos
    #    (para conservar separación entre párrafos)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # 5. Eliminar caracteres de control que no sean salto de línea
    #    \x0c = form feed (salto de página dentro del texto)
    #    \t   = tabulación (en texto narrativo no tiene sentido)
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)

    # 6. Eliminar espacios al inicio y fin de cada línea
    lineas = [linea.strip() for linea in texto.split("\n")]
    texto = "\n".join(lineas)

    # 7. Eliminar líneas que son solo números (números de página)
    #    Ejemplo: una línea que solo contiene "47" o "— 47 —"
    lineas = texto.split("\n")
    lineas_filtradas = [
        linea for linea in lineas
        if not re.fullmatch(r"[\s\d\-–—|]*", linea) or linea == ""
    ]
    texto = "\n".join(lineas_filtradas)

    # 8. Eliminar espacios al inicio y fin del texto completo
    return texto.strip()


# ════════════════════════════════════════════════════════════════════════════
# LIMPIEZA DE TABLAS (sin alterar estructura matricial)
# ════════════════════════════════════════════════════════════════════════════

def limpiar_celda(celda: str) -> str:
    """
    Limpia el contenido de una celda de tabla.

    Problemas comunes:
      - Saltos de línea dentro de una celda (texto largo en celda estrecha)
        Ejemplo: "Agencia de la Comunidad de Madrid para la\nReeducación..."
      - Espacios múltiples
      - Guiones de partición de palabras

    IMPORTANTE: No eliminamos la celda aunque quede vacía.
    Una celda vacía es parte de la estructura matricial.
    """
    if not celda:
        return ""

    # Unir palabras partidas con guión
    celda = re.sub(r"-\n(\w)", r"\1", celda)

    # Reemplazar saltos de línea internos por espacio
    celda = celda.replace("\n", " ")

    # Normalizar espacios múltiples
    celda = re.sub(r" {2,}", " ", celda)

    return celda.strip()


def limpiar_tabla(tabla: list[list[str]]) -> list[list[str]]:
    """
    Limpia todas las celdas de una tabla conservando su estructura matricial.

    La tabla entra y sale con las mismas dimensiones (mismo número de filas
    y columnas). Solo se limpia el contenido de cada celda.

    Args:
        tabla: Lista de listas de strings (estructura matricial)

    Returns:
        Misma estructura con celdas limpias
    """
    return [
        [limpiar_celda(celda) for celda in fila]
        for fila in tabla
    ]


def tabla_a_texto(tabla: list[list[str]], separador: str = " | ") -> str:
    """
    Convierte una tabla matricial a representación textual para el chunker.

    Por qué convertir a texto:
      El chunker y el embedder trabajan con strings. Necesitamos una
      representación que preserve la relación fila×columna y sea legible
      para el LLM.

    Formato elegido: filas separadas por salto de línea, celdas por " | "
      Ejemplo:
        Consejería | 2025 | 2026 | Var.(€) | Var.(%)
        Sanidad | 10.459,7 | 11.009,5 | 549,8 | 5,3%
        Educación | 6.699,6 | 6.959,0 | 259,4 | 3,9%

    Las celdas vacías se representan como "-" para que el LLM entienda
    que la posición existe pero no tiene valor, sin confundirlo con
    texto ausente.

    Args:
        tabla:     Tabla limpia (lista de listas)
        separador: Separador entre celdas (por defecto " | ")

    Returns:
        Representación textual de la tabla
    """
    if not tabla:
        return ""

    filas_texto = []
    for fila in tabla:
        # Las celdas vacías se marcan con "-" para preservar la estructura visual
        celdas_repr = [celda if celda else "-" for celda in fila]
        filas_texto.append(separador.join(celdas_repr))

    return "\n".join(filas_texto)


# ════════════════════════════════════════════════════════════════════════════
# NORMALIZACIÓN DE UN DOCUMENTO COMPLETO
# ════════════════════════════════════════════════════════════════════════════

def normalizar_pagina(pagina: dict) -> dict:
    """
    Normaliza una página del JSON generado por pdf_extractor.

    Transforma:
      - texto crudo → texto limpio
      - tablas crudas → tablas limpias (misma estructura)
      - tablas limpias → representación textual (para el chunker)

    La representación textual de las tablas se añade al campo
    "tables_text": una lista de strings, uno por tabla.
    El campo "tables" (estructura matricial) se conserva intacto.
    """
    texto_limpio = limpiar_texto(pagina.get("text", ""))

    tablas_originales = pagina.get("tables", [])
    tablas_limpias = [limpiar_tabla(t) for t in tablas_originales]
    tablas_texto = [tabla_a_texto(t) for t in tablas_limpias]

    return {
        "page": pagina["page"],
        "text": texto_limpio,
        "tables": tablas_limpias,        # estructura matricial limpia
        "tables_text": tablas_texto       # representación textual para chunker
    }


def normalizar_documento(datos_raw: dict) -> dict:
    """
    Normaliza el documento completo producido por pdf_extractor.

    Args:
        datos_raw: Dict con estructura {source, total_pages, pages}

    Returns:
        Mismo dict con páginas normalizadas y campo "normalized": True
    """
    logger.info(f"Normalizando: {datos_raw['source']}")

    paginas_normalizadas = []
    for pagina in datos_raw["pages"]:
        pagina_norm = normalizar_pagina(pagina)
        paginas_normalizadas.append(pagina_norm)

    # Estadísticas
    total_chars = sum(len(p["text"]) for p in paginas_normalizadas)
    total_tablas = sum(len(p["tables"]) for p in paginas_normalizadas)
    chars_originales = sum(len(p["text"]) for p in datos_raw["pages"])

    logger.info(
        f"  Texto: {chars_originales:,} → {total_chars:,} caracteres "
        f"({chars_originales - total_chars:+,} chars eliminados)"
    )
    logger.info(f"  Tablas conservadas: {total_tablas} (estructura intacta)")

    return {
        "source": datos_raw["source"],
        "total_pages": datos_raw["total_pages"],
        "normalized": True,
        "pages": paginas_normalizadas
    }


def normalizar_desde_json(
    ruta_json: Path | str,
    guardar: bool = True
) -> dict:
    """
    Carga un JSON de pdf_extractor, lo normaliza y opcionalmente lo guarda.

    El archivo de salida tiene el mismo nombre con sufijo "_normalized":
      folleto_presupuestos_2026.json → folleto_presupuestos_2026_normalized.json

    Args:
        ruta_json: Ruta al JSON generado por pdf_extractor
        guardar:   Si True, guarda el resultado en data/processed/

    Returns:
        Documento normalizado
    """
    ruta_json = Path(ruta_json)

    with open(ruta_json, encoding="utf-8") as f:
        datos_raw = json.load(f)

    datos_normalizados = normalizar_documento(datos_raw)

    if guardar:
        nombre_salida = ruta_json.stem + "_normalized.json"
        ruta_salida = PROCESSED_DIR / nombre_salida

        with open(ruta_salida, "w", encoding="utf-8") as f:
            json.dump(datos_normalizados, f, ensure_ascii=False, indent=2)

        logger.info(f"  Guardado en: {ruta_salida}")

    return datos_normalizados


# ════════════════════════════════════════════════════════════════════════════
# TEST BLOCK
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Normaliza los JSONs disponibles en data/processed/ y muestra
    una comparativa antes/después para verificar la limpieza.

    Uso:
        python ingestion/normalizer.py
        python ingestion/normalizer.py data/processed/mi_archivo.json
    """
    import sys

    if len(sys.argv) > 1:
        jsons = [Path(sys.argv[1])]
    else:
        # Procesamos todos los JSONs que NO sean ya normalizados
        jsons = [
            p for p in PROCESSED_DIR.glob("*.json")
            if "_normalized" not in p.stem
        ]

    if not jsons:
        print(f"No se encontraron JSONs en {PROCESSED_DIR}")
        sys.exit(1)

    for ruta_json in jsons:
        print(f"\n{'='*60}")
        print(f"Normalizando: {ruta_json.name}")
        print(f"{'='*60}")

        datos = normalizar_desde_json(ruta_json, guardar=True)

        # ── Comparativa texto antes/después ─────────────────────────────
        # Cargamos el original para comparar
        with open(ruta_json, encoding="utf-8") as f:
            original = json.load(f)

        print("\n── MUESTRA: texto página 4 ──")
        pag_orig = next((p for p in original["pages"] if p["page"] == 4), None)
        pag_norm = next((p for p in datos["pages"] if p["page"] == 4), None)

        if pag_orig and pag_norm:
            print("ANTES:")
            print(repr(pag_orig["text"][:200]))
            print("\nDESPUÉS:")
            print(repr(pag_norm["text"][:200]))

        # ── Muestra de tabla con estructura conservada ───────────────────
        primera_pag_con_tabla = next(
            (p for p in datos["pages"] if p["tables"]), None
        )

        if primera_pag_con_tabla:
            num_pag = primera_pag_con_tabla["page"]
            tabla = primera_pag_con_tabla["tables"][0]
            tabla_txt = primera_pag_con_tabla["tables_text"][0]

            print(f"\n── TABLA (página {num_pag}) ──")
            print(f"Dimensiones: {len(tabla)} filas × {len(tabla[0]) if tabla else 0} cols")
            print("\nEstructura matricial (primeras 4 filas):")
            for fila in tabla[:4]:
                print(f"  {fila}")

            print("\nRepresentación textual (primeras 4 líneas):")
            for linea in tabla_txt.split("\n")[:4]:
                print(f"  {linea}")

"""
embedder.py — Generación de embeddings y carga en Qdrant.

Qué hace:
  - Lee los chunks generados por chunker.py
  - Genera un embedding (vector numérico) para cada chunk usando Gemini
  - Sube cada vector + su payload (metadatos) a Qdrant
  - Crea la colección en Qdrant si no existe

Por qué embeddings:
  Un embedding es la "huella semántica" de un texto. Dos frases que
  significan lo mismo tendrán vectores muy parecidos aunque usen palabras
  distintas. Qdrant almacena esos vectores y nos permite encontrar los
  chunks más similares a una pregunta en milisegundos.

Modelo: gemini-embedding-001 (Google)
  - 3072 dimensiones
  - Buen rendimiento en español
  - Gratuito via Google AI Studio
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types as genai_types
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Rutas y config ─────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# Cargamos configuración desde .env
import sys
sys.path.insert(0, str(ROOT_DIR))
from config import (
    GOOGLE_API_KEY,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
)

# Dimensiones del modelo gemini-embedding-001
EMBEDDING_DIM = 3072

# Tamaño del batch para subir puntos a Qdrant
# 100 puntos por batch es un buen balance entre velocidad y memoria
BATCH_SIZE = 100

# Pausa entre llamadas a la API de embeddings (segundos)
# Google AI Studio tiene límite de ~1500 requests/min en el tier gratuito
# Con 0.05s de pausa estamos muy por debajo del límite
PAUSA_ENTRE_LLAMADAS = 15

# Longitud mínima de un chunk para ser embebido
# Chunks muy cortos (títulos, números de página) aportan poco al RAG
MIN_CHARS_CHUNK = 20


# ════════════════════════════════════════════════════════════════════════════
# METADATOS TERRITORIALES
# ════════════════════════════════════════════════════════════════════════════

# Tabla de códigos INE para comunidades autónomas
# Fuente: https://www.ine.es/daco/daco42/codmun/cod_ccaa.htm
CODIGOS_INE_CCAA = {
    "andalucia":          "01",
    "aragon":             "02",
    "asturias":           "03",
    "baleares":           "04",
    "canarias":           "05",
    "cantabria":          "06",
    "castilla_la_mancha": "08",
    "castilla_leon":      "07",
    "cataluna":           "09",
    "extremadura":        "11",
    "galicia":            "12",
    "madrid":             "13",
    "murcia":             "14",
    "navarra":            "15",
    "pais_vasco":         "16",
    "la_rioja":           "17",
    "valencia":           "10",
    "ceuta":              "18",
    "melilla":            "19",
}

def inferir_metadatos_territoriales(
    nombre_archivo: str,
    metadatos_extra: Optional[dict] = None
) -> dict:
    """
    Infiere los metadatos territoriales a partir del nombre del archivo.

    En el MVP inferimos de forma simple desde el nombre del fichero.
    En producción esto vendrá de un manifiesto JSON que acompañe a cada PDF.

    Args:
        nombre_archivo: Nombre del PDF (ej. "folleto_presupuestos_2026.pdf")
        metadatos_extra: Dict opcional para sobreescribir cualquier campo

    Returns:
        Dict con todos los campos territoriales y temporales
    """
    nombre = nombre_archivo.lower()

    # ── Año ─────────────────────────────────────────────────────────────
    import re
    match_año = re.search(r"20\d{2}", nombre)
    año = int(match_año.group()) if match_año else None

    # ── Tipo de documento ────────────────────────────────────────────────
    if "folleto" in nombre or "resumen" in nombre:
        doc_type = "folleto"
    elif "articulado" in nombre or "ley" in nombre:
        doc_type = "articulado"
    elif "memoria" in nombre:
        doc_type = "memoria"
    else:
        doc_type = "otro"

    # ── Territorio ───────────────────────────────────────────────────────
    # Por defecto asumimos Madrid autonómico (MVP).
    # Al escalar, este bloque se reemplaza por lectura de un manifiesto.
    if "madrid" in nombre or "cm" in nombre:
        nivel_territorial = "comunidad"
        ambito           = "autonomico"
        pais             = "España"
        comunidad        = "Madrid"
        provincia        = None
        municipio        = None
        codigo_ine       = CODIGOS_INE_CCAA["madrid"]
    elif "estatal" in nombre or "pge" in nombre or "nacional" in nombre:
        nivel_territorial = "pais"
        ambito           = "estatal"
        pais             = "España"
        comunidad        = None
        provincia        = None
        municipio        = None
        codigo_ine       = "00"
    else:
        # Fallback: marcamos como desconocido para revisión manual
        nivel_territorial = "desconocido"
        ambito           = "desconocido"
        pais             = "España"
        comunidad        = None
        provincia        = None
        municipio        = None
        codigo_ine       = None

    metadatos = {
        "año":               año,
        "nivel_territorial": nivel_territorial,
        "ambito":            ambito,
        "pais":              pais,
        "comunidad":         comunidad,
        "provincia":         provincia,
        "municipio":         municipio,
        "codigo_ine":        codigo_ine,
        "doc_type":          doc_type,
    }

    # Sobreescribimos con cualquier metadato explícito que se pase
    if metadatos_extra:
        metadatos.update(metadatos_extra)

    return metadatos


def inferir_organismo(chunk: dict) -> Optional[str]:
    """
    Intenta detectar la consejería u organismo al que pertenece un chunk.

    Estrategia simple: buscamos nombres de consejerías conocidas en el
    contenido del chunk. En producción esto mejoraría con NER o con
    metadatos del documento fuente.
    """
    import unicodedata
    # Normalizamos: quitamos acentos para que "educación" == "educacion"
    def quitar_acentos(s):
        return "".join(
            c for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) != "Mn"
        )

    contenido = quitar_acentos(chunk.get("content", "").lower())

    consejerias = [
        ("sanidad",                    "Sanidad"),
        ("educacion",                  "Educación"),
        ("vivienda",                   "Vivienda, Transportes e Infraestructuras"),
        ("transportes",                "Vivienda, Transportes e Infraestructuras"),
        ("infraestructuras",           "Vivienda, Transportes e Infraestructuras"),
        ("familia",                    "Familia, Juventud y Asuntos Sociales"),
        ("asuntos sociales",           "Familia, Juventud y Asuntos Sociales"),
        ("presidencia",                "Presidencia, Justicia y Administración Local"),
        ("justicia",                   "Presidencia, Justicia y Administración Local"),
        ("medio ambiente",             "Medio Ambiente, Agricultura e Interior"),
        ("agricultura",                "Medio Ambiente, Agricultura e Interior"),
        ("interior",                   "Medio Ambiente, Agricultura e Interior"),
        ("empleo",                     "Políticas de Empleo"),
        ("digitalizacion",             "Digitalización"),
        ("economia",                   "Economía, Hacienda y Empleo"),
        ("hacienda",                   "Economía, Hacienda y Empleo"),
        ("cultura",                    "Cultura, Turismo y Deporte"),
        ("turismo",                    "Cultura, Turismo y Deporte"),
        ("deporte",                    "Cultura, Turismo y Deporte"),
    ]

    for termino, nombre_oficial in consejerias:
        if termino in contenido:
            return nombre_oficial

    return None


# ════════════════════════════════════════════════════════════════════════════
# CLIENTE QDRANT
# ════════════════════════════════════════════════════════════════════════════

def crear_cliente_qdrant() -> QdrantClient:
    """Crea y devuelve un cliente conectado a Qdrant."""
    cliente = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    logger.info(f"Conectado a Qdrant en {QDRANT_HOST}:{QDRANT_PORT}")
    return cliente


def asegurar_coleccion(cliente: QdrantClient, nombre: str) -> None:
    """
    Crea la colección en Qdrant si no existe.

    Una colección es como una tabla en una base de datos relacional,
    pero para vectores. Definimos la dimensión (3072 para gemini-embedding-001)
    y la métrica de distancia (coseno es la estándar para embeddings de texto).
    """
    colecciones = [c.name for c in cliente.get_collections().collections]

    if nombre in colecciones:
        logger.info(f"Colección '{nombre}' ya existe — reutilizando")
        return

    cliente.create_collection(
        collection_name=nombre,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE,
        )
    )
    logger.info(f"Colección '{nombre}' creada ({EMBEDDING_DIM} dims, coseno)")


# ════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE EMBEDDINGS
# ════════════════════════════════════════════════════════════════════════════

# Cliente global de Gemini (se inicializa una sola vez)
_gemini_client: Optional[genai.Client] = None


def inicializar_gemini() -> genai.Client:
    """
    Inicializa y devuelve el cliente de Google GenAI.

    Usamos v1beta porque es donde están disponibles los modelos de embedding
    de Gemini en Google AI Studio.
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(api_version="v1beta"),
        )
        logger.info(f"Gemini configurado. Modelo de embeddings: {EMBEDDING_MODEL}")
    return _gemini_client


def generar_embedding(texto: str, reintentos: int = 3) -> list[float]:
    """
    Genera el embedding de un texto usando Gemini gemini-embedding-001.

    Incluye reintentos con backoff exponencial para manejar errores
    transitorios de la API (rate limits, timeouts).

    Args:
        texto:      Texto a embeber
        reintentos: Número de intentos antes de fallar

    Returns:
        Lista de 3072 floats representando el vector semántico del texto
    """
    for intento in range(reintentos):
        try:
            cliente = inicializar_gemini()
            resultado = cliente.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texto,
                config=genai_types.EmbedContentConfig(
                    task_type="retrieval_document",  # optimizado para indexación RAG
                ),
            )
            return resultado.embeddings[0].values

        except Exception as e:
            if intento < reintentos - 1:
                espera = 2 ** intento  # 1s, 2s, 4s
                logger.warning(f"Error en embedding (intento {intento+1}): {e}. Reintentando en {espera}s...")
                time.sleep(espera)
            else:
                logger.error(f"Fallo definitivo al generar embedding: {e}")
                raise


# ════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE PAYLOADS
# ════════════════════════════════════════════════════════════════════════════

def construir_payload(chunk: dict, metadatos_territoriales: dict) -> dict:
    """
    Construye el payload completo que se almacena en Qdrant junto al vector.

    El payload es lo que el retriever devuelve al LLM junto con el fragmento
    de texto. Incluye todo lo necesario para que el LLM cite la fuente
    correctamente y para que el sistema pueda filtrar por territorio/año.
    """
    return {
        # ── Identificación del chunk ─────────────────────────────────────
        "chunk_id":          chunk["chunk_id"],
        "source":            chunk["source"],
        "page":              chunk["page"],
        "type":              chunk["type"],      # "text" o "table"
        "content":           chunk["content"],   # el texto que verá el LLM

        # ── Temporal ─────────────────────────────────────────────────────
        "año":               metadatos_territoriales.get("año"),

        # ── Territorial ──────────────────────────────────────────────────
        "nivel_territorial": metadatos_territoriales.get("nivel_territorial"),
        "ambito":            metadatos_territoriales.get("ambito"),
        "pais":              metadatos_territoriales.get("pais"),
        "comunidad":         metadatos_territoriales.get("comunidad"),
        "provincia":         metadatos_territoriales.get("provincia"),
        "municipio":         metadatos_territoriales.get("municipio"),
        "codigo_ine":        metadatos_territoriales.get("codigo_ine"),

        # ── Documento ────────────────────────────────────────────────────
        "doc_type":          metadatos_territoriales.get("doc_type"),
        "organismo":         inferir_organismo(chunk),
    }


# ════════════════════════════════════════════════════════════════════════════
# CARGA EN QDRANT
# ════════════════════════════════════════════════════════════════════════════

def subir_batch(
    cliente: QdrantClient,
    puntos: list[PointStruct],
    coleccion: str
) -> None:
    """Sube un batch de puntos a Qdrant."""
    cliente.upsert(
        collection_name=coleccion,
        points=puntos,
    )


def embeber_y_cargar(
    chunks: list[dict],
    metadatos_extra: Optional[dict] = None,
    coleccion: str = QDRANT_COLLECTION,
) -> int:
    """
    Pipeline completo: chunks → embeddings → Qdrant.

    Para cada chunk:
      1. Filtramos chunks demasiado cortos
      2. Generamos el embedding con Gemini
      3. Construimos el payload con todos los metadatos
      4. Acumulamos en un batch
      5. Subimos el batch a Qdrant cuando llega a BATCH_SIZE

    Args:
        chunks:         Lista de chunks de chunker.py
        metadatos_extra: Metadatos territoriales adicionales para sobreescribir
        coleccion:      Nombre de la colección en Qdrant

    Returns:
        Número de puntos insertados en Qdrant
    """
    if not chunks:
        logger.warning("Lista de chunks vacía. Nada que embeber.")
        return 0

    # Inferimos metadatos territoriales del primer chunk (todos son del mismo doc)
    nombre_fuente = chunks[0]["source"]
    metadatos_territoriales = inferir_metadatos_territoriales(
        nombre_fuente, metadatos_extra
    )
    logger.info(
        f"Metadatos territoriales: {metadatos_territoriales['ambito']} | "
        f"{metadatos_territoriales.get('comunidad', 'N/A')} | "
        f"año {metadatos_territoriales.get('año', 'N/A')} | "
        f"{metadatos_territoriales['doc_type']}"
    )

    # Inicializamos clientes
    inicializar_gemini()  # precalentamos el cliente
    cliente_qdrant = crear_cliente_qdrant()
    asegurar_coleccion(cliente_qdrant, coleccion)

    # Filtramos chunks demasiado cortos
    chunks_validos = [
        c for c in chunks
        if len(c.get("content", "")) >= MIN_CHARS_CHUNK
    ]
    chunks_descartados = len(chunks) - len(chunks_validos)
    if chunks_descartados:
        logger.info(f"Chunks descartados por longitud mínima: {chunks_descartados}")

    logger.info(f"Procesando {len(chunks_validos)} chunks...")

    batch_actual = []
    total_insertados = 0

    for i, chunk in enumerate(chunks_validos):
        # Generamos el embedding
        vector = generar_embedding(chunk["content"])
        time.sleep(PAUSA_ENTRE_LLAMADAS)

        # Construimos el payload
        payload = construir_payload(chunk, metadatos_territoriales)

        # Creamos el punto de Qdrant
        # Usamos UUID como ID numérico — Qdrant requiere int o UUID
        punto = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=payload,
        )
        batch_actual.append(punto)

        # Subimos cuando el batch está lleno
        if len(batch_actual) >= BATCH_SIZE:
            subir_batch(cliente_qdrant, batch_actual, coleccion)
            total_insertados += len(batch_actual)
            logger.info(f"  Subidos {total_insertados}/{len(chunks_validos)} chunks")
            batch_actual = []

    # Subimos el batch final si tiene puntos
    if batch_actual:
        subir_batch(cliente_qdrant, batch_actual, coleccion)
        total_insertados += len(batch_actual)

    logger.info(f"Carga completada: {total_insertados} puntos en Qdrant")
    return total_insertados


def embeber_desde_json(
    ruta_chunks: Path | str,
    metadatos_extra: Optional[dict] = None,
    coleccion: str = QDRANT_COLLECTION,
) -> int:
    """
    Carga un JSON de chunks y los embebe en Qdrant.

    Args:
        ruta_chunks:    Ruta al JSON de chunks (de chunker.py)
        metadatos_extra: Metadatos territoriales para sobreescribir los inferidos
        coleccion:      Nombre de la colección en Qdrant

    Returns:
        Número de puntos insertados
    """
    ruta_chunks = Path(ruta_chunks)

    with open(ruta_chunks, encoding="utf-8") as f:
        chunks = json.load(f)

    logger.info(f"Cargados {len(chunks)} chunks desde {ruta_chunks.name}")
    return embeber_y_cargar(chunks, metadatos_extra, coleccion)


# ════════════════════════════════════════════════════════════════════════════
# TEST BLOCK
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Embebe los chunks disponibles en data/processed/ y los carga en Qdrant.

    Requisitos para ejecutar:
      1. Qdrant corriendo: docker compose up -d
      2. GOOGLE_API_KEY definida en .env
      3. Chunks generados: python ingestion/chunker.py

    Uso:
        # Procesar todos los chunks disponibles:
        python ingestion/embedder.py

        # Procesar un archivo específico con metadatos manuales:
        python ingestion/embedder.py data/processed/mi_archivo_chunks.json

        # Sobreescribir metadatos territoriales (útil para otros territorios):
        # Edita la variable METADATOS_OVERRIDE más abajo
    """
    import sys

    # ── Metadatos opcionales para sobreescribir los inferidos ───────────
    # Descomenta y edita si necesitas especificar territorio manualmente:
    # METADATOS_OVERRIDE = {
    #     "año":               2026,
    #     "nivel_territorial": "comunidad",
    #     "ambito":            "autonomico",
    #     "comunidad":         "Cataluña",
    #     "codigo_ine":        "09",
    #     "doc_type":          "articulado",
    # }
    METADATOS_OVERRIDE = None

    if len(sys.argv) > 1:
        archivos = [Path(sys.argv[1])]
    else:
        archivos = sorted(PROCESSED_DIR.glob("*_chunks.json"))

    if not archivos:
        print(f"No se encontraron archivos de chunks en {PROCESSED_DIR}")
        print("Ejecuta primero: python ingestion/chunker.py")
        sys.exit(1)

    total_global = 0
    for ruta in archivos:
        print(f"\n{'='*60}")
        print(f"Procesando: {ruta.name}")
        print(f"{'='*60}")

        insertados = embeber_desde_json(
            ruta,
            metadatos_extra=METADATOS_OVERRIDE,
        )
        total_global += insertados

    print(f"\nTotal insertado en Qdrant: {total_global} puntos")
    print(f"Dashboard para verificar: http://localhost:6333/dashboard")

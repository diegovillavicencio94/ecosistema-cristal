"""
retriever.py — Búsqueda semántica en Qdrant para el RAG.

Qué hace:
  - Convierte la pregunta del usuario en un embedding (mismo modelo que el indexador)
  - Busca en Qdrant los chunks más similares semánticamente
  - Devuelve los resultados como dicts limpios con texto + metadatos

Por qué este orden importa:
  El retriever es el primer paso del RAG. La calidad de las respuestas
  del LLM depende directamente de qué chunks recuperamos aquí.
  Un retriever que devuelve chunks irrelevantes → respuestas incorrectas,
  aunque el LLM sea excelente.

Flujo:
  pregunta (str)
    → embedding de la pregunta (mismo modelo que al indexar)
    → búsqueda por similitud coseno en Qdrant
    → top-K chunks ordenados por relevancia
    → lista de dicts {content, source, page, score, ...}
"""

import logging
import time
from typing import Optional

from google import genai
from google.genai import types as genai_types
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, Range

import sys
from pathlib import Path

# Añadimos la raíz del proyecto al path para poder importar config
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import (
    GOOGLE_API_KEY,
    EMBEDDING_MODEL,
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_COLLECTION,
    TOP_K_RESULTS,
)

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Dimensiones del modelo — debe coincidir exactamente con lo usado en embedder.py
# Si cambia el modelo, cambia este valor y hay que reindexar todos los documentos
EMBEDDING_DIM = 3072


# ════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN DE CLIENTES (singleton)
# ════════════════════════════════════════════════════════════════════════════

# Guardamos los clientes como variables de módulo para no reconectarlos
# en cada llamada. Es el patrón "singleton ligero" — una única instancia
# compartida por toda la sesión.
_gemini_client: Optional[genai.Client] = None
_qdrant_client: Optional[QdrantClient] = None


def _get_gemini() -> genai.Client:
    """
    Devuelve el cliente de Gemini, inicializándolo si es la primera vez.
    Usamos v1beta porque los modelos de embedding de Gemini solo están
    disponibles en esa versión de la API.
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(api_version="v1beta"),
        )
        logger.info(f"Cliente Gemini inicializado. Modelo: {EMBEDDING_MODEL}")
    return _gemini_client


def _get_qdrant() -> QdrantClient:
    """Devuelve el cliente de Qdrant, inicializándolo si es la primera vez."""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        logger.info(f"Cliente Qdrant inicializado en {QDRANT_HOST}:{QDRANT_PORT}")
    return _qdrant_client


# ════════════════════════════════════════════════════════════════════════════
# EMBEDDING DE LA CONSULTA
# ════════════════════════════════════════════════════════════════════════════

def embeber_consulta(pregunta: str, reintentos: int = 3) -> list[float]:
    """
    Convierte la pregunta del usuario en un vector de 3072 dimensiones.

    CRÍTICO: usamos task_type="retrieval_query" aquí, no "retrieval_document".
    Gemini tiene dos modos de embedding:
      - retrieval_document: para indexar fragmentos de documentos (embedder.py)
      - retrieval_query:    para convertir preguntas en vectores de búsqueda

    Usar el modo correcto mejora la calidad de recuperación porque el modelo
    optimiza el vector de forma distinta según si es un documento o una consulta.

    Args:
        pregunta:   Texto de la pregunta del usuario
        reintentos: Intentos antes de fallar (con backoff exponencial)

    Returns:
        Vector de 3072 floats
    """
    for intento in range(reintentos):
        try:
            cliente = _get_gemini()
            resultado = cliente.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=pregunta,
                config=genai_types.EmbedContentConfig(
                    task_type="retrieval_query",  # ← distinto del indexador
                ),
            )
            return resultado.embeddings[0].values

        except Exception as e:
            if intento < reintentos - 1:
                espera = 2 ** intento  # 1s, 2s, 4s
                logger.warning(
                    f"Error al embeber consulta (intento {intento+1}): {e}. "
                    f"Reintentando en {espera}s..."
                )
                time.sleep(espera)
            else:
                logger.error(f"Fallo definitivo al embeber consulta: {e}")
                raise


# ════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE FILTROS
# ════════════════════════════════════════════════════════════════════════════

def construir_filtro(
    año: Optional[int] = None,
    comunidad: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    tipo_chunk: Optional[str] = None,
) -> Optional[Filter]:
    """
    Construye un filtro de Qdrant para combinar búsqueda semántica con
    restricciones sobre los metadatos del payload.

    Analogía: es como buscar en Google pero añadiendo "site:madrid.org" o
    "before:2026". El vector encuentra lo más similar, el filtro restringe
    dentro de qué documentos buscar.

    Ejemplos de uso:
      - Solo presupuestos de 2026: año=2026
      - Solo documentos de Madrid: comunidad="Madrid"
      - Solo tablas (para preguntas de importes): tipo_chunk="table"
      - Combinados: año=2026, comunidad="Madrid"

    En el MVP no usamos filtros (devuelve None → búsqueda sin restricciones).
    Los parámetros están listos para cuando la interfaz Streamlit los exponga.

    Returns:
        Objeto Filter de Qdrant, o None si no hay restricciones
    """
    condiciones = []

    if año is not None:
        condiciones.append(
            FieldCondition(key="año", match=MatchValue(value=año))
        )

    if comunidad is not None:
        condiciones.append(
            FieldCondition(key="comunidad", match=MatchValue(value=comunidad))
        )

    if tipo_doc is not None:
        # tipo_doc: "folleto", "articulado", "memoria", "otro"
        condiciones.append(
            FieldCondition(key="doc_type", match=MatchValue(value=tipo_doc))
        )

    if tipo_chunk is not None:
        # tipo_chunk: "text" o "table"
        condiciones.append(
            FieldCondition(key="type", match=MatchValue(value=tipo_chunk))
        )

    if not condiciones:
        return None  # Sin filtros → búsqueda en toda la colección

    # must = todas las condiciones deben cumplirse (AND lógico)
    return Filter(must=condiciones)


# ════════════════════════════════════════════════════════════════════════════
# BÚSQUEDA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

def buscar(
    pregunta: str,
    top_k: int = TOP_K_RESULTS,
    año: Optional[int] = None,
    comunidad: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    tipo_chunk: Optional[str] = None,
    score_minimo: float = 0.0,
) -> list[dict]:
    """
    Función principal del retriever. Busca los chunks más relevantes para
    una pregunta dada.

    Args:
        pregunta:    Pregunta en lenguaje natural del usuario
        top_k:       Número máximo de chunks a devolver (default: TOP_K_RESULTS de config)
        año:         Filtrar por año presupuestario (ej. 2026)
        comunidad:   Filtrar por comunidad autónoma (ej. "Madrid")
        tipo_doc:    Filtrar por tipo de documento ("folleto", "articulado", etc.)
        tipo_chunk:  Filtrar por tipo de chunk ("text" o "table")
        score_minimo: Descartar resultados con similitud menor a este umbral
                     0.0 = sin umbral (devuelve siempre top_k resultados)
                     0.7 = solo resultados muy relevantes (más restrictivo)

    Returns:
        Lista de dicts ordenados por relevancia (mayor score primero):
        [
          {
            "content":    "texto del chunk",
            "source":     "folleto_presupuestos_2026.pdf",
            "page":       8,
            "type":       "table",
            "score":      0.87,
            "chunk_id":   "folleto_presupuestos_2026_p8_t0_c0",
            "año":        2026,
            "comunidad":  "Madrid",
            "doc_type":   "folleto",
            "organismo":  "Sanidad",
          },
          ...
        ]
    """
    logger.info(f"Buscando: '{pregunta[:80]}...' | top_k={top_k}")

    # 1. Convertimos la pregunta en vector
    vector_consulta = embeber_consulta(pregunta)

    # 2. Construimos el filtro (None si no hay restricciones)
    filtro = construir_filtro(año, comunidad, tipo_doc, tipo_chunk)
    if filtro:
        logger.info(f"  Filtros activos: año={año}, comunidad={comunidad}, "
                    f"tipo_doc={tipo_doc}, tipo_chunk={tipo_chunk}")

    # 3. Buscamos en Qdrant
    # Nota: qdrant-client >= 1.12 usa query_points() en lugar de search()
    cliente = _get_qdrant()
    respuesta = cliente.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector_consulta,
        limit=top_k,
        query_filter=filtro,
        with_payload=True,   # incluimos el payload completo (texto + metadatos)
        with_vectors=False,  # no necesitamos los vectores en la respuesta
    )
    resultados_raw = respuesta.points  # query_points devuelve un objeto con .points

    # 4. Convertimos los objetos de Qdrant a dicts limpios
    # El resto del código (chain, interfaz) no sabe nada de Qdrant
    resultados = []
    for hit in resultados_raw:
        score = hit.score

        # Filtramos por score mínimo si se especificó
        if score < score_minimo:
            continue

        payload = hit.payload or {}
        resultados.append({
            # Contenido principal
            "content":   payload.get("content", ""),
            # Metadatos de trazabilidad (para citar la fuente)
            "source":    payload.get("source", ""),
            "page":      payload.get("page"),
            "type":      payload.get("type", "text"),
            "chunk_id":  payload.get("chunk_id", ""),
            # Score de similitud coseno (0.0 = nada similar, 1.0 = idéntico)
            "score":     round(score, 4),
            # Metadatos territoriales y documentales
            "año":       payload.get("año"),
            "comunidad": payload.get("comunidad"),
            "doc_type":  payload.get("doc_type"),
            "organismo": payload.get("organismo"),
        })

    logger.info(f"  Recuperados {len(resultados)} chunks "
                f"(scores: {[r['score'] for r in resultados]})")

    return resultados


# ════════════════════════════════════════════════════════════════════════════
# UTILIDADES DE DIAGNÓSTICO
# ════════════════════════════════════════════════════════════════════════════

def info_coleccion() -> dict:
    """
    Devuelve información sobre la colección de Qdrant.
    Útil para verificar que la colección existe y tiene datos.
    """
    cliente = _get_qdrant()
    info = cliente.get_collection(QDRANT_COLLECTION)
    return {
        "nombre":        QDRANT_COLLECTION,
        "total_puntos":  info.points_count,
        "dimensiones":   info.config.params.vectors.size,
        "distancia":     info.config.params.vectors.distance.name,
    }


# ════════════════════════════════════════════════════════════════════════════
# TEST BLOCK
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Test del retriever contra la colección en Qdrant.

    Requisitos:
      - Qdrant corriendo: docker compose up -d
      - Colección indexada (embedder.py ejecutado)
      - GOOGLE_API_KEY en .env

    Uso:
        python rag/retriever.py
        python rag/retriever.py "¿Cuánto se gasta en sanidad?"
    """
    import sys

    # ── 1. Verificar que la colección existe y tiene datos ───────────────
    print("\n── Estado de Qdrant ──")
    try:
        info = info_coleccion()
        print(f"  Colección:   {info['nombre']}")
        print(f"  Puntos:      {info['total_puntos']}")
        print(f"  Dimensiones: {info['dimensiones']}")
        print(f"  Distancia:   {info['distancia']}")

        if info["total_puntos"] == 0:
            print("\nATENCIÓN: La colección está vacía. Ejecuta embedder.py primero.")
            sys.exit(1)

        if info["dimensiones"] != EMBEDDING_DIM:
            print(f"\nATENCIÓN: Dimensiones incorrectas. "
                  f"Esperadas: {EMBEDDING_DIM}, en Qdrant: {info['dimensiones']}")
            sys.exit(1)

    except Exception as e:
        print(f"\nError al conectar con Qdrant: {e}")
        print("¿Está corriendo Docker? Ejecuta: docker compose up -d")
        sys.exit(1)

    # ── 2. Preguntas de test ─────────────────────────────────────────────
    if len(sys.argv) > 1:
        preguntas = [" ".join(sys.argv[1:])]
    else:
        # Batería de preguntas que cubren distintos tipos de contenido
        preguntas = [
            "¿Cuánto se gasta en sanidad en el presupuesto de Madrid?",
            "¿Qué es el capítulo 1 de gastos de personal?",
            "¿Cuál es el total de ingresos previstos para 2026?",
            "¿Cuánto destina la Comunidad de Madrid a educación?",
        ]

    for pregunta in preguntas:
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {pregunta}")
        print(f"{'='*60}")

        resultados = buscar(pregunta, top_k=3)

        for i, r in enumerate(resultados, 1):
            print(f"\n── Resultado {i} (score: {r['score']}) ──")
            print(f"  Fuente:    {r['source']} · pág. {r['page']}")
            print(f"  Tipo:      {r['type']}")
            print(f"  Organismo: {r['organismo'] or 'N/A'}")
            print(f"  Contenido:")
            # Mostramos los primeros 300 chars del contenido
            contenido_preview = r["content"][:300].replace("\n", " ")
            print(f"    {contenido_preview}...")

    # ── 3. Test con filtro (opcional) ────────────────────────────────────
    print(f"\n{'='*60}")
    print("TEST CON FILTRO: solo tablas de 2026")
    print(f"{'='*60}")

    resultados_filtrados = buscar(
        "gasto total por consejería",
        top_k=3,
        año=2026,
        tipo_chunk="table",
    )

    for i, r in enumerate(resultados_filtrados, 1):
        print(f"\n── Resultado {i} (score: {r['score']}) ──")
        print(f"  Fuente: {r['source']} · pág. {r['page']}")
        print(f"  Año:    {r['año']}")
        print(f"  Contenido (primeras 3 líneas):")
        for linea in r["content"].split("\n")[:3]:
            print(f"    {linea}")

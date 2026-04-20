"""
retriever.py — Búsqueda semántica en Qdrant para el RAG.
"""

import logging
import time
from typing import Optional

from google import genai
from google.genai import types as genai_types
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

import sys
from pathlib import Path

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EMBEDDING_DIM = 3072

_gemini_client: Optional[genai.Client] = None
_qdrant_client: Optional[QdrantClient] = None


def _get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(api_version="v1beta"),
        )
        logger.info(f"Cliente Gemini inicializado. Modelo: {EMBEDDING_MODEL}")
    return _gemini_client


def _get_qdrant() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        # Qdrant local — sin API key
        _qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        logger.info(f"Cliente Qdrant inicializado en {QDRANT_HOST}:{QDRANT_PORT}")
    return _qdrant_client


def embeber_consulta(pregunta: str, reintentos: int = 3) -> list[float]:
    for intento in range(reintentos):
        try:
            cliente = _get_gemini()
            resultado = cliente.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=pregunta,
                config=genai_types.EmbedContentConfig(task_type="retrieval_query"),
            )
            return resultado.embeddings[0].values
        except Exception as e:
            if intento < reintentos - 1:
                espera = 2 ** intento
                logger.warning(f"Error embedding (intento {intento+1}): {e}. Reintentando en {espera}s...")
                time.sleep(espera)
            else:
                raise


def construir_filtro(
    año: Optional[int] = None,
    comunidad: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    tipo_chunk: Optional[str] = None,
) -> Optional[Filter]:
    condiciones = []
    if año is not None:
        condiciones.append(FieldCondition(key="año", match=MatchValue(value=año)))
    if comunidad is not None:
        condiciones.append(FieldCondition(key="comunidad", match=MatchValue(value=comunidad)))
    if tipo_doc is not None:
        condiciones.append(FieldCondition(key="doc_type", match=MatchValue(value=tipo_doc)))
    if tipo_chunk is not None:
        condiciones.append(FieldCondition(key="type", match=MatchValue(value=tipo_chunk)))
    return Filter(must=condiciones) if condiciones else None


def buscar(
    pregunta: str,
    top_k: int = TOP_K_RESULTS,
    año: Optional[int] = None,
    comunidad: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    tipo_chunk: Optional[str] = None,
    score_minimo: float = 0.0,
) -> list[dict]:
    logger.info(f"Buscando: '{pregunta[:80]}' | top_k={top_k}")

    vector_consulta = embeber_consulta(pregunta)
    filtro = construir_filtro(año, comunidad, tipo_doc, tipo_chunk)

    cliente = _get_qdrant()
    respuesta = cliente.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector_consulta,
        limit=top_k,
        query_filter=filtro,
        with_payload=True,
        with_vectors=False,
    )

    resultados = []
    for hit in respuesta.points:
        if hit.score < score_minimo:
            continue
        payload = hit.payload or {}
        resultados.append({
            "content":   payload.get("content", ""),
            "source":    payload.get("source", ""),
            "page":      payload.get("page"),
            "type":      payload.get("type", "text"),
            "chunk_id":  payload.get("chunk_id", ""),
            "score":     round(hit.score, 4),
            "año":       payload.get("año"),
            "comunidad": payload.get("comunidad"),
            "doc_type":  payload.get("doc_type"),
            "organismo": payload.get("organismo"),
        })

    logger.info(f"Recuperados {len(resultados)} chunks")
    return resultados


def info_coleccion() -> dict:
    cliente = _get_qdrant()
    info = cliente.get_collection(QDRANT_COLLECTION)
    return {
        "nombre":       QDRANT_COLLECTION,
        "total_puntos": info.points_count,
        "dimensiones":  info.config.params.vectors.size,
        "distancia":    info.config.params.vectors.distance.name,
    }


if __name__ == "__main__":
    print("\n── Estado de Qdrant ──")
    try:
        info = info_coleccion()
        print(f"  Colección:   {info['nombre']}")
        print(f"  Puntos:      {info['total_puntos']}")
        print(f"  Dimensiones: {info['dimensiones']}")
    except Exception as e:
        print(f"Error al conectar con Qdrant: {e}")
        print("¿Está corriendo Docker? Ejecuta: docker-compose up -d")
        sys.exit(1)

    preguntas = ["¿Cuánto se gasta en sanidad en el presupuesto de Madrid?"]
    for pregunta in preguntas:
        print(f"\nPREGUNTA: {pregunta}")
        resultados = buscar(pregunta, top_k=3)
        for i, r in enumerate(resultados, 1):
            print(f"\n── Resultado {i} (score: {r['score']}) ──")
            print(f"  Fuente: {r['source']} · pág. {r['page']} · tipo: {r['type']}")
            print(f"  {r['content'][:200]}...")

"""
chain.py — Cadena RAG completa: pregunta → retriever → llm → respuesta.

Qué hace:
  - Orquesta la secuencia completa del RAG en una sola función
  - Expone una interfaz limpia que usan pipeline.py y app.py
  - Añade logging de trazabilidad para ver qué chunks se usaron

Por qué existe separado de retriever.py y llm.py:
  retriever.py sabe buscar. llm.py sabe generar. chain.py sabe
  en qué orden llamar a cada uno y cómo pasarles los datos.
  Separar responsabilidades facilita testear cada pieza por separado
  y cambiar una sin afectar a las otras.

Flujo completo:
  pregunta (str)
    → retriever.buscar()       → chunks relevantes
    → llm.generar_respuesta()  → texto en lenguaje ciudadano
    → RespuestaRAG             → respuesta + fuentes + metadatos
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Importamos los módulos que ya tenemos construidos y testeados
from rag.retriever import buscar
from rag.llm import generar_respuesta

from config import TOP_K_RESULTS

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# ESTRUCTURA DE RESPUESTA
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class RespuestaRAG:
    """
    Estructura de datos que devuelve el chain.

    Usamos un dataclass (en lugar de un dict) para que el resto del código
    acceda a los campos con autocompletado y sin riesgo de typos en las keys.

    Campos:
        pregunta:    La pregunta original del usuario
        respuesta:   Texto generado por el LLM en lenguaje ciudadano
        chunks:      Los fragmentos recuperados de Qdrant (para trazabilidad)
        fuentes:     Lista deduplicada de (documento, página) usados
        sin_contexto: True si el retriever no encontró nada relevante
    """
    pregunta:     str
    respuesta:    str
    chunks:       list[dict] = field(default_factory=list)
    fuentes:      list[dict] = field(default_factory=list)
    sin_contexto: bool = False


# ════════════════════════════════════════════════════════════════════════════
# UTILIDADES
# ════════════════════════════════════════════════════════════════════════════

def extraer_fuentes(chunks: list[dict]) -> list[dict]:
    """
    Construye una lista deduplicada de fuentes a partir de los chunks.

    Si el mismo documento aparece en varios chunks, lo listamos una sola vez.
    El LLM ya cita las páginas en el texto; esta lista es para la interfaz
    (Streamlit puede mostrarla como referencias al pie).

    Returns:
        Lista de dicts únicos: [{source, page, doc_type, año}, ...]
        ordenados por documento y página
    """
    vistas = set()
    fuentes = []

    for chunk in chunks:
        clave = (chunk.get("source", ""), chunk.get("page"))
        if clave not in vistas:
            vistas.add(clave)
            fuentes.append({
                "source":   chunk.get("source", ""),
                "page":     chunk.get("page"),
                "doc_type": chunk.get("doc_type"),
                "año":      chunk.get("año"),
            })

    # Ordenamos por nombre de fuente y luego por página
    fuentes.sort(key=lambda f: (f["source"], f["page"] or 0))
    return fuentes


# ════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════

def preguntar(
    pregunta: str,
    top_k: int = TOP_K_RESULTS,
    año: Optional[int] = None,
    comunidad: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    tipo_chunk: Optional[str] = None,
    score_minimo: float = 0.0,
) -> RespuestaRAG:
    """
    Función principal del RAG. Recibe una pregunta y devuelve una respuesta
    con fuentes citadas.

    Es la única función que necesitan conocer pipeline.py y app.py.

    Args:
        pregunta:     Pregunta en lenguaje natural
        top_k:        Número de chunks a recuperar (default: config TOP_K_RESULTS)
        año:          Filtrar por año presupuestario
        comunidad:    Filtrar por comunidad autónoma
        tipo_doc:     Filtrar por tipo de documento
        tipo_chunk:   Filtrar por tipo de chunk ("text" o "table")
        score_minimo: Umbral mínimo de similitud (0.0 = sin umbral)

    Returns:
        RespuestaRAG con respuesta, chunks usados y fuentes
    """
    logger.info(f"[RAG] Pregunta: '{pregunta}'")

    # ── Paso 1: Recuperar chunks relevantes ─────────────────────────────
    chunks = buscar(
        pregunta=pregunta,
        top_k=top_k,
        año=año,
        comunidad=comunidad,
        tipo_doc=tipo_doc,
        tipo_chunk=tipo_chunk,
        score_minimo=score_minimo,
    )

    if not chunks:
        logger.warning("[RAG] No se encontraron chunks relevantes")
        return RespuestaRAG(
            pregunta=pregunta,
            respuesta=(
                "No encontré información relevante en los documentos disponibles. "
                "Prueba a reformular la pregunta o a ser más específico."
            ),
            chunks=[],
            fuentes=[],
            sin_contexto=True,
        )

    logger.info(
        f"[RAG] {len(chunks)} chunks recuperados | "
        f"scores: {[c['score'] for c in chunks]}"
    )

    # ── Paso 2: Generar respuesta con el LLM ────────────────────────────
    respuesta = generar_respuesta(
        pregunta=pregunta,
        chunks=chunks,
    )

    # ── Paso 3: Extraer fuentes para la interfaz ─────────────────────────
    fuentes = extraer_fuentes(chunks)

    logger.info(f"[RAG] Respuesta generada ({len(respuesta)} chars) | {len(fuentes)} fuentes")

    return RespuestaRAG(
        pregunta=pregunta,
        respuesta=respuesta,
        chunks=chunks,
        fuentes=fuentes,
        sin_contexto=False,
    )


# ════════════════════════════════════════════════════════════════════════════
# TEST BLOCK
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Test de integración completo: pregunta → Qdrant → Gemini → respuesta.

    Este es el test más importante hasta ahora — conecta todo el pipeline
    RAG por primera vez con datos reales.

    Requisitos:
      - Qdrant corriendo: docker compose up -d
      - Colección indexada (embedder.py ejecutado)
      - GOOGLE_API_KEY en .env con gemini-2.5-flash disponible

    Uso:
        python rag/chain.py
        python rag/chain.py "¿Cuánto se gasta en educación en 2026?"
    """
    import sys

    if len(sys.argv) > 1:
        preguntas = [" ".join(sys.argv[1:])]
    else:
        preguntas = [
            "¿Cuánto se gasta en sanidad en el presupuesto de Madrid para 2026?",
            "¿Qué es el capítulo 1 de gastos de personal y cuánto supone?",
            "¿Cuáles son los ingresos totales previstos para 2026?",
        ]

    for pregunta in preguntas:
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {pregunta}")
        print(f"{'='*60}")

        resultado = preguntar(pregunta)

        print(f"\nRESPUESTA:")
        print(resultado.respuesta)

        print(f"\nCHUNKS USADOS ({len(resultado.chunks)}):")
        for i, chunk in enumerate(resultado.chunks, 1):
            print(
                f"  {i}. [{chunk['type']}] {chunk['source']} · "
                f"pág. {chunk['page']} · score {chunk['score']}"
            )

        print(f"\nFUENTES ÚNICAS ({len(resultado.fuentes)}):")
        for f in resultado.fuentes:
            print(f"  - {f['source']} · pág. {f['page']} ({f['doc_type']}, {f['año']})")

        print(f"\nSin contexto: {resultado.sin_contexto}")

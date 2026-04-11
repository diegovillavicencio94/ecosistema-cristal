"""
interface/api.py — FastAPI REST backend para el Ecosistema de Cristal.

Uso:
    uvicorn interface.api:app --reload --port 8000
"""

import sys
import json
import numpy as np
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

UMAP_CACHE_PATH = ROOT_DIR / "data" / "processed" / "umap_cache.json"

app = FastAPI(title="Ecosistema de Cristal — API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Modelos request/response ─────────────────────────────────────────────────

class PreguntaRequest(BaseModel):
    pregunta: str
    top_k: int = 5
    año: Optional[int] = None
    comunidad: Optional[str] = None
    tipo_doc: Optional[str] = None


class ChunkResponse(BaseModel):
    content: str
    source: str
    page: Optional[int] = None
    type: str = "text"
    score: float = 0.0
    chunk_id: str = ""
    año: Optional[int] = None
    comunidad: Optional[str] = None
    doc_type: Optional[str] = None
    organismo: Optional[str] = None


class FuenteResponse(BaseModel):
    source: str
    page: Optional[int] = None
    doc_type: Optional[str] = None
    año: Optional[int] = None


class RespuestaResponse(BaseModel):
    pregunta: str
    respuesta: str
    chunks: list[ChunkResponse]
    fuentes: list[FuenteResponse]
    sin_contexto: bool


class ChunkItem(BaseModel):
    """Un punto de Qdrant sin su vector — solo payload + id."""
    chunk_id: str
    source: str
    page: Optional[int] = None
    type: str = "text"
    content: str = ""
    año: Optional[int] = None
    doc_type: Optional[str] = None
    organismo: Optional[str] = None
    nivel_territorial: Optional[str] = None
    ambito: Optional[str] = None


class UMAPPoint(BaseModel):
    chunk_id: str
    x: float
    y: float
    z: float          # ← añadido
    source: str
    doc_type: Optional[str] = None
    año: Optional[int] = None
    type: str = "text"
    content_preview: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_qdrant():
    from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
    from qdrant_client import QdrantClient
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT), QDRANT_COLLECTION


def _payload_to_chunk_item(point_id, payload: dict) -> ChunkItem:
    return ChunkItem(
        chunk_id=payload.get("chunk_id", str(point_id)),
        source=payload.get("source", ""),
        page=payload.get("page"),
        type=payload.get("type", "text"),
        content=payload.get("content", ""),
        año=payload.get("año"),
        doc_type=payload.get("doc_type"),
        organismo=payload.get("organismo"),
        nivel_territorial=payload.get("nivel_territorial"),
        ambito=payload.get("ambito"),
    )


# ─── Endpoints existentes ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    try:
        cliente, coleccion = _get_qdrant()
        info = cliente.get_collection(coleccion)
        return {
            "qdrant": "ok",
            "coleccion": coleccion,
            "puntos": info.points_count,
            "dimensiones": info.config.params.vectors.size,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/preguntar", response_model=RespuestaResponse)
def preguntar(req: PreguntaRequest):
    try:
        from rag.chain import preguntar as chain_preguntar
        resultado = chain_preguntar(
            pregunta=req.pregunta,
            top_k=req.top_k,
            año=req.año,
            comunidad=req.comunidad,
            tipo_doc=req.tipo_doc,
        )

        chunks = [
            ChunkResponse(
                content=c.get("content", ""),
                source=c.get("source", ""),
                page=c.get("page"),
                type=c.get("type", "text"),
                score=c.get("score", 0.0),
                chunk_id=c.get("chunk_id", ""),
                año=c.get("año"),
                comunidad=c.get("comunidad"),
                doc_type=c.get("doc_type"),
                organismo=c.get("organismo"),
            )
            for c in resultado.chunks
        ]

        fuentes = [
            FuenteResponse(
                source=f.get("source", ""),
                page=f.get("page"),
                doc_type=f.get("doc_type"),
                año=f.get("año"),
            )
            for f in resultado.fuentes
        ]

        return RespuestaResponse(
            pregunta=resultado.pregunta,
            respuesta=resultado.respuesta,
            chunks=chunks,
            fuentes=fuentes,
            sin_contexto=resultado.sin_contexto,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Endpoint 3A: /chunks ─────────────────────────────────────────────────────

@app.get("/chunks", response_model=List[ChunkItem])
def get_chunks(
    doc_type: Optional[str] = Query(None, description="Filtrar por tipo: articulado, folleto, resumen"),
    año: Optional[int] = Query(None, description="Filtrar por año: 2025, 2026"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo de contenido: text, table"),
    limit: int = Query(500, ge=1, le=1000, description="Máximo de chunks a devolver"),
):
    """
    Devuelve todos los chunks indexados en Qdrant (sin vectores).
    Permite filtrar por doc_type, año y tipo de contenido.
    Usado por el módulo 'El Archivo'.
    """
    try:
        cliente, coleccion = _get_qdrant()

        # scroll() recupera puntos sin necesidad de vector de consulta,
        # al contrario que search(). Ideal para listar el catálogo completo.
        # with_payload=True → queremos los metadatos
        # with_vectors=False → ahorramos ancho de banda (cada vector pesa ~24KB a 3072 dims)
        resultado, _ = cliente.scroll(
            collection_name=coleccion,
            with_payload=True,
            with_vectors=False,
            limit=limit,
        )

        chunks = [_payload_to_chunk_item(p.id, p.payload or {}) for p in resultado]

        # Filtrado en Python (más simple que construir filtros Qdrant para este volumen)
        if doc_type:
            chunks = [c for c in chunks if c.doc_type == doc_type]
        if año:
            chunks = [c for c in chunks if c.año == año]
        if tipo:
            chunks = [c for c in chunks if c.type == tipo]

        return chunks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Endpoint 3B: /umap ───────────────────────────────────────────────────────

@app.get("/umap", response_model=List[UMAPPoint])
def get_umap(recalcular: bool = Query(False, description="Forzar recálculo ignorando caché")):
    """
    Devuelve las coordenadas UMAP 2D de todos los chunks.
    
    Primera llamada: recupera vectores de Qdrant, reduce con UMAP, 
    guarda en data/processed/umap_cache.json.
    Llamadas siguientes: sirve la caché directamente (< 10ms).
    
    Forzar recálculo: GET /umap?recalcular=true
    """
    # 1. Servir caché si existe y no se fuerza recálculo
    if not recalcular and UMAP_CACHE_PATH.exists():
        try:
            with open(UMAP_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # caché corrupta → recalculamos

    # 2. Recuperar vectores de Qdrant
    try:
        cliente, coleccion = _get_qdrant()

        # with_vectors=True → necesitamos los embeddings para reducir
        resultado, _ = cliente.scroll(
            collection_name=coleccion,
            with_payload=True,
            with_vectors=True,
            limit=2000,  # más que suficiente para nuestro dataset
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error Qdrant: {e}")

    if not resultado:
        raise HTTPException(status_code=404, detail="No hay puntos en la colección")

    # 3. Extraer matrices y metadata
    vectores = []
    payloads = []
    ids = []

    for punto in resultado:
        if punto.vector is None:
            continue
        # punto.vector puede ser list o dict (named vectors) → normalizamos a list
        vec = punto.vector if isinstance(punto.vector, list) else list(punto.vector.values())[0]
        vectores.append(vec)
        payloads.append(punto.payload or {})
        ids.append(punto.id)

    if len(vectores) < 2:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 2 puntos para UMAP")

    # 4. Reducción UMAP 3072 → 2 dimensiones
    try:
        import umap  # umap-learn
        reducer = umap.UMAP(
    n_components=3,       # ← 2 → 3
    n_neighbors=15,
    min_dist=0.1,
    metric="cosine",
    random_state=42,
        )
        coords = reducer.fit_transform(np.array(vectores))
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="umap-learn no instalado. Ejecuta: pip install umap-learn"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error UMAP: {e}")

    # 5. Construir respuesta
    puntos_umap = []
    for i, (payload, coord) in enumerate(zip(payloads, coords)):
        content = payload.get("content", "")
        puntos_umap.append(UMAPPoint(
    chunk_id=payload.get("chunk_id", str(ids[i])),
    x=float(coord[0]),
    y=float(coord[1]),
    z=float(coord[2]),    # ← añadido
    source=payload.get("source", ""),
    doc_type=payload.get("doc_type"),
    año=payload.get("año"),
    type=payload.get("type", "text"),
    content_preview=content[:200] + ("…" if len(content) > 200 else ""),
))

    # 6. Guardar caché
    try:
        UMAP_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(UMAP_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in puntos_umap], f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Si falla el guardado no es fatal, devolvemos igualmente
        print(f"[WARN] No se pudo guardar caché UMAP: {e}")

    return puntos_umap
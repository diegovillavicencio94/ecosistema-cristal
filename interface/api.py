"""
interface/api.py — FastAPI REST backend para el Ecosistema de Cristal.

Uso:
    uvicorn interface.api:app --reload --port 8000
"""

import sys
import json
import numpy as np
from pathlib import Path
from typing import Optional, List, Any

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


# ─── Modelos ──────────────────────────────────────────────────────────────────

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
    datos_grafico: Optional[Any] = None  # dict con estructura Recharts o null


class ChunkItem(BaseModel):
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
    z: float
    source: str
    doc_type: Optional[str] = None
    año: Optional[int] = None
    type: str = "text"
    content_preview: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_qdrant():
    from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION
    from qdrant_client import QdrantClient
    # Qdrant local — sin API key
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


# ─── Endpoints ────────────────────────────────────────────────────────────────

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
            datos_grafico=resultado.datos_grafico,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chunks", response_model=List[ChunkItem])
def get_chunks(
    doc_type: Optional[str] = Query(None),
    año: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
):
    try:
        cliente, coleccion = _get_qdrant()
        resultado, _ = cliente.scroll(
            collection_name=coleccion,
            with_payload=True,
            with_vectors=False,
            limit=limit,
        )
        chunks = [_payload_to_chunk_item(p.id, p.payload or {}) for p in resultado]
        if doc_type:
            chunks = [c for c in chunks if c.doc_type == doc_type]
        if año:
            chunks = [c for c in chunks if c.año == año]
        if tipo:
            chunks = [c for c in chunks if c.type == tipo]
        return chunks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/umap", response_model=List[UMAPPoint])
def get_umap(recalcular: bool = Query(False)):
    if not recalcular and UMAP_CACHE_PATH.exists():
        try:
            with open(UMAP_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    try:
        cliente, coleccion = _get_qdrant()
        resultado, _ = cliente.scroll(
            collection_name=coleccion,
            with_payload=True,
            with_vectors=True,
            limit=2000,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error Qdrant: {e}")

    if not resultado:
        raise HTTPException(status_code=404, detail="No hay puntos en la colección")

    vectores, payloads, ids = [], [], []
    for punto in resultado:
        if punto.vector is None:
            continue
        vec = punto.vector if isinstance(punto.vector, list) else list(punto.vector.values())[0]
        vectores.append(vec)
        payloads.append(punto.payload or {})
        ids.append(punto.id)

    if len(vectores) < 2:
        raise HTTPException(status_code=422, detail="Se necesitan al menos 2 puntos para UMAP")

    try:
        import umap
        reducer = umap.UMAP(
            n_components=3, n_neighbors=15,
            min_dist=0.1, metric="cosine", random_state=42,
        )
        coords = reducer.fit_transform(np.array(vectores))
    except ImportError:
        raise HTTPException(status_code=500, detail="umap-learn no instalado. Ejecuta: pip install umap-learn")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error UMAP: {e}")

    puntos_umap = []
    for i, (payload, coord) in enumerate(zip(payloads, coords)):
        content = payload.get("content", "")
        puntos_umap.append(UMAPPoint(
            chunk_id=payload.get("chunk_id", str(ids[i])),
            x=float(coord[0]), y=float(coord[1]), z=float(coord[2]),
            source=payload.get("source", ""),
            doc_type=payload.get("doc_type"),
            año=payload.get("año"),
            type=payload.get("type", "text"),
            content_preview=content[:200] + ("…" if len(content) > 200 else ""),
        ))

    try:
        UMAP_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(UMAP_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump([p.model_dump() for p in puntos_umap], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] No se pudo guardar caché UMAP: {e}")

    return puntos_umap

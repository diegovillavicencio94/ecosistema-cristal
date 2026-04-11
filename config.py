"""
config.py — Configuración central del proyecto.
Carga variables de entorno y expone constantes tipadas.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── Google AI ──────────────────────────────────────────────────────
GOOGLE_API_KEY: str  = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str    = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")

# ─── Qdrant local ───────────────────────────────────────────────────
QDRANT_HOST: str       = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT: int       = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "presupuestos_v1")

# ─── Chunking ───────────────────────────────────────────────────────
CHUNK_SIZE: int    = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

# ─── RAG ────────────────────────────────────────────────────────────
TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))

# ─── Gráficos ───────────────────────────────────────────────────────
# "conservador" → solo tablas con números claros
# "moderado"    → también texto con cifras concretas
# "agresivo"    → intenta graficar siempre que haya datos numéricos
GRAFICO_AGRESIVIDAD: str = os.getenv("GRAFICO_AGRESIVIDAD", "conservador")

# ─── Validación mínima ──────────────────────────────────────────────
if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "GOOGLE_API_KEY no está definida. "
        "Copia .env.example a .env y añade tu clave de Google AI Studio."
    )

# 🔬 Ecosistema de Cristal

Plataforma de transparencia presupuestaria ciudadana impulsada por IA.  
Desarrollada por el **Equipo 1 — AI Challenge · Sprint 2** (Paula · Diego · Klaus · Edgar · Ginés · Mamen).

---

## ¿Qué hace?

**El Guía Experto** — Chatbot RAG que responde preguntas sobre los Presupuestos Generales de la Comunidad de Madrid en lenguaje ciudadano, citando fragmentos de los documentos oficiales.

**El Archivo** — Explorador de todos los fragmentos indexados: filtrable por tipo de documento, año y contenido.

**El Mapa del Conocimiento** — Visualización 3D del espacio vectorial UMAP: muestra cómo el sistema "entiende" semánticamente los documentos.

---

## Stack

| Componente | Herramienta |
|---|---|
| LLM | Gemini 2.5 Flash |
| Embeddings | gemini-embedding-001 (3072 dims) |
| Vector DB | Qdrant (Docker) |
| RAG Framework | LangChain |
| Backend | FastAPI |
| Frontend | React + Framer Motion + Three.js |
| Extracción PDF | pdfplumber |

---

## Requisitos previos

- Python 3.11+
- Node.js 18+
- Docker Desktop corriendo
- Cuenta en [Google AI Studio](https://aistudio.google.com) con facturación activada

---

## Setup paso a paso

### 1. Clonar el repositorio

```bash
git clone https://github.com/diegovillavicencio94/ecosistema-cristal.git
cd ecosistema-cristal
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Abre `.env` y añade tu clave de Google:

```
GOOGLE_API_KEY=tu_clave_aqui
```

Para obtener la clave: [aistudio.google.com](https://aistudio.google.com) → Get API Key.

> ⚠️ **Nunca subas el archivo `.env` a GitHub.** Ya está en `.gitignore`.

### 3. Arrancar Qdrant (base de datos vectorial)

```bash
docker-compose up -d
```

Verifica que está corriendo en: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 4. Instalar dependencias Python

```bash
pip install -r requirements.txt
pip install umap-learn scikit-learn
```

### 5. Indexar los documentos

Coloca los PDFs en `data/raw/` y ejecuta:

```bash
python pipeline.py --ingest
```

Esto extrae, chunka, genera embeddings y carga todo en Qdrant (~309 fragmentos con los 3 PDFs incluidos).

> La primera vez tarda varios minutos por los rate limits de la API de Google.

### 6. Instalar dependencias del frontend

```bash
cd interface/frontend
npm install
cd ../..
```

---

## Ejecutar la aplicación

Necesitas **dos terminales abiertas**:

**Terminal 1 — Backend:**
```bash
uvicorn interface.api:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd interface/frontend
npm start
```

La app abre automáticamente en [http://localhost:3000](http://localhost:3000)

---

## Estructura del proyecto

```
ecosistema-cristal/
├── ingestion/
│   ├── pdf_extractor.py     # pdfplumber → texto + tablas
│   ├── normalizer.py        # limpieza de texto
│   ├── chunker.py           # partición en ~500 tokens
│   └── embedder.py          # Gemini embeddings → Qdrant
├── rag/
│   ├── retriever.py         # búsqueda semántica en Qdrant
│   ├── llm.py               # Gemini LLM wrapper
│   └── chain.py             # cadena RAG completa
├── interface/
│   ├── api.py               # FastAPI backend
│   └── frontend/            # React app
│       └── src/
│           ├── App.js
│           ├── components/
│           └── modules/
│               ├── Archivo/
│               └── Mapa/
├── data/
│   ├── raw/                 # PDFs originales (no en repo)
│   └── processed/           # JSONs intermedios + caché UMAP
├── pipeline.py              # orquestador CLI
├── config.py                # configuración centralizada
├── docker-compose.yml       # Qdrant
├── requirements.txt
└── .env.example             # plantilla de variables de entorno
```

---

## Comandos útiles

```bash
# Ver estado del sistema (Qdrant + fragmentos indexados)
python pipeline.py --status

# Hacer una consulta desde terminal
python pipeline.py --query "¿Cuánto se destina a sanidad en 2026?"

# Indexar un PDF específico
python pipeline.py --ingest data/raw/mi_documento.pdf

# Forzar recálculo del mapa UMAP
curl http://localhost:8000/umap?recalcular=true

# Ver todos los fragmentos indexados (API)
curl http://localhost:8000/chunks | python3 -m json.tool | head -50
```

---

## Solución de problemas frecuentes

| Error | Causa | Solución |
|---|---|---|
| `Connection refused :6333` | Qdrant no está corriendo | `docker-compose up -d` |
| `429 Too Many Requests` | Rate limit de Google API | Esperar 1 min o activar facturación |
| `404 model not found` | Modelo de Gemini incorrecto | Verificar `GEMINI_MODEL` en `.env` |
| `node_modules not found` | Falta instalar dependencias JS | `cd interface/frontend && npm install` |
| Mapa 3D no carga | Caché UMAP corrupta | `rm data/processed/umap_cache.json` y recargar |

---

## Documentación técnica

Ver `DEVLOG.md` para el registro completo de decisiones de arquitectura, problemas encontrados y soluciones por sesión.

# 🔍 Ecosistema de Cristal — Motor RAG (Reto 1)
Chatbot de transparencia presupuestaria · Sprint 2 · AI Challenge

## Stack
| Capa | Herramienta |
|---|---|
| LLM | Gemini 2.0 Flash (Google AI Studio) |
| Embeddings | text-embedding-004 (Google) |
| Vector DB | Qdrant (Docker) |
| RAG Framework | LangChain |
| Extracción PDF | pdfplumber |
| Interfaz | Streamlit |

## Setup inicial

### 1. Clonar y preparar entorno
```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
cp .env.example .env
# Edita .env y añade tu GOOGLE_API_KEY
```

### 3. Arrancar Qdrant
```bash
docker compose up -d
# Dashboard disponible en: http://localhost:6333/dashboard
```

### 4. Cargar documentos (una vez tengas PDFs en data/raw/)
```bash
python pipeline.py --ingest
```

### 5. Lanzar el chat
```bash
# Terminal
python pipeline.py --query "¿Qué es el capítulo 2 de gastos?"

# Streamlit
streamlit run interface/app.py
```

## Estructura
```
ecosistema-cristal/
├── ingestion/
│   ├── pdf_extractor.py   # pdfplumber → texto + tablas
│   ├── normalizer.py      # limpieza de texto
│   ├── chunker.py         # partición en ~500 tokens
│   └── embedder.py        # Gemini embeddings → Qdrant
├── rag/
│   ├── retriever.py       # búsqueda en Qdrant
│   ├── llm.py             # Gemini LLM wrapper
│   └── chain.py           # cadena RAG completa
├── interface/
│   └── app.py             # UI Streamlit
├── data/
│   ├── raw/               # PDFs originales aquí
│   └── processed/         # JSONs intermedios
├── pipeline.py            # orquestador CLI
├── config.py
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Dashboard Qdrant
Una vez Docker esté corriendo: **http://localhost:6333/dashboard**
Desde ahí puedes ver colecciones, vectores y hacer queries manuales.

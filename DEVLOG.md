# DEVLOG — Ecosistema de Cristal

Registro de decisiones técnicas, avances y problemas por sesión.

---

## Sesión 2026-04-10

### Completado
- `docker-compose.yml` — Qdrant con dashboard en localhost:6333/dashboard
- `requirements.txt` — dependencias: google-generativeai, langchain, langchain-google-genai, langchain-qdrant, qdrant-client, pdfplumber, pandas, tiktoken, streamlit, python-dotenv, tqdm
- `config.py` — configuración centralizada con carga desde .env y validación de GOOGLE_API_KEY
- `.env.example` — plantilla con todas las variables necesarias
- `README.md` — instrucciones completas de setup para el proyecto
- `project-setup/SYSTEM_PROMPT.md` — system prompt para Claude Project
- `project-setup/GUIA_DE_TRABAJO.md` — guía de sesiones y comandos útiles

### Decisiones tomadas
- **Gemini 2.0 Flash** como LLM: gratuito via Google AI Studio, sin restricciones de rate para MVP
- **text-embedding-004**: embeddings gratuitos de Google, 768 dimensiones, buen rendimiento en español
- **Qdrant via Docker**: elegido sobre ChromaDB por su dashboard nativo que permite visualizar vectores sin código adicional. Escalable a producción con el mismo contenedor
- **LangChain** como framework RAG: ecosistema más maduro, integración nativa con Gemini y Qdrant, mejor documentación para aprendizaje
- **Construcción un archivo a la vez**: metodología elegida para facilitar el aprendizaje y el debugging incremental

### Problemas encontrados
- Ninguno en esta sesión

### Próximo paso
- `ingestion/pdf_extractor.py` — extracción de texto y tablas desde PDFs con pdfplumber
- Diego debe subir un PDF de prueba (presupuesto público) para testear la extracción en vivo

---

## Sesión 2026-04-10 (continuación)

### Completado
- `ingestion/pdf_extractor.py` — extracción de texto y tablas desde PDFs con pdfplumber

### Decisiones tomadas
- **Separación texto/tablas por página**: texto narrativo y tablas estructuradas se almacenan en campos distintos del JSON. Razón: evitar que los números de las tablas contaminen el texto al chunkar
- **Degradación graciosamente**: si la detección de bounding boxes de tablas falla, el extractor cae a extraer todo el texto sin filtrar en lugar de crashear
- **JSON en data/processed/**: cada PDF genera un JSON con estructura `{source, total_pages, pages[{page, text, tables}]}` — es el contrato de datos entre extractor y normalizer

### Problemas encontrados
- **Celdas fusionadas en articulado**: tablas con celdas fusionadas generan columnas desplazadas y celdas vacías (ej. tabla 2 página 32). pdfplumber las "descomprime" incorrectamente. A corregir en normalizer.py
- 23 tablas detectadas en el articulado vs 39 en el folleto: el articulado es mayoritariamente texto legal con tablas puntuales de dotaciones

### Próximo paso
- `ingestion/normalizer.py` — limpieza de texto (normalización de espacios, caracteres especiales) y corrección de tablas con celdas fusionadas/desplazadas

---

## Sesión 2026-04-11

### Completado
- `ingestion/pdf_extractor.py` — extracción de texto y tablas desde PDFs con pdfplumber
- `ingestion/normalizer.py` — limpieza de texto y tablas sin alterar estructura matricial
- `ingestion/chunker.py` — chunking de texto (~500 tokens con overlap) y tablas (cabecera repetida por chunk)
- `ingestion/embedder.py` — generación de embeddings con Gemini y carga en Qdrant con metadatos completos
- Pipeline de ingesta ejecutado en local con 3 PDFs reales (articulado 2025, folleto 2026, resumen ingresos/gastos 2026)
- Qdrant corriendo en Docker con colección `presupuestos_v1` (3072 dims, coseno)

### Decisiones tomadas
- **gemini-embedding-001** en lugar de text-embedding-004: único modelo de embedding disponible en la cuenta de Google AI Studio. 3072 dimensiones en lugar de 768
- **Conservar estructura matricial en tablas**: celdas vacías se preservan como "" — en presupuestos una celda vacía es un dato semántico (glosa que no aplica), no ruido
- **Cabecera repetida por chunk de tabla**: cada chunk incluye la fila de cabecera para que el LLM siempre sepa a qué columna pertenece cada valor
- **Aproximación de tokens sin tiktoken**: 1 token ≈ 4 caracteres para español. Error ±10%, suficiente para decisiones de chunking. tiktoken requiere descarga de ficheros externos bloqueada en el entorno
- **Payload con metadatos territoriales escalables**: cada punto en Qdrant incluye `nivel_territorial`, `ambito`, `pais`, `comunidad`, `provincia`, `municipio`, `codigo_ine` — diseñado para escalar más allá de Madrid
- **API v1beta**: el SDK `google.genai` requiere v1beta para acceder a los modelos de embedding (v1 devuelve 404)
- **Facturación activada en Google AI Studio**: límite gratuito de RPD (requests por día) insuficiente para la ingesta completa. Con facturación: 2000 RPM, pausa de 1 segundo entre llamadas

### Problemas encontrados
- `google-generativeai` deprecado → migrado a `google.genai`
- `text-embedding-004` no disponible en la cuenta → sustituido por `gemini-embedding-001`
- Rate limit 429 en tier gratuito (RPD agotado tras dos ejecuciones fallidas) → resuelto activando facturación
- `tiktoken` requiere descarga de ficheros BPE bloqueada en el sandbox → resuelto con aproximación de 4 chars/token
- Nombres de archivos con espacios y paréntesis en los PDFs originales — no causan errores pero son inelegantes. Recomendado renombrar antes de ingestas futuras

### Próximo paso
- Verificar en dashboard de Qdrant que los 311 puntos están cargados correctamente
- Bloque 2: `rag/retriever.py` — búsqueda semántica en Qdrant
- Bloque 2: `rag/llm.py` — wrapper de Gemini 2.0 Flash para generación de respuestas
- Bloque 2: `rag/chain.py` — cadena RAG completa que conecta retriever + LLM

- Pipeline de ingesta completado: 309 puntos cargados en Qdrant
  (311 chunks generados, 2 descartados por longitud < 20 chars)

---

## Sesión 2026-04-11 (continuación — Bloque 2)

### Completado
- `rag/retriever.py` — búsqueda semántica en Qdrant con filtros por metadatos
- `rag/llm.py` — wrapper de Gemini 2.5 Flash con system prompt ciudadano
- `rag/chain.py` — cadena RAG completa (retriever + llm) con estructura RespuestaRAG

### Decisiones tomadas
- **query_points() en lugar de search()**: qdrant-client >= 1.12 renombró el método. Actualizado en retriever.py
- **task_type="retrieval_query" vs "retrieval_document"**: el retriever usa el modo query para los embeddings de consulta — Gemini optimiza el vector de forma distinta según si es documento o pregunta
- **RespuestaRAG como dataclass**: en lugar de dict, para que pipeline.py y app.py accedan a campos con autocompletado sin riesgo de typos
- **max_output_tokens=2048**: ajustado desde 1024 — la respuesta de capítulo 1 se cortaba en el límite anterior
- **gemini-2.5-flash**: reemplazo de gemini-2.0-flash, deprecado para nuevos usuarios desde marzo 2026. Actualizar en config.py y .env

### Problemas encontrados
- `QdrantClient.search()` deprecado → sustituido por `query_points()` + leer `respuesta.points`
- `gemini-2.0-flash` no disponible para nuevos usuarios → migrado a `gemini-2.5-flash`
- `max_output_tokens=1024` insuficiente para respuestas largas → subido a 2048

### Próximo paso
- Bloque 3: `pipeline.py` — orquestador CLI con flags --ingest y --query

---

## Sesión 2026-04-11 (continuación — Bloque 3)

### Completado
- `pipeline.py` — orquestador CLI con flags --ingest, --query y --status

### Decisiones tomadas
- **Imports locales dentro de cada función**: cmd_ingest() importa los módulos de ingesta; cmd_query() importa chain. Evita cargar dependencias innecesarias según el modo de uso y acelera el arranque
- **nargs="?" + const="__ALL__"** para --ingest: permite distinguir "procesar todo data/raw/" vs "procesar un PDF específico" con un solo flag
- **Pregunta antes de reindexar**: si un PDF ya tiene chunks generados, el pipeline pregunta confirmación antes de reprocesar. Evita duplicados accidentales en Qdrant
- **--status como comando de diagnóstico**: muestra estado de Qdrant, PDFs indexados y JSONs procesados. Útil al inicio de cada sesión
- **max_output_tokens subido a 8192** en llm.py: el valor anterior (2048) causaba respuestas cortadas en consultas con contexto denso

### Problemas encontrados
- Respuesta cortada en la primera consulta ("alcanzando aproximadamente 11.0") → causa: max_output_tokens=2048 insuficiente → resuelto subiendo a 8192

### Próximo paso
- Bloque 4: `interface/app.py` — UI Streamlit

---

## Sesión 2026-04-11 (continuación — Bloque 4 Streamlit)

### Completado
- `interface/app.py` — UI Streamlit con chat acumulativo, filtros, fuentes y debug

### Decisiones tomadas
- **Chat acumulativo con st.session_state**: el historial persiste entre reruns. Cada mensaje se guarda como dict {role, content, rag} — el objeto RespuestaRAG completo se guarda para poder re-renderizar fuentes y debug al recargar
- **renderizar_respuesta() como punto de extensión**: función aislada donde en el futuro se añade soporte para gráficos (st.bar_chart), tablas (st.dataframe) e imágenes sin reescribir la lógica del chat
- **CSS custom con Google Fonts**: Cormorant Garamond (serif, headings) + Jost (sans-serif, cuerpo). Paleta: crema #F2EDE4, azul pizarra #3B5068, efecto cristal con backdrop-filter: blur()
- **Preguntas de ejemplo como botones**: patrón session_state + rerun() para simular eventos en Streamlit sin callbacks complejos
- **Imports dentro de procesar_pregunta()**: chain se importa solo cuando el usuario hace una pregunta, no al arrancar la app (acelera el inicio)

### Problemas encontrados
- Ninguno en esta sesión (pendiente de test en local)

### Próximo paso
- Testear la app con streamlit run interface/app.py
- Verificar que el CSS carga correctamente (requiere conexión para Google Fonts)

---

## Sesión 2026-04-11 (continuación — Bloque 4 React)

### Completado
- `interface/api.py` — FastAPI con endpoints /health, /status, /preguntar
- `interface/frontend/` — App React completa con los siguientes componentes:
  - `App.js` — layout principal, historial en localStorage, scroll suave
  - `components/AnimatedBackground.js` — esferas animadas liquid glass
  - `components/Sidebar.js` — filtros, ejemplos, contador de fragmentos
  - `components/ChatMessage.js` — burbujas usuario/asistente, fuentes inline
  - `components/FragmentPanel.js` — panel lateral con chunks recuperados y tablas renderizadas
  - `components/ChatInput.js` — input flotante con spinner de carga
  - `components/WelcomeScreen.js` — pantalla inicial con sugerencias

### Decisiones tomadas
- **React + FastAPI** en lugar de Streamlit: permite replicar el diseño Liquid Glass con Framer Motion, imposible en Streamlit
- **AnimatedBackground** con keyframes CSS inyectados en runtime: evita dependencias externas de animación para el fondo, mejor rendimiento
- **FragmentPanel** muestra todos los chunks del mensaje al clicar cualquier fuente
- **proxy en package.json** apunta a localhost:8000 — en dev no hace falta CORS explícito

### Problemas encontrados
- Esferas animadas del fondo poco visibles por opacity baja + backdrop-filter del sidebar → resuelto subiendo opacidad x2 y reduciendo blur
- Filtrado de líneas "Fuente:" en el frontend (cleanContent) en lugar de cambiar el system prompt — más robusto ante variaciones del LLM
- localStorage con clave versionada (ec_mensajes_v1) para poder invalidar caché si cambia la estructura de datos

### Próximo paso
- Bloque 5: módulos de visualización educativa (El Archivo + El Mapa)

---

## Sesión 2026-04-11 (continuación — Bloque 5)

### Completado
- `interface/api.py` — añadidos endpoints `/chunks` y `/umap` (3D, n_components=3, caché JSON en data/processed/umap_cache.json)
- `App.js` — refactorizado con navegación por tabs: El Guía · El Archivo · El Mapa
- `components/FragmentPanel.js` — fix score tag condicional (score > 0), badges doc_type y año añadidos
- `modules/Archivo/ArchivoModule.jsx` — tabla filtrable con stats por tipo/documento, búsqueda libre, clic en fila abre FragmentPanel
- `modules/Mapa/MapaModule.jsx` — scatter 3D con Three.js: rotación drag, zoom scroll, tooltip hover, clic → FragmentPanel
- Mejoras al Mapa: ejes de orientación tenues (X/Y/Z), etiquetas de cluster proyectadas en 2D, nota explicativa colapsable

### Decisiones tomadas
- **UMAP 3D (n_components=3)** en lugar de 2D: permite ver distancias reales entre clusters al girar el espacio
- **Three.js r128** (ya en stack): evita dependencia nueva, suficiente para scatter de 309 puntos
- **Caché JSON en data/processed/**: el recálculo UMAP tarda ~15s; la caché lo hace instantáneo en recargas. Forzar recálculo con `GET /umap?recalcular=true`
- **Filtro por doc_type en leyenda**: opacidad 0.06 para dimming, sin eliminar puntos del DOM — más rápido y mantiene la referencia espacial
- **Ejes sin números**: las coordenadas UMAP son arbitrarias; añadir valores numéricos en los ejes sería engañoso. Solo líneas de orientación + marcas cada 3 unidades
- **Etiquetas de cluster proyectadas con tick**: se recalcula la proyección 3D→2D cada 6 frames para que las etiquetas sigan al cluster al girar, sin coste excesivo
- **Nota explicativa colapsable**: comunica al ciudadano que la distancia relativa importa, no la posición absoluta ni los valores de los ejes
- **Sidebar oculto en tabs Archivo y Mapa**: el sidebar de filtros solo tiene sentido en el chat; en los otros módulos ocupa espacio innecesario

### Problemas encontrados
- FragmentPanel mostraba "score 0" en chunks sin score semántico (provenientes del Archivo o el Mapa) → resuelto con condicional `score > 0`
- Three.js necesita cleanup explícito (`cancelAnimationFrame` + `removeChild` + `renderer.dispose()`) al desmontar el componente para evitar memory leaks al cambiar de tab
- umap_cache.json generado con n_components=2 era incompatible con el Mapa 3D → borrado y regenerado con n_components=3

### Próximo paso
- Definir con Diego el Bloque 6: opciones candidatas:
  - Integración Archivo → Chat (clic en fragmento precarga pregunta contextual)
  - Exportación de historial de chat
  - Ampliación del corpus (más PDFs de otras CCAA)
  - Preparación demo para sprint con el equipo
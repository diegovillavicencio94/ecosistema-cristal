"""
interface/app.py — Interfaz Streamlit del Ecosistema de Cristal.

Qué hace:
  - Chat acumulativo (historial visible, estilo GPT)
  - Filtros opcionales en sidebar: año y tipo de documento
  - Respuesta del LLM con fuentes al pie
  - Panel de debug colapsable con chunks recuperados
  - Diseño visual "liquid glass": fondo crema, azul pizarra, tipografía serif

Extensibilidad futura (arquitectura preparada):
  - renderizar_respuesta() es el punto de extensión para gráficos/tablas/imágenes
  - Si el LLM devuelve JSON estructurado, esta función puede detectarlo
    y renderizar st.bar_chart, st.dataframe, st.image, etc.

Uso:
    streamlit run interface/app.py
"""

import sys
from pathlib import Path

import streamlit as st

# ─── Path setup ─────────────────────────────────────────────────────────────
# Añadimos la raíz del proyecto al path para poder importar chain, config, etc.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA (debe ser lo primero tras los imports de st)
# ════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Ecosistema de Cristal",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════════════════
# CSS CUSTOM — Estética "liquid glass" / Ecosistema de Cristal
# ════════════════════════════════════════════════════════════════════════════

# El CSS se inyecta con st.markdown(unsafe_allow_html=True).
# Usamos las fuentes Cormorant Garamond (serif elegante, como en la imagen)
# y Jost (sans-serif limpia para el cuerpo).
# Paleta: crema cálido (#F2EDE4), azul pizarra (#3B5068), dorado suave (#B8996A)

CSS = """
<style>
/* ── Fuentes ─────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Jost:wght@300;400;500&display=swap');

/* ── Variables de color ──────────────────────────────────────────────────── */
:root {
    --crema:        #F2EDE4;
    --crema-oscuro: #E8E0D4;
    --azul:         #3B5068;
    --azul-claro:   #5B7A99;
    --azul-hover:   #2A3D52;
    --dorado:       #B8996A;
    --texto:        #2C2C2C;
    --texto-suave:  #6B6B6B;
    --cristal:      rgba(255, 255, 255, 0.45);
    --cristal-borde: rgba(255, 255, 255, 0.6);
    --sombra:       rgba(59, 80, 104, 0.08);
}

/* ── Reset global ────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--crema) !important;
    font-family: 'Jost', sans-serif;
    color: var(--texto);
}

/* Fondo con textura sutil (grid lines como en la imagen) */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(59, 80, 104, 0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(59, 80, 104, 0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(
        160deg,
        rgba(59, 80, 104, 0.92) 0%,
        rgba(43, 61, 82, 0.96) 100%
    ) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid rgba(255,255,255,0.12);
}

[data-testid="stSidebar"] * {
    color: rgba(255, 255, 255, 0.9) !important;
    font-family: 'Jost', sans-serif !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Cormorant Garamond', serif !important;
    font-weight: 400;
    letter-spacing: 0.02em;
}

/* Labels de los filtros */
[data-testid="stSidebar"] label {
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(255,255,255,0.6) !important;
    font-weight: 500;
}

/* Selectboxes y sliders en sidebar */
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stSlider {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px;
}

/* Divisor en sidebar */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
    margin: 1.5rem 0;
}

/* ── Área principal ──────────────────────────────────────────────────────── */
.main .block-container {
    padding: 2rem 3rem 6rem 3rem;
    max-width: 860px;
    margin: 0 auto;
    position: relative;
    z-index: 1;
}

/* ── Header del proyecto ─────────────────────────────────────────────────── */
.ec-header {
    text-align: center;
    padding: 2.5rem 0 1.5rem 0;
    border-bottom: 1px solid rgba(59, 80, 104, 0.12);
    margin-bottom: 2rem;
}

.ec-header h1 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.6rem;
    font-weight: 300;
    color: var(--azul);
    letter-spacing: -0.01em;
    margin: 0 0 0.4rem 0;
    line-height: 1.1;
}

.ec-header p {
    font-family: 'Jost', sans-serif;
    font-size: 0.82rem;
    color: var(--texto-suave);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 0;
    font-weight: 400;
}

/* ── Mensajes del chat ───────────────────────────────────────────────────── */

/* Mensaje del usuario */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: rgba(59, 80, 104, 0.06) !important;
    border: 1px solid rgba(59, 80, 104, 0.10) !important;
    border-radius: 16px !important;
    padding: 1rem 1.25rem !important;
    margin: 0.75rem 0 !important;
    backdrop-filter: blur(8px);
}

/* Mensaje del asistente (efecto cristal) */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: var(--cristal) !important;
    border: 1px solid var(--cristal-borde) !important;
    border-radius: 16px !important;
    padding: 1.25rem 1.5rem !important;
    margin: 0.75rem 0 !important;
    backdrop-filter: blur(16px);
    box-shadow: 0 4px 24px var(--sombra), inset 0 1px 0 rgba(255,255,255,0.5);
}

/* Texto dentro de los mensajes */
[data-testid="stChatMessage"] p {
    font-family: 'Jost', sans-serif !important;
    font-size: 0.97rem !important;
    line-height: 1.75 !important;
    color: var(--texto) !important;
}

/* ── Input del chat ──────────────────────────────────────────────────────── */
[data-testid="stChatInput"] {
    background: var(--cristal) !important;
    border: 1px solid rgba(59, 80, 104, 0.2) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(20px);
    box-shadow: 0 4px 20px var(--sombra), inset 0 1px 0 rgba(255,255,255,0.6);
}

[data-testid="stChatInput"] textarea {
    font-family: 'Jost', sans-serif !important;
    font-size: 0.95rem !important;
    color: var(--texto) !important;
    background: transparent !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--texto-suave) !important;
}

/* Botón de envío */
[data-testid="stChatInput"] button {
    background: var(--azul) !important;
    border-radius: 10px !important;
    color: white !important;
}

[data-testid="stChatInput"] button:hover {
    background: var(--azul-hover) !important;
}

/* ── Fuentes al pie del mensaje ──────────────────────────────────────────── */
.ec-fuentes {
    margin-top: 1.2rem;
    padding-top: 0.8rem;
    border-top: 1px solid rgba(59, 80, 104, 0.12);
}

.ec-fuentes-titulo {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--texto-suave);
    font-weight: 500;
    margin-bottom: 0.4rem;
}

.ec-fuente-item {
    font-size: 0.80rem;
    color: var(--azul-claro);
    padding: 0.15rem 0;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

/* ── Chips de metadatos ──────────────────────────────────────────────────── */
.ec-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.6rem;
}

.ec-chip {
    background: rgba(59, 80, 104, 0.08);
    border: 1px solid rgba(59, 80, 104, 0.15);
    border-radius: 20px;
    padding: 0.2rem 0.65rem;
    font-size: 0.72rem;
    color: var(--azul);
    font-weight: 500;
    letter-spacing: 0.03em;
}

/* ── Panel de debug (expander) ───────────────────────────────────────────── */
.streamlit-expanderHeader {
    font-family: 'Jost', sans-serif !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--texto-suave) !important;
    background: transparent !important;
    border: none !important;
    padding-left: 0 !important;
}

.streamlit-expanderContent {
    background: rgba(59, 80, 104, 0.03) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(59, 80, 104, 0.08) !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.82rem !important;
}

/* ── Estado vacío (bienvenida) ───────────────────────────────────────────── */
.ec-bienvenida {
    text-align: center;
    padding: 3rem 2rem;
    opacity: 0.7;
}

.ec-bienvenida-icono {
    font-size: 2.5rem;
    margin-bottom: 1rem;
}

.ec-bienvenida h3 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.5rem;
    font-weight: 300;
    color: var(--azul);
    margin-bottom: 0.5rem;
}

.ec-bienvenida p {
    font-size: 0.88rem;
    color: var(--texto-suave);
    line-height: 1.6;
    max-width: 420px;
    margin: 0 auto;
}

/* ── Preguntas de ejemplo ────────────────────────────────────────────────── */
.ec-ejemplos {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 1.5rem;
    max-width: 480px;
    margin-left: auto;
    margin-right: auto;
}

.ec-ejemplo-btn {
    background: var(--cristal);
    border: 1px solid rgba(59, 80, 104, 0.15);
    border-radius: 10px;
    padding: 0.65rem 1rem;
    font-size: 0.85rem;
    color: var(--azul);
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
    font-family: 'Jost', sans-serif;
    backdrop-filter: blur(8px);
}

/* ── Spinner de carga ────────────────────────────────────────────────────── */
[data-testid="stSpinner"] {
    color: var(--azul) !important;
}

/* ── Badges de score ─────────────────────────────────────────────────────── */
.ec-score-alto  { color: #2E7D5A; font-weight: 600; }
.ec-score-medio { color: #B07D2A; font-weight: 600; }
.ec-score-bajo  { color: #8B3A3A; font-weight: 600; }

/* ── Scrollbar custom ────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(59, 80, 104, 0.25); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: rgba(59, 80, 104, 0.4); }

/* ── Ocultar elementos de Streamlit que no queremos ──────────────────────── */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

/* ── Botones de ejemplo como st.button ───────────────────────────────────── */
.stButton > button {
    background: var(--cristal) !important;
    border: 1px solid rgba(59, 80, 104, 0.18) !important;
    border-radius: 10px !important;
    color: var(--azul) !important;
    font-family: 'Jost', sans-serif !important;
    font-size: 0.84rem !important;
    font-weight: 400 !important;
    padding: 0.5rem 1rem !important;
    text-align: left !important;
    width: 100% !important;
    backdrop-filter: blur(8px);
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background: rgba(59, 80, 104, 0.10) !important;
    border-color: rgba(59, 80, 104, 0.30) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px var(--sombra) !important;
}

/* Etiquetas de radio buttons en sidebar */
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.88rem !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    color: rgba(255,255,255,0.85) !important;
    cursor: pointer;
}
</style>
"""


# ════════════════════════════════════════════════════════════════════════════
# HELPERS DE RENDERIZADO
# ════════════════════════════════════════════════════════════════════════════

def score_a_clase(score: float) -> str:
    """Devuelve la clase CSS según el score de similitud."""
    if score >= 0.75:
        return "ec-score-alto"
    elif score >= 0.55:
        return "ec-score-medio"
    return "ec-score-bajo"


def renderizar_fuentes(fuentes: list[dict]) -> str:
    """
    Genera el HTML de las fuentes al pie de la respuesta.

    En el futuro, aquí podríamos añadir links a los PDFs originales
    si los servimos como archivos estáticos.
    """
    if not fuentes:
        return ""

    items = ""
    for f in fuentes:
        doc = f.get("source", "Documento desconocido")
        pag = f.get("page", "?")
        doc_type = f.get("doc_type", "")
        año = f.get("año", "")

        # Nombre más legible: quitamos extensión y guiones bajos
        doc_nombre = doc.replace(".pdf", "").replace("_", " ").title()

        badge = f" · {doc_type}" if doc_type else ""
        año_str = f" · {año}" if año else ""

        items += f"""
        <div class="ec-fuente-item">
            <span>📄</span>
            <span>{doc_nombre}{badge}{año_str} — pág. {pag}</span>
        </div>"""

    return f"""
    <div class="ec-fuentes">
        <div class="ec-fuentes-titulo">Fuentes consultadas</div>
        {items}
    </div>"""


def renderizar_respuesta(respuesta_rag) -> None:
    """
    Renderiza la respuesta del RAG en el chat.

    PUNTO DE EXTENSIÓN FUTURA:
    Esta función es donde añadiremos soporte para gráficos y tablas.
    Por ahora renderiza solo texto + fuentes. En el futuro:

      if respuesta_rag.tipo == "grafico_barras":
          st.bar_chart(respuesta_rag.datos)
      elif respuesta_rag.tipo == "tabla":
          st.dataframe(respuesta_rag.datos)

    Args:
        respuesta_rag: Objeto RespuestaRAG de chain.py
    """
    # Texto de la respuesta
    st.markdown(respuesta_rag.respuesta)

    # Fuentes al pie
    if respuesta_rag.fuentes:
        st.markdown(
            renderizar_fuentes(respuesta_rag.fuentes),
            unsafe_allow_html=True
        )

    # Panel de debug: chunks usados (colapsable)
    if respuesta_rag.chunks and not respuesta_rag.sin_contexto:
        with st.expander(f"🔍 {len(respuesta_rag.chunks)} fragmentos recuperados", expanded=False):
            for i, chunk in enumerate(respuesta_rag.chunks, 1):
                score = chunk.get("score", 0)
                clase_score = score_a_clase(score)
                tipo = chunk.get("type", "texto")
                icono = "📊" if tipo == "table" else "📝"
                fuente = chunk.get("source", "").replace(".pdf", "")
                pag = chunk.get("page", "?")
                organismo = chunk.get("organismo", "")

                st.markdown(
                    f"""**{icono} Fragmento {i}** &nbsp;·&nbsp; """
                    f"""{fuente} · pág. {pag}"""
                    + (f" &nbsp;·&nbsp; {organismo}" if organismo else "")
                    + f"""&nbsp;&nbsp;<span class="{clase_score}">score {score}</span>""",
                    unsafe_allow_html=True
                )

                # Preview del contenido (primeras 200 chars)
                contenido_preview = chunk.get("content", "")[:200]
                if len(chunk.get("content", "")) > 200:
                    contenido_preview += "…"

                st.caption(contenido_preview)

                if i < len(respuesta_rag.chunks):
                    st.divider()


# ════════════════════════════════════════════════════════════════════════════
# ESTADO DE SESIÓN
# ════════════════════════════════════════════════════════════════════════════

def inicializar_estado() -> None:
    """
    Inicializa las variables de sesión de Streamlit.

    st.session_state persiste entre reruns del script (cada interacción
    del usuario provoca un rerun). Sin esto, el historial del chat se
    borraría en cada mensaje.
    """
    if "mensajes" not in st.session_state:
        # Lista de dicts: {"role": "user"|"assistant", "content": str, "rag": RespuestaRAG|None}
        st.session_state.mensajes = []

    if "pregunta_ejemplo" not in st.session_state:
        st.session_state.pregunta_ejemplo = None


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

def renderizar_sidebar() -> dict:
    """
    Renderiza el sidebar con filtros y devuelve los valores seleccionados.

    Returns:
        Dict con: año, tipo_doc, top_k
    """
    with st.sidebar:
        # ── Logo / Título ────────────────────────────────────────────────
        st.markdown("""
        <div style="padding: 1rem 0 1.5rem 0; text-align: center;">
            <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">◇</div>
            <div style="font-family: 'Cormorant Garamond', serif; font-size: 1.4rem; font-weight: 300; letter-spacing: 0.02em;">
                Ecosistema<br>de Cristal
            </div>
            <div style="font-size: 0.68rem; letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5; margin-top: 0.3rem;">
                Transparencia Presupuestaria · IA
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # ── Filtros ──────────────────────────────────────────────────────
        st.markdown("**Filtros de búsqueda**")

        # Año
        año_opciones = {
            "Todos los años": None,
            "2025": 2025,
            "2026": 2026,
        }
        año_seleccionado = st.selectbox(
            "Año presupuestario",
            options=list(año_opciones.keys()),
            index=0,
        )
        año = año_opciones[año_seleccionado]

        # Tipo de documento
        doc_opciones = {
            "Todos los documentos": None,
            "Folleto resumen": "folleto",
            "Articulado / Ley": "articulado",
            "Memoria": "memoria",
        }
        doc_seleccionado = st.selectbox(
            "Tipo de documento",
            options=list(doc_opciones.keys()),
            index=0,
        )
        tipo_doc = doc_opciones[doc_seleccionado]

        # Número de fragmentos
        top_k = st.slider(
            "Fragmentos a recuperar",
            min_value=1,
            max_value=10,
            value=5,
            help="Cuántos fragmentos de documentos se consultan para generar la respuesta"
        )

        st.markdown("---")

        # ── Botón limpiar historial ───────────────────────────────────────
        if st.button("🗑 Limpiar conversación", use_container_width=True):
            st.session_state.mensajes = []
            st.rerun()

        st.markdown("---")

        # ── Info del sistema ──────────────────────────────────────────────
        st.markdown("""
        <div style="font-size: 0.72rem; opacity: 0.5; line-height: 1.7;">
            <div style="text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.4rem;">Sistema</div>
            LLM: Gemini 2.5 Flash<br>
            Embeddings: gemini-embedding-001<br>
            Vector DB: Qdrant · 309 puntos<br>
            Documentos: 3 PDFs indexados
        </div>
        """, unsafe_allow_html=True)

    return {"año": año, "tipo_doc": tipo_doc, "top_k": top_k}


# ════════════════════════════════════════════════════════════════════════════
# ESTADO VACÍO (pantalla de bienvenida)
# ════════════════════════════════════════════════════════════════════════════

PREGUNTAS_EJEMPLO = [
    "¿Cuánto se gasta en sanidad en el presupuesto de Madrid para 2026?",
    "¿Qué es el capítulo 1 de gastos de personal?",
    "¿Cuáles son los ingresos totales previstos para 2026?",
    "¿Cuánto destina la Comunidad de Madrid a educación?",
    "¿Qué partidas han crecido más respecto al año anterior?",
]


def renderizar_bienvenida() -> None:
    """
    Muestra la pantalla de bienvenida cuando no hay mensajes en el historial.
    Incluye preguntas de ejemplo que el usuario puede pulsar para lanzar.
    """
    st.markdown("""
    <div class="ec-bienvenida">
        <div class="ec-bienvenida-icono">◇</div>
        <h3>El Guía Experto</h3>
        <p>Pregunta sobre los presupuestos de la Comunidad de Madrid
        en lenguaje natural. Accedo a documentos oficiales y te respondo
        con fuentes citadas.</p>
    </div>
    """, unsafe_allow_html=True)

    # Preguntas de ejemplo como botones
    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.markdown(
            "<div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em; "
            "color:var(--texto-suave); text-align:center; margin-bottom:0.75rem;'>"
            "Preguntas de ejemplo</div>",
            unsafe_allow_html=True
        )
        for pregunta in PREGUNTAS_EJEMPLO:
            # Cada botón guarda la pregunta en session_state y fuerza un rerun
            if st.button(f"→ {pregunta}", key=f"ej_{pregunta}"):
                st.session_state.pregunta_ejemplo = pregunta
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# LÓGICA PRINCIPAL DEL CHAT
# ════════════════════════════════════════════════════════════════════════════

def procesar_pregunta(pregunta: str, filtros: dict) -> None:
    """
    Ejecuta el pipeline RAG para una pregunta y actualiza el historial.

    Flujo:
      1. Añade el mensaje del usuario al historial
      2. Renderiza el spinner mientras llama al RAG
      3. Añade la respuesta al historial
      4. Renderiza la respuesta con fuentes y debug

    Args:
        pregunta: Texto de la pregunta del usuario
        filtros:  Dict con año, tipo_doc, top_k del sidebar
    """
    # Importamos aquí para no cargar las dependencias pesadas al arrancar
    from rag.chain import preguntar

    # Añadimos el mensaje del usuario al estado
    st.session_state.mensajes.append({
        "role": "user",
        "content": pregunta,
        "rag": None,
    })

    # Renderizamos el mensaje del usuario
    with st.chat_message("user"):
        st.markdown(pregunta)

    # Llamamos al RAG con spinner de carga
    with st.chat_message("assistant"):
        with st.spinner("Consultando los documentos presupuestarios…"):
            try:
                resultado = preguntar(
                    pregunta=pregunta,
                    top_k=filtros["top_k"],
                    año=filtros["año"],
                    tipo_doc=filtros["tipo_doc"],
                )
                renderizar_respuesta(resultado)

                # Guardamos el resultado completo en el historial
                st.session_state.mensajes.append({
                    "role": "assistant",
                    "content": resultado.respuesta,
                    "rag": resultado,
                })

            except Exception as e:
                # Error gracioso: mostramos el error sin crashear la app
                mensaje_error = (
                    f"⚠️ Ha ocurrido un error al procesar tu consulta.\n\n"
                    f"**Detalle técnico:** `{str(e)}`\n\n"
                    f"Comprueba que Qdrant está corriendo (`docker compose up -d`) "
                    f"y que la API key de Google es válida."
                )
                st.error(mensaje_error)
                st.session_state.mensajes.append({
                    "role": "assistant",
                    "content": mensaje_error,
                    "rag": None,
                })


def renderizar_historial() -> None:
    """
    Renderiza todos los mensajes previos del historial al cargar la página.

    Streamlit rerenderiza toda la página en cada interacción, así que
    necesitamos reconstruir el historial del chat en cada rerun.
    """
    for mensaje in st.session_state.mensajes:
        if mensaje["role"] == "user":
            with st.chat_message("user"):
                st.markdown(mensaje["content"])
        else:
            with st.chat_message("assistant"):
                rag = mensaje.get("rag")
                if rag:
                    # Si tenemos el objeto RAG completo, renderizamos con fuentes y debug
                    renderizar_respuesta(rag)
                else:
                    # Fallback: solo texto (errores o mensajes sin RAG)
                    st.markdown(mensaje["content"])


# ════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Función principal de la app Streamlit.

    Streamlit ejecuta este script de arriba a abajo en cada interacción
    del usuario. El estado persiste a través de st.session_state.
    """
    # Inyectamos el CSS
    st.markdown(CSS, unsafe_allow_html=True)

    # Inicializamos el estado de sesión
    inicializar_estado()

    # Renderizamos el sidebar y obtenemos los filtros
    filtros = renderizar_sidebar()

    # Header principal
    st.markdown("""
    <div class="ec-header">
        <h1>El Ecosistema de Cristal</h1>
        <p>Plataforma de Transparencia Presupuestaria · Comunidad de Madrid</p>
    </div>
    """, unsafe_allow_html=True)

    # Si el usuario pulsó una pregunta de ejemplo (desde la pantalla de bienvenida)
    # la procesamos antes de renderizar el historial
    pregunta_pendiente = st.session_state.get("pregunta_ejemplo")
    if pregunta_pendiente:
        st.session_state.pregunta_ejemplo = None
        procesar_pregunta(pregunta_pendiente, filtros)
    else:
        # Estado vacío: mostramos bienvenida
        if not st.session_state.mensajes:
            renderizar_bienvenida()
        else:
            # Hay historial: lo renderizamos completo
            renderizar_historial()

    # Input del chat (siempre visible en la parte inferior)
    if pregunta := st.chat_input("Pregunta sobre los presupuestos de Madrid…"):
        # Si hay historial previo, lo renderizamos primero
        if st.session_state.mensajes and not pregunta_pendiente:
            renderizar_historial()
        procesar_pregunta(pregunta, filtros)


if __name__ == "__main__":
    main()

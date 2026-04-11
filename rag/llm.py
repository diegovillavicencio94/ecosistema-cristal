"""
llm.py — Wrapper de Gemini 2.0 Flash para generación de respuestas RAG.

Qué hace:
  - Recibe una pregunta y los chunks recuperados por el retriever
  - Construye el prompt con contexto + instrucciones de tono
  - Llama a Gemini 2.0 Flash y devuelve la respuesta

Por qué está separado de chain.py:
  El prompt es la pieza más sensible del RAG — lo ajustaremos
  más que cualquier otro componente. Aislarlo aquí permite iterar
  el tono, el formato y las instrucciones sin tocar la orquestación.

Decisión de diseño — prompt en español y tono ciudadano:
  El sistema prompt le indica al LLM que es un guía de transparencia
  presupuestaria, no un asistente genérico. Esto reduce alucinaciones
  porque el modelo sabe que solo debe responder con lo que está en
  el contexto, y en un lenguaje accesible, no técnico-contable.
"""

import logging
import time
from typing import Optional

from google import genai
from google.genai import types as genai_types

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import GOOGLE_API_KEY, GEMINI_MODEL

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ════════════════════════════════════════════════════════════════════════════

# El system prompt define el "personaje" y las reglas del LLM.
# Es la instrucción más importante del sistema — determina tono,
# comportamiento ante preguntas sin respuesta, y formato de citas.
SYSTEM_PROMPT = """Eres el Guía Experto del Ecosistema de Cristal, una plataforma de transparencia presupuestaria ciudadana.

Tu misión es traducir los presupuestos públicos de la Comunidad de Madrid a lenguaje claro y accesible para cualquier ciudadano, sin jerga contable.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE con información que aparezca en el CONTEXTO proporcionado. No uses tu conocimiento general sobre presupuestos.
2. Si el contexto no contiene información suficiente para responder, dilo claramente: "No tengo información suficiente en los documentos disponibles para responder a eso."
3. Cita siempre la fuente: indica el nombre del documento y la página al final de cada dato importante.
4. Usa lenguaje sencillo. Evita términos como "capítulo presupuestario", "dotación económica" o "ejercicio fiscal" sin explicarlos.
5. Si hay cifras, exprésalas de forma comprensible (ej: "11.009 millones de euros" → "más de 11.000 millones de euros, el equivalente a...").
6. Sé honesto sobre la fecha de los datos: indica si son del presupuesto 2025 o 2026.

FORMATO DE RESPUESTA:
- Respuesta directa en 2-4 párrafos
- Al final, una línea de fuentes: "📄 Fuente: [documento] · pág. [N]"
- Si hay varios documentos, lista cada fuente en línea separada
"""


# ════════════════════════════════════════════════════════════════════════════
# CLIENTE GEMINI (singleton)
# ════════════════════════════════════════════════════════════════════════════

_gemini_client: Optional[genai.Client] = None


def _get_gemini() -> genai.Client:
    """
    Devuelve el cliente de Gemini, inicializándolo si es la primera vez.
    Para el LLM usamos v1 (estable), no v1beta como en los embeddings.
    Los modelos de generación están disponibles en v1.
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
        logger.info(f"Cliente Gemini LLM inicializado. Modelo: {GEMINI_MODEL}")
    return _gemini_client


# ════════════════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DEL PROMPT
# ════════════════════════════════════════════════════════════════════════════

def construir_contexto(chunks: list[dict]) -> str:
    """
    Convierte la lista de chunks del retriever en un bloque de contexto
    formateado para incluir en el prompt del LLM.

    Cada chunk lleva su fuente y página para que el LLM pueda citarlos
    en la respuesta. El formato es deliberadamente simple para no confundir
    al modelo con marcado complejo.

    Ejemplo de salida:
        [Fragmento 1 — folleto_presupuestos_2026.pdf · pág. 8 · tabla]
        Distribución de Presupuesto | Presupuesto 2025 | Presupuesto 2026...

        [Fragmento 2 — folleto_presupuestos_2026.pdf · pág. 24 · texto]
        6.1 Sanidad. Seguiremos prestando una asistencia sanitaria...

    Args:
        chunks: Lista de dicts del retriever (con keys: content, source, page, type)

    Returns:
        String con todos los fragmentos formateados y numerados
    """
    if not chunks:
        return "No se encontraron fragmentos relevantes en los documentos."

    bloques = []
    for i, chunk in enumerate(chunks, 1):
        # Nombre de archivo limpio (sin ruta completa ni extensión larga)
        fuente = chunk.get("source", "documento desconocido")
        pagina = chunk.get("page", "?")
        tipo = chunk.get("type", "texto")
        contenido = chunk.get("content", "")

        encabezado = f"[Fragmento {i} — {fuente} · pág. {pagina} · {tipo}]"
        bloques.append(f"{encabezado}\n{contenido}")

    return "\n\n".join(bloques)


def construir_prompt_usuario(pregunta: str, contexto: str) -> str:
    """
    Construye el mensaje de usuario que va al LLM.

    Separamos el contexto de la pregunta con un delimitador claro
    para que el modelo no confunda el contenido de los documentos
    con instrucciones o con la pregunta en sí.

    Args:
        pregunta: Pregunta del usuario en lenguaje natural
        contexto: Bloque de contexto generado por construir_contexto()

    Returns:
        Prompt completo listo para enviar al LLM
    """
    return f"""CONTEXTO (fragmentos de los documentos presupuestarios):
---
{contexto}
---

PREGUNTA DEL CIUDADANO:
{pregunta}

Responde basándote exclusivamente en el contexto proporcionado."""


# ════════════════════════════════════════════════════════════════════════════
# GENERACIÓN DE RESPUESTA
# ════════════════════════════════════════════════════════════════════════════

def generar_respuesta(
    pregunta: str,
    chunks: list[dict],
    reintentos: int = 3,
) -> str:
    """
    Genera una respuesta en lenguaje ciudadano a partir de la pregunta
    y los chunks recuperados por el retriever.

    Args:
        pregunta:   Pregunta del usuario
        chunks:     Lista de chunks del retriever (resultado de buscar())
        reintentos: Intentos antes de fallar (con backoff exponencial)

    Returns:
        Respuesta en texto plano con citas de fuente al final
    """
    if not chunks:
        return (
            "No encontré información relevante en los documentos disponibles "
            "para responder a tu pregunta. Prueba a reformularla o a ser más específico."
        )

    # Construimos el prompt
    contexto = construir_contexto(chunks)
    prompt_usuario = construir_prompt_usuario(pregunta, contexto)

    logger.info(
        f"Generando respuesta con {len(chunks)} chunks de contexto "
        f"({len(contexto)} chars)"
    )

    for intento in range(reintentos):
        try:
            cliente = _get_gemini()

            respuesta = cliente.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt_usuario,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,      # baja temperatura = respuestas más fieles al contexto
                    max_output_tokens=8192,
                ),
            )

            texto_respuesta = respuesta.text
            logger.info(f"Respuesta generada ({len(texto_respuesta)} chars)")
            return texto_respuesta

        except Exception as e:
            if intento < reintentos - 1:
                espera = 2 ** intento
                logger.warning(
                    f"Error al generar respuesta (intento {intento+1}): {e}. "
                    f"Reintentando en {espera}s..."
                )
                time.sleep(espera)
            else:
                logger.error(f"Fallo definitivo al generar respuesta: {e}")
                raise


# ════════════════════════════════════════════════════════════════════════════
# TEST BLOCK
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    Test de llm.py usando chunks ficticios (no necesita Qdrant).

    Esto permite verificar que el LLM responde correctamente y en el
    tono adecuado antes de conectar con el retriever real.

    Uso:
        python rag/llm.py
    """

    # Chunks ficticios que simulan lo que devolvería el retriever
    # Usamos datos reales del presupuesto para que la prueba sea significativa
    chunks_prueba = [
        {
            "content": (
                "6.1 Sanidad\n"
                "Seguiremos prestando una asistencia sanitaria de vanguardia que cura, "
                "cuida y acompaña, contando para ello con un Presupuesto récord que "
                "asciende a 11.009,5 millones de euros, lo que supone el 35,9% del total "
                "y un crecimiento del 5,3% respecto al año anterior."
            ),
            "source": "folleto_proyecto_presupuestos_generales_2026.pdf",
            "page": 24,
            "type": "text",
            "score": 0.78,
        },
        {
            "content": (
                "Distribución de Presupuesto | Presupuesto 2025 | Presupuesto 2026 | Var.(€) | Var.(%)\n"
                "Sanidad | 10.459,7 | 11.009,5 | 549,8 | 5,3%\n"
                "Educación, Ciencia y Universidades | 6.699,6 | 6.959,0 | 259,4 | 3,9%\n"
                "Vivienda, Transportes e Infraestructuras | 3.290,0 | 3.292,6 | 2,6 | 0,1%"
            ),
            "source": "folleto_proyecto_presupuestos_generales_2026.pdf",
            "page": 8,
            "type": "table",
            "score": 0.76,
        },
    ]

    preguntas_prueba = [
        "¿Cuánto se gasta en sanidad?",
        "¿Qué porcentaje del presupuesto va a educación?",
        "¿Cuánto cuesta construir el metro de Madrid?",  # pregunta sin respuesta en el contexto
    ]

    for pregunta in preguntas_prueba:
        print(f"\n{'='*60}")
        print(f"PREGUNTA: {pregunta}")
        print(f"{'='*60}")

        respuesta = generar_respuesta(pregunta, chunks_prueba)
        print(respuesta)

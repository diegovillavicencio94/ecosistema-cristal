"""
chain.py — Cadena RAG completa: pregunta -> retriever -> llm -> respuesta + grafico.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from rag.retriever import buscar
from rag.llm import generar_respuesta
from config import TOP_K_RESULTS, GOOGLE_API_KEY, GEMINI_MODEL, GRAFICO_AGRESIVIDAD

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ============================================================
# ESTRUCTURA DE RESPUESTA
# ============================================================

@dataclass
class RespuestaRAG:
    pregunta:      str
    respuesta:     str
    chunks:        list[dict] = field(default_factory=list)
    fuentes:       list[dict] = field(default_factory=list)
    sin_contexto:  bool = False
    datos_grafico: Optional[dict] = None


# ============================================================
# DETECCION DE GRAFICO
# ============================================================

PROMPT_CONSERVADOR = (
    "Analiza estos fragmentos de presupuestos publicos y determina si contienen "
    "datos numericos claramente tabulados y comparables (ej: importes por consejeria, "
    "capitulos de gasto, variaciones entre anios). Solo extrae datos si son "
    "inequivocamente graficables como tabla estructurada. "
    "Si hay cualquier ambiguedad, devuelve null."
)

PROMPT_MODERADO = (
    "Analiza estos fragmentos de presupuestos publicos y determina si contienen "
    "datos numericos relevantes que permitan una comparacion visual (tablas O texto "
    "con cifras concretas asociadas a categorias). Extrae si los datos tienen al "
    "menos 2 categorias con valores numericos claros."
)

PROMPT_AGRESIVO = (
    "Analiza estos fragmentos de presupuestos publicos e intenta extraer cualquier "
    "dato numerico que pueda visualizarse. Si hay cifras con etiquetas, extraelas."
)

PROMPTS_AGRESIVIDAD = {
    "conservador": PROMPT_CONSERVADOR,
    "moderado":    PROMPT_MODERADO,
    "agresivo":    PROMPT_AGRESIVO,
}

INSTRUCCION_JSON = (
    "Si hay datos graficables devuelve UNICAMENTE un JSON valido con esta estructura:\n"
    '{"tipo": "bar", "titulo": "titulo descriptivo", "unidad": "millones de euros", '
    '"comparativo": false, "datos": [{"nombre": "etiqueta", "valor": numero}]}\n\n'
    "Si hay dos series temporales (2025 vs 2026) usa:\n"
    '{"tipo": "bar", "titulo": "titulo", "unidad": "millones de euros", '
    '"comparativo": true, "etiqueta_a": "2025", "etiqueta_b": "2026", '
    '"datos_comparativo": [{"nombre": "etiqueta", "valor_a": numero, "valor_b": numero}]}\n\n'
    "Reglas: maximo 12 categorias, solo valores numericos, "
    "si no hay datos graficables devuelve exactamente: null\n"
    "No añadas texto ni explicaciones fuera del JSON."
)


def detectar_grafico(chunks: list[dict], pregunta: str) -> Optional[dict]:
    """
    Analiza los chunks y devuelve estructura Recharts si detecta datos graficables.
    Usa google.genai (no el deprecado google.generativeai).
    """
    chunks_tabla = [c for c in chunks if c.get("type") == "table"]

    if GRAFICO_AGRESIVIDAD == "conservador" and not chunks_tabla:
        logger.info("[GRAFICO] Sin tablas — omitiendo (conservador)")
        return None

    chunks_para_analizar = chunks_tabla if GRAFICO_AGRESIVIDAD == "conservador" else chunks
    partes_contexto = []
    for i, c in enumerate(chunks_para_analizar[:4]):
        partes_contexto.append(
            "[Fragmento " + str(i+1) + " - " + str(c.get("source","?")) +
            " pag." + str(c.get("page","?")) + "]\n" + str(c.get("content",""))
        )
    contexto = "\n\n---\n\n".join(partes_contexto)

    instruccion = PROMPTS_AGRESIVIDAD.get(GRAFICO_AGRESIVIDAD, PROMPT_CONSERVADOR)

    prompt = (
        instruccion + "\n\n"
        "Pregunta del usuario: " + pregunta + "\n\n"
        "Fragmentos a analizar:\n" + contexto + "\n\n"
        + INSTRUCCION_JSON
    )

    try:
        from google import genai as google_genai
        from google.genai import types as genai_types

        cliente = google_genai.Client(
            api_key=GOOGLE_API_KEY,
            http_options=genai_types.HttpOptions(api_version="v1beta"),
        )
        respuesta = cliente.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )
        texto = respuesta.text.strip()
        logger.info("[GRAFICO DEBUG] Respuesta raw de Gemini: " + repr(texto[:500]))


        # Limpiar backticks de markdown si los hay
        if "```" in texto:
            partes = texto.split("```")
            # el JSON suele estar en partes[1]
            texto = partes[1] if len(partes) > 1 else partes[0]
            if texto.startswith("json"):
                texto = texto[4:]
        texto = texto.strip()

        if texto.lower() == "null" or texto == "":
            logger.info("[GRAFICO] No hay datos graficables")
            return None

        datos = json.loads(texto)

        if not isinstance(datos, dict):
            return None
        if "tipo" not in datos or ("datos" not in datos and "datos_comparativo" not in datos):
            return None

        logger.info("[GRAFICO] Detectado: tipo=" + str(datos.get("tipo")) + " | " + str(datos.get("titulo")))
        return datos

    except json.JSONDecodeError as e:
        logger.warning("[GRAFICO] JSON invalido: " + str(e))
        return None
    except Exception as e:
        logger.warning("[GRAFICO] Error: " + str(e))
        return None


# ============================================================
# UTILIDADES
# ============================================================

def extraer_fuentes(chunks: list[dict]) -> list[dict]:
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
                "anio":     chunk.get("año"),
            })
    fuentes.sort(key=lambda f: (f["source"], f["page"] or 0))
    return fuentes


# ============================================================
# FUNCION PRINCIPAL
# ============================================================

def preguntar(
    pregunta: str,
    top_k: int = TOP_K_RESULTS,
    año: Optional[int] = None,
    comunidad: Optional[str] = None,
    tipo_doc: Optional[str] = None,
    tipo_chunk: Optional[str] = None,
    score_minimo: float = 0.0,
) -> RespuestaRAG:
    logger.info("[RAG] Pregunta: '" + pregunta + "'")

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
                "No encontre informacion relevante en los documentos disponibles. "
                "Prueba a reformular la pregunta o a ser mas especifico."
            ),
            chunks=[], fuentes=[], sin_contexto=True, datos_grafico=None,
        )

    logger.info("[RAG] " + str(len(chunks)) + " chunks | scores: " + str([c["score"] for c in chunks]))

    respuesta = generar_respuesta(pregunta=pregunta, chunks=chunks)
    datos_grafico = detectar_grafico(chunks=chunks, pregunta=pregunta)
    fuentes = extraer_fuentes(chunks)

    logger.info(
        "[RAG] Respuesta: " + str(len(respuesta)) + " chars | "
        "Fuentes: " + str(len(fuentes)) + " | "
        "Grafico: " + ("si" if datos_grafico else "no")
    )

    return RespuestaRAG(
        pregunta=pregunta,
        respuesta=respuesta,
        chunks=chunks,
        fuentes=fuentes,
        sin_contexto=False,
        datos_grafico=datos_grafico,
    )


# ============================================================
# TEST BLOCK
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        preguntas = [" ".join(sys.argv[1:])]
    else:
        preguntas = [
            "Cual es el presupuesto por consejeria en 2026?",
        ]

    for pregunta in preguntas:
        print("\n" + "="*60)
        print("PREGUNTA: " + pregunta)
        print("="*60)
        resultado = preguntar(pregunta)
        print("\nRESPUESTA:\n" + resultado.respuesta)
        print("\nCHUNKS: " + str([(c["type"], c["score"]) for c in resultado.chunks]))
        if resultado.datos_grafico:
            print("\nGRAFICO: " + json.dumps(resultado.datos_grafico, ensure_ascii=False, indent=2))
        else:
            print("\nGRAFICO: No detectado")

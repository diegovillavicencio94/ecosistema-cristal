"""
pdf_extractor.py — Extracción de texto y tablas desde PDFs con pdfplumber.

Qué hace:
  - Lee un PDF página a página
  - Extrae el texto narrativo de cada página
  - Extrae las tablas estructuradas (importes, partidas, etc.)
  - Guarda el resultado como JSON en data/processed/

Por qué pdfplumber:
  - Detecta tablas automáticamente usando líneas y espaciado
  - Extrae texto respetando el orden de lectura
  - Funciona bien con PDFs generados (no escaneados)
"""

import json
import logging
from pathlib import Path
from typing import Optional

import pdfplumber

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Rutas por defecto ───────────────────────────────────────────────────────
# __file__ es ingestion/pdf_extractor.py → subimos un nivel para llegar a la raíz
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def extraer_tabla(tabla_raw: list[list]) -> list[list[str]]:
    """
    Limpia una tabla extraída por pdfplumber.

    pdfplumber devuelve listas de listas donde las celdas vacías son None.
    Las convertimos a strings vacíos para evitar errores en pasos posteriores.

    Ejemplo de entrada:  [["Consejería", "2025", None], [None, "10.459", "11.009"]]
    Ejemplo de salida:   [["Consejería", "2025", ""], ["", "10.459", "11.009"]]
    """
    tabla_limpia = []
    for fila in tabla_raw:
        fila_limpia = [str(celda).strip() if celda is not None else "" for celda in fila]
        # Ignoramos filas completamente vacías (artefactos del PDF)
        if any(celda != "" for celda in fila_limpia):
            tabla_limpia.append(fila_limpia)
    return tabla_limpia


def extraer_texto_sin_tablas(pagina: pdfplumber.page.Page) -> str:
    """
    Extrae el texto de una página excluyendo las zonas que contienen tablas.

    Por qué: si extraemos texto plano de una página con tablas, los números
    quedan mezclados con el texto narrativo en un orden confuso. Mejor tener
    texto y tablas por separado.

    Cómo: pdfplumber puede identificar los bounding boxes de las tablas y
    excluirlos al extraer el texto.
    """
    try:
        # Identificamos las tablas en la página para excluir sus zonas
        bboxes_tablas = [tabla.bbox for tabla in pagina.find_tables()]

        if not bboxes_tablas:
            # Sin tablas: extraemos todo el texto directamente
            return pagina.extract_text() or ""

        # Con tablas: filtramos los objetos de texto que caen dentro de las tablas
        # Un objeto de texto está "dentro" de una tabla si su bbox se solapa
        def fuera_de_tablas(objeto):
            x0, y0, x1, y1 = objeto["x0"], objeto["top"], objeto["x1"], objeto["bottom"]
            for tx0, ty0, tx1, ty1 in bboxes_tablas:
                # Comprobamos solapamiento
                if x0 >= tx0 and x1 <= tx1 and y0 >= ty0 and y1 <= ty1:
                    return False  # Está dentro de una tabla → lo excluimos
            return True

        # Creamos una "sub-página" solo con los objetos fuera de tablas
        pagina_sin_tablas = pagina.filter(fuera_de_tablas)
        return pagina_sin_tablas.extract_text() or ""

    except Exception as e:
        # Si algo falla en la detección de tablas, degradamos graciosamente
        # a extraer todo el texto sin filtrar
        logger.warning(f"Error al separar texto de tablas: {e}. Extrayendo texto completo.")
        return pagina.extract_text() or ""


def procesar_pagina(pagina: pdfplumber.page.Page, num_pagina: int) -> dict:
    """
    Procesa una página individual y devuelve un dict con texto y tablas.

    Estructura del dict resultante:
    {
        "page": 1,
        "text": "El Gobierno de la Comunidad de Madrid...",
        "tables": [
            [["Consejería", "2025", "2026"], ["Sanidad", "10.459", "11.009"], ...]
        ]
    }
    """
    logger.debug(f"  Procesando página {num_pagina}...")

    # Extraemos texto (excluyendo zonas de tablas)
    texto = extraer_texto_sin_tablas(pagina)

    # Extraemos tablas
    tablas_raw = pagina.extract_tables()
    tablas = [extraer_tabla(t) for t in tablas_raw] if tablas_raw else []

    # Estadísticas para logging
    num_chars = len(texto)
    num_tablas = len(tablas)
    num_filas = sum(len(t) for t in tablas)

    if num_chars > 0 or num_tablas > 0:
        logger.debug(
            f"    → {num_chars} caracteres de texto, "
            f"{num_tablas} tabla(s) con {num_filas} filas en total"
        )
    else:
        logger.debug(f"    → Página vacía o con solo imágenes")

    return {
        "page": num_pagina,
        "text": texto,
        "tables": tablas
    }


def extraer_pdf(ruta_pdf: Path | str, guardar_json: bool = True) -> dict:
    """
    Extrae todo el contenido de un PDF y opcionalmente lo guarda en JSON.

    Args:
        ruta_pdf:    Ruta al archivo PDF (absoluta o relativa)
        guardar_json: Si True, guarda el resultado en data/processed/

    Returns:
        Diccionario con la estructura:
        {
            "source": "nombre_archivo.pdf",
            "total_pages": 48,
            "pages": [
                {"page": 1, "text": "...", "tables": [...]},
                ...
            ]
        }
    """
    ruta_pdf = Path(ruta_pdf)

    if not ruta_pdf.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_pdf}")

    logger.info(f"Iniciando extracción: {ruta_pdf.name}")

    paginas_extraidas = []

    with pdfplumber.open(ruta_pdf) as pdf:
        total_paginas = len(pdf.pages)
        logger.info(f"  Total de páginas: {total_paginas}")

        for i, pagina in enumerate(pdf.pages, start=1):
            datos_pagina = procesar_pagina(pagina, i)
            paginas_extraidas.append(datos_pagina)

            # Log de progreso cada 10 páginas para PDFs grandes
            if i % 10 == 0:
                logger.info(f"  Progreso: {i}/{total_paginas} páginas procesadas")

    # Estadísticas finales
    total_chars = sum(len(p["text"]) for p in paginas_extraidas)
    total_tablas = sum(len(p["tables"]) for p in paginas_extraidas)
    paginas_con_contenido = sum(
        1 for p in paginas_extraidas
        if p["text"].strip() or p["tables"]
    )

    logger.info(
        f"Extracción completada: "
        f"{total_chars:,} caracteres, "
        f"{total_tablas} tablas, "
        f"{paginas_con_contenido}/{total_paginas} páginas con contenido"
    )

    resultado = {
        "source": ruta_pdf.name,
        "total_pages": total_paginas,
        "pages": paginas_extraidas
    }

    if guardar_json:
        _guardar_json(resultado, ruta_pdf.stem)

    return resultado


def _guardar_json(datos: dict, nombre_base: str) -> Path:
    """
    Guarda el resultado de extracción en data/processed/ como JSON.

    El nombre del archivo es el mismo que el PDF pero con extensión .json.
    Ejemplo: presupuesto_2026.pdf → data/processed/presupuesto_2026.json
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ruta_salida = PROCESSED_DIR / f"{nombre_base}.json"

    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON guardado en: {ruta_salida}")
    return ruta_salida


def inspeccionar_json(ruta_json: Path | str, num_paginas: int = 3) -> None:
    """
    Utilidad de inspección: muestra las primeras N páginas de un JSON extraído.
    Útil para verificar que la extracción fue correcta sin abrir el JSON completo.
    """
    ruta_json = Path(ruta_json)

    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)

    print(f"\n{'='*60}")
    print(f"Archivo: {datos['source']}")
    print(f"Total páginas: {datos['total_pages']}")
    print(f"{'='*60}")

    for pagina in datos["pages"][:num_paginas]:
        print(f"\n--- PÁGINA {pagina['page']} ---")

        texto_preview = pagina["text"][:300].replace("\n", " ")
        if texto_preview:
            print(f"TEXTO: {texto_preview}{'...' if len(pagina['text']) > 300 else ''}")
        else:
            print("TEXTO: (vacío)")

        if pagina["tables"]:
            for j, tabla in enumerate(pagina["tables"]):
                print(f"\nTABLA {j+1} ({len(tabla)} filas):")
                # Mostramos solo las primeras 3 filas de cada tabla
                for fila in tabla[:3]:
                    print(f"  {fila}")
                if len(tabla) > 3:
                    print(f"  ... ({len(tabla) - 3} filas más)")
        else:
            print("TABLAS: (ninguna)")


# ─── TEST BLOCK ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Bloque de test: ejecuta la extracción sobre los PDFs de data/raw/
    y muestra una preview del resultado.

    Uso:
        python ingestion/pdf_extractor.py
    """
    import sys

    # Buscamos PDFs en data/raw/ o en el directorio que se pase como argumento
    if len(sys.argv) > 1:
        pdfs = [Path(sys.argv[1])]
    else:
        pdfs = list(RAW_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No se encontraron PDFs en {RAW_DIR}")
        print("Copia un PDF a data/raw/ o pasa la ruta como argumento:")
        print("  python ingestion/pdf_extractor.py /ruta/al/archivo.pdf")
        sys.exit(1)

    for ruta_pdf in pdfs:
        print(f"\nProcesando: {ruta_pdf.name}")
        resultado = extraer_pdf(ruta_pdf, guardar_json=True)

        # Ruta del JSON generado
        ruta_json = PROCESSED_DIR / f"{ruta_pdf.stem}.json"

        # Mostramos preview de las primeras 2 páginas
        inspeccionar_json(ruta_json, num_paginas=2)

        # Estadísticas de tablas para evaluar calidad de extracción
        tablas_por_pagina = [
            (p["page"], len(p["tables"]))
            for p in resultado["pages"]
            if p["tables"]
        ]
        if tablas_por_pagina:
            print(f"\nPáginas con tablas detectadas:")
            for pag, num in tablas_por_pagina:
                print(f"  Página {pag}: {num} tabla(s)")
        else:
            print("\nATENCIÓN: No se detectaron tablas en ninguna página.")
            print("Posible causa: tablas renderizadas como imágenes o sin líneas visibles.")

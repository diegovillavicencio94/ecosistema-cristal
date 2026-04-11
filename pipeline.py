"""
pipeline.py — Orquestador CLI del Ecosistema de Cristal.

Punto de entrada único para operar el sistema completo desde la terminal.
Orquesta los bloques de ingesta y RAG sin que el usuario tenga que
conocer el orden interno de los módulos.

Modos de uso:
  # Ingesta: PDF → texto → chunks → embeddings → Qdrant
  python pipeline.py --ingest
  python pipeline.py --ingest data/raw/mi_presupuesto.pdf

  # Consulta RAG: pregunta → retriever → LLM → respuesta ciudadana
  python pipeline.py --query "¿Cuánto se gasta en sanidad?"
  python pipeline.py --query "..." --año 2026
  python pipeline.py --query "..." --top-k 3
  python pipeline.py --query "..." --comunidad Madrid
  python pipeline.py --query "..." --tipo-doc folleto

  # Estado del sistema
  python pipeline.py --status

Flujo --ingest (un PDF):
  PDF → pdf_extractor → normalizer → chunker → embedder → Qdrant

Flujo --ingest (sin argumento):
  Para cada PDF en data/raw/ → mismo flujo anterior

Flujo --query:
  pregunta → chain.preguntar() → imprime respuesta + fuentes
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# ─── Rutas ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

RAW_DIR       = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# BLOQUE 1 — INGESTA
# ════════════════════════════════════════════════════════════════════════════

def ingestar_pdf(ruta_pdf: Path) -> int:
    """
    Ejecuta el pipeline completo de ingesta para un único PDF.

    Pasos:
      1. pdf_extractor  → JSON con texto y tablas por página
      2. normalizer     → JSON con texto limpio y tablas normalizadas
      3. chunker        → JSON con chunks listos para embeber
      4. embedder       → puntos subidos a Qdrant

    Args:
        ruta_pdf: Ruta al archivo PDF a procesar

    Returns:
        Número de puntos insertados en Qdrant (0 si algo falla)
    """
    # Importamos aquí (no al inicio del módulo) para que --query no cargue
    # las dependencias de ingesta innecesariamente — y viceversa.
    # Es una optimización de tiempo de arranque, no un error de diseño.
    from ingestion.pdf_extractor import extraer_pdf
    from ingestion.normalizer   import normalizar_documento
    from ingestion.chunker      import chunkear_documento
    from ingestion.embedder     import embeber_y_cargar

    nombre = ruta_pdf.name
    print(f"\n{'='*60}")
    print(f"Ingestando: {nombre}")
    print(f"{'='*60}")

    t_inicio = time.time()

    # ── Paso 1: Extracción ───────────────────────────────────────────────
    print("\n[1/4] Extrayendo texto y tablas del PDF...")
    try:
        datos_raw = extraer_pdf(ruta_pdf, guardar_json=True)
    except Exception as e:
        logger.error(f"Error en extracción de {nombre}: {e}")
        return 0

    paginas_con_contenido = sum(
        1 for p in datos_raw["pages"]
        if p["text"].strip() or p["tables"]
    )
    print(f"      ✓ {datos_raw['total_pages']} páginas procesadas "
          f"({paginas_con_contenido} con contenido)")

    # ── Paso 2: Normalización ────────────────────────────────────────────
    print("\n[2/4] Normalizando texto y tablas...")
    try:
        datos_norm = normalizar_documento(datos_raw)
    except Exception as e:
        logger.error(f"Error en normalización de {nombre}: {e}")
        return 0

    chars_antes = sum(len(p["text"]) for p in datos_raw["pages"])
    chars_despues = sum(len(p["text"]) for p in datos_norm["pages"])
    print(f"      ✓ {chars_antes:,} → {chars_despues:,} caracteres "
          f"({chars_antes - chars_despues:+,} eliminados)")

    # Guardamos el JSON normalizado para trazabilidad
    import json
    ruta_norm = PROCESSED_DIR / f"{ruta_pdf.stem}_normalized.json"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(ruta_norm, "w", encoding="utf-8") as f:
        json.dump(datos_norm, f, ensure_ascii=False, indent=2)

    # ── Paso 3: Chunking ─────────────────────────────────────────────────
    print("\n[3/4] Dividiendo en chunks...")
    try:
        chunks = chunkear_documento(datos_norm)
    except Exception as e:
        logger.error(f"Error en chunking de {nombre}: {e}")
        return 0

    chunks_texto = sum(1 for c in chunks if c["type"] == "text")
    chunks_tabla = sum(1 for c in chunks if c["type"] == "table")
    print(f"      ✓ {len(chunks)} chunks generados "
          f"({chunks_texto} texto + {chunks_tabla} tabla)")

    # Guardamos los chunks para trazabilidad
    ruta_chunks = PROCESSED_DIR / f"{ruta_pdf.stem}_chunks.json"
    with open(ruta_chunks, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # ── Paso 4: Embedding y carga en Qdrant ──────────────────────────────
    print("\n[4/4] Generando embeddings y cargando en Qdrant...")
    print("      (esto puede tardar varios minutos según el tamaño del PDF)")
    try:
        insertados = embeber_y_cargar(chunks)
    except Exception as e:
        logger.error(f"Error en embedding/carga de {nombre}: {e}")
        return 0

    t_total = time.time() - t_inicio
    print(f"\n      ✓ {insertados} puntos insertados en Qdrant")
    print(f"      Tiempo total: {t_total:.1f}s")

    return insertados


def cmd_ingest(ruta_especifica: str | None) -> None:
    """
    Maneja el flag --ingest.

    Si se pasa una ruta, procesa ese PDF.
    Si no, procesa todos los PDFs de data/raw/ que aún no tienen
    chunks generados (para no reprocesar lo que ya está en Qdrant).

    Args:
        ruta_especifica: Ruta al PDF como string, o None para procesar data/raw/
    """
    if ruta_especifica:
        # ── Modo: PDF específico ─────────────────────────────────────────
        ruta_pdf = Path(ruta_especifica)
        if not ruta_pdf.exists():
            print(f"Error: no se encontró el archivo: {ruta_pdf}")
            sys.exit(1)
        if ruta_pdf.suffix.lower() != ".pdf":
            print(f"Error: el archivo debe ser un PDF: {ruta_pdf}")
            sys.exit(1)

        insertados = ingestar_pdf(ruta_pdf)
        if insertados > 0:
            print(f"\n✅ Ingesta completada: {insertados} puntos en Qdrant")
            print(f"   Dashboard: http://localhost:6333/dashboard")
        else:
            print(f"\n❌ La ingesta falló. Revisa los logs para más detalles.")
            sys.exit(1)

    else:
        # ── Modo: todos los PDFs de data/raw/ ───────────────────────────
        if not RAW_DIR.exists():
            print(f"Error: no existe la carpeta {RAW_DIR}")
            print(f"Crea la carpeta y copia tus PDFs en ella.")
            sys.exit(1)

        pdfs = sorted(RAW_DIR.glob("*.pdf"))
        if not pdfs:
            print(f"No se encontraron PDFs en {RAW_DIR}")
            print(f"Copia tus PDFs en data/raw/ y vuelve a ejecutar.")
            sys.exit(1)

        print(f"PDFs encontrados en data/raw/: {len(pdfs)}")

        # Identificamos cuáles ya tienen chunks (para informar, no para saltar)
        # Nota: no saltamos automáticamente porque el usuario puede querer
        # reindexar si cambió el modelo de embeddings o el tamaño de chunk
        ya_procesados = {
            p.stem.replace("_chunks", "")
            for p in PROCESSED_DIR.glob("*_chunks.json")
        } if PROCESSED_DIR.exists() else set()

        for pdf in pdfs:
            if pdf.stem in ya_procesados:
                print(f"\n⚠️  {pdf.name} ya tiene chunks generados.")
                respuesta = input("    ¿Reindexar igualmente? [s/N]: ").strip().lower()
                if respuesta != "s":
                    print(f"    Saltando {pdf.name}")
                    continue

            ingestar_pdf(pdf)

        print(f"\n{'='*60}")
        print(f"✅ Ingesta de todos los PDFs completada")
        print(f"   Dashboard: http://localhost:6333/dashboard")


# ════════════════════════════════════════════════════════════════════════════
# BLOQUE 2 — CONSULTA RAG
# ════════════════════════════════════════════════════════════════════════════

def cmd_query(
    pregunta: str,
    top_k: int,
    año: int | None,
    comunidad: str | None,
    tipo_doc: str | None,
) -> None:
    """
    Maneja el flag --query.

    Llama a chain.preguntar() con los filtros opcionales e imprime
    la respuesta formateada con fuentes al final.

    Args:
        pregunta:  Pregunta en lenguaje natural
        top_k:     Número de chunks a recuperar
        año:       Filtrar por año (ej. 2026)
        comunidad: Filtrar por comunidad autónoma (ej. "Madrid")
        tipo_doc:  Filtrar por tipo de documento ("folleto", "articulado", "memoria")
    """
    from rag.chain import preguntar

    print(f"\n{'='*60}")
    print(f"PREGUNTA: {pregunta}")
    if año:       print(f"  Filtro año: {año}")
    if comunidad: print(f"  Filtro comunidad: {comunidad}")
    if tipo_doc:  print(f"  Filtro tipo doc: {tipo_doc}")
    print(f"{'='*60}\n")

    print("Buscando en los documentos indexados...")

    resultado = preguntar(
        pregunta=pregunta,
        top_k=top_k,
        año=año,
        comunidad=comunidad,
        tipo_doc=tipo_doc,
    )

    # ── Respuesta ────────────────────────────────────────────────────────
    print("\nRESPUESTA:")
    print("─" * 60)
    print(resultado.respuesta)

    # ── Chunks usados (modo debug) ───────────────────────────────────────
    if resultado.chunks:
        print(f"\nCHUNKS RECUPERADOS ({len(resultado.chunks)}):")
        for i, chunk in enumerate(resultado.chunks, 1):
            print(
                f"  {i}. [{chunk['type']:5}] "
                f"{chunk['source']} · pág. {chunk['page']} · "
                f"score {chunk['score']}"
            )

    # ── Indicador de sin contexto ────────────────────────────────────────
    if resultado.sin_contexto:
        print("\n⚠️  El retriever no encontró chunks relevantes.")
        print("   Prueba a reformular la pregunta o comprueba que Qdrant tiene datos.")


# ════════════════════════════════════════════════════════════════════════════
# ESTADO DEL SISTEMA
# ════════════════════════════════════════════════════════════════════════════

def cmd_status() -> None:
    """
    Muestra el estado actual del sistema: Qdrant, PDFs indexados, colección.
    Útil para verificar antes de arrancar una sesión de trabajo.
    """
    from config import QDRANT_COLLECTION, QDRANT_HOST, QDRANT_PORT

    print(f"\n{'='*60}")
    print("ESTADO DEL SISTEMA — Ecosistema de Cristal")
    print(f"{'='*60}")

    # ── Qdrant ───────────────────────────────────────────────────────────
    print("\n── Qdrant ──")
    try:
        from qdrant_client import QdrantClient
        cliente = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        info = cliente.get_collection(QDRANT_COLLECTION)
        print(f"  Estado:      ✅ Corriendo en {QDRANT_HOST}:{QDRANT_PORT}")
        print(f"  Colección:   {QDRANT_COLLECTION}")
        print(f"  Puntos:      {info.points_count}")
        print(f"  Dimensiones: {info.config.params.vectors.size}")
    except Exception as e:
        print(f"  Estado:      ❌ No disponible ({e})")
        print(f"  Solución:    docker compose up -d")

    # ── PDFs en data/raw/ ────────────────────────────────────────────────
    print("\n── PDFs en data/raw/ ──")
    if RAW_DIR.exists():
        pdfs = sorted(RAW_DIR.glob("*.pdf"))
        if pdfs:
            ya_procesados = {
                p.stem.replace("_chunks", "")
                for p in PROCESSED_DIR.glob("*_chunks.json")
            } if PROCESSED_DIR.exists() else set()

            for pdf in pdfs:
                estado = "✅ indexado" if pdf.stem in ya_procesados else "⏳ pendiente"
                print(f"  {estado}  {pdf.name}")
        else:
            print("  (ningún PDF encontrado)")
    else:
        print(f"  (carpeta {RAW_DIR} no existe)")

    # ── JSONs en data/processed/ ─────────────────────────────────────────
    print("\n── Archivos procesados en data/processed/ ──")
    if PROCESSED_DIR.exists():
        jsons = sorted(PROCESSED_DIR.glob("*.json"))
        if jsons:
            for j in jsons:
                print(f"  {j.name}")
        else:
            print("  (ningún JSON encontrado)")
    else:
        print(f"  (carpeta {PROCESSED_DIR} no existe)")


# ════════════════════════════════════════════════════════════════════════════
# CLI — ARGPARSE
# ════════════════════════════════════════════════════════════════════════════

def construir_parser() -> argparse.ArgumentParser:
    """
    Define los argumentos de la CLI.

    Usamos argparse (librería estándar de Python) para parsear los flags.
    No necesita instalarse — viene incluida en Python.
    """
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="Ecosistema de Cristal — Orquestador CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Indexar todos los PDFs de data/raw/:
  python pipeline.py --ingest

  # Indexar un PDF específico:
  python pipeline.py --ingest data/raw/folleto_presupuestos_2026.pdf

  # Consulta básica:
  python pipeline.py --query "¿Cuánto se gasta en sanidad?"

  # Consulta con filtros:
  python pipeline.py --query "gasto por consejería" --año 2026 --top-k 3

  # Ver estado del sistema:
  python pipeline.py --status
        """
    )

    # Grupo mutuamente excluyente: solo uno de los tres modos a la vez
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--ingest",
        nargs="?",           # 0 o 1 argumento (None si no se pasa ninguno)
        const="__ALL__",     # valor cuando se usa --ingest sin argumento
        metavar="PDF",
        help="Ingestar un PDF específico o todos los de data/raw/"
    )
    grupo.add_argument(
        "--query",
        metavar="PREGUNTA",
        help="Hacer una consulta RAG en lenguaje natural"
    )
    grupo.add_argument(
        "--status",
        action="store_true",
        help="Mostrar estado del sistema (Qdrant, PDFs, colección)"
    )

    # Opciones de consulta (solo aplican con --query)
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        metavar="N",
        help="Número de chunks a recuperar (default: 5)"
    )
    parser.add_argument(
        "--año",
        type=int,
        default=None,
        metavar="AÑO",
        help="Filtrar por año presupuestario (ej. 2026)"
    )
    parser.add_argument(
        "--comunidad",
        type=str,
        default=None,
        metavar="NOMBRE",
        help="Filtrar por comunidad autónoma (ej. Madrid)"
    )
    parser.add_argument(
        "--tipo-doc",
        type=str,
        default=None,
        choices=["folleto", "articulado", "memoria", "otro"],
        metavar="TIPO",
        help="Filtrar por tipo de documento"
    )

    return parser


# ════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = construir_parser()
    args = parser.parse_args()

    if args.ingest is not None:
        # --ingest sin argumento → args.ingest == "__ALL__"
        # --ingest ruta/archivo.pdf → args.ingest == "ruta/archivo.pdf"
        ruta = None if args.ingest == "__ALL__" else args.ingest
        cmd_ingest(ruta)

    elif args.query:
        cmd_query(
            pregunta=args.query,
            top_k=args.top_k,
            año=args.año,
            comunidad=args.comunidad,
            tipo_doc=args.tipo_doc,
        )

    elif args.status:
        cmd_status()


if __name__ == "__main__":
    main()

"""
Orquesta el proceso completo de indexación de documentos.

El indexador coordina las distintas etapas del pipeline sin contener
la lógica específica de ninguna de ellas.

Flujo:

indexar_documentos()
        │
        ▼
_obtener_markdowns_limpios()
        │
        ├── Si existe el .md limpio → lo reutiliza
        ├── Si solo existe el raw → lo limpia
        └── Si no existe ninguno → convierte PDF + limpia
        │
        ▼
cargar_documentos()
        │
        ▼
Para cada Documento:
        │
        ▼
parsear_markdown()
        │
        ▼
¿Es un manual con Knowledge?
        │
   ┌────┴────┐
   │         │
  Sí         No
   │         │
crear_arbol  crear_chunks
crear_chunks
enlazar
guardar_json
   │         │
   └────┬────┘
        ▼
Añadir chunks
        ▼
Embeddings
        ▼
Vector Store (ChromaDB)
"""

import logging
from pathlib import Path

from src.core.models import Chunk, Documento
from src.ingestion.docling_converter import convertir_pdf_a_markdown
from src.ingestion.text_cleaner import limpiar_archivo_markdown
from src.ingestion.document_loader import cargar_documentos
from src.ingestion.markdown_parser import MarkdownNode, parsear_markdown
from src.knowledge.builder import crear_arbol
from src.knowledge.linker import enlazar
from src.knowledge.exporter import guardar_json
from src.ingestion.chunker import crear_chunks_documento
from src.rag.embeddings import crear_embeddings_chunks
from src.rag.vector_store import VectorStore

from src.core.config import (
    CARPETA_DOCUMENTOS,
    CARPETA_MARKDOWN_RAW,
    CARPETA_MARKDOWN_CLEAN,
    CARPETA_KNOWLEDGE,
    MANUALES_CON_KNOWLEDGE,
)

logger = logging.getLogger(__name__)

def _es_manual_con_knowledge(documento: Documento) -> bool:
    """
    Indica si el documento debe generar un árbol de conocimiento.
    """

    return documento.metodologia.nombre in MANUALES_CON_KNOWLEDGE


def _procesar_manual(
    documento: Documento,
    raiz_markdown: MarkdownNode,
) -> list[Chunk]:
    """
    Procesa un manual con que dispone de árbol de conocimiento.

    Args:
        documento: Documento a procesar.
        raiz_markdown: Nodo raíz del Markdown parseado.

    Returns:
        Lista de chunks generados a partir del documento.
    """

    arbol = crear_arbol(
        raiz_markdown,
        documento.metodologia,
    )

    chunks = crear_chunks_documento(
        documento,
        raiz_markdown,
    )

    enlazar(
        arbol,
        chunks,
    )

    ruta_json = CARPETA_KNOWLEDGE / f"{documento.nombre}.json"

    guardar_json(
        arbol,
        ruta_json,
    )

    return chunks


def _procesar_documento_extra(
    documento: Documento,
    raiz_markdown: MarkdownNode,
) -> list[Chunk]:
    """
    Procesa un documento que no genera árbol de conocimiento.
    """

    return crear_chunks_documento(
        documento,
        raiz_markdown,
    )


def indexar_documentos() -> None:
    """
    Ejecuta el pipeline completo de indexación.

    Coordina todas las etapas necesarias para transformar los documentos
    en registros almacenados en la base vectorial.
    """

    try:

        logger.info("Iniciando indexación...")

        markdowns = _obtener_markdowns_limpios()

        if not markdowns:
            logger.warning("No hay documentos para indexar.")
            return

        logger.info(
            "%d markdowns encontrados.",
            len(markdowns),
        )

        documentos = cargar_documentos(markdowns)
        
        logger.info(
            "%d documentos cargados.",
            len(documentos),
        )

        todos_los_chunks: list[Chunk] = []

        for documento in documentos:

            raiz_markdown = parsear_markdown(documento.texto)

            if _es_manual_con_knowledge(documento):
                
                chunks = _procesar_manual(
                    documento,
                    raiz_markdown,
                )
            else:
                chunks = _procesar_documento_extra(
                    documento,
                    raiz_markdown,
                )

            todos_los_chunks.extend(chunks)
            
        logger.info(
            "%d chunks generados.",
            len(todos_los_chunks),
        )

        embeddings = crear_embeddings_chunks(todos_los_chunks)
        
        logger.info("Embeddings creados")

        vector_store = VectorStore()

        vector_store.indexar_chunks(
            todos_los_chunks,
            embeddings,
        )
        
        logger.info("Vectores indexados")
        logger.info("Indexación finalizada.")

    except Exception:
        logger.exception("La indexación ha fallado.")
        raise


def _obtener_markdowns_limpios() -> list[Path]:
    """
    Obtiene los Markdown limpios necesarios para continuar el pipeline.

    Para cada PDF:

    - reutiliza el Markdown limpio si existe;
    - si solo existe el Markdown raw, lo limpia;
    - si no existe ninguno, convierte el PDF y lo limpia.

    Returns:
        Lista con las rutas de los Markdown limpios.
    """

    markdowns_limpios: list[Path] = []

    pdfs = sorted(CARPETA_DOCUMENTOS.rglob("*.pdf"))

    if not pdfs:
        raise FileNotFoundError(
            "No se han encontrado archivos PDF en la carpeta documents."
        )

    for ruta_pdf in pdfs:

        metodologia = ruta_pdf.parent.name

        nombre = ruta_pdf.stem

        ruta_raw = CARPETA_MARKDOWN_RAW / metodologia / f"{nombre}.md"

        ruta_clean = CARPETA_MARKDOWN_CLEAN / metodologia / f"{nombre}.md"

        # Existe el MD limpio
        if ruta_clean.exists():
            logger.debug("Markdown limpio encontrado: %s", ruta_clean.name)

            markdowns_limpios.append(ruta_clean)

            continue

        # NO existe el MD limpio pero SI el raw
        if ruta_raw.exists():
            logger.info("Limpiando Markdown: %s", ruta_raw.name)

            ruta_clean = limpiar_archivo_markdown(ruta_raw, ruta_clean)

            markdowns_limpios.append(ruta_clean)

            continue

        # NO existen los MD limpios/raw solo PDF
        logger.info("Convirtiendo PDF: %s", ruta_pdf.name)

        ruta_raw = convertir_pdf_a_markdown(ruta_pdf)

        ruta_clean = limpiar_archivo_markdown(
            ruta_raw,
            ruta_clean,
        )

        markdowns_limpios.append(ruta_clean)

        logger.debug("Markdown limpio generado: %s", ruta_clean.name)
        
    return markdowns_limpios

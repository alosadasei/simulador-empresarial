"""
Convierte un archivo PDF a Markdown mediante Docling.

El archivo Markdown generado se guarda dentro de:

data/markdown_raw/<metodologia>/<nombre_documento>.md

La metodología se obtiene automáticamente a partir del nombre
de la carpeta donde se encuentra el PDF.
"""

import logging
from pathlib import Path
from docling.document_converter import DocumentConverter
from src.core.config import CARPETA_MARKDOWN_RAW

logger = logging.getLogger(__name__)
converter = DocumentConverter()


def convertir_pdf_a_markdown(ruta_pdf: str | Path) -> Path:
    """
    Convierte un archivo PDF a Markdown mediante Docling.

    La metodología se detecta por el nombre de la carpeta
    que contiene el PDF.

    Ejemplo:

        documents/lean_startup/manual.pdf

    Generará:

        data/markdown_raw/lean_startup/manual.md

    Args:
        ruta_pdf: Ruta del archivo PDF que se va a convertir.

    Returns:
        Ruta del archivo Markdown generado.
    """

    ruta_pdf = Path(ruta_pdf)

    if not ruta_pdf.exists():
        raise FileNotFoundError(
            f"No existe el archivo PDF: {ruta_pdf}"
        )

    if not ruta_pdf.is_file():
        raise ValueError(
            f"La ruta no corresponde a un archivo: {ruta_pdf}"
        )

    if ruta_pdf.suffix.lower() != ".pdf":
        raise ValueError(
            f"El archivo no tiene extensión PDF: {ruta_pdf}"
        )

    metodologia = ruta_pdf.parent.name

    ruta_markdown = CARPETA_MARKDOWN_RAW / metodologia / f"{ruta_pdf.stem}.md"

    ruta_markdown.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.debug("Convirtiendo PDF: %s", ruta_pdf)
    logger.debug("Metodología detectada: %s", metodologia)

    try: 
        resultado = converter.convert(ruta_pdf)

        texto_markdown = (
            resultado.document.export_to_markdown()
        )

    except Exception as error:
        raise RuntimeError(
            f"Error al convertir el PDF '{ruta_pdf}' a Markdown."
        ) from error

    ruta_markdown.write_text(
        texto_markdown,
        encoding="utf-8",
    )

    logger.debug("Conversión terminada correctamente.")
    logger.debug("Markdown guardado en: %s", ruta_markdown)

    return ruta_markdown


def convertir_carpeta(ruta_carpeta: str | Path) -> list[Path]:
    """
    Convierte todos los archivos PDF contenidos en una carpeta
    (incluyendo subcarpetas) a Markdown.

    Args:
        ruta_carpeta: Carpeta donde buscar los archivos PDF.

    Returns:
        Lista con las rutas de los Markdown generados.
    """

    ruta_carpeta = Path(ruta_carpeta)

    if not ruta_carpeta.exists():
        raise FileNotFoundError(f"No existe la carpeta: {ruta_carpeta}")

    if not ruta_carpeta.is_dir():
        raise ValueError(f"La ruta no corresponde a una carpeta: {ruta_carpeta}")

    markdowns = []

    for ruta_pdf in ruta_carpeta.rglob("*.pdf"):
        markdown = convertir_pdf_a_markdown(ruta_pdf)
        markdowns.append(markdown)

    return markdowns


if __name__ == "__main__":
    logger.info(
        "Este módulo proporciona funciones para convertir "
        "archivos PDF a Markdown mediante Docling."
    )

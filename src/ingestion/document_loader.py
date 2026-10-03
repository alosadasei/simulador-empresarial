"""
Carga documentos Markdown limpios y los convierte en objetos Documento.

La metodología se obtiene automáticamente a partir del nombre
de la carpeta que contiene cada archivo Markdown.
"""

from pathlib import Path
from src.core.models import Documento, Metodologia
import logging

logger = logging.getLogger(__name__)


def cargar_documento(
    ruta_md: Path,
    metodologia: Metodologia,
) -> Documento:
    """
    Carga un archivo Markdown y lo convierte en un objeto Documento.

    Args:
        ruta_md: Ruta del archivo Markdown.
        metodologia: Metodología asociada al documento.

    Returns:
        Objeto Documento con el contenido del archivo.
    """

    if not ruta_md.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta_md}")

    if not ruta_md.is_file():
        raise ValueError(f"La ruta no corresponde a un archivo: {ruta_md}")

    if ruta_md.suffix.lower() != ".md":
        raise ValueError(f"El archivo no tiene extensión Markdown: {ruta_md}")

    texto = ruta_md.read_text(encoding="utf-8")

    return Documento(
        metodologia=metodologia,
        nombre=ruta_md.stem,
        texto=texto,
        ruta=str(ruta_md),
    )


def cargar_documentos(
    rutas_markdown: list[Path],
) -> list[Documento]:
    """
    Convierte una lista de archivos Markdown en objetos Documento.

    La metodología se obtiene automáticamente a partir del nombre
    de la carpeta que contiene cada archivo.

    Args:
        rutas_markdown: Lista de archivos Markdown limpios.

    Returns:
        Lista de objetos Documento.
    """

    documentos = []

    for ruta_md in rutas_markdown:

        nombre_metodologia = ruta_md.parent.name

        metodologia = Metodologia(nombre=nombre_metodologia)

        documento = cargar_documento(
            ruta_md=ruta_md,
            metodologia=metodologia,
        )

        documentos.append(documento)

    return documentos


if __name__ == "__main__":

    logger.info("Este módulo proporciona funciones para cargar documentos Markdown.")

"""
Servicios auxiliares para la gestión de documentos.

Incluye funciones para obtener metodologías, localizar carpetas
y validar documentos.
"""

from pathlib import Path
from src.core.config import CARPETA_DOCUMENTOS


def obtener_metodologias() -> list[str]:
    """
    Devuelve las metodologías disponibles a partir de las
    subcarpetas existentes dentro de documents.
    """

    if not CARPETA_DOCUMENTOS.exists():
        return []

    metodologias = [
        carpeta.name for carpeta in CARPETA_DOCUMENTOS.iterdir() if carpeta.is_dir()
    ]

    return sorted(metodologias)


def mostrar_nombre_metodologia(
    metodologia: str,
) -> str:
    """
    Convierte el nombre de una carpeta en un texto legible.

    Ejemplo:
        lean_startup -> Lean Startup
    """

    return metodologia.replace("_", " ").title()


def obtener_carpeta_metodologia(
    metodologia: str | None,
) -> Path | None:
    """
    Devuelve la carpeta asociada a una metodología.

    Si la metodología no existe o no es válida,
    devuelve None.
    """

    if not metodologia:
        return None

    carpeta_metodologia = CARPETA_DOCUMENTOS / metodologia

    if not carpeta_metodologia.exists():
        return None

    if not carpeta_metodologia.is_dir():
        return None

    return carpeta_metodologia


def obtener_documentos(
    metodologia: str,
) -> list[str]:
    """
    Devuelve los archivos PDF de una metodología.
    """

    carpeta_metodologia = obtener_carpeta_metodologia(metodologia)

    if carpeta_metodologia is None:
        return []

    documentos = [
        archivo.name
        for archivo in carpeta_metodologia.iterdir()
        if archivo.is_file() and archivo.suffix.lower() == ".pdf"
    ]

    return sorted(documentos)


def es_pdf(
    nombre_archivo: str,
) -> bool:
    """
    Comprueba si un archivo tiene extensión PDF.
    """

    return Path(nombre_archivo).suffix.lower() == ".pdf"




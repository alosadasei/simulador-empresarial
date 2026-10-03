"""Módulo de limpieza de archivos Markdown."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from src.core.config import (
    CARPETA_MARKDOWN_RAW,
    CARPETA_MARKDOWN_CLEAN,
)

CABECERAS_PIES_RUIDO = {
    "Lean Startup en Educación",
    "Lean Startup en Educacion",
    'porque "emprender no es una opción"',
    'porque "emprender no es una opcion"',
    "www.pablopenalver.com",
}


SIMBOLOS_OCR = {
    "",
    "口",
    "司",
    "！",
}


LIMPIEZAS = (
    lambda texto: eliminar_marcadores_imagen(texto),
    lambda texto: eliminar_cabeceras_y_pies(texto),
    lambda texto: eliminar_numeros_pagina(texto),
    lambda texto: eliminar_simbolos_ocr(texto),
    lambda texto: eliminar_isbn(texto),
    lambda texto: unir_palabras_partidas(texto),
    lambda texto: unir_parrafos_partidos(texto),
    lambda texto: normalizar_formato(texto),
    lambda texto: eliminar_lineas_vacias(texto),
)


def limpiar_texto(texto: str) -> str:
    """
    Limpia y normaliza el contenido de un documento Markdown.
    """

    for limpieza in LIMPIEZAS:
        texto = limpieza(texto)

    return texto.strip()


def eliminar_marcadores_imagen(texto: str) -> str:
    """Elimina los marcadores de imagen generados al convertir el PDF."""

    return texto.replace("<!-- image -->", "")


def eliminar_cabeceras_y_pies(texto: str) -> str:
    """Elimina cabeceras y pies de página repetidos."""

    lineas_limpias = []

    for linea in texto.splitlines():
        contenido = linea.strip()

        if contenido in CABECERAS_PIES_RUIDO:
            continue

        lineas_limpias.append(linea)

    return "\n".join(lineas_limpias)


def eliminar_numeros_pagina(texto: str) -> str:
    """Elimina líneas que contienen únicamente un número de página."""

    lineas_limpias = []

    for linea in texto.splitlines():
        contenido = linea.strip()

        if contenido.isdigit():
            continue

        lineas_limpias.append(linea)

    return "\n".join(lineas_limpias)


def eliminar_simbolos_ocr(texto: str) -> str:
    """Elimina símbolos extraños introducidos durante la extracción OCR."""

    for simbolo in SIMBOLOS_OCR:
        texto = texto.replace(simbolo, "")

    return texto


def eliminar_isbn(texto: str) -> str:
    """Elimina las líneas que contienen códigos ISBN."""

    patron_isbn = re.compile(
        r"\bISBN(?:-1[03])?\s*:?\s*[\dXx\- ]{10,20}\b",
        re.IGNORECASE,
    )

    lineas_limpias = []

    for linea in texto.splitlines():

        if patron_isbn.search(linea):
            continue

        lineas_limpias.append(linea)

    return "\n".join(lineas_limpias)


def unir_palabras_partidas(texto: str) -> str:
    """
    Une palabras cortadas mediante un guion y un salto de línea.
    """

    return re.sub(
        r"([a-záéíóúüñ])-\s*\n\s*([a-záéíóúüñ])",
        r"\1\2",
        texto,
        flags=re.IGNORECASE,
    )


def unir_parrafos_partidos(texto: str) -> str:
    """
    Une líneas consecutivas que parecen pertenecer al mismo párrafo.

    Conserva títulos, listas, tablas y bloques Markdown.
    """

    lineas = texto.splitlines()
    resultado = []
    parrafo_actual = ""

    for linea in lineas:

        contenido = linea.strip()

        if not contenido:

            if parrafo_actual:
                resultado.append(parrafo_actual)
                parrafo_actual = ""

            resultado.append("")
            continue

        if es_elemento_markdown(contenido):

            if parrafo_actual:
                resultado.append(parrafo_actual)
                parrafo_actual = ""

            resultado.append(contenido)
            continue

        if not parrafo_actual:
            parrafo_actual = contenido
        else:
            parrafo_actual += " " + contenido

    if parrafo_actual:
        resultado.append(parrafo_actual)

    return "\n".join(resultado)


def es_elemento_markdown(linea: str) -> bool:
    """
    Comprueba si una línea es un elemento Markdown que no debe unirse.
    """

    patrones_markdown = (
        "#",
        "- ",
        "* ",
        "+ ",
        "> ",
        "|",
        "```",
    )

    if linea.startswith(patrones_markdown):
        return True

    if re.match(r"^\d+[.)]\s+", linea):
        return True

    return False


def normalizar_formato(texto: str) -> str:
    """Normaliza espacios sin destruir el Markdown."""

    texto = texto.replace("\u2003", " ")
    texto = texto.replace("\u00a0", " ")
    texto = texto.replace("\t", " ")

    texto = re.sub(r"[ ]{2,}", " ", texto)

    return "\n".join(linea.strip() for linea in texto.splitlines())


def eliminar_lineas_vacias(texto: str) -> str:
    """Conserva como máximo una línea vacía entre bloques."""

    return re.sub(r"\n{3,}", "\n\n", texto)


def limpiar_archivo_markdown(
    ruta_entrada: Path,
    ruta_salida: Path,
) -> Path:
    """
    Limpia un archivo Markdown y devuelve la ruta del archivo generado.
    """

    if not ruta_entrada.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta_entrada}")

    if ruta_entrada.suffix.lower() != ".md":
        raise ValueError(f"El archivo no es Markdown: {ruta_entrada}")

    texto_original = ruta_entrada.read_text(encoding="utf-8")

    texto_limpio = limpiar_texto(texto_original)

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ruta_salida.write_text(
        texto_limpio,
        encoding="utf-8",
    )

    logger.debug("Archivo limpio creado: %s", ruta_salida)

    return ruta_salida


def limpiar_markdowns(
    rutas_markdown: list[Path],
) -> list[Path]:
    """
    Limpia una lista de archivos Markdown.

    Conserva la estructura de carpetas dentro de
    data/markdown_clean.
    """

    rutas_limpias = []

    for ruta_entrada in rutas_markdown:

        ruta_relativa = ruta_entrada.relative_to(CARPETA_MARKDOWN_RAW)

        ruta_salida = CARPETA_MARKDOWN_CLEAN / ruta_relativa

        ruta_limpia = limpiar_archivo_markdown(
            ruta_entrada,
            ruta_salida,
        )

        rutas_limpias.append(ruta_limpia)

    logger.debug("\nSe han limpiado %d archivos Markdown", len(rutas_limpias))

    return rutas_limpias


if __name__ == "__main__":

    logger.info("Este módulo proporciona funciones para limpiar archivos Markdown.")

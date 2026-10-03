"""
Utilidad para convertir tablas Markdown en texto natural, pensado para
mejorar la calidad semántica de los embeddings de chunks que contienen
tablas (donde el ruido sintáctico de '|' y '---' diluye la señal).

No modifica el texto original del chunk (que se sigue mostrando tal cual
al usuario); solo se usa para generar una versión "aplanada" que se puede
concatenar o sustituir en texto_embedding().
"""

import re
import logging

_FILA_TABLA_RE = re.compile(r"^\s*\|.*\|\s*$")
UMBRAL_CELDAS_VACIAS = 0.15

logger = logging.getLogger(__name__)


def _es_fila_separadora(fila: str) -> bool:
    """Detecta filas del tipo | --- | --- | usadas para separar cabecera y cuerpo."""
    
    contenido = fila.strip().strip("|")
    celdas = [c.strip() for c in contenido.split("|")]
    return all(re.fullmatch(r":?-{2,}:?", c) for c in celdas if c != "")


def _parsear_fila(fila: str) -> list[str]:
    """Convierte una fila '| a | b | c |' en ['a', 'b', 'c']."""
    
    contenido = fila.strip().strip("|")
    return [celda.strip() for celda in contenido.split("|")]


def aplanar_tablas(texto: str) -> str:
    """
    Busca bloques de tabla Markdown dentro de un texto y los convierte
    en frases del tipo 'Cabecera - Columna: valor1, valor2' por cada fila,
    dejando el resto del texto (párrafos normales) intacto.
    """

    lineas = texto.splitlines()
    resultado: list[str] = []

    i = 0
    while i < len(lineas):
        linea = lineas[i]

        if _FILA_TABLA_RE.match(linea):
            # Recoger todas las líneas consecutivas que formen la tabla
            bloque = []
            while i < len(lineas) and _FILA_TABLA_RE.match(lineas[i]):
                bloque.append(lineas[i])
                i += 1

            resultado.append(_tabla_a_texto(bloque))
        else:
            resultado.append(linea)
            i += 1

    return "\n".join(resultado)


def _tabla_a_texto(bloque: list[str]) -> str:
    """
    Convierte un bloque de filas de tabla Markdown en frases naturales.

    Se distinguen dos tipos de tablas:

    - Tablas de categorías: cada columna representa una categoría y sus
      filas contienen elementos de dicha categoría.
    - Resto de tablas: cada fila representa un registro y se transforma
      en frases del tipo:
          "{contexto} - {etiqueta} - {columna}: {valor}."
    """

    filas = [fila for fila in bloque if not _es_fila_separadora(fila)]

    if len(filas) < 2:
        return ""

    cabecera = _parsear_fila(filas[0])
    cuerpo = [_parsear_fila(fila) for fila in filas[1:]]

    # Completar filas más cortas con cadenas vacías.
    for fila in cuerpo:
        fila.extend([""] * (len(cabecera) - len(fila)))

    if _es_tabla_por_columnas(cabecera, cuerpo):
        return _tabla_por_columnas(cabecera, cuerpo)

    return _tabla_por_filas(cabecera, cuerpo)


def _es_tabla_por_columnas(cabecera: list[str], cuerpo: list[list[str]]) -> bool:
    """
    Heurística: si una proporción notable de celdas está vacía, es más
    probable que la tabla sea de categorías por columna.
    """

    total_celdas = 0
    celdas_vacias = 0

    for fila in cuerpo:
        for valor in fila:
            total_celdas += 1
            if not valor:
                celdas_vacias += 1

    if total_celdas == 0:
        return False

    return (celdas_vacias / total_celdas) > UMBRAL_CELDAS_VACIAS


def _tabla_por_filas(cabecera: list[str], cuerpo: list[list[str]]) -> str:
    """Formato 'etiqueta_fila - columna: valor.' usando la primera columna como etiqueta."""

    contexto = cabecera[0]
    frases = []

    for fila in cuerpo:
        if fila[0].isdigit() and len(fila) > 1:
            etiqueta_fila = fila[1]
        else:
            etiqueta_fila = fila[0]

        for nombre_columna, valor in zip(cabecera[1:], fila[1:]):
            if valor:
                frases.append(f"{contexto} - {etiqueta_fila} - {nombre_columna}: {valor}.")

    return "\n".join(frases)


def _tabla_por_columnas(cabecera: list[str], cuerpo: list[list[str]]) -> str:
    """Formato 'columna: valor1, valor2, valor3.' agrupando cada columna como categoría."""

    frases = []

    for indice_columna, nombre_columna in enumerate(cabecera):
        valores = [
            fila[indice_columna]
            for fila in cuerpo
            if fila[indice_columna]
        ]

        if valores:
            frases.append(f"{nombre_columna}: {', '.join(valores)}.")

    return "\n".join(frases)


if __name__ == "__main__":
    logger.info("Esta utilidad no está pensada para ejecutarse directamente. Se importa desde src/core/models.py para aplanar tablas en chunks.")

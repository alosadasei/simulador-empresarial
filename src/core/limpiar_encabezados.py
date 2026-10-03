"""
Utilidad para eliminar la numeración estructural de los encabezados
cuando se generan los embeddings.

No modifica el texto original; únicamente limpia títulos como:

    4. APLICACIONES
    5.3 INFOGRAFÍA
    2.3.1 MATRIZ DAFO

dejando únicamente:

    APLICACIONES
    INFOGRAFÍA
    MATRIZ DAFO
"""

import re

_NUMERACION_RE = re.compile(r"^\d+(?:\.\d+)*\.\s+")


def limpiar_encabezado(texto: str) -> str:
    """
    Elimina la numeración estructural situada al inicio
    de un encabezado.
    """

    return _NUMERACION_RE.sub(
        "",
        texto,
    ).strip()

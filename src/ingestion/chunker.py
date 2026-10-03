"""
Se encarga de dividir un Documento en una lista de Chunk,
procurando que cada uno represente una unidad coherente de conocimiento.
 
Reglas de división:
- El nivel 1 (#) nunca genera un chunk propio; únicamente identifica el
  módulo o unidad y se almacena como contexto del resto de chunks.
- Los niveles 2, 3, 4 y 5 (##, ###, ####, #####) generan un chunk únicamente cuando
  contienen texto propio (con independencia de que además tengan hijos,
  que generarán sus propios chunks por separado).
- Si un encabezado no contiene texto propio, actúa únicamente como nodo
  de la jerarquía y proporciona contexto a sus descendientes, sin generar
  chunk.
- Cada chunk guarda, según hasta qué nivel llegue su ruta:
    titulo      -> header de nivel 1 (módulo)
    subtitulo   -> header de nivel 2, si existe en la ruta
    seccion     -> header de nivel 3, si existe en la ruta
    subseccion  -> header de nivel 4, si existe en la ruta
    apartado    -> header de nivel 5, si existe en la ruta
"""

import logging
from src.core.models import Chunk, Documento
from src.ingestion.markdown_parser import MarkdownNode

logger = logging.getLogger(__name__)

# Relación entre el nivel del encabezado Markdown y el atributo
# correspondiente del modelo Chunk.
_CAMPO_POR_NIVEL = {
    1: "titulo",
    2: "subtitulo",
    3: "seccion",
    4: "subseccion",
    5: "apartado",
}


def _guardar_chunk(
    chunks: list[Chunk],
    documento: Documento,
    indice: int,
    contexto: dict[str, str | None],
    texto: str,
) -> int:
    """
    Crea un Chunk a partir del texto del nodo y lo añade a la lista,
    si contiene contenido.

    Args:
        chunks: Lista donde se almacenan los chunks generados.
        documento: Documento al que pertenece el chunk.
        indice: Posición del chunk dentro del documento.
        contexto: Diccionario con titulo/subtitulo/seccion/subseccion/apartado ya resueltos.
        texto: Texto del nodo (ya venido de la property nodo.texto).

    Returns:
        El siguiente índice disponible.
    """

    if texto:
        chunks.append(
            Chunk(
                documento=documento,
                indice=indice,
                texto=texto,
                titulo=contexto.get("titulo"),
                subtitulo=contexto.get("subtitulo"),
                seccion=contexto.get("seccion"),
                subseccion=contexto.get("subseccion"),
                apartado=contexto.get("apartado"),
            )
        )
        indice += 1

    return indice


def _generar_chunks(
    nodo: MarkdownNode,
    documento: Documento,
    contexto: dict[str, str | None],
    chunks: list[Chunk],
    indice: int,
) -> int:
    """
    Recorre el árbol de encabezados generando un Chunk para cada nodo
    de nivel 2 o superior que contenga texto propio, propagando el
    contexto jerárquico (titulo, subtitulo, seccion, subseccion, apartado).
    """

    nuevo_contexto = contexto
    campo = _CAMPO_POR_NIVEL.get(nodo.nivel)

    if campo is not None and nodo.titulo is not None:
        nuevo_contexto = contexto.copy()
        nuevo_contexto[campo] = nodo.titulo

        # Si este nodo es, p.ej., un nuevo subtitulo (##), los niveles más
        # profundos que aún no se han visto (seccion, subseccion, apartado) deben
        # limpiarse para no arrastrar los de una rama anterior del árbol.
        for nivel_mayor, campo_mayor in _CAMPO_POR_NIVEL.items():
            if nivel_mayor > nodo.nivel:
                nuevo_contexto[campo_mayor] = None

    # Texto suelto antes de cualquier header (nivel 0): siempre se guarda aparte
    if nodo.nivel == 0:
        indice = _guardar_chunk(chunks, documento, indice, {}, nodo.texto)

    # Nivel 1: nunca genera chunk propio, solo aporta contexto (ya hecho arriba)
    elif nodo.nivel == 1:
        pass

    # Los niveles superiores al 1 generan chunk únicamente si contienen texto propio.
    else:
        indice = _guardar_chunk(chunks, documento, indice, nuevo_contexto, nodo.texto)

    # Los hijos siempre se procesan aparte, generen o no chunk propio el padre
    for hijo in nodo.hijos:
        indice = _generar_chunks(hijo, documento, nuevo_contexto, chunks, indice)

    return indice


def crear_chunks_documento(
    documento: Documento,
    raiz_markdown: MarkdownNode,
) -> list[Chunk]:
    """
    Divide un Documento en una lista de Chunk utilizando los encabezados
    Markdown como separadores de secciones, respetando la jerarquía:
    el nivel 1 se guarda como módulo/contexto y los headers (a partir del nivel 2) generan chunks si tienen texto propio.

    Args:
        documento: Documento que se desea fragmentar.
        raiz_markdown: Árbol de encabezados previamente generado a partir del contenido del documento.

    Returns:
        Lista de chunks pertenecientes al documento.
    """

    chunks: list[Chunk] = []

    contexto_inicial: dict[str, str | None] = {
        "titulo": None,
        "subtitulo": None,
        "seccion": None,
        "subseccion": None,
        "apartado": None,
    }

    _generar_chunks(
        raiz_markdown,
        documento=documento,
        contexto=contexto_inicial,
        chunks=chunks,
        indice=0,
    )

    return chunks


def crear_chunks_documentos(
    documentos: list[Documento], arboles: list[MarkdownNode]
) -> list[Chunk]:
    """
    Divide una colección de documentos en Chunk.

    Args:
        documentos: Lista de documentos.
        arboles: Lista de árboles de encabezados.

    Returns:
        Lista con todos los chunks generados.
    """

    todos_los_chunks: list[Chunk] = []

    for documento, arbol in zip(documentos, arboles):

        chunks_documento = crear_chunks_documento(documento, arbol)

        todos_los_chunks.extend(chunks_documento)

    return todos_los_chunks


if __name__ == "__main__":

    logger.info("Este módulo proporciona funciones para dividir " "Documentos en Chunks.")

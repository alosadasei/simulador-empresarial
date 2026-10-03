"""Vincula los chunks con los nodos del árbol de conocimiento a los que pertenecen."""

from src.knowledge.models import KnowledgeTree, KnowledgeNode
from src.core.models import Chunk


def enlazar(arbol: KnowledgeTree, chunks: list[Chunk]) -> None:
    """
    Enlaza los chunks con los nodos del árbol de conocimiento.

    Para cada chunk, localiza el KnowledgeNode al que pertenece según
    su ruta jerárquica (titulo, subtitulo, seccion, etc.) y establece
    la relación entre ambos.

    Args:
        arbol: Árbol de conocimiento del documento.
        chunks: Lista de chunks generados a partir del mismo documento.
    """

    for chunk in chunks:
        nodo = _buscar_nodo(arbol, chunk)
        _enlazar_chunk_nodo(chunk, nodo)


def _buscar_nodo(
    arbol: KnowledgeTree,
    chunk: Chunk,
) -> KnowledgeNode:
    """
    Recorre el árbol siguiendo la ruta jerárquica del chunk
    hasta localizar el nodo correspondiente.
    """

    nodo = arbol.raiz

    for titulo in chunk.jerarquia_original():
        nodo = _buscar_hijo(nodo, titulo)

        if nodo is None:
            raise ValueError(
                f"No se encontró el nodo '{titulo}' "
                f"para el chunk {chunk.indice}"
            )

    return nodo


def _buscar_hijo(
    nodo: KnowledgeNode,
    titulo: str,
) -> KnowledgeNode | None:
    """
    Devuelve el hijo cuyo título coincide con el indicado.
    """


    for hijo in nodo.hijos:
        if hijo.titulo == titulo:
            return hijo

    return None


def _enlazar_chunk_nodo(
    chunk: Chunk,
    nodo: KnowledgeNode,
) -> None:
    """
    Establece la relación entre un chunk y un nodo del árbol.

    Actualiza el chunk con el identificador del nodo y registra el chunk
    dentro del nodo correspondiente.

    Args:
        chunk: Chunk que se desea enlazar.
        nodo: Nodo del árbol al que pertenece el chunk.
    """

    chunk.node_id = nodo.id
    if chunk.indice not in nodo.chunk_ids:
        nodo.chunk_ids.append(chunk.indice)

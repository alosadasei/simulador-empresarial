"""
Exporta un KnowledgeTree a un fichero JSON.
"""

import json
from pathlib import Path

from src.knowledge.models import KnowledgeNode, KnowledgeTree


def _nodo_a_dict(nodo: KnowledgeNode) -> dict:
    """
    Convierte recursivamente un KnowledgeNode en un diccionario.
    """

    return {
        "id": nodo.id,
        "titulo": nodo.titulo,
        "nivel": nodo.nivel,
        "chunk_ids": nodo.chunk_ids,
        "hijos": [_nodo_a_dict(hijo) for hijo in nodo.hijos],
    }


def arbol_a_dict(arbol: KnowledgeTree) -> dict:
    """
    Convierte un KnowledgeTree en un diccionario.
    """

    return {
        "metodologia": arbol.metodologia.nombre,
        "raiz": _nodo_a_dict(arbol.raiz),
    }


def guardar_json(
    arbol: KnowledgeTree,
    ruta: Path,
) -> None:
    """
    Guarda un KnowledgeTree en formato JSON.
    """

    ruta.parent.mkdir(parents=True, exist_ok=True)

    with ruta.open(
        "w",
        encoding="utf-8",
    ) as fichero:

        json.dump(
            arbol_a_dict(arbol),
            fichero,
            ensure_ascii=False,
            indent=4,
        )

"""Carga un árbol de conocimiento desde su archivo JSON."""


from pathlib import Path
import json

from src.knowledge.models import KnowledgeTree, KnowledgeNode
from src.core.models import Metodologia


def cargar_arbol(ruta:  Path) -> KnowledgeTree:
    """
    Carga un KnowledgeTree desde un fichero JSON.
    """

    ruta = Path(ruta)

    with ruta.open("r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    raiz = _dict_a_nodo(datos["raiz"])

    return KnowledgeTree(
        metodologia=Metodologia(datos["metodologia"]),
        raiz=raiz
    )


def _dict_a_nodo(datos: dict[str, object]) -> KnowledgeNode:
    """
    Convierte recursivamente un diccionario JSON
    en un KnowledgeNode.
    """

    nodo = KnowledgeNode(
        id=datos.get("id"),
        titulo=datos.get("titulo"),
        nivel=datos.get("nivel"),
        chunk_ids=datos.get("chunk_ids", [])
    )

    nodo.hijos = [
        _dict_a_nodo(hijo)
        for hijo in datos.get("hijos", [])
    ]

    for hijo in nodo.hijos:
        hijo.padre = nodo

    return nodo


def main() -> None:
    """Genera un JSON de ejemplo y lo carga, para probar el cargador a mano."""
    ruta = Path("prueba_arbol.json")

    datos = {
        "metodologia": "Metodologia_ejemplo",
        "raiz": {
            "id": "root",
            "titulo": "Raíz",
            "nivel": 0,
            "chunk_ids": [],
            "hijos": [
                {
                    "id": "hijo-1",
                    "titulo": "Hijo 1",
                    "nivel": 1,
                    "chunk_ids": [],
                    "hijos": []
                }
            ]
        }
    }

    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    arbol = cargar_arbol(ruta)
    assert arbol.raiz.hijos[0].padre is arbol.raiz


if __name__ == "__main__":
    main()
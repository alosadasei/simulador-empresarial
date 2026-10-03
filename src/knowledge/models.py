"""Modelos del árbol de conocimiento: nodos jerárquicos y el árbol de cada metodología."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.models import Metodologia


@dataclass
class KnowledgeNode:
    """
    Representa un apartado del conocimiento.

    Cada nodo corresponde a un encabezado Markdown (#, ##, ###, #### o #####)
    y mantiene las relaciones jerárquicas con el resto de apartados del manual.
    """     
    id: str    
    titulo: str | None = None    
    nivel: int = 0
    padre: KnowledgeNode | None = None
    hijos: list[KnowledgeNode] = field(default_factory=list)    
    chunk_ids: list[int] = field(default_factory=list)


@dataclass
class KnowledgeTree:
    """
    Representa el árbol de conocimiento de una metodología.
    """

    metodologia: Metodologia
    raiz: KnowledgeNode

    def buscar_por_id(self, id_buscado: str) -> KnowledgeNode | None:
        """Busca un nodo por su id recorriendo el árbol."""
        return self._buscar_en_nodo(self.raiz, id_buscado)

    def _buscar_en_nodo(
        self,
        nodo: KnowledgeNode,
        id_buscado: str,
    ) -> KnowledgeNode | None:
        """Busca un nodo por id recorriendo recursivamente el subárbol de `nodo`."""
        if nodo.id == id_buscado:
            return nodo

        for hijo in nodo.hijos:
            resultado = self._buscar_en_nodo(hijo, id_buscado)
            if resultado is not None:
                return resultado

        return None

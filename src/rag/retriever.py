"""
Módulo encargado de recuperar los candidatos de la búsqueda vectorial.

El retriever representa la fase de recuperación de información del sistema RAG.

Responsabilidades:

- Convertir la pregunta del usuario en un embedding.
- Consultar la base vectorial.
- Recuperar los candidatos obtenidos por similitud vectorial.

Este módulo desacopla el sistema RAG de la implementación concreta de la base de datos vectorial.

Arquitectura:
                    PREGUNTA
                       │
                       ▼
                  RAG.responder()
                       │
                       ▼
                  ┌──────────┐
                  │ Retriever│
                  └────┬─────┘
                       │
             metodología = simulacion_empresarial
                       │
                       ▼
                 VectorStore
                       │
          ┌────────────┴────────────┐
          │                         │
 simulacion_empresarial.md   se_material_complementario.md
          │                         │
          └────────────┬────────────┘
                       │
                       ▼
              candidatos recuperados
                       │
                       ▼
               ContextExpander
                       │
             usa node_id del Chunk
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
 árbol simulacion          árbol complementario
"""

import logging

from src.rag.embeddings import crear_embedding_texto
from src.rag.vector_store import VectorStore
from src.core.models import ResultadoBusqueda
from src.core.config import K_BUSQUEDA

logger = logging.getLogger(__name__)


class Retriever:
    """
    Recupera los candidatos obtenidos mediante búsqueda vectorial.
    """

    def __init__(self):
        """Crea el almacén vectorial sobre el que se hacen las búsquedas."""
        self.vector_store = VectorStore()

    def recuperar_candidatos(
        self,
        pregunta: str,
        metodologia: str,
        k: int = K_BUSQUEDA,
    ) -> list[ResultadoBusqueda]:
        """
        Recupera los candidatos obtenidos mediante búsqueda vectorial.

        Genera el embedding de la pregunta y consulta la base vectorial para recuperar los candidatos más similares.

        Args:
            pregunta (str): Texto de la consulta del usuario.
            metodologia: Nombre de la metodología sobre la que se realizará la búsqueda.
            k (int): Número máximo de chunks a recuperar.

        Returns:
            list: Lista de candidatos (objetos ResultadoBusqueda) recuperados junto con su distancia de similitud.

        Raises:
            ValueError: Si la pregunta o la metodología están vacías, o si `k` no es mayor que cero.
        """

        if not pregunta.strip():
            raise ValueError("La pregunta no puede estar vacía.")

        if k <= 0:
            raise ValueError("El número de resultados a recuperar debe ser mayor que cero.")

        if not metodologia.strip():
            raise ValueError("La metodología no puede estar vacía.")

        embedding = crear_embedding_texto(pregunta)

        return self.vector_store.buscar(
            embedding,
            metodologia,
            k,
        )
        
    def recuperar_por_nodo(
        self,
        node_id: str,
        metodologia: str,
    ) -> list:
        """
            Recupera directamente los chunks pertenecientes a un nodo del árbol,
            sin pasar por búsqueda semántica. Se usa en modo guiado.
        """

        return self.vector_store.obtener_por_nodo(node_id, metodologia)

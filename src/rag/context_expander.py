"""
Módulo encargado de expandir y organizar el contexto recuperado.

A partir de los resultados de la búsqueda, selecciona los chunks
según sus umbrales de relevancia y puede enriquecer el contexto
utilizando las relaciones jerárquicas del KnowledgeTree.

También elimina duplicados y ordena los chunks según su posición
dentro de la jerarquía de conocimiento.
"""

from src.core.models import IntentResult, EstrategiaContexto, ResultadoBusqueda, Chunk
from src.rag.context_strategies import ContextStrategies
from src.core.config import UMBRAL_ACEPTABLE, UMBRAL_BUENO, UMBRAL_EXCELENTE, MAXIMO_CHUNKS, MINIMO_CHUNKS
from src.rag.historial import Historial
from src.knowledge.models import KnowledgeNode, KnowledgeTree
import logging
logger = logging.getLogger(__name__)

class ContextExpander:

    """
    Expande y organiza los chunks recuperados utilizando
    la estructura jerárquica del KnowledgeTree.
    """

    def __init__(
        self, 
        arboles: dict[str, KnowledgeTree], 
        historial: Historial,
        ):
        """
        Inicializa el expandidor de contexto con los árboles de conocimiento y el historial.
        """
        self.arboles = arboles
        self.historial = historial
        self.strategies = ContextStrategies()

    def expandir(
        self,
        resultados: list[ResultadoBusqueda],
        intencion: IntentResult,
    ) -> list[Chunk]:
        """
        Selecciona y organiza el contexto recuperado.

        El ContextExpander se encarga de la expansión jerárquica
        común. Después delega en la estrategia correspondiente
        las decisiones específicas de cada intención.
        """
        estrategia = self._obtener_estrategia(intencion)
        
        # logger.debug(
        #             "Estrategia de contexto: %s | padres=%s | hermanos=%s | hijos=%s",
        #             intencion.intencion,
        #             estrategia.anadir_padres,
        #             estrategia.anadir_hermanos,
        #             estrategia.anadir_hijos,
        #         )

        candidatos = self._aplicar_umbrales(resultados, estrategia)

        logger.debug(
            "Chunks después de umbrales: %d",
            len(candidatos),
        )

        if estrategia.anadir_padres:
            candidatos = self._enriquecer_con_padres(candidatos)

        logger.debug(
            "Chunks después de añadir padres: %d",
            len(candidatos),
        )

        if estrategia.anadir_hermanos:
            candidatos = self._enriquecer_con_hermanos(candidatos)

        if estrategia.anadir_hijos:
            candidatos = self._enriquecer_con_hijos(candidatos)

        candidatos = self._eliminar_duplicados(candidatos)

        candidatos = self._ordenar_por_jerarquia(candidatos)
        
        logger.debug(
            "Chunks finales enviados al PromptBuilder: %d",
            len(candidatos),
        )

        return candidatos
    

    def _aplicar_umbrales(
        self,
        resultados: list[ResultadoBusqueda],
        estrategia: EstrategiaContexto,
    ) -> list[Chunk]:
        """
        Filtra los chunks recuperados según su relevancia.

        Prioriza chunks excelentes. Si no hay suficientes,
        amplía progresivamente el umbral de aceptación.
        """

        excelentes = [
            resultado.chunk
            for resultado in resultados
                if resultado.distancia <= estrategia.umbral_excelente
        ]

        if len(excelentes) >= MINIMO_CHUNKS:
            return excelentes[:MAXIMO_CHUNKS]

        buenos = [
            resultado.chunk
            for resultado in resultados
            if resultado.distancia <= estrategia.umbral_bueno
        ]

        if len(buenos) >= MINIMO_CHUNKS:
            return buenos[:MAXIMO_CHUNKS]

        aceptables = [
            resultado.chunk
            for resultado in resultados
            if resultado.distancia <= estrategia.umbral_aceptable
        ]

        return aceptables[:MAXIMO_CHUNKS]

    def _obtener_arbol(
        self,
        chunk: Chunk,
    ) -> KnowledgeTree | None:
        """Devuelve el árbol de conocimiento del documento al que pertenece el chunk."""

        return self.arboles.get(
            chunk.documento.nombre
        )

    def _clave_chunk(
        self, 
        chunk: Chunk,
        ) -> tuple[str, int]:
        """Clave única del chunk: ruta del documento e índice."""

        return (
            chunk.documento.ruta,
            chunk.indice,
        )

    def _clave_chunk_id(
        self,
        chunk: Chunk,
        chunk_id: int,
    ) -> tuple[str, int]:
        """Clave única de un chunk del mismo documento a partir de su índice."""

        return (
            chunk.documento.ruta,
            chunk_id,
        )

    def _obtener_nodo(
        self,
        chunk: Chunk,
    ) -> KnowledgeNode | None:
        """Devuelve el nodo del árbol asociado al chunk, o None si no tiene."""

        arbol = self._obtener_arbol(chunk)

        if arbol is None or chunk.node_id is None:
            return None

        return self._buscar_nodo(
            arbol.raiz,
            chunk.node_id,
        )

    def _buscar_nodo(
        self,
        nodo: KnowledgeNode,
        node_id: str,
    ) -> KnowledgeNode | None:
        """
        Busca recursivamente un nodo del árbol a partir de su identificador.

        Recorre el nodo actual y sus descendientes hasta encontrar
        el nodo con el `node_id` indicado. Devuelve None si no existe.
        """

        if nodo.id == node_id:
            return nodo

        for hijo in nodo.hijos:
            encontrado = self._buscar_nodo(hijo, node_id)
            if encontrado is not None:
                return encontrado

        return None

    def _enriquecer_con_padres(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """
        Enriquece el contexto con los chunks del nodo padre que ya hayan sido
        recuperados por el Retriever.
        """

        resultado = chunks.copy()

        chunks_por_clave = {self._clave_chunk(chunk): chunk for chunk in chunks}

        for chunk in chunks:

            nodo = self._obtener_nodo(chunk)

            if nodo is None or nodo.padre is None:
                continue

            for chunk_id in nodo.padre.chunk_ids:

                clave = self._clave_chunk_id(
                    chunk,
                    chunk_id,
                )

                chunk_padre = chunks_por_clave.get(clave)

                if chunk_padre is not None:
                    resultado.append(chunk_padre)

        return resultado

    def _enriquecer_con_hermanos(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """
        Enriquece el contexto con los chunks hermanos que ya hayan sido
        recuperados por el Retriever.
        """

        resultado = chunks.copy()

        chunks_por_clave = {self._clave_chunk(chunk): chunk for chunk in chunks}

        for chunk in chunks:
            nodo = self._obtener_nodo(chunk)
            if nodo is None or nodo.padre is None:
                continue

            for chunk_id in nodo.padre.chunk_ids:
                if chunk_id == chunk.indice:
                    continue

                clave = self._clave_chunk_id(chunk, chunk_id)

                chunk_hermano = chunks_por_clave.get(clave)

                if chunk_hermano is not None:
                    resultado.append(chunk_hermano)

        return resultado

    def _enriquecer_con_hijos(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """
        Enriquece el contexto con los chunks hijos que ya hayan sido
        recuperados por el Retriever.
        """

        resultado = chunks.copy()

        chunks_por_clave = {self._clave_chunk(chunk): chunk for chunk in chunks}

        for chunk in chunks:
            nodo = self._obtener_nodo(chunk)
            if nodo is None:
                continue

            for hijo in nodo.hijos:
                for chunk_id in hijo.chunk_ids:
                    if chunk_id == chunk.indice:
                        continue

                    clave = self._clave_chunk_id(chunk, chunk_id)

                    chunk_hijo = chunks_por_clave.get(clave)

                    if chunk_hijo is not None:
                        resultado.append(chunk_hijo)

        return resultado

    def _eliminar_duplicados(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """
        Elimina los chunks duplicados conservando el orden original.
        """

        vistos = set()
        resultado = []

        for chunk in chunks:

            clave = (
                chunk.documento.ruta,
                chunk.indice,
            )

            if clave in vistos:
                continue

            vistos.add(clave)
            resultado.append(chunk)

        return resultado

    def _ruta_nodo(
        self,
        nodo: KnowledgeNode,
    ) -> tuple[int, ...]:
        """Devuelve la posición del nodo entre sus hermanos en cada nivel, desde la raíz."""

        ruta = []

        while nodo.padre is not None:
            posicion = nodo.padre.hijos.index(nodo)
            ruta.append(posicion)
            nodo = nodo.padre

        ruta.append(0)

        return tuple(reversed(ruta))

    def _ordenar_por_jerarquia(
        self,
        chunks: list[Chunk],
    ) -> list[Chunk]:
        """Ordena los chunks según el orden del documento (posición en el árbol)."""

        def clave(chunk: Chunk):
            # Los chunks sin nodo van al final; el resto, por su ruta en el árbol.
            nodo = self._obtener_nodo(chunk)

            if nodo is None:
                return (float("inf"),)

            return self._ruta_nodo(nodo)

        return sorted(chunks, key=clave)

    def _obtener_estrategia(
        self,
        intencion: IntentResult,
    ) -> EstrategiaContexto:
        """Elige la estrategia de expansión de contexto según la intención detectada."""

        if intencion.intencion == "consulta_conceptual":
            return self.strategies.consulta_conceptual()
        
        if intencion.intencion == "pasos":
            return self.strategies.pasos()
        
        if intencion.intencion == "ejemplo":
            return self.strategies.ejemplo()
        
        if intencion.intencion == "actividad":
                    return self.strategies.actividad()
        
        if intencion.intencion == "comparacion":
            return self.strategies.comparacion()
                
        if intencion.intencion == "otra":
            return self.strategies.otra()

        raise ValueError(
            f"Intención no soportada: {intencion.intencion}"
        )

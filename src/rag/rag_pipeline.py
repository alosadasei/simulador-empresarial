"""
Coordina el flujo principal del sistema RAG.

Este módulo actúa como punto de entrada al sistema de recuperación
aumentada por generación (RAG), coordinando las distintas etapas
del proceso:

- Recuperar candidatos mediante el Retriever.
- Obtener el contexto reciente de la conversación.
- Construir el prompt con la pregunta, el historial y los resultados recuperados.
- Enviar el prompt al modelo de lenguaje.
- Guardar la conversación en el historial.
- Devolver la respuesta generada.

El resto de la aplicación, como el chatbot web, interactúa con
el sistema RAG a través de esta clase.
"""

import uuid

from src.rag.retriever import Retriever
from src.rag.prompt_builder import ConstructorPrompts
from src.rag.llm_client import LLMClient
from src.rag.historial import Historial
from src.rag.context_expander import ContextExpander
from src.rag.intent_classifier import IntentClassifier
from src.rag.guided_steps import obtener_ids_pasos
from src.rag.guided_mode import GuidedMode
from src.rag.guided_context_builder import GuidedContextBuilder
from src.core.models import Mensaje
from src.knowledge.models import KnowledgeTree

import logging

logger = logging.getLogger(__name__)

class RAG:
    """
    Orquesta las etapas principales del sistema RAG.

    Coordina la recuperación de candidatos, el historial de la
    conversación, la construcción del prompt y la generación
    de respuestas mediante el modelo de lenguaje.
    """

    def __init__(self, arboles: dict[str, KnowledgeTree], historial=None):
        """
        Inicializa el sistema RAG con los árboles de conocimiento.

        Args:
            arboles: Árboles de conocimiento por metodología.
            historial: Almacén de historial de conversación. Debe ofrecer
                los métodos ``obtener_contexto`` y ``agregar_mensaje``.
                Si no se indica, se usa el historial en fichero JSON.
        """

        self.retriever = Retriever()
        self.prompt_builder = ConstructorPrompts()
        self.llm = LLMClient()
        self.historial = historial if historial is not None else Historial()
        self.id_conversacion = str(uuid.uuid4())
        self.intent_classifier = IntentClassifier()
        self.arboles = arboles

        self.context_expander = ContextExpander(
            arboles,
            self.historial,
        )

        self.guided_mode = GuidedMode()
        self.guided_context_builder = GuidedContextBuilder(arboles)

    def responder(
        self,
        pregunta: str,
        metodologia: str,
        id_conversacion: str,
        modo_guiado: bool = False,
        estado_guiado: dict | None = None,
        paso_id: str | None = None,
    ) -> tuple[str, dict | None]:

        """
        Genera una respuesta utilizando el flujo completo del sistema RAG.

        Args:
            pregunta: Pregunta realizada por el usuario.
            metodologia: Metodología sobre la que se realizará la búsqueda.

        Returns:
            Respuesta generada por el modelo de lenguaje.
        """

        logger.info("Recuperando contexto...")

        historial = self.historial.obtener_contexto(id_conversacion)

        intencion = self.intent_classifier.clasificar(pregunta)

        # logger.debug(
        #     "Intención: %s | Keywords: %s | Método: %s",
        #     intencion.intencion,
        #     intencion.palabras_clave,
        #     intencion.metodo,
        # )

        consulta_retrieval = pregunta

        if modo_guiado and paso_id is not None:

            arbol = self.arboles[metodologia]
            paso_seleccionado = arbol.buscar_por_id(paso_id)

            if paso_seleccionado is not None:
                consulta_retrieval = paso_seleccionado.titulo

                logger.info(
                    "Consulta guiada basada en paso | paso=%s | consulta=%s",
                    paso_id,
                    consulta_retrieval,
                )

        candidatos = self.retriever.recuperar_candidatos(
            consulta_retrieval,
            metodologia,
        )      

        # Logger para info de cada chunk que recupera el retriever
        # logger.info(
        #     "Consulta RAG | metodología=%s | candidatos=%d",
        #     metodologia,
        #     len(candidatos),
        # )

        # for candidato in candidatos:
        #     logger.debug(
        #         "Chunk recuperado | documento=%s | ruta=%s | "
        #         "título=%s | node_id=%s | índice=%d | distancia=%.3f",
        #         candidato.chunk.documento.nombre,
        #         candidato.chunk.documento.ruta,
        #         candidato.chunk.titulo,
        #         candidato.chunk.node_id,
        #         candidato.chunk.indice,
        #         candidato.distancia,
        #     )

        candidatos_expandidos = self.context_expander.expandir(candidatos, intencion)

        logger.info("Construyendo prompt...")

        arbol = self.arboles[metodologia]

        # ---------------------------------------------------------
        # MODO GUIADO
        # ---------------------------------------------------------

        generar_con_llm = True

        if modo_guiado:

            # Obtener los pasos disponibles para esta metodología.
            pasos_ids = obtener_ids_pasos(
                metodologia,
                arbol,
            )

            # Si todavía no existe checklist, lo inicializamos.
            if estado_guiado is None:

                estado_guiado = self.guided_mode.estado_inicial(pasos_ids)

            # Comprobamos que el estado pertenece a la estructura
            # actual de la metodología.
            estado_guiado["pasos_ids"] = pasos_ids

            # Si desde la interfaz se ha seleccionado un paso,
            # lo guardamos como paso actual.
            if paso_id is not None:

                estado_guiado = self.guided_mode.seleccionar_paso(
                    estado_guiado,
                    paso_id,
                )

            # Obtenemos el elemento actualmente seleccionado.
            paso = self.guided_mode.obtener_paso_actual(
                estado_guiado,
                arbol,
            )            

            if paso is None:

                # Todavía no se ha seleccionado ningún elemento.
                respuesta = (
                    "Selecciona un elemento del checklist "
                    "para comenzar a trabajar en él."
                )

                generar_con_llm = False

            else:

                pregunta_guiada = (
                    f"Quiero trabajar la actividad '{paso.titulo}'. "
                    "Ayúdame a realizarla paso a paso utilizando el contexto "
                    "proporcionado y teniendo en cuenta el progreso realizado."
                )

                # logger.info(
                #     "Modo guiado | paso=%s | id=%s",
                #     paso.titulo,
                #     paso.id,
                # )

                chunks_paso = []

                nodos_contexto = [paso] + paso.hijos

                for nodo in nodos_contexto:

                    chunks_paso.extend(
                        self.retriever.recuperar_por_nodo(
                            nodo.id,
                            metodologia,
                        )
                    )

                # Construimos el contexto específico del elemento.
                contexto_guiado = self.guided_context_builder.construir(
                    paso=paso,
                    chunks=chunks_paso,
                    progreso=estado_guiado.get("completados", []),
                    arbol=arbol,
                )

                # Prompt específico del modo guiado.
                prompt = self.prompt_builder.construir_prompt_guiado(
                    historial,
                    pregunta_guiada,
                    contexto_guiado,
                )

        # ---------------------------------------------------------
        # MODO PREGUNTAS
        # ---------------------------------------------------------

        else:

            prompt = self.prompt_builder.construir_prompt(
                historial,
                pregunta,
                candidatos_expandidos,
            )

        if generar_con_llm:

            logger.debug("\n========== PROMPT ==========\n")
            logger.debug("%s", prompt)
            logger.debug("\n============================\n")

            logger.info("Consultando el modelo...")

            # Genera la respuesta solo cuando todavía necesitamos consultar al LLM.
            respuesta = self.llm.generar_respuesta(prompt)

        # Guardar la pregunta en historial
        pregunta_historial = pregunta

        if modo_guiado and paso_id is not None:
            pregunta_historial = paso.titulo

        self.historial.agregar_mensaje(
            id_conversacion,
            Mensaje("user", pregunta_historial)
        )

        # Guardar la respuesta en historial
        self.historial.agregar_mensaje(id_conversacion, Mensaje("bot", respuesta))

        logger.info("Respuesta recibida.")
        return respuesta, estado_guiado

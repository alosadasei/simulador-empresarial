"""
Módulo encargado de construir el prompt que se enviará al modelo
de lenguaje.

Responsabilidades:
- Formatear el contexto recuperado por el retriever.
- Añadir las instrucciones para el modelo.
- Incorporar la pregunta del usuario.

Este módulo desacopla la construcción del prompt del resto del
pipeline RAG, facilitando modificar las instrucciones o el formato
sin afectar al chatbot ni al retriever.
"""

from src.core.models import Chunk, Mensaje
import logging
import textwrap

logger = logging.getLogger(__name__)


INSTRUCCIONES = (
    "Eres un profesor de Formación Profesional.\n"
    "Responde solo con la información del contexto proporcionado; "
    "si no la contiene, indícalo y no inventes nada.\n"
    "Explica con tus propias palabras, combinando varios fragmentos "
    "si es necesario, sin copiar textos largos.\n"
    "Responde en texto plano: no uses Markdown (nada de **, #, guiones "
    "de lista, etc.). Para listas, usa numeración simple (1. 2. 3.).\n"
    "No añadas sangrías al inicio de las líneas.\n"
    "Sé conciso: entre 80 y 180 palabras, ajustando según la complejidad "
    "de la pregunta, pero si necesitas un poco más usa máximo 200 palabras."
)

INSTRUCCIONES_GUIADO = (
    "Eres un profesor de Formación Profesional guiando al alumno paso a paso.\n"
    "Usa solo la información del contexto proporcionado; si no es suficiente, indícalo y no inventes nada.\n"
    "Explica el paso actual con tus propias palabras, resumido donde puedas y teniendo en cuenta su progreso anterior, sin copiar textos largos.\n"
    "Céntrate únicamente en el paso actual y termina con una pregunta "
    "o actividad breve para que el alumno participe.\n"
    "Responde en texto plano: no uses Markdown (nada de **, #, guiones "
    "de lista, etc.). Para listas, usa numeración simple (1. 2. 3.).\n"
    "Sé conciso: entre 100 y 400 palabras, sin rellenar de más pero sin cortar la explicación."
)

class ConstructorPrompts:
    """Construye los prompts que se envían al modelo."""

    def _formatear_contexto(
            self,
            chunks: list[Chunk],
        ) -> str:
        """
        Convierte una lista de chunks en un único bloque de contexto para el prompt.
        """

        partes: list[str] = []

        for chunk in chunks:

            encabezado = " > ".join(chunk.jerarquia_limpia()) or "Sin contexto"
            partes.append(f"[{encabezado}]\n{chunk.texto}")

        return "\n\n".join(partes)


    def _formatear_historial(
            self,
            mensajes: list[Mensaje]
        ) -> str:
        """
        Formatea una lista de mensajes para el prompt.

        Convierte cada objeto Mensaje en una línea del historial con el formato:
        - <rol>: <contenido>

        Args:
            mensajes: Lista de objetos Mensaje que representan el historial.

        Returns:
            Una cadena con el historial formateado para incluir en el prompt.
        """

        if not mensajes:
            logger.warning("(sin historial previo)")
            return "(sin historial previo)"

        lineas: list[str] = []

        for mensaje in mensajes:
            lineas.append(f"- {mensaje.rol}: {mensaje.contenido}")

        return "\n".join(lineas)
        

    def construir_prompt(self, historial: list[Mensaje], pregunta: str, chunks: list[Chunk]) -> str:
        """
        Une cuatro partes:

        1. Instrucciones para el modelo.
        2. Contexto recuperado.
        3. Pregunta del usuario.
        4. Historial de la conversación.
        """

        if not chunks:
            raise ValueError(
                "No se han proporcionado chunks para construir el prompt."
            )

        if not pregunta or not pregunta.strip():
            raise ValueError(
                "La pregunta no puede estar vacía."
            )
        
        contexto = self._formatear_contexto(chunks)
        historial_formateado = self._formatear_historial(historial)

        return textwrap.dedent(f"""
            {INSTRUCCIONES}

            Contexto:
            {contexto}

            Pregunta:
            {pregunta}

            Historial:
            {historial_formateado}
        """).strip()


    def construir_prompt_guiado(
            self,
            historial: list[Mensaje],
            pregunta: str,
            contexto: dict,
        ) -> str:
        """
        Construye el prompt para el modo de aprendizaje guiado.
        """

        if not contexto:
            raise ValueError(
                "No se ha proporcionado contexto guiado."
            )

        if not pregunta or not pregunta.strip():
            raise ValueError(
                "La pregunta no puede estar vacía."
            )

        contexto_chunks = self._formatear_contexto(
            contexto["chunks"]
        )

        historial_formateado = self._formatear_historial(
            historial
        )

        progreso_formateado = self._formatear_progreso(
            contexto["progreso"]
        )

        return textwrap.dedent(f"""
            {INSTRUCCIONES_GUIADO}

            Paso actual:
            {contexto["titulo"]}

            Ruta del proceso:
            {" > ".join(contexto["ruta"])}

            Paso padre:
            {contexto["padre"]}

            Información del paso:
            {contexto_chunks}

            Progreso anterior del alumno:
            {progreso_formateado}

            Pregunta del alumno:
            {pregunta}

            Historial de la conversación:
            {historial_formateado}
        """).strip()


    def _formatear_progreso(
            self,
            progreso: list[dict],
        ) -> str:
        """
        Formatea el progreso anterior del alumno para incluirlo en el prompt.

        Args:
            progreso: Lista de pasos trabajados y respuestas del alumno.

        Returns:
            Una cadena con el progreso formateado.
        """

        if not progreso:
            return "(sin progreso previo)"

        lineas = [f"- {titulo}" for titulo in progreso]
        return "\n".join(lineas)


if __name__ == "__main__":
    logger.info("Módulo encargado de construir el prompt para el LLM.")

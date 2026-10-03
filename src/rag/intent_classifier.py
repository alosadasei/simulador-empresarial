"""Clasificador de intención de las preguntas del usuario, basado en reglas y expresiones regulares."""

import re
from src.core.models import IntentResult

class IntentClassifier:
    """
    Detecta la intención principal de una pregunta de usuario
    mediante un conjunto de reglas basadas en patrones lingüísticos.
    """

    INTENCIONES = {
        "consulta_conceptual",
        "pasos",
        "ejemplo",
        "actividad",
        "comparacion",
        "otra",
    }

    def clasificar(self, pregunta: str) -> IntentResult:
        """
        Clasifica una pregunta y extrae las palabras clave relevantes.

        Args:
            pregunta: Pregunta formulada por el usuario.

        Returns:
            Resultado con la intención detectada, las palabras clave
            y el método utilizado para la clasificación.
        """

        texto = pregunta.lower().strip()

        intencion = self._detectar_intencion(texto)

        if intencion == "consulta_conceptual":
            palabras_clave = self._extraer_concepto(texto)

        elif intencion == "pasos":
            palabras_clave = self._extraer_proceso(texto)

        elif intencion == "ejemplo":
            palabras_clave = self._extraer_ejemplo(texto)

        elif intencion == "actividad":
            palabras_clave = self._extraer_actividad(texto)

        elif intencion == "comparacion":
            palabras_clave = self._extraer_conceptos_comparacion(texto)

        else:
            palabras_clave = self._extraer_palabras_genericas(texto)

        return IntentResult(
            intencion=intencion,
            palabras_clave=palabras_clave,
            metodo="reglas",
        )

    # ------------------------------------------------------------------
    # Detección de intención
    # ------------------------------------------------------------------

    def _detectar_intencion(self, texto: str) -> str:
        """
        Determina la intención de una pregunta aplicando las reglas
        en un orden de prioridad determinado.

        Args:
            texto: Pregunta normalizada en minúsculas.

        Returns:
            Nombre de la intención detectada.
            Devuelve "otra" si ninguna regla coincide.
        """

        if self._es_comparacion(texto):
            return "comparacion"

        if self._es_pasos(texto):
            return "pasos"

        if self._es_ejemplo(texto):
            return "ejemplo"

        if self._es_actividad(texto):
            return "actividad"

        if self._es_consulta_conceptual(texto):
            return "consulta_conceptual"

        return "otra"

    def _es_comparacion(self, texto: str) -> bool:
        """
        Comprueba si la pregunta solicita comparar dos o más conceptos.

        Args:
            texto: Pregunta normalizada.

        Returns:
            True si se detecta un patrón de comparación.
        """

        patrones = (
            r"\bdiferencia\b",
            r"\bdiferencias\b",
            r"\bqué diferencia hay entre\b",
            r"\ben qué se diferencian\b",
            r"\bqué diferencias hay entre\b",
            r"\bcomparar\b",
            r"\bcompara\b",
            r"\bcomparación\b",
            r"\bcomparativa\b",
            r"\bcomparado con\b",
            r"\bfrente a\b",
        )

        return any(re.search(patron, texto) for patron in patrones)

    def _es_pasos(self, texto: str) -> bool:
        """
        Comprueba si la pregunta solicita instrucciones o una secuencia
        de pasos para realizar una acción o proceso.

        Args:
            texto: Pregunta normalizada.

        Returns:
            True si se detecta un patrón relacionado con pasos o procesos.
        """

        patrones = (
            r"\bcuáles son los pasos\b",
            r"\bqué pasos\b",
            r"\bpasos para\b",
            r"\bpasos necesarios\b",
            r"\bqué pasos hay que seguir\b",
            r"\bcómo se hace\b",
            r"\bcómo hacer\b",
            r"\bcómo realizar\b",
            r"\bcómo se realiza\b",
            r"\bcómo se lleva a cabo\b",
            r"\bqué hay que hacer para\b",
            r"\bqué tengo que hacer\b",
            r"\bqué debo hacer\b",
            r"\bqué debo hacer para\b",
            r"\bguíame\b",
            r"\bexplícame cómo\b",
        )

        return any(re.search(patron, texto) for patron in patrones)

    def _es_ejemplo(self, texto: str) -> bool:
        """
        Comprueba si la pregunta solicita o hace referencia a un ejemplo.

        Args:
            texto: Pregunta normalizada.

        Returns:
            True si se detecta un patrón relacionado con ejemplos.
        """

        patrones = (
            r"\bejemplo\b",
            r"\bejemplos\b",
            r"\bponme un ejemplo\b",
            r"\bdame un ejemplo\b",
            r"\bponme ejemplos\b",
            r"\bdame ejemplos\b",
        )

        return any(re.search(patron, texto) for patron in patrones)

    def _es_actividad(self, texto: str) -> bool:
        """
        Comprueba si la pregunta solicita o hace referencia a una
        actividad, ejercicio, caso práctico, tarea o foro.

        Args:
            texto: Pregunta normalizada.

        Returns:
            True si se detecta un patrón relacionado con actividades.
        """

        patrones = (
            r"\bactividad\b",
            r"\bactividades\b",
            r"\bcaso práctico\b",
            r"\bcasos prácticos\b",
            r"\bejercicio\b",
            r"\bejercicios\b",
            r"\bpráctica\b",
            r"\bprácticas\b",
            r"\bforo\b",
            r"\bforos\b",
            r"\btarea\b",
            r"\btareas\b",
        )

        return any(re.search(patron, texto) for patron in patrones)

    def _es_consulta_conceptual(self, texto: str) -> bool:
        """
        Comprueba si la pregunta solicita una explicación, definición
        o descripción de un concepto.

        Args:
            texto: Pregunta normalizada.

        Returns:
            True si se detecta un patrón de consulta conceptual.
        """

        patrones = (
            r"\bqué es\b",
            r"\bqué significa\b",
            r"\bqué son\b",
            r"\bdefine\b",
            r"\bdefinición de\b",
            r"\ben qué consiste\b",
            r"\bexplícame\b",
            r"\bqué elementos\b",
            r"\bcuáles son los elementos\b",
            r"\bqué características\b",
            r"\bcuáles son las características\b",
            r"\bpara qué sirve\b",
            r"\bcuál es la función\b",
            r"\bqué función tiene\b",
            r"\bpor qué\b",
        )

        return any(re.search(patron, texto) for patron in patrones)

    # ------------------------------------------------------------------
    # Extracción de conceptos
    # ------------------------------------------------------------------

    def _extraer_concepto(self, texto: str) -> list[str]:
        """
        Extrae las palabras clave de una consulta conceptual,
        eliminando las expresiones utilizadas para formular la pregunta.

        Args:
            texto: Pregunta normalizada.

        Returns:
            Lista de palabras clave asociadas al concepto consultado.
        """

        patrones = (
            "qué es",
            "qué son",
            "qué significa",
            "define",
            "definición de",
            "en qué consiste",
            "explícame",
            "qué elementos",
            "cuáles son los elementos",
            "qué características",
            "cuáles son las características",
            "para qué sirve",
            "cuál es la función",
            "qué función tiene",
            "por qué",
        )

        texto_limpio = self._quitar_patrones(texto, patrones)
        return self._limpiar_palabras(texto_limpio)

    def _extraer_proceso(self, texto: str) -> list[str]:
        """
        Extrae las palabras clave de una consulta sobre pasos o procesos,
        eliminando las expresiones que solicitan las instrucciones.

        Args:
            texto: Pregunta normalizada.

        Returns:
            Lista de palabras clave asociadas al proceso consultado.
        """

        patrones = (
            "cuáles son los pasos para",
            "cuáles son los pasos",
            "qué pasos hay que seguir para",
            "qué pasos hay que seguir",
            "qué pasos para",
            "pasos necesarios para",
            "pasos para",
            "cómo se hace",
            "cómo hacer",
            "cómo realizar",
            "cómo se realiza",
            "cómo se lleva a cabo",
            "qué hay que hacer para",
            "qué tengo que hacer para",
            "qué tengo que hacer",
            "qué debo hacer para",
            "qué debo hacer",
            "guíame",
            "explícame cómo",
        )

        texto_limpio = self._quitar_patrones(texto, patrones)
        return self._limpiar_palabras(texto_limpio)

    def _extraer_conceptos_comparacion(self, texto: str) -> list[str]:
        """
        Extrae las palabras clave de una consulta comparativa,
        eliminando las expresiones que indican la comparación.

        Args:
            texto: Pregunta normalizada.

        Returns:
            Lista de palabras clave correspondientes a los conceptos
            que se desean comparar.
        """

        patrones = (
            "qué diferencia hay entre",
            "qué diferencias hay entre",
            "en qué se diferencian",
            "diferencias entre",
            "diferencia entre",
            "comparación entre",
            "comparar",
            "compara",
            "comparativa entre",
            "comparado con",
            "frente a",
        )

        texto_limpio = self._quitar_patrones(texto, patrones)
        return self._limpiar_palabras(texto_limpio)

    def _extraer_ejemplo(self, texto: str) -> list[str]:
        """
        Extrae las palabras clave de una consulta que solicita un ejemplo.

        Args:
            texto: Pregunta normalizada.

        Returns:
            Lista de palabras clave asociadas al ejemplo solicitado.
        """

        patrones = (
            "ponme un ejemplo de",
            "dame un ejemplo de",
            "ponme un ejemplo",
            "dame un ejemplo",
            "ponme ejemplos de",
            "dame ejemplos de",
            "ponme ejemplos",
            "dame ejemplos",
            "ejemplo de",
            "ejemplos de",
        )

        texto_limpio = self._quitar_patrones(texto, patrones)
        return self._limpiar_palabras(texto_limpio)

    def _extraer_actividad(self, texto: str) -> list[str]:
        """
        Extrae las palabras clave de una consulta sobre actividades,
        ejercicios, casos prácticos, tareas o foros.

        Args:
            texto: Pregunta normalizada.

        Returns:
            Lista de palabras clave asociadas a la actividad solicitada.
        """

        patrones = (
            "caso práctico de",
            "casos prácticos de",
            "actividad de",
            "actividad sobre",
            "actividad",
            "ejercicio de",
            "ejercicio",
            "tarea de",
            "tarea",
            "foro sobre",
            "foro",
        )

        texto_limpio = self._quitar_patrones(texto, patrones)
        return self._limpiar_palabras(texto_limpio)

    def _extraer_palabras_genericas(
        self,
        texto: str,
    ) -> list[str]:
        """
        Extrae palabras clave de una pregunta que no ha podido asociarse
        con una intención específica.

        Args:
            texto: Pregunta normalizada.

        Returns:
            Lista de palabras clave de la pregunta.
        """

        return self._limpiar_palabras(texto)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _quitar_patrones(self, texto: str, patrones: tuple[str, ...], ) -> str:
        """
        Elimina del texto las expresiones utilizadas para identificar
        o formular una intención.

        Args:
            texto: Texto del que se eliminarán los patrones.
            patrones: Expresiones que deben eliminarse.

        Returns:
            Texto restante después de eliminar los patrones.
        """

        texto_limpio = texto 

        for patron in patrones:

            texto_limpio = texto_limpio.replace(patron, " ")

        return texto_limpio

    def _limpiar_palabras(self, texto: str) -> list[str]:
        """
        Extrae las palabras relevantes del texto y elimina palabras
        funcionales o demasiado cortas.

        Args:
            texto: Texto del que se extraerán las palabras.

        Returns:
            Lista de palabras clave normalizadas.
        """

        palabras_ignoradas = {
            "qué",
            "que",
            "es",
            "son",
            "los",
            "las",
            "una",
            "uno",
            "para",
            "del",
            "por",
            "con",
            "entre",
            "cómo",
            "como",
            "hay",
            "se",
        }

        palabras = re.findall(r"\b[\wáéíóúüñ]+\b", texto) 

        return [ 
            palabra 
            for palabra in palabras 
            if palabra not in palabras_ignoradas and len(palabra) > 2 
        ]

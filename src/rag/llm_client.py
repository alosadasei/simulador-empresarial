"""
Módulo encargado de comunicarse con el modelo de lenguaje.

Su única responsabilidad es enviar un prompt al LLM y devolver
la respuesta generada.
"""

from dotenv import load_dotenv
from groq import Groq
import logging
import os
import re


from src.core.config import MODELO_LLM

load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Gestiona la comunicación con el modelo de lenguaje.
    """

    def __init__(
        self,
        modelo: str = MODELO_LLM,
    ) -> None:
        """
        Inicializa el cliente del modelo.

        Args:
            modelo: Nombre del modelo disponible en Ollama.
        """

        self.modelo = modelo

        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))


    def _consultar_modelo(
        self,
        prompt: str,
    ):
        """
        Envía un prompt al modelo de lenguaje.

        Args:
            prompt: Prompt que se enviará al modelo.

        Returns:
            Respuesta completa devuelta por Ollama.
        """

        return self.client.chat.completions.create(
            model=self.modelo,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0,
            reasoning_effort="none",
            reasoning_format="hidden",
            max_completion_tokens=450,
        )


    def generar_respuesta(
        self,
        prompt: str,
    ) -> str:
        """
        Genera una respuesta a partir de un prompt.

        Args:
            prompt: Prompt que se enviará al modelo.

        Returns:
            Texto generado por el modelo.
        """

        if not prompt.strip():
            raise ValueError("El prompt no puede estar vacío.")

        try:
            respuesta = self._consultar_modelo(prompt)

            # Logger debug para ver el gasto aprox de tokens
            # logger.debug("=" * 50)
            # logger.debug("Modelo: %s", self.modelo)
            # logger.debug("Prompt: %d tokens", respuesta.usage.prompt_tokens)
            # logger.debug("Respuesta: %d tokens", respuesta.usage.completion_tokens)
            # logger.debug("Total: %d tokens", respuesta.usage.total_tokens)
            # logger.debug("=" * 50)

        except Exception as e:
            logger.exception("Error al comunicarse con el modelo de lenguaje.")
            raise RuntimeError("Error al comunicarse con el modelo de lenguaje.") from e

        respuesta = respuesta.choices[0].message.content

        if respuesta is None:
            raise RuntimeError("El modelo no ha devuelto contenido en la respuesta.")
        
        respuesta = re.sub(
            r"<think>.*?</think>",
            "",
            respuesta,
            flags=re.DOTALL,
        ).strip()

        return respuesta


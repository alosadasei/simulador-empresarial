"""
    Gestiona el historial de conversaciones guardado en un archivo JSON.
    Permite recuperar los mensajes de una conversación por su identificador
    y preparar la estructura para futuras operaciones de almacenamiento,
    limpieza o actualización del historial.
"""

import logging
import json
from filelock import FileLock
from pathlib import Path

from src.core.models import Mensaje
from src.core.config import CARPETA_HISTORIAL

logger = logging.getLogger(__name__)


class Historial:
    """Historial de conversaciones guardado en un archivo JSON con bloqueo de archivo."""

    def __init__(self, ruta_historial: Path = CARPETA_HISTORIAL):
        """Prepara la ruta del historial y el bloqueo que evita escrituras concurrentes."""
        self.ruta = Path(ruta_historial)
        self.lock = FileLock(str(self.ruta) + ".lock")

    def obtener_historial(self, id_conversacion: str) -> list[Mensaje]:
        """
        Devuelve el historial de una conversación.

        Si el archivo no existe o la conversación no está registrada,
        devuelve una lista vacía.

        Args:
            id_conversacion: Identificador único de la conversación.

        Returns:
            Lista de objetos Mensaje que forman el historial de la conversación.
        """

        conversaciones = self._cargar_historial()
        mensajes = conversaciones.get(id_conversacion, [])

        logger.debug(
            "Se han recuperado %d mensajes para la conversación %s",
            len(mensajes),
            id_conversacion
        )
        return [self._mensaje_desde_dict(mensaje) for mensaje in mensajes]

    def obtener_contexto(
        self,
        id_conversacion: str,
        max_mensajes: int = 6
    ) -> list:
        """
        Devuelve los últimos mensajes de una conversación para utilizarlos
        como contexto del LLM.

        Args:
            id_conversacion: Identificador de la conversación.
            max_mensajes: Número máximo de mensajes a devolver.

        Returns:
            Lista con los últimos mensajes de la conversación.
        """

        historial = self.obtener_historial(id_conversacion)

        logger.debug(
            "Historial cargado:\n%s",
            historial[-max_mensajes:]
        )

        return historial[-max_mensajes:]

    def agregar_mensaje(
        self,
        id_conversacion: str,
        mensaje: Mensaje
    ) -> None:
        """
        Agrega un mensaje al historial de una conversación.

        Args:
            id_conversacion: Identificador de la conversación.
            mensaje: Objeto Mensaje a agregar al historial.
        """
        with self.lock:
            conversaciones = self._cargar_historial()

            if id_conversacion not in conversaciones:
                conversaciones[id_conversacion] = []

            conversaciones[id_conversacion].append(self._mensaje_a_dict(mensaje))
            self._guardar_historial(conversaciones)

    def eliminar_conversacion(self, id_conversacion: str) -> None:
        """
        Elimina una conversación completa del historial.

        Args:
            id_conversacion: Identificador de la conversación a borrar.
        """
        with self.lock:
            conversaciones = self._cargar_historial()

            if id_conversacion in conversaciones:
                del conversaciones[id_conversacion]
                self._guardar_historial(conversaciones)

    def _cargar_historial(self) -> dict:
        """
        Lee el historial desde el archivo JSON y devuelve el diccionario
        de conversaciones.

        Si el archivo no existe, devuelve un diccionario vacío.
        """

        if not self.ruta.exists():
            return {}

        with self.ruta.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _guardar_historial(self, conversaciones: dict) -> None:
        """
        Guarda el diccionario de conversaciones en el archivo JSON.
        """

        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.ruta.open("w", encoding="utf-8") as f:
            json.dump(conversaciones, f, ensure_ascii=False, indent=4)

    def _mensaje_desde_dict(self, mensaje: dict) -> Mensaje:
        """Convierte un diccionario JSON en un objeto Mensaje."""

        return Mensaje(**mensaje)

    def _mensaje_a_dict(self, mensaje: Mensaje) -> dict:
        """Convierte un objeto Mensaje en un diccionario JSON."""

        return {
            "rol": mensaje.rol,
            "contenido": mensaje.contenido
        }

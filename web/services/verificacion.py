"""
Servicio web de la verificación en dos pasos.

Orquesta la generación y el envío del código por correo y guarda en la
sesión de Flask qué usuario tiene una verificación pendiente (todavía
ha introducido usuario y contraseña, pero no el código).
"""

import logging

from flask import session

from src.core.config import VERIFICACION_VALIDEZ_MINUTOS
from src.usuarios.correo import (
    CorreoNoConfigurado,
    ErrorCorreo,
    correo_configurado,
    enviar_correo,
)
from src.usuarios.modelos import Usuario
from src.usuarios.verificacion import RepositorioVerificacion

logger = logging.getLogger(__name__)

# Clave de la sesión donde se guarda la verificación pendiente.
_CLAVE_SESION = "verificacion_pendiente"

repositorio = RepositorioVerificacion()

__all__ = [
    "inicializar",
    "enviar_codigo",
    "comprobar_codigo",
    "segundos_para_reenviar",
    "cancelar",
    "marcar_pendiente",
    "dni_pendiente",
    "origen_pendiente",
    "limpiar_pendiente",
    "correo_configurado",
    "CorreoNoConfigurado",
    "ErrorCorreo",
]

# Accesos desde los que puede iniciarse la verificación.
ORIGEN_ALUMNADO = "alumnado"
ORIGEN_PROFESORADO = "profesorado"


def inicializar() -> None:
    """Crea la tabla de códigos de verificación si no existe."""

    repositorio.inicializar()


def _cuerpo_correo(codigo: str) -> str:
    """Texto del correo con el código de verificación de inicio de sesión."""
    return (
        "Hola,\n\n"
        f"Tu código de verificación es: {codigo}\n\n"
        f"Caduca en {VERIFICACION_VALIDEZ_MINUTOS} minutos. Si no has "
        "intentado iniciar sesión, puedes ignorar este mensaje.\n\n"
        "Asistente IA para FP"
    )


def enviar_codigo(usuario: Usuario) -> None:
    """
    Genera un código nuevo y lo envía al correo del usuario.

    Lanza :class:`CorreoNoConfigurado` o :class:`ErrorCorreo` si no se
    puede entregar; en ese caso no queda ningún código pendiente.
    """

    codigo = repositorio.crear_codigo(usuario.dni)

    try:
        enviar_correo(
            usuario.email,
            "Tu código de acceso",
            _cuerpo_correo(codigo),
        )
    except (CorreoNoConfigurado, ErrorCorreo):
        repositorio.limpiar(usuario.dni)
        raise

    logger.info(
        "Código de verificación enviado para el DNI %s.",
        usuario.dni,
    )


def comprobar_codigo(dni: str, codigo: str) -> str:
    """Devuelve el resultado de comprobar el código introducido."""

    return repositorio.comprobar(dni, (codigo or "").strip())


def segundos_para_reenviar(dni: str) -> int:
    """Segundos que faltan para poder pedir otro código."""

    return repositorio.segundos_para_reenviar(dni)


def cancelar(dni: str) -> None:
    """Elimina el código pendiente del usuario."""

    repositorio.limpiar(dni)


# ----------------------------------------------------------------------
# Estado en la sesión
# ----------------------------------------------------------------------
def marcar_pendiente(dni: str, origen: str = ORIGEN_ALUMNADO) -> None:
    """
    Marca en la sesión que este DNI tiene una verificación pendiente.

    ``origen`` indica desde qué acceso se ha iniciado (``alumnado`` o
    ``profesorado``); determina a dónde se envía al usuario al terminar.
    """

    session[_CLAVE_SESION] = {"dni": dni, "origen": origen}


def dni_pendiente() -> str | None:
    """DNI con verificación pendiente en la sesión, o ``None``."""

    dato = session.get(_CLAVE_SESION)

    return dato["dni"] if dato else None


def origen_pendiente() -> str:
    """
    Acceso desde el que se inició la verificación pendiente.

    Devuelve ``alumnado`` por defecto (también si no hay nada pendiente).
    """

    dato = session.get(_CLAVE_SESION) or {}

    return dato.get("origen", ORIGEN_ALUMNADO)


def limpiar_pendiente() -> None:
    """Borra la marca de verificación pendiente de la sesión."""

    session.pop(_CLAVE_SESION, None)

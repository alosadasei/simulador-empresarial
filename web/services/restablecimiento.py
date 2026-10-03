"""
Servicio web del restablecimiento de contraseña.

Orquesta la generación y el envío del código por correo y guarda en la
sesión de Flask qué usuario tiene un restablecimiento pendiente.

Es el equivalente de :mod:`web.services.verificacion` pero para el
enlace "¿Has olvidado tu contraseña?" que aparece en ambos accesos
(alumnado y profesorado).
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
from src.usuarios.restablecimiento import RepositorioRestablecimiento

logger = logging.getLogger(__name__)

# Clave de la sesión donde se guarda el restablecimiento pendiente.
_CLAVE_SESION = "restablecimiento_pendiente"

repositorio = RepositorioRestablecimiento()

__all__ = [
    "inicializar",
    "enviar_codigo",
    "comprobar_codigo",
    "segundos_para_reenviar",
    "cancelar",
    "marcar_pendiente",
    "dni_pendiente",
    "limpiar_pendiente",
    "correo_configurado",
    "CorreoNoConfigurado",
    "ErrorCorreo",
]


def inicializar() -> None:
    """Crea la tabla de códigos de restablecimiento si no existe."""

    repositorio.inicializar()


def _cuerpo_correo(codigo: str) -> str:
    """Texto del correo con el código para restablecer la contraseña."""
    return (
        "Hola,\n\n"
        "Has solicitado restablecer tu contraseña.\n\n"
        f"Tu código es: {codigo}\n\n"
        f"Caduca en {VERIFICACION_VALIDEZ_MINUTOS} minutos. Si no has "
        "sido tú, ignora este mensaje: tu contraseña no cambiará.\n\n"
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
            "Restablecer tu contraseña",
            _cuerpo_correo(codigo),
        )
    except (CorreoNoConfigurado, ErrorCorreo):
        repositorio.limpiar(usuario.dni)
        raise

    logger.info(
        "Código de restablecimiento enviado para el DNI %s.",
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
def marcar_pendiente(dni: str) -> None:
    """Marca en la sesión que este DNI tiene un restablecimiento pendiente."""

    session[_CLAVE_SESION] = {"dni": dni}


def dni_pendiente() -> str | None:
    """DNI con restablecimiento pendiente en la sesión, o ``None``."""

    dato = session.get(_CLAVE_SESION)

    return dato["dni"] if dato else None


def limpiar_pendiente() -> None:
    """Borra la marca de restablecimiento pendiente de la sesión."""

    session.pop(_CLAVE_SESION, None)

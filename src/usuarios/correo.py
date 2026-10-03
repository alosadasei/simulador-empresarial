"""
Envío de correo electrónico mediante SMTP (biblioteca estándar).

Se usa para entregar los códigos de la verificación en dos pasos. La
configuración se lee de variables de entorno a través de
:mod:`src.core.config` (``SMTP_HOST``, ``SMTP_PORT``, ``SMTP_USER``,
``SMTP_PASSWORD``, ``SMTP_FROM``, ``SMTP_TLS``).
"""

import smtplib
import ssl
from email.message import EmailMessage

from src.core.config import (
    SMTP_CONTRASENA,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_REMITENTE,
    SMTP_TLS,
    SMTP_USUARIO,
)


class ErrorCorreo(Exception):
    """No se ha podido enviar el correo electrónico."""


class CorreoNoConfigurado(ErrorCorreo):
    """Falta la configuración del servidor SMTP."""


def correo_configurado() -> bool:
    """
    Indica si hay datos suficientes para enviar correo.

    Se considera configurado cuando existen servidor y remitente.
    """

    return bool(SMTP_HOST and SMTP_REMITENTE)


def enviar_correo(
    destinatario: str,
    asunto: str,
    cuerpo: str,
) -> None:
    """
    Envía un correo de texto plano.

    Lanza :class:`CorreoNoConfigurado` si falta la configuración SMTP y
    :class:`ErrorCorreo` si el servidor rechaza el mensaje o no responde.
    """

    if not correo_configurado():
        raise CorreoNoConfigurado(
            "El servicio de correo no está configurado (falta SMTP_HOST)."
        )

    mensaje = EmailMessage()
    mensaje["From"] = SMTP_REMITENTE
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(cuerpo)

    contexto = ssl.create_default_context()

    try:
        if SMTP_PORT == 465:
            servidor = smtplib.SMTP_SSL(
                SMTP_HOST,
                SMTP_PORT,
                context=contexto,
                timeout=15,
            )
        else:
            servidor = smtplib.SMTP(
                SMTP_HOST,
                SMTP_PORT,
                timeout=15,
            )

        with servidor:
            if SMTP_PORT != 465 and SMTP_TLS:
                servidor.starttls(context=contexto)

            if SMTP_USUARIO:
                servidor.login(SMTP_USUARIO, SMTP_CONTRASENA)

            servidor.send_message(mensaje)

    except (smtplib.SMTPException, OSError) as error:
        raise ErrorCorreo(
            f"No se ha podido enviar el correo: {error}"
        ) from error

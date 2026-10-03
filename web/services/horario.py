"""
Control del horario de acceso del alumnado.

Los alumnos (rol ``usuario``) solo pueden iniciar sesión y generar
respuestas del chatbot entre ``HORARIO_ALUMNADO_INICIO`` y
``HORARIO_ALUMNADO_FIN``, en hora de ``ZONA_HORARIA_ALUMNADO``. Las
cuentas de profesorado no tienen esta restricción, ni siquiera cuando
acceden por la puerta de alumnado.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from src.core.config import (
    HORARIO_ALUMNADO_FIN,
    HORARIO_ALUMNADO_INICIO,
    ZONA_HORARIA_ALUMNADO,
)

_ZONA = ZoneInfo(ZONA_HORARIA_ALUMNADO)

MENSAJE_FUERA_DE_HORARIO = (
    "El acceso del alumnado solo está disponible de "
    f"{HORARIO_ALUMNADO_INICIO:02d}:00 a {HORARIO_ALUMNADO_FIN:02d}:00."
)


def dentro_de_horario_alumnado() -> bool:
    """
    Indica si la hora actual está dentro del horario permitido para el
    alumnado.
    """

    hora = datetime.now(_ZONA).hour

    return HORARIO_ALUMNADO_INICIO <= hora < HORARIO_ALUMNADO_FIN

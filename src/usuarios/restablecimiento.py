"""
Repositorio de códigos para restablecer la contraseña.

Reutiliza :class:`RepositorioVerificacion` sobre una tabla propia
(``codigos_restablecimiento``): mismo funcionamiento (código de un solo
uso, con caducidad e intentos limitados) pero independiente del código
de acceso en dos pasos.
"""

from pathlib import Path

from src.core.config import RUTA_BASE_DATOS_USUARIOS
from src.usuarios.verificacion import (
    TABLA_RESTABLECIMIENTO,
    RepositorioVerificacion,
)


class RepositorioRestablecimiento(RepositorioVerificacion):
    """Códigos de un solo uso para restablecer la contraseña."""

    def __init__(
        self,
        ruta_bd: Path | str = RUTA_BASE_DATOS_USUARIOS,
    ) -> None:
        """Usa la tabla de códigos de restablecimiento de contraseña."""
        super().__init__(
            ruta_bd=ruta_bd,
            tabla=TABLA_RESTABLECIMIENTO,
        )

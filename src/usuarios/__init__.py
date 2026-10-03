"""
Paquete de gestión de usuarios.

Define el modelo de usuario, la seguridad de las contraseñas, el
repositorio que persiste las cuentas en una base de datos SQLite y la
verificación en dos pasos por correo electrónico.

Existen dos roles diferenciados:

- ``usuario``: solo tiene acceso a la parte pública de la aplicación.
- ``profesor``: además tiene acceso a la parte privada (panel de gestión).
"""

from src.usuarios.correo import (
    CorreoNoConfigurado,
    ErrorCorreo,
    correo_configurado,
    enviar_correo,
)
from src.usuarios.modelos import (
    ROL_PROFESOR,
    ROL_USUARIO,
    ROLES_VALIDOS,
    Usuario,
)
from src.usuarios.repositorio import (
    DatosInvalidos,
    ErrorUsuarios,
    RepositorioUsuarios,
    UsuarioNoEncontrado,
    UsuarioYaExiste,
)
from src.usuarios.restablecimiento import RepositorioRestablecimiento
from src.usuarios.verificacion import RepositorioVerificacion

__all__ = [
    "ROL_PROFESOR",
    "ROL_USUARIO",
    "ROLES_VALIDOS",
    "Usuario",
    "RepositorioUsuarios",
    "ErrorUsuarios",
    "DatosInvalidos",
    "UsuarioYaExiste",
    "UsuarioNoEncontrado",
    "RepositorioVerificacion",
    "RepositorioRestablecimiento",
    "correo_configurado",
    "enviar_correo",
    "ErrorCorreo",
    "CorreoNoConfigurado",
]

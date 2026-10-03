"""
Modelo de dominio de los usuarios.

El modelo es independiente de la base de datos: representa únicamente
los datos de una cuenta tal y como los usa el resto de la aplicación.
La contraseña (su hash) nunca forma parte de este objeto.
"""

from dataclasses import dataclass

# Roles disponibles en la aplicación.
ROL_USUARIO = "usuario"
ROL_PROFESOR = "profesor"

ROLES_VALIDOS = frozenset({ROL_USUARIO, ROL_PROFESOR})


@dataclass(frozen=True, slots=True)
class Usuario:
    """
    Representa una cuenta de la aplicación.

    Contiene:
    - ``dni``: documento de identidad. Actúa como identificador único.
    - ``nombre_usuario``: nombre de acceso, único.
    - ``nombre``: nombre real de la persona.
    - ``fecha_nacimiento``: fecha en formato ``AAAA-MM-DD``.
    - ``email``: correo electrónico, único.
    - ``rol``: ``usuario`` (parte pública) o ``profesor`` (parte privada).
    - ``activo``: si es ``False``, la cuenta está dada de baja y no
      puede iniciar sesión (solo aplicable al alumnado).
    """

    dni: str
    nombre_usuario: str
    nombre: str
    fecha_nacimiento: str
    email: str
    rol: str
    activo: bool = True

    @property
    def es_profesor(self) -> bool:
        """Indica si la cuenta tiene acceso a la parte privada."""

        return self.rol == ROL_PROFESOR

    def a_diccionario(self) -> dict:
        """
        Devuelve una representación serializable del usuario.

        Es la forma en la que se guarda en la sesión de Flask.
        """

        return {
            "dni": self.dni,
            "nombre_usuario": self.nombre_usuario,
            "nombre": self.nombre,
            "fecha_nacimiento": self.fecha_nacimiento,
            "email": self.email,
            "rol": self.rol,
            "activo": self.activo,
        }

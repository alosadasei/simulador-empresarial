"""
Servicios web relacionados con las cuentas de usuario.

Expone una instancia única del repositorio de usuarios y utilidades
para manejar la sesión de Flask (iniciar sesión, cerrarla y consultar
quién es el usuario actual y su rol).
"""

from flask import session

from src.usuarios import (
    ROL_PROFESOR,
    ROL_USUARIO,
    RepositorioUsuarios,
    Usuario,
)

# Clave bajo la que se guarda el usuario en la sesión.
_CLAVE_SESION = "usuario"

# Repositorio compartido por toda la aplicación web.
repositorio = RepositorioUsuarios()


def inicializar_usuarios() -> None:
    """
    Prepara la base de datos de usuarios.

    Crea el esquema (cuentas y códigos de verificación) si no existe y
    siembra la cuenta de profesor inicial a partir de las variables de
    entorno ``USUARIO_PROFESOR`` y ``CONTRASENA_PROFESOR``.
    """

    from web.services import restablecimiento, verificacion

    repositorio.inicializar()
    verificacion.inicializar()
    restablecimiento.inicializar()
    repositorio.asegurar_profesor_inicial()


def iniciar_sesion(usuario: Usuario) -> None:
    """
    Guarda al usuario autenticado en la sesión.

    Se mantiene también la clave ``profesor_autenticado`` para que el
    código existente del panel privado siga funcionando sin cambios.
    """

    session[_CLAVE_SESION] = usuario.a_diccionario()
    session["profesor_autenticado"] = usuario.es_profesor

    if usuario.es_profesor:
        session["usuario_profesor"] = usuario.nombre_usuario
    else:
        session.pop("usuario_profesor", None)


def cerrar_sesion() -> None:
    """Elimina cualquier rastro de sesión del usuario."""

    session.clear()


def usuario_actual() -> dict | None:
    """
    Devuelve los datos del usuario autenticado (diccionario) o ``None``.
    """

    return session.get(_CLAVE_SESION)


def hay_sesion() -> bool:
    """Indica si hay un usuario (de cualquier rol) autenticado."""

    return usuario_actual() is not None


def rol_actual() -> str | None:
    """Devuelve el rol del usuario autenticado, o ``None``."""

    usuario = usuario_actual()

    return usuario["rol"] if usuario else None


def es_profesor() -> bool:
    """Indica si el usuario autenticado tiene acceso a la parte privada."""

    return rol_actual() == ROL_PROFESOR


def es_usuario() -> bool:
    """Indica si el usuario autenticado tiene el rol público básico."""

    return rol_actual() == ROL_USUARIO

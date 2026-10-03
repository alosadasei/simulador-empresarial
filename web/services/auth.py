"""
Servicios relacionados con la autenticación y los permisos.

Incluye funciones auxiliares para comprobar la sesión y decoradores
para proteger rutas según el rol del usuario:

- ``login_requerido`` / ``profesor_requerido``: solo profesores
  (parte privada de la aplicación).
- ``sesion_requerida``: cualquier usuario autenticado.
"""
from collections.abc import Callable
from functools import wraps

from flask import flash, redirect, session, url_for


def profesor_autenticado() -> bool:
    """
    Comprueba si hay un profesor con la sesión iniciada.
    """

    return bool(
        session.get(
            "profesor_autenticado",
            False,
        )
    )


def usuario_autenticado() -> bool:
    """
    Comprueba si hay algún usuario (de cualquier rol) con la sesión
    iniciada.
    """

    return session.get("usuario") is not None


def profesor_requerido(
    funcion: Callable,
) -> Callable:
    """
    Protege una ruta para que solo pueda acceder un profesor
    autenticado. Si no, redirige al formulario de acceso.
    """

    @wraps(funcion)
    def funcion_protegida(
        *args,
        **kwargs,
    ):
        """Redirige al login si no hay profesor autenticado; si lo hay, ejecuta la vista."""
        if not profesor_autenticado():
            flash(
                (
                    "Debes iniciar sesión como profesor para "
                    "acceder al panel."
                ),
                "error",
            )

            return redirect(url_for("profesorado.login"))

        return funcion(
            *args,
            **kwargs,
        )

    return funcion_protegida


def sesion_requerida(
    funcion: Callable,
) -> Callable:
    """
    Protege una ruta para que solo pueda acceder un usuario
    autenticado, sea del rol que sea.
    """

    @wraps(funcion)
    def funcion_protegida(
        *args,
        **kwargs,
    ):
        """Redirige al login si no hay sesión; si la hay, ejecuta la vista."""
        if not usuario_autenticado():
            flash(
                "Debes iniciar sesión para acceder a esta página.",
                "error",
            )

            return redirect(url_for("auth.login"))

        return funcion(
            *args,
            **kwargs,
        )

    return funcion_protegida


# Alias histórico: en el código anterior "login" equivalía a "profesor".
login_requerido = profesor_requerido
"""
Acceso y alta de cuentas de profesorado.

Estas rutas viven bajo ``/profesorado`` y NO se enlazan desde ninguna
página pública de la aplicación — solo debe conocerlas el profesorado,
a quien se le compartirá la URL por otro canal (correo, por ejemplo).

Relación con el login general (``/login``):

- Por ``/login`` puede entrar cualquier cuenta, también la de un
  profesor, pero siempre a la parte pública y al chatbot: nunca al
  panel. Un profesor que entra por ahí sigue sin aparecer en el
  listado de alumnado.
- Estas rutas son la única puerta al panel privado: una cuenta de
  alumnado que intente entrar aquí recibe el mismo "usuario o
  contraseña incorrectos" que si no existiera.

El segundo paso (código de verificación por correo) se reutiliza tal
cual del módulo ``auth``. Lo que decide el destino final es el acceso
por el que se ha empezado (``origen``), no el rol de la cuenta.
"""
import logging

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from src.usuarios import DatosInvalidos, UsuarioYaExiste
from src.usuarios.modelos import ROL_PROFESOR
from web.services import verificacion
from web.services.auth import profesor_autenticado, usuario_autenticado
from web.services.usuarios import repositorio

logger = logging.getLogger(__name__)

profesorado_bp = Blueprint(
    "profesorado",
    __name__,
    url_prefix="/profesorado",
)


def _ocultar_email(email: str) -> str:
    """
    Enmascara un correo para mostrarlo sin revelarlo por completo.
    """

    try:
        local, dominio = email.split("@", 1)
    except ValueError:
        return email

    visible = local[:2] if len(local) > 2 else local[:1]
    oculto = "*" * max(3, len(local) - len(visible))

    return f"{visible}{oculto}@{dominio}"


@profesorado_bp.route(
    "/acceso",
    methods=["GET", "POST"],
)
def login():
    """
    Primer paso del acceso exclusivo de profesorado.

    Si las credenciales corresponden a una cuenta de alumnado (o no
    existen), se responde exactamente igual que si el usuario no
    existiera: no se revela nada sobre qué cuentas hay en el sistema.
    """

    if profesor_autenticado():
        return redirect(url_for("profesor.gestionar_documentos"))

    if usuario_autenticado():
        return redirect(url_for("public.inicio"))

    if verificacion.dni_pendiente():
        return redirect(url_for("auth.verificar_login"))

    if request.method == "POST":
        identificador = request.form.get(
            "identificador",
            "",
        ).strip()

        contrasena = request.form.get(
            "contrasena",
            "",
        )

        usuario = repositorio.autenticar(identificador, contrasena)

        if usuario is None or not usuario.es_profesor:
            flash(
                "El usuario o la contraseña no son correctos.",
                "error",
            )

            return render_template("profesorado_login.html")

        if not verificacion.correo_configurado():
            logger.error(
                "Inicio de sesión de profesorado bloqueado: el servidor "
                "SMTP no está configurado."
            )

            flash(
                "El servicio de correo no está disponible en este "
                "momento. Inténtalo de nuevo más tarde.",
                "error",
            )

            return render_template("profesorado_login.html")

        try:
            verificacion.enviar_codigo(usuario)

        except (verificacion.CorreoNoConfigurado, verificacion.ErrorCorreo) as error:
            logger.error(
                "No se ha podido enviar el código de verificación: %s",
                error,
            )

            flash(
                "No se ha podido enviar el código de verificación a tu "
                "correo. Inténtalo de nuevo más tarde.",
                "error",
            )

            return render_template("profesorado_login.html")

        verificacion.marcar_pendiente(usuario.dni, "profesorado")

        flash(
            "Te hemos enviado un código de verificación a "
            f"{_ocultar_email(usuario.email)}.",
            "informacion",
        )

        return redirect(url_for("auth.verificar_login"))

    return render_template("profesorado_login.html")


@profesorado_bp.route(
    "/registro",
    methods=["GET", "POST"],
)
def registro():
    """
    Alta de una cuenta nueva con rol ``profesor``.
    """

    if profesor_autenticado():
        return redirect(url_for("profesor.gestionar_documentos"))

    campos = {
        "nombre_usuario": "",
        "nombre": "",
        "fecha_nacimiento": "",
        "email": "",
    }

    if request.method == "POST":
        for campo in campos:
            campos[campo] = request.form.get(campo, "").strip()

        contrasena = request.form.get("contrasena", "")
        confirmacion = request.form.get("confirmacion", "")

        email = campos["email"]

        if not email:
            flash(
                "El correo electrónico es obligatorio.",
                "error",
            )

            return render_template(
                "profesorado_registro.html",
                campos=campos,
            )

        if contrasena != confirmacion:
            flash(
                "Las contraseñas no coinciden.",
                "error",
            )

            return render_template(
                "profesorado_registro.html",
                campos=campos,
            )

        # Nombre de usuario: si no se indica, se deriva del correo,
        # comprobando que no choque con uno ya existente.
        base_nombre_usuario = campos["nombre_usuario"] or email.split(
            "@",
            1,
        )[0]

        if len(base_nombre_usuario) < 3:
            base_nombre_usuario = f"profe-{base_nombre_usuario}"

        nombre_usuario = base_nombre_usuario
        sufijo = 1

        while repositorio.obtener_por_nombre_usuario(nombre_usuario) is not None:
            sufijo += 1
            nombre_usuario = f"{base_nombre_usuario}{sufijo}"

        nombre = campos["nombre"] or nombre_usuario
        fecha_nacimiento = campos["fecha_nacimiento"] or "2000-01-01"

        # DNI: se genera automáticamente (no lo introduce el usuario).
        # Es determinista a partir del correo, así que si por una
        # coincidencia muy improbable choca con uno ya existente,
        # se reintenta con una semilla ligeramente distinta.
        usuario_creado = None

        for intento in range(5):
            semilla = email if intento == 0 else f"{email}:{intento}"
            dni = repositorio._dni_placeholder(semilla)

            try:
                usuario_creado = repositorio.crear_usuario(
                    nombre_usuario=nombre_usuario,
                    nombre=nombre,
                    fecha_nacimiento=fecha_nacimiento,
                    email=email,
                    dni=dni,
                    contrasena=contrasena,
                    rol=ROL_PROFESOR,
                )

                break

            except UsuarioYaExiste as error:
                if repositorio.obtener_por_dni(dni) is None:
                    # El conflicto es real (email o usuario duplicado),
                    # no una colisión del DNI generado.
                    flash(str(error), "error")

                    return render_template(
                        "profesorado_registro.html",
                        campos=campos,
                    )

                continue

            except DatosInvalidos as error:
                flash(str(error), "error")

                return render_template(
                    "profesorado_registro.html",
                    campos=campos,
                )

        if usuario_creado is None:
            flash(
                "No se ha podido crear la cuenta. Inténtalo de nuevo.",
                "error",
            )

            return render_template(
                "profesorado_registro.html",
                campos=campos,
            )

        flash(
            "Cuenta de profesorado creada. Inicia sesión para acceder.",
            "exito",
        )

        return redirect(url_for("profesorado.login"))

    return render_template(
        "profesorado_registro.html",
        campos=campos,
    )
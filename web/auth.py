"""
Rutas de autenticación y registro de usuarios.

El inicio de sesión tiene dos pasos:

1. El usuario introduce identificador y contraseña.
2. Se le envía un código por correo que debe introducir para completar
   el acceso.

Las cuentas nuevas (rol ``usuario``) se crean desde ``/registro``. Las
de profesor solo se crean sembrando o editando la base de datos.
"""
import logging

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.core.config import VERIFICACION_LONGITUD_CODIGO
from src.usuarios import (
    DatosInvalidos,
    UsuarioNoEncontrado,
    UsuarioYaExiste,
)
from src.usuarios.seguridad import (
    LONGITUD_MINIMA_CONTRASENA,
    contrasena_es_valida,
)
from web.services import restablecimiento, verificacion
from web.services.auth import profesor_autenticado, usuario_autenticado
from web.services.horario import (
    MENSAJE_FUERA_DE_HORARIO,
    dentro_de_horario_alumnado,
)
from web.services.usuarios import (
    cerrar_sesion,
    iniciar_sesion,
    repositorio,
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint(
    "auth",
    __name__,
)


def _destino_tras_login(es_profesor: bool, origen: str = "alumnado") -> str:
    """
    Decide a dónde enviar al usuario recién autenticado.

    Solo el acceso de profesorado (``origen == "profesorado"``) lleva al
    panel privado. Si un profesor entra por el acceso de alumnado, se le
    lleva a la parte pública como a cualquier otra cuenta.
    """

    if es_profesor and origen == "profesorado":
        return url_for("profesor.gestionar_documentos")

    return url_for("public.inicio")


def _ocultar_email(email: str) -> str:
    """
    Enmascara un correo para mostrarlo sin revelarlo por completo.

    Ejemplo: ``ana.perez@ejemplo.com`` -> ``an******@ejemplo.com``.
    """

    try:
        local, dominio = email.split("@", 1)
    except ValueError:
        return email

    visible = local[:2] if len(local) > 2 else local[:1]
    oculto = "*" * max(3, len(local) - len(visible))

    return f"{visible}{oculto}@{dominio}"


@auth_bp.route(
    "/login",
    methods=["GET", "POST"],
)
def login():
    """
    Primer paso del acceso de alumnado: comprueba identificador y
    contraseña y, si son correctos, envía un código de verificación al
    correo del usuario.

    Una cuenta de profesor también puede entrar por aquí: accederá a la
    parte pública y al chatbot como un alumno más (nunca al panel), y
    seguirá sin aparecer en el listado de alumnado.
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

        if usuario is None:
            flash(
                "El usuario o la contraseña no son correctos.",
                "error",
            )

            return render_template("login.html")

        if not usuario.es_profesor and not usuario.activo:
            flash(
                "Esta cuenta ha sido dada de baja. Contacta con tu "
                "profesor si crees que es un error.",
                "error",
            )

            return render_template("login.html")

        if not usuario.es_profesor and not dentro_de_horario_alumnado():
            flash(MENSAJE_FUERA_DE_HORARIO, "error")

            return render_template("login.html")

        if not verificacion.correo_configurado():
            logger.error(
                "Inicio de sesión bloqueado: el servidor SMTP no está "
                "configurado."
            )

            flash(
                "El servicio de correo no está disponible en este "
                "momento. Inténtalo de nuevo más tarde.",
                "error",
            )

            return render_template("login.html")

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

            return render_template("login.html")

        verificacion.marcar_pendiente(usuario.dni, "alumnado")

        flash(
            "Te hemos enviado un código de verificación a "
            f"{_ocultar_email(usuario.email)}.",
            "informacion",
        )

        return redirect(url_for("auth.verificar_login"))

    return render_template("login.html")


@auth_bp.route(
    "/login/verificar",
    methods=["GET", "POST"],
)
def verificar_login():
    """
    Segundo paso del acceso: comprueba el código enviado por correo.
    """

    dni = verificacion.dni_pendiente()

    if not dni:
        return redirect(url_for("auth.login"))

    usuario = repositorio.obtener_por_dni(dni)

    if usuario is None:
        verificacion.limpiar_pendiente()

        return redirect(url_for("auth.login"))

    if not usuario.es_profesor and not usuario.activo:
        verificacion.limpiar_pendiente()

        flash(
            "Esta cuenta ha sido dada de baja. Contacta con tu "
            "profesor si crees que es un error.",
            "error",
        )

        return redirect(url_for("auth.login"))

    if not usuario.es_profesor and not dentro_de_horario_alumnado():
        verificacion.limpiar_pendiente()

        flash(MENSAJE_FUERA_DE_HORARIO, "error")

        return redirect(url_for("auth.login"))

    if request.method == "POST":
        resultado = verificacion.comprobar_codigo(
            dni,
            request.form.get("codigo", ""),
        )

        if resultado == "ok":
            origen = verificacion.origen_pendiente()

            iniciar_sesion(usuario)
            verificacion.limpiar_pendiente()

            flash(
                "Has iniciado sesión correctamente.",
                "exito",
            )

            return redirect(
                _destino_tras_login(usuario.es_profesor, origen)
            )

        if resultado == "incorrecto":
            flash(
                "El código no es correcto. Revísalo e inténtalo de nuevo.",
                "error",
            )

        elif resultado == "expirado":
            verificacion.limpiar_pendiente()

            flash(
                "El código ha caducado. Vuelve a iniciar sesión para "
                "recibir uno nuevo.",
                "error",
            )

            return redirect(url_for("auth.login"))

        elif resultado == "bloqueado":
            verificacion.limpiar_pendiente()

            flash(
                "Demasiados intentos fallidos. Vuelve a iniciar sesión "
                "para recibir un código nuevo.",
                "error",
            )

            return redirect(url_for("auth.login"))

        else:  # sin_codigo
            verificacion.limpiar_pendiente()

            flash(
                "No hay ninguna verificación pendiente. Inicia sesión "
                "de nuevo.",
                "error",
            )

            return redirect(url_for("auth.login"))

    return render_template(
        "verificar.html",
        email_oculto=_ocultar_email(usuario.email),
        longitud_codigo=VERIFICACION_LONGITUD_CODIGO,
        segundos_reenvio=verificacion.segundos_para_reenviar(dni),
    )


@auth_bp.route(
    "/login/reenviar",
    methods=["POST"],
)
def reenviar_codigo():
    """
    Envía un código nuevo, respetando el tiempo de espera entre envíos.
    """

    dni = verificacion.dni_pendiente()

    if not dni:
        return redirect(url_for("auth.login"))

    usuario = repositorio.obtener_por_dni(dni)

    if usuario is None:
        verificacion.limpiar_pendiente()

        return redirect(url_for("auth.login"))

    espera = verificacion.segundos_para_reenviar(dni)

    if espera > 0:
        flash(
            f"Espera {espera} segundos antes de pedir otro código.",
            "error",
        )

        return redirect(url_for("auth.verificar_login"))

    try:
        verificacion.enviar_codigo(usuario)

    except (verificacion.CorreoNoConfigurado, verificacion.ErrorCorreo) as error:
        logger.error(
            "No se ha podido reenviar el código de verificación: %s",
            error,
        )

        flash(
            "No se ha podido reenviar el código. Inténtalo más tarde.",
            "error",
        )

        return redirect(url_for("auth.verificar_login"))

    flash(
        "Te hemos enviado un código nuevo.",
        "informacion",
    )

    return redirect(url_for("auth.verificar_login"))


@auth_bp.route("/login/cancelar")
def cancelar_verificacion():
    """
    Cancela una verificación pendiente y vuelve al formulario de acceso.
    """

    dni = verificacion.dni_pendiente()

    if dni:
        verificacion.cancelar(dni)

    verificacion.limpiar_pendiente()

    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Restablecimiento de contraseña ("¿Has olvidado tu contraseña?")
#
# Flujo compartido por los dos accesos. El parámetro ``origen``
# (``alumnado`` o ``profesorado``) solo sirve para volver al login
# correcto y para que cada puerta atienda a su propio rol.
# ---------------------------------------------------------------------------
def _origen_valido(valor: str | None) -> str:
    """Normaliza el origen (alumnado o profesorado); cualquier otro valor cae en alumnado."""
    return "profesorado" if valor == "profesorado" else "alumnado"


def _login_de_origen(origen: str) -> str:
    """Devuelve la URL de login correspondiente al origen."""
    if origen == "profesorado":
        return url_for("profesorado.login")

    return url_for("auth.login")


def _contexto_recuperar(origen: str) -> dict:
    """Datos que necesita la plantilla de recuperar contraseña."""
    return {
        "origen": origen,
        "url_login": _login_de_origen(origen),
    }


def _contexto_restablecer(origen: str, dni: str | None) -> dict:
    """Datos que necesita la plantilla de restablecer contraseña, incluida la espera para reenviar el código."""
    return {
        "origen": origen,
        "url_login": _login_de_origen(origen),
        "longitud_codigo": VERIFICACION_LONGITUD_CODIGO,
        "segundos_reenvio": (
            restablecimiento.segundos_para_reenviar(dni) if dni else 0
        ),
    }


@auth_bp.route(
    "/recuperar-contrasena",
    methods=["GET", "POST"],
)
def recuperar_contrasena():
    """
    Paso 1: el usuario introduce su correo y se le envía un código.

    La respuesta es siempre la misma exista o no la cuenta, para no
    revelar qué correos están registrados.
    """

    if usuario_autenticado() or profesor_autenticado():
        return redirect(url_for("public.inicio"))

    origen = _origen_valido(request.values.get("origen"))

    if request.method == "POST":
        if not restablecimiento.correo_configurado():
            logger.error(
                "Restablecimiento bloqueado: el servidor SMTP no está "
                "configurado."
            )

            flash(
                "El servicio de correo no está disponible en este "
                "momento. Inténtalo de nuevo más tarde.",
                "error",
            )

            return render_template(
                "recuperar_contrasena.html",
                **_contexto_recuperar(origen),
            )

        email = request.form.get("email", "").strip()

        usuario = repositorio.obtener_por_email(email) if email else None

        coincide_rol = (
            usuario is not None
            and usuario.es_profesor == (origen == "profesorado")
        )

        if coincide_rol:
            try:
                restablecimiento.enviar_codigo(usuario)
                restablecimiento.marcar_pendiente(usuario.dni)

            except (
                restablecimiento.CorreoNoConfigurado,
                restablecimiento.ErrorCorreo,
            ) as error:
                # No se revela el fallo: se responde igual que siempre.
                logger.error(
                    "No se ha podido enviar el código de "
                    "restablecimiento: %s",
                    error,
                )

        session["restablecimiento_origen"] = origen

        flash(
            "Si existe una cuenta con ese correo electrónico, recibirás "
            "un código para restablecer la contraseña.",
            "informacion",
        )

        return redirect(url_for("auth.restablecer_contrasena"))

    return render_template(
        "recuperar_contrasena.html",
        **_contexto_recuperar(origen),
    )


@auth_bp.route(
    "/restablecer-contrasena",
    methods=["GET", "POST"],
)
def restablecer_contrasena():
    """
    Paso 2: el usuario introduce el código recibido y su contraseña
    nueva.
    """

    if usuario_autenticado() or profesor_autenticado():
        return redirect(url_for("public.inicio"))

    origen = session.get("restablecimiento_origen")

    if not origen:
        return redirect(url_for("auth.recuperar_contrasena"))

    dni = restablecimiento.dni_pendiente()

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        nueva = request.form.get("contrasena", "")
        confirmacion = request.form.get("confirmacion", "")

        if nueva != confirmacion:
            flash("Las contraseñas no coinciden.", "error")

            return render_template(
                "restablecer_contrasena.html",
                **_contexto_restablecer(origen, dni),
            )

        if not contrasena_es_valida(nueva):
            flash(
                "La contraseña debe tener al menos "
                f"{LONGITUD_MINIMA_CONTRASENA} caracteres.",
                "error",
            )

            return render_template(
                "restablecer_contrasena.html",
                **_contexto_restablecer(origen, dni),
            )

        if dni is None:
            # No hay ningún código real (el correo no estaba registrado
            # o el rol no coincidía): mismo mensaje que un código erróneo.
            flash("El código no es correcto o ha caducado.", "error")

            return render_template(
                "restablecer_contrasena.html",
                **_contexto_restablecer(origen, dni),
            )

        resultado = restablecimiento.comprobar_codigo(dni, codigo)

        if resultado == "ok":
            try:
                repositorio.cambiar_contrasena(dni, nueva)

            except (DatosInvalidos, UsuarioNoEncontrado) as error:
                logger.error(
                    "No se ha podido cambiar la contraseña: %s",
                    error,
                )

                restablecimiento.limpiar_pendiente()
                session.pop("restablecimiento_origen", None)

                flash(
                    "No se ha podido actualizar la contraseña. Vuelve a "
                    "solicitar un código.",
                    "error",
                )

                return redirect(
                    url_for("auth.recuperar_contrasena", origen=origen)
                )

            restablecimiento.limpiar_pendiente()
            session.pop("restablecimiento_origen", None)

            flash(
                "Tu contraseña se ha actualizado. Ya puedes iniciar "
                "sesión.",
                "exito",
            )

            return redirect(_login_de_origen(origen))

        if resultado == "incorrecto":
            flash("El código no es correcto o ha caducado.", "error")

            return render_template(
                "restablecer_contrasena.html",
                **_contexto_restablecer(
                    origen,
                    restablecimiento.dni_pendiente(),
                ),
            )

        # expirado / bloqueado / sin_codigo
        restablecimiento.limpiar_pendiente()

        flash(
            "El código ha caducado o se han agotado los intentos. "
            "Solicita uno nuevo.",
            "error",
        )

        return redirect(
            url_for("auth.recuperar_contrasena", origen=origen)
        )

    return render_template(
        "restablecer_contrasena.html",
        **_contexto_restablecer(origen, dni),
    )


@auth_bp.route(
    "/restablecer-contrasena/reenviar",
    methods=["POST"],
)
def reenviar_restablecimiento():
    """
    Envía un código de restablecimiento nuevo, respetando la espera
    entre envíos.
    """

    origen = session.get("restablecimiento_origen")

    if not origen:
        return redirect(url_for("auth.recuperar_contrasena"))

    dni = restablecimiento.dni_pendiente()

    if dni is None:
        flash(
            "Si existe una cuenta con ese correo electrónico, recibirás "
            "otro código.",
            "informacion",
        )

        return redirect(url_for("auth.restablecer_contrasena"))

    espera = restablecimiento.segundos_para_reenviar(dni)

    if espera > 0:
        flash(
            f"Espera {espera} segundos antes de pedir otro código.",
            "error",
        )

        return redirect(url_for("auth.restablecer_contrasena"))

    usuario = repositorio.obtener_por_dni(dni)

    if usuario is None:
        restablecimiento.limpiar_pendiente()
        session.pop("restablecimiento_origen", None)

        return redirect(url_for("auth.recuperar_contrasena"))

    try:
        restablecimiento.enviar_codigo(usuario)

    except (
        restablecimiento.CorreoNoConfigurado,
        restablecimiento.ErrorCorreo,
    ) as error:
        logger.error(
            "No se ha podido reenviar el código de restablecimiento: %s",
            error,
        )

        flash(
            "No se ha podido reenviar el código. Inténtalo más tarde.",
            "error",
        )

        return redirect(url_for("auth.restablecer_contrasena"))

    flash("Te hemos enviado un código nuevo.", "informacion")

    return redirect(url_for("auth.restablecer_contrasena"))


@auth_bp.route("/restablecer-contrasena/cancelar")
def cancelar_restablecimiento():
    """
    Cancela un restablecimiento pendiente y vuelve al login de origen.
    """

    origen = session.get("restablecimiento_origen") or "alumnado"

    dni = restablecimiento.dni_pendiente()

    if dni:
        restablecimiento.cancelar(dni)

    restablecimiento.limpiar_pendiente()
    session.pop("restablecimiento_origen", None)

    return redirect(_login_de_origen(origen))


@auth_bp.route(
    "/registro",
    methods=["GET", "POST"],
)
def registro():
    """
    Alta de una cuenta nueva con rol ``usuario``.
    """

    if usuario_autenticado():
        return redirect(url_for("public.inicio"))

    campos = {
        "nombre_usuario": "",
        "nombre": "",
        "fecha_nacimiento": "",
        "email": "",
        "dni": "",
    }

    if request.method == "POST":
        for campo in campos:
            campos[campo] = request.form.get(campo, "").strip()

        contrasena = request.form.get("contrasena", "")
        confirmacion = request.form.get("confirmacion", "")

        if contrasena != confirmacion:
            flash(
                "Las contraseñas no coinciden.",
                "error",
            )

            return render_template("registro.html", campos=campos)

        try:
            repositorio.crear_usuario(
                nombre_usuario=campos["nombre_usuario"],
                nombre=campos["nombre"],
                fecha_nacimiento=campos["fecha_nacimiento"],
                email=campos["email"],
                dni=campos["dni"],
                contrasena=contrasena,
            )

        except (DatosInvalidos, UsuarioYaExiste) as error:
            flash(str(error), "error")

            return render_template("registro.html", campos=campos)

        flash(
            "Cuenta creada. Inicia sesión para acceder.",
            "exito",
        )

        return redirect(url_for("auth.login"))

    return render_template("registro.html", campos=campos)


@auth_bp.route("/logout")
def logout():
    """
    Cierra la sesión del usuario actual.
    """

    cerrar_sesion()

    flash(
        "Has cerrado sesión correctamente.",
        "informacion",
    )

    return redirect(url_for("public.inicio"))
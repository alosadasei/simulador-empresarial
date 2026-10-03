"""
Rutas del panel de administración para profesores.

Permite gestionar los documentos y reconstruir la base de conocimiento.
"""
from pathlib import Path
import json
from werkzeug.utils import secure_filename
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from src.ingestion.indexador import indexar_documentos
from src.rag.conversaciones_bd import RepositorioConversaciones
from src.usuarios import DatosInvalidos, UsuarioYaExiste
from src.usuarios.modelos import ROL_USUARIO
from web.services.auth import login_requerido
from web.services.usuarios import repositorio
from web.services.documentos import (
    es_pdf,
    mostrar_nombre_metodologia,
    obtener_carpeta_metodologia,
    obtener_documentos,
    obtener_metodologias,
)

profesor_bp = Blueprint(
    "profesor",
    __name__,
    url_prefix="/profesor",
)

# Repositorio de conversaciones, para que el profesorado pueda
# consultarlas en modo solo lectura. Es una instancia independiente de
# la que usa el chatbot (evita un import circular con web.public), pero
# apunta a la misma base de datos.
conversaciones_alumnado = RepositorioConversaciones()
conversaciones_alumnado.inicializar()

from src.core.config import RUTA_CONFIGURACION, METODOLOGIA_ACTIVA_POR_DEFECTO

def obtener_metodologia_activa():
    """
    Obtiene la metodología actualmente activa para el alumnado.
    """

    if not RUTA_CONFIGURACION.exists():
        return METODOLOGIA_ACTIVA_POR_DEFECTO

    try:
        with RUTA_CONFIGURACION.open(
            "r",
            encoding="utf-8",
        ) as archivo:
            configuracion = json.load(archivo)

        metodologia = configuracion.get(
            "metodologia_activa",
            METODOLOGIA_ACTIVA_POR_DEFECTO,
        )

        if metodologia in obtener_metodologias():
            return metodologia

    except (OSError, json.JSONDecodeError):
        pass

    return METODOLOGIA_ACTIVA_POR_DEFECTO


def guardar_metodologia_activa(metodologia):
    """
    Guarda la metodología activa para el alumnado.
    """

    RUTA_CONFIGURACION.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    configuracion = {
        "metodologia_activa": metodologia,
    }

    with RUTA_CONFIGURACION.open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            configuracion,
            archivo,
            ensure_ascii=False,
            indent=4,
        )


@profesor_bp.route("/documentos")
@login_requerido
def gestionar_documentos():
    """
    Muestra las metodologías disponibles y los documentos
    de la metodología seleccionada.
    """

    metodologias = obtener_metodologias()

    metodologia_seleccionada = request.args.get("metodologia")

    documentos = []

    if metodologia_seleccionada in metodologias:
        documentos = obtener_documentos(metodologia_seleccionada)

    metodologia_activa = obtener_metodologia_activa()

    return render_template(
        "gestion_documentos.html",
        metodologias=metodologias,
        metodologia_seleccionada=metodologia_seleccionada,
        metodologia_activa=metodologia_activa,
        documentos=documentos,
        mostrar_nombre_metodologia=mostrar_nombre_metodologia,
    )


@profesor_bp.route(
    "/metodologia-activa",
    methods=["POST"],
)
@login_requerido
def cambiar_metodologia_activa():
    """
    Cambia la metodología que verá y utilizará el alumnado.
    """

    metodologia = request.form.get(
        "metodologia",
        "",
    ).strip()

    metodologias = obtener_metodologias()

    if metodologia not in metodologias:
        flash(
            "La metodología seleccionada no es válida.",
            "error",
        )

        return redirect(url_for("profesor.gestionar_documentos"))

    try:
        guardar_metodologia_activa(metodologia)

        flash(
            (
                "Metodología activa cambiada a "
                f"{mostrar_nombre_metodologia(metodologia)}."
            ),
            "exito",
        )

    except OSError as error:
        flash(
            ("No se ha podido cambiar la metodología activa: " f"{error}"),
            "error",
        )

    return redirect(
        url_for(
            "profesor.gestionar_documentos",
            metodologia=metodologia,
        )
    )


@profesor_bp.route(
    "/documentos/subir",
    methods=["POST"],
)
@login_requerido
def subir_documento():
    """
    Sube un archivo PDF a la metodología seleccionada.
    """

    metodologia = request.form.get("metodologia")

    archivo = request.files.get("archivo")

    carpeta_metodologia = obtener_carpeta_metodologia(metodologia)

    if carpeta_metodologia is None:
        flash(
            ("La metodología seleccionada " "no es válida."),
            "error",
        )

        return redirect(url_for("profesor.gestionar_documentos"))

    if archivo is None or archivo.filename is None or archivo.filename == "":
        flash(
            ("Debes seleccionar " "un archivo."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    nombre_seguro = secure_filename(archivo.filename)

    if not nombre_seguro:
        flash(
            ("El nombre del archivo " "no es válido."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    if not es_pdf(nombre_seguro):
        flash(
            ("Solo se permiten " "archivos PDF."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    ruta_destino = carpeta_metodologia / nombre_seguro

    if ruta_destino.exists():
        flash(
            ("Ya existe un documento " "con ese nombre."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    archivo.save(ruta_destino)

    flash(
        ("Documento subido " "correctamente."),
        "exito",
    )

    return redirect(
        url_for(
            "profesor.gestionar_documentos",
            metodologia=metodologia,
        )
    )


@profesor_bp.route(
    "/documentos/eliminar",
    methods=["POST"],
)
@login_requerido
def eliminar_documento():
    """
    Elimina un archivo PDF de la metodología seleccionada.
    """

    metodologia = request.form.get("metodologia")

    nombre_documento = request.form.get("documento")

    carpeta_metodologia = obtener_carpeta_metodologia(metodologia)

    if carpeta_metodologia is None:
        flash(
            ("La metodología seleccionada " "no es válida."),
            "error",
        )

        return redirect(url_for("profesor.gestionar_documentos"))

    if not nombre_documento:
        flash(
            ("No se ha indicado " "ningún documento."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    nombre_seguro = secure_filename(nombre_documento)

    if nombre_seguro != nombre_documento:
        flash(
            ("El nombre del documento " "no es válido."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    ruta_documento = carpeta_metodologia / nombre_seguro

    if not ruta_documento.exists():
        flash(
            "El documento no existe.",
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    if not ruta_documento.is_file() or not es_pdf(nombre_seguro):
        flash(
            ("El archivo seleccionado " "no es un PDF válido."),
            "error",
        )

        return redirect(
            url_for(
                "profesor.gestionar_documentos",
                metodologia=metodologia,
            )
        )

    ruta_documento.unlink()

    flash(
        ("Documento eliminado " "correctamente."),
        "exito",
    )

    return redirect(
        url_for(
            "profesor.gestionar_documentos",
            metodologia=metodologia,
        )
    )


@profesor_bp.route(
    "/documentos/reconstruir",
    methods=["POST"],
)
@login_requerido
def reconstruir_base_vectorial():
    """
    Actualiza la base de conocimiento ejecutando
    el proceso completo de indexación.
    """

    metodologia = request.form.get("metodologia")

    carpeta_metodologia = obtener_carpeta_metodologia(metodologia)

    if carpeta_metodologia is None:
        flash(
            ("La metodología seleccionada " "no es válida."),
            "error",
        )

        return redirect(url_for("profesor.gestionar_documentos"))

    try:
        indexar_documentos()

        flash(
            ("Base de conocimiento " "actualizada correctamente."),
            "exito",
        )

    except Exception as error:
        flash(
            ("No se ha podido actualizar " "la base de conocimiento: " f"{error}"),
            "error",
        )

    return redirect(
        url_for(
            "profesor.gestionar_documentos",
            metodologia=metodologia,
        )
    )


@profesor_bp.route(
    "/alumnos/nuevo",
    methods=["GET", "POST"],
)
@login_requerido
def registrar_alumno():
    """
    Da de alta la cuenta de un alumno nuevo desde el panel de
    profesorado.
    """

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

            return render_template("registrar_alumno.html", campos=campos)

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

            return render_template("registrar_alumno.html", campos=campos)

        flash(
            f"Cuenta creada para {campos['nombre']}.",
            "exito",
        )

        return redirect(url_for("profesor.listar_alumnos"))

    return render_template("registrar_alumno.html", campos=campos)


@profesor_bp.route("/alumnos")
@login_requerido
def listar_alumnos():
    """
    Muestra el listado de cuentas de alumnado, con el número de
    conversaciones guardadas de cada una.
    """

    alumnos = repositorio.listar(rol=ROL_USUARIO)

    alumnos_con_datos = [
        {
            "usuario": alumno,
            "numero_conversaciones": conversaciones_alumnado.contar(
                alumno.dni
            ),
        }
        for alumno in alumnos
    ]

    return render_template(
        "alumnos.html",
        alumnos=alumnos_con_datos,
    )


@profesor_bp.route(
    "/alumnos/<dni>/estado",
    methods=["POST"],
)
@login_requerido
def cambiar_estado_alumno(dni):
    """
    Da de alta o de baja la cuenta de un alumno (alterna su estado).

    Una cuenta dada de baja conserva sus datos y conversaciones, pero
    no puede iniciar sesión.
    """

    alumno = repositorio.obtener_por_dni(dni)

    if alumno is None or alumno.es_profesor:
        flash(
            "No se ha encontrado ese alumno.",
            "error",
        )

        return redirect(url_for("profesor.listar_alumnos"))

    repositorio.cambiar_estado(dni, not alumno.activo)

    flash(
        (
            f"{alumno.nombre} ha sido dado de baja."
            if alumno.activo
            else f"{alumno.nombre} ha sido dado de alta."
        ),
        "exito",
    )

    return redirect(url_for("profesor.listar_alumnos"))


@profesor_bp.route(
    "/alumnos/<dni>/eliminar",
    methods=["POST"],
)
@login_requerido
def eliminar_alumno(dni):
    """
    Elimina la cuenta de un alumno junto con todas sus conversaciones
    guardadas.
    """

    alumno = repositorio.obtener_por_dni(dni)

    if alumno is None or alumno.es_profesor:
        flash(
            "No se ha encontrado ese alumno.",
            "error",
        )

        return redirect(url_for("profesor.listar_alumnos"))

    repositorio.eliminar_usuario(dni)

    flash(
        f"{alumno.nombre} y todas sus conversaciones han sido eliminados.",
        "exito",
    )

    return redirect(url_for("profesor.listar_alumnos"))


@profesor_bp.route("/alumnos/<dni>/conversaciones")
@login_requerido
def conversaciones_alumno(dni):
    """
    Muestra la lista de conversaciones guardadas de un alumno.
    """

    alumno = repositorio.obtener_por_dni(dni)

    if alumno is None or alumno.es_profesor:
        flash(
            "No se ha encontrado ese alumno.",
            "error",
        )

        return redirect(url_for("profesor.listar_alumnos"))

    conversaciones = conversaciones_alumnado.listar(dni)

    return render_template(
        "conversaciones_alumno.html",
        alumno=alumno,
        conversaciones=conversaciones,
        mostrar_nombre_metodologia=mostrar_nombre_metodologia,
    )


@profesor_bp.route("/alumnos/<dni>/conversaciones/<id_conversacion>")
@login_requerido
def ver_conversacion_alumno(dni, id_conversacion):
    """
    Muestra el contenido completo de una conversación de un alumno,
    en modo solo lectura.
    """

    alumno = repositorio.obtener_por_dni(dni)

    if alumno is None or alumno.es_profesor:
        flash(
            "No se ha encontrado ese alumno.",
            "error",
        )

        return redirect(url_for("profesor.listar_alumnos"))

    conversacion = conversaciones_alumnado.obtener(id_conversacion, dni)

    if conversacion is None:
        flash(
            "Esa conversación no existe.",
            "error",
        )

        return redirect(
            url_for(
                "profesor.conversaciones_alumno",
                dni=dni,
            )
        )

    mensajes = conversaciones_alumnado.obtener_historial(id_conversacion)

    return render_template(
        "ver_conversacion_alumno.html",
        alumno=alumno,
        conversacion=conversacion,
        mensajes=mensajes,
        mostrar_nombre_metodologia=mostrar_nombre_metodologia,
    )
"""Rutas del alumnado: inicio, gestión de conversaciones, chat y modo guiado."""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import logging

logger = logging.getLogger(__name__)

from src.rag.rag_pipeline import RAG
from src.rag.conversaciones_bd import (
    MAXIMO_CONVERSACIONES,
    ConversacionNoEncontrada,
    LimiteConversaciones,
    RepositorioConversaciones,
)
from src.knowledge.loader import cargar_arbol
from src.rag.guided_steps import obtener_pasos, obtener_actividades_lean
from web.profesor import obtener_metodologia_activa
from web.services.auth import sesion_requerida
from web.services.horario import (
    MENSAJE_FUERA_DE_HORARIO,
    dentro_de_horario_alumnado,
)
from web.services.usuarios import cerrar_sesion, es_usuario, usuario_actual
from web.services.documentos import (
    obtener_metodologias,
    mostrar_nombre_metodologia,
)

from src.core.config import RUTA_ARBOL_LEAN, RUTA_ARBOL_SIMULACION, RUTA_ARBOL_COMPLEMENTARIO

arbol_lean = cargar_arbol(RUTA_ARBOL_LEAN)
arbol_simulacion = cargar_arbol(RUTA_ARBOL_SIMULACION)
arbol_complementario = cargar_arbol(RUTA_ARBOL_COMPLEMENTARIO)


arboles = {
    "lean_startup": arbol_lean,
    "simulacion_empresarial": arbol_simulacion,
    "se_material_complementario": arbol_complementario,
}

# Almacén de conversaciones en base de datos. Hace también de historial
# para el pipeline RAG.
conversaciones_bd = RepositorioConversaciones()
conversaciones_bd.inicializar()

rag = RAG(arboles, historial=conversaciones_bd)

public_bp = Blueprint(
    "public",
    __name__,
)


def _dni_actual() -> str | None:
    """DNI del usuario autenticado, o ``None``."""

    usuario = usuario_actual()

    return usuario["dni"] if usuario else None


def _conversacion_actual(dni: str, metodologia: str | None = None):
    """
    Devuelve la conversación activa del usuario.

    Usa el identificador guardado en la sesión; si no es válido o no
    existe, recupera la más reciente y, si no hay ninguna, crea la
    primera.
    """

    id_conversacion = session.get("id_conversacion")

    if id_conversacion:
        conversacion = conversaciones_bd.obtener(id_conversacion, dni)

        if conversacion is not None:
            return conversacion

    conversacion = conversaciones_bd.obtener_o_crear_actual(dni, metodologia)
    session["id_conversacion"] = conversacion.id

    return conversacion


@public_bp.route("/")
@sesion_requerida
def inicio():
    """
    Muestra la portada principal de la aplicación.

    Solo accesible con sesión iniciada: no hay contenido público.
    """

    return render_template("inicio.html")


@public_bp.route(
    "/chat/nueva",
    methods=["POST"],
)
@sesion_requerida
def nueva_conversacion():
    """
    Crea una conversación nueva y la marca como activa.

    Si el usuario ya tiene el máximo permitido, avisa y no crea ninguna.
    """

    dni = _dni_actual()

    try:
        conversacion = conversaciones_bd.crear(
            dni,
            metodologia=obtener_metodologia_activa(),
        )

    except LimiteConversaciones as error:
        flash(str(error), "error")

        return redirect(url_for("public.chat"))

    session["id_conversacion"] = conversacion.id

    flash(
        "Se ha creado una conversación nueva.",
        "exito",
    )

    return redirect(url_for("public.chat"))


@public_bp.route(
    "/chat/cambiar",
    methods=["POST"],
)
@sesion_requerida
def cambiar_conversacion():
    """
    Cambia la conversación activa a la seleccionada en la lista.
    """

    dni = _dni_actual()

    id_conversacion = request.form.get(
        "conversacion_id",
        "",
    ).strip()

    conversacion = conversaciones_bd.obtener(id_conversacion, dni)

    if conversacion is None:
        flash(
            "Esa conversación no existe.",
            "error",
        )
    else:
        session["id_conversacion"] = conversacion.id

    return redirect(url_for("public.chat"))


@public_bp.route(
    "/chat/reiniciar",
    methods=["POST"],
)
@sesion_requerida
def reiniciar_conversacion():
    """
    Reinicia la conversación activa: borra sus mensajes y su progreso
    guiado, pero la mantiene en la lista.
    """

    dni = _dni_actual()

    conversacion = _conversacion_actual(dni)

    try:
        conversaciones_bd.reiniciar(conversacion.id, dni)

        flash(
            "La conversación se ha reiniciado.",
            "exito",
        )

    except ConversacionNoEncontrada:
        flash(
            "No se ha podido reiniciar la conversación.",
            "error",
        )

    return redirect(url_for("public.chat"))


@public_bp.route(
    "/chat/eliminar",
    methods=["POST"],
)
@sesion_requerida
def eliminar_conversacion():
    """
    Elimina una conversación de la lista del usuario.
    """

    dni = _dni_actual()

    id_conversacion = request.form.get(
        "conversacion_id",
        "",
    ).strip()

    try:
        conversaciones_bd.eliminar(id_conversacion, dni)

        flash(
            "Conversación eliminada.",
            "informacion",
        )

    except ConversacionNoEncontrada:
        flash(
            "Esa conversación no existe.",
            "error",
        )

    if session.get("id_conversacion") == id_conversacion:
        session.pop("id_conversacion", None)

    return redirect(url_for("public.chat"))


@public_bp.route(
    "/chat",
    methods=["GET", "POST"],
)
@sesion_requerida
def chat():
    """
    Muestra la interfaz del chatbot y procesa las preguntas del usuario.

    La conversación activa se guarda en la base de datos, de modo que el
    usuario puede retomarla al volver a entrar. En el lateral se muestra
    la lista de sus conversaciones guardadas.
    """

    dni = _dni_actual()

    metodologias = obtener_metodologias()

    metodologia_seleccionada = obtener_metodologia_activa()

    if metodologia_seleccionada not in metodologias:
        metodologia_seleccionada = metodologias[0] if metodologias else ""

    conversacion = _conversacion_actual(dni, metodologia_seleccionada)
    id_conversacion = conversacion.id

    if request.method == "POST":
        pregunta = request.form.get(
            "pregunta",
            "",
        ).strip()

        modo = request.form.get(
            "modo",
            "normal",
        )

        if not pregunta:
            flash(
                "Debes escribir una pregunta.",
                "error",
            )

        elif not metodologia_seleccionada:
            flash(
                ("Debes seleccionar una " "metodología válida."),
                "error",
            )

        elif es_usuario() and not dentro_de_horario_alumnado():
            cerrar_sesion()

            flash(MENSAJE_FUERA_DE_HORARIO, "error")

            return redirect(url_for("auth.login"))

        elif modo == "normal":
            try:
                rag.responder(
                    pregunta=pregunta,
                    metodologia=metodologia_seleccionada,
                    id_conversacion=id_conversacion,
                    modo_guiado=False,
                )

                conversaciones_bd.establecer_metodologia(
                    id_conversacion,
                    metodologia_seleccionada,
                )

            except Exception as error:
                flash(
                    ("No se ha podido generar " f"la respuesta: {error}"),
                    "error",
                )

        elif modo == "guiado":
            try:
                estado_guiado = conversaciones_bd.obtener_estado_guiado(
                    id_conversacion
                )

                _, estado_guiado = rag.responder(
                    pregunta=pregunta,
                    metodologia=metodologia_seleccionada,
                    id_conversacion=id_conversacion,
                    modo_guiado=True,
                    estado_guiado=estado_guiado,
                )

                conversaciones_bd.guardar_estado_guiado(
                    id_conversacion,
                    estado_guiado,
                )

                conversaciones_bd.establecer_metodologia(
                    id_conversacion,
                    metodologia_seleccionada,
                )

            except Exception as error:
                flash(
                    ("No se ha podido generar " f"el modo guiado: {error}"),
                    "error",
                )

    conversacion_mensajes = conversaciones_bd.obtener_historial(id_conversacion)

    conversaciones = conversaciones_bd.listar(dni)

    arbol = arboles.get(metodologia_seleccionada)

    pasos = (
        obtener_pasos(
            metodologia_seleccionada,
            arbol,
        )
        if arbol
        else []
    )

    estado_guia = conversaciones_bd.obtener_estado_guiado(id_conversacion)

    actividades_por_paso = {}

    if metodologia_seleccionada == "lean_startup":
        for paso in pasos:
            actividades_por_paso[paso.id] = obtener_actividades_lean(paso)

    return render_template(
        "chatbot.html",
        conversacion=conversacion_mensajes,
        conversaciones=conversaciones,
        conversacion_actual=conversacion,
        maximo_conversaciones=MAXIMO_CONVERSACIONES,
        metodologias=metodologias,
        metodologia_seleccionada=metodologia_seleccionada,
        mostrar_nombre_metodologia=mostrar_nombre_metodologia,
        pasos=pasos,
        estado_guia=estado_guia,
        actividades_por_paso=actividades_por_paso,
    )


@public_bp.route(
    "/chat/seleccionar-paso",
    methods=["POST"],
)
@sesion_requerida
def seleccionar_paso():
    """
    Selecciona un paso del modo guiado y genera una primera respuesta
    del asistente sobre él.
    """

    dni = _dni_actual()

    metodologia = request.form.get(
        "metodologia",
        "",
    ).strip()

    paso_id = request.form.get(
        "paso_id",
        "",
    ).strip()

    if not metodologia or not paso_id:
        return {
            "ok": False,
            "error": "Faltan datos para seleccionar la actividad.",
        }, 400

    if metodologia not in arboles:
        return {
            "ok": False,
            "error": "La metodología seleccionada no es válida.",
        }, 400

    if es_usuario() and not dentro_de_horario_alumnado():
        cerrar_sesion()

        return {
            "ok": False,
            "error": MENSAJE_FUERA_DE_HORARIO,
            "sesion_cerrada": True,
        }, 401

    conversacion = _conversacion_actual(dni, metodologia)
    id_conversacion = conversacion.id

    try:

        estado_guiado = conversaciones_bd.obtener_estado_guiado(id_conversacion)

        if estado_guiado is None:
            estado_guiado = {
                "activo": True,
                "completados": [],
                "paso_actual": None,
                "pasos_ids": [],
            }
        else:
            estado_guiado["activo"] = True

        respuesta, estado_guiado = rag.responder(
            pregunta="",
            metodologia=metodologia,
            id_conversacion=id_conversacion,
            modo_guiado=True,
            estado_guiado=estado_guiado,
            paso_id=paso_id,
        )

        if estado_guiado.get("paso_actual") != paso_id:
            return {
                "ok": False,
                "error": "La actividad seleccionada no es válida.",
            }, 400

        conversaciones_bd.guardar_estado_guiado(id_conversacion, estado_guiado)
        conversaciones_bd.establecer_metodologia(id_conversacion, metodologia)

        return {
            "ok": True,
            "respuesta": respuesta,
            "paso_id": paso_id,
        }

    except Exception:

        logger.exception("Error al seleccionar paso guiado.")
        return {
            "ok": False,
            "error": "No se ha podido iniciar la actividad.",
        }, 500


@public_bp.route(
    "/chat/marcar-paso",
    methods=["POST"],
)
@sesion_requerida
def marcar_paso():
    """
    Guarda el estado de completado de un paso/actividad en la
    conversación activa.
    """

    dni = _dni_actual()

    metodologia = request.form.get(
        "metodologia",
        "",
    ).strip()

    paso_id = request.form.get(
        "paso_id",
        "",
    ).strip()

    completado = (
        request.form.get(
            "completado",
            "false",
        )
        == "true"
    )

    if not metodologia or not paso_id:
        return {
            "ok": False,
            "error": "Faltan datos.",
        }, 400

    if metodologia not in arboles:
        return {
            "ok": False,
            "error": "La metodología no es válida.",
        }, 400

    conversacion = _conversacion_actual(dni, metodologia)
    id_conversacion = conversacion.id

    estado = conversaciones_bd.obtener_estado_guiado(id_conversacion)

    if estado is None:
        estado = {
            "activo": False,
            "completados": [],
            "paso_actual": None,
            "pasos_ids": [],
        }

    completados = estado.setdefault(
        "completados",
        [],
    )

    if completado:
        if paso_id not in completados:
            completados.append(paso_id)
    else:
        if paso_id in completados:
            completados.remove(paso_id)

    conversaciones_bd.guardar_estado_guiado(id_conversacion, estado)

    return {
        "ok": True,
        "completado": completado,
    }
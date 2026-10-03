"""Configuración global: rutas del proyecto, parámetros del RAG y variables de entorno."""

import os
from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent

CARPETA_DOCUMENTOS = RAIZ_PROYECTO / "documents"
CARPETA_DATA = RAIZ_PROYECTO / "data" 
CARPETA_MARKDOWN_RAW = CARPETA_DATA / "markdown_raw"
CARPETA_MARKDOWN_CLEAN = CARPETA_DATA / "markdown_clean"
CARPETA_VECTOR_STORE = CARPETA_DATA / "vector_store"
CARPETA_HISTORIAL = CARPETA_DATA / "historial_conversaciones.json"
CARPETA_KNOWLEDGE = CARPETA_DATA / "knowledge"

# Árboles de conocimiento disponibles.
RUTA_ARBOL_LEAN = CARPETA_KNOWLEDGE / "lean_startup.json"
RUTA_ARBOL_SIMULACION = CARPETA_KNOWLEDGE / "simulacion_empresarial.json"
RUTA_ARBOL_COMPLEMENTARIO = CARPETA_KNOWLEDGE / "se_material_complementario.json"

# Ruta config profesor/a de la metodologia activa
RUTA_CONFIGURACION = CARPETA_DATA / "configuracion.json"

# Base de datos de usuarios (SQLite).
RUTA_BASE_DATOS_USUARIOS = CARPETA_DATA / "usuarios.db"

METODOLOGIA_ACTIVA_POR_DEFECTO = "simulacion_empresarial"

MANUALES_CON_KNOWLEDGE = {
    "lean_startup",
    "simulacion_empresarial",
}

# Modelo embedding
MODELO_EMBEDDINGS = "BAAI/bge-m3"

# Constantes RAG
K_BUSQUEDA = 20

UMBRAL_EXCELENTE = 0.4
UMBRAL_BUENO = 0.6
UMBRAL_ACEPTABLE = 0.8

MINIMO_CHUNKS = 2
MAXIMO_CHUNKS = 3

# LLM
MODELO_LLM = "qwen/qwen3.8-27b"

# Chatbot
# Credenciales del profesor inicial.
#
# Se utilizan una única vez para sembrar (crear) la cuenta de profesor
# en la base de datos de usuarios la primera vez que arranca la aplicación.
# A partir de ese momento las cuentas viven en data/usuarios.db.
USUARIO_PROFESOR = os.getenv(
    "USUARIO_PROFESOR",
    "profesor",
)

CONTRASENA_PROFESOR = os.getenv(
    "CONTRASENA_PROFESOR",
    "profesor123",
)

FLASK_SECRET_KEY = os.getenv(
    "FLASK_SECRET_KEY",
    "clave-provisional-desarrollo",
)

# ---------------------------------------------------------------------------
# Verificación en dos pasos por correo electrónico
# ---------------------------------------------------------------------------

# Servidor SMTP usado para enviar los códigos de acceso. Si no se
# configura SMTP_HOST, el inicio de sesión queda bloqueado (no hay forma
# de entregar el código).
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")
SMTP_USUARIO = os.getenv("SMTP_USER", "")
SMTP_CONTRASENA = os.getenv("SMTP_PASSWORD", "")
SMTP_REMITENTE = os.getenv("SMTP_FROM", "") or SMTP_USUARIO
SMTP_TLS = os.getenv("SMTP_TLS", "true").strip().lower() not in {
    "false",
    "0",
    "no",
    "off",
}

# Parámetros del código de verificación.
VERIFICACION_LONGITUD_CODIGO = 6
VERIFICACION_VALIDEZ_MINUTOS = 10
VERIFICACION_MAXIMO_INTENTOS = 5
VERIFICACION_ESPERA_REENVIO_SEGUNDOS = 60

# Horario de acceso del alumnado (rol "usuario"): solo pueden iniciar
# sesión y generar respuestas del chatbot dentro de este rango. No
# afecta a las cuentas de profesorado. El centro está en Canarias, cuya
# hora coincide con la de "Europe/London" (una hora menos que la
# península todo el año, con el mismo cambio de horario de verano).
HORARIO_ALUMNADO_INICIO = 8
HORARIO_ALUMNADO_FIN = 16
ZONA_HORARIA_ALUMNADO = "Europe/London"

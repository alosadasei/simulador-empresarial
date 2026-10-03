"""
Punto de entrada de la aplicación web.

Este módulo únicamente crea y configura la aplicación Flask,
registra los Blueprints y establece la configuración global.
"""

import os
import logging
from pathlib import Path
from flask import Flask
from src.core.config import FLASK_SECRET_KEY
from web.public import public_bp
from web.auth import auth_bp
from web.profesor import profesor_bp
from web.profesorado import profesorado_bp
from web.services.usuarios import inicializar_usuarios

Path("data/logs").mkdir(exist_ok=True)

logging.basicConfig(
    filename="data/logs/rag.log",
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    encoding="utf-8",
)

werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.propagate = False
werkzeug_logger.addHandler(logging.StreamHandler())
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static",
)

# Registro de los Blueprints de la aplicación.
app.register_blueprint(public_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(profesor_bp)
app.register_blueprint(profesorado_bp)

# La clave secreta permite que Flask gestione las sesiones.
#
# Primero intenta leerla desde una variable de entorno de .env
# Si no existe, utiliza una clave provisional para desarrollo local.
app.secret_key = FLASK_SECRET_KEY

# Prepara la base de datos de usuarios: crea el esquema si no existe
# y siembra la cuenta de profesor inicial.
inicializar_usuarios()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
"""
Módulo principal de ejecución, donde se configuran las APIs.
"""

import locale

from flask import Flask

from flask_jwt_extended import JWTManager

from gatovid import api
from gatovid.config import BaseConfig
from gatovid.exts import db
from gatovid.models import TokenBlacklist


def register_extensions(app: Flask) -> None:
    """
    Inicializa las extensiones a partir de la aplicación.
    """

    db.init_app(app)


def create_app() -> Flask:
    """
    Inicializando la aplicación.
    """

    app = Flask("gatovid")
    app.config.from_object(BaseConfig)
    register_extensions(app)

    return app


# Se usa el locale en español por defecto para algunos aspectos como el formato
# de fechas.
locale.setlocale(locale.LC_ALL, "es_ES.utf8")

app = create_app()
# Configuramos el Manager de sesiones con JWT
jwt = JWTManager(app)


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload):
    """
    Configuración para la revocación de tokens. Se comprueba en la
    base de datos si un token ha sido revocado antes de aceptarlo.
    """
    jti = jwt_payload["jti"]
    return TokenBlacklist.check_blacklist(jti)


# Los "blueprint" sirven para que los endpoints de la página web sean más
# modulares.
app.register_blueprint(api.data.mod)
app.register_blueprint(api.game.mod)


@app.route("/")
def index():
    return "This site is meant to be used as an API, not a web interface"


logger = app.logger

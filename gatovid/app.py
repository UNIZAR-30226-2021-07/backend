"""
Módulo principal de ejecución, donde se configuran las APIs.
"""

import locale

from flask import Flask

from gatovid import api
from gatovid.config import BaseConfig
from gatovid.exts import db, jwt, sess, socket
from gatovid.models import TokenBlacklist


def register_extensions(app: Flask) -> None:
    """
    Inicializa las extensiones a partir de la aplicación.
    """

    db.init_app(app)
    jwt.init_app(app)
    socket.init_app(app)
    sess.init_app(app)

    # Configuración para la revocación de tokens. Se comprueba en la
    # base de datos si un token ha sido revocado antes de aceptarlo.
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return TokenBlacklist.check_blacklist(jti)

    # Configuración de mensajes de error personalizados

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            "error": "Token de sesión expirado",
        }

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return {
            "error": "Token de sesión inválido",
        }

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {
            "error": "Token de sesión revocado",
        }


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

# Los "blueprint" sirven para que los endpoints de la página web sean más
# modulares.
app.register_blueprint(api.data.mod)
# app.register_blueprint(api.game.mod)


@app.route("/")
def index():
    return "This site is meant to be used as an API, not a web interface"


logger = app.logger

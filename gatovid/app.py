"""
Módulo principal de ejecución, donde se configuran las APIs.
"""

import locale

from flask import Flask

from gatovid import api
from gatovid.config import BaseConfig
from gatovid.exts import cors, db, jwt, sess, socket
from gatovid.models import TokenBlacklist
from gatovid.util import msg_err


def register_extensions(app: Flask) -> None:
    """
    Inicializa las extensiones a partir de la aplicación.
    """

    db.init_app(app)
    jwt.init_app(app)
    socket.init_app(app)
    sess.init_app(app)
    cors.init_app(
        app,
        resources={
            "/data/*": {
                "origins": [
                    "http://localhost:5000",
                    "http://localhost:3000",
                    "https://unizar-30226-2021-07.github.io:80",
                ],
                "methods": ["OPTIONS", "GET", "POST"],
                "allow_headers": ["Authorization", "Content-Type"],
            }
        },
    )

    # Configuración para la revocación de tokens. Se comprueba en la
    # base de datos si un token ha sido revocado antes de aceptarlo.
    @jwt.token_in_blocklist_loader
    def check_if_token_is_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return TokenBlacklist.check_blacklist(jti)

    # Configuración de mensajes de error personalizados

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return msg_err("Token de sesión expirado", code=401)

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return msg_err("Token de sesión inválido", code=401)

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return msg_err("Token de sesión revocado", code=401)


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


@app.route("/")
def index():
    return "This site is meant to be used as an API, not a web interface"

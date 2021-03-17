"""
Módulo principal de ejecución, donde se configuran las APIs.
"""

import locale

from flask import Flask

from gatovid import api
from gatovid.config import BaseConfig
from gatovid.exts import db


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

# Los "blueprint" sirven para que los endpoints de la página web sean más
# modulares.
app = create_app()
app.register_blueprint(api.data.mod)
app.register_blueprint(api.game.mod)


logger = app.logger

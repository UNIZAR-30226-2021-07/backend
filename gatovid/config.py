"""
Módulo con la configuración necesaria para el setup con información para la base
de datos, Flask...
"""

import os


def get_db_uri():
    """
    La base de datos se puede configurar de diferentes formas en función de
    si es local o en la nube. `DATABASE_URL` es usado por Heroku o
    similares, mientras que con Docker se exporta
    DB_{NAME,USER,PASS,SERVICE}.
    """

    url = os.environ.get("DATABASE_URL")

    if url is not None:
        url = url.replace("postgres://", "postgresql://")
    else:
        DB_NAME = os.environ["DB_NAME"]
        DB_USER = os.environ["DB_USER"]
        DB_PASS = os.environ["DB_PASS"]
        DB_SERVICE = os.environ["DB_SERVICE"]
        DB_PORT = os.environ["DB_PORT"]
        url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_SERVICE}:{DB_PORT}/{DB_NAME}"

    return url


class BaseConfig:
    SECRET_KEY = os.environ["SECRET_KEY"]
    DEBUG = os.environ.get("DEBUG", False)
    SQLALCHEMY_DATABASE_URI = get_db_uri()
    JSON_AS_ASCII = False  # Para poder devolver JSON con UTF-8

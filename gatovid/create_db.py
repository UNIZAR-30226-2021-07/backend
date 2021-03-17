"""
Inicializa algunos datos de prueba en la BBDD.
"""

from gatovid.app import app
from gatovid.exts import db


def db_reset():
    """
    Resetea la base de datos desde cero para poder insertar filas nuevas.
    """

    with app.app_context():
        db.drop_all()
        db.create_all()


def db_init():
    """
    Añade datos a algunas tablas.
    """

    with app.app_context():
        """
        TODO
        """

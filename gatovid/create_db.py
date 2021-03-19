"""
Inicializa algunos datos de prueba en la BBDD.
"""

from sqlalchemy.exc import IntegrityError

from gatovid.app import app
from gatovid.exts import db
from gatovid.models import User


def db_reset():
    """
    Resetea la base de datos desde cero para poder insertar filas nuevas.
    """

    print("Cleaning database... ", end="")
    with app.app_context():
        db.drop_all()
        db.create_all()
    print("done")


def db_test_data():
    """
    Añade datos iniciales a algunas tablas.
    """

    with app.app_context():
        users = [
            User(id="test_user1", password="whatever1"),
            User(id="test_user2", password="whatever2"),
            User(id="test_user3", password="whatever3"),
        ]
        for user in users:
            db.session.add(user)
        db.session.commit()

        users = [
            User(id="test_user1", password="whatever1"),
            User(id="test_user2", password="whatever2"),
            User(id="test_user3", password="whatever3"),
        ]


def db_init():
    try:
        print("Generating fake data... ", end="")
        db_test_data()
        print("done")
    except IntegrityError:
        print("initialization already done, skipping.")

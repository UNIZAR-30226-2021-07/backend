"""
Modelos representativos de los datos en la base de datos y en la RAM para los
juegos.

Una parte de los datos se almacena en los clientes, como las fotos de perfil,
cartas, o tableros de juego. Su estructura y listado se almacenan en archivos
json del repositorio UNIZAR-30226-2021-07/assets, que se lee en este módulo
para tener la misma estructura de datos en el backend.

NOTE: si este fichero crece considerablemente se puede convertir en un
directorio en vez de un único fichero.
"""

import json
from enum import Enum

from gatovid.exts import bcrypt, db

PROFILE_PICS_PATH = "assets/profile_pics.json"
CARDS_PATH = "assets/cards.json"
BOARDS_PATH = "assets/boards.json"

# PROFILE_PICS = json.loads(open(PROFILE_PICS_PATH, "r").read())
# CARDS = json.loads(open(CARDS_PATH, "r").read())
# BOARDS = json.loads(open(BOARDS_PATH, "r").read())


class User(db.Model):
    """
    Información de un usuario sobre su registro y perfil. También incluye
    relaciones con sus estadísticas y compras.
    """

    # Se usa su correo electrónico como clave primaria, de forma que se pueda
    # cambiar el email.
    email = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)

    # La contraseña es un campo privado porque su acceso es más complejo. Su
    # modificación requiere encriptarla previamente.
    _password = db.Column(db.String, nullable=False)

    coins = db.Column(db.String, default=0)

    picture = db.Column(db.Integer, default=0)
    board = db.Column(db.Integer, default=0)

    # Relación "One to One" (1:1)
    stats = db.relationship("Stats", uselist=False, back_populates="user")
    # Relación "One to Many" (1:N)
    purchases = db.relationship("Purchase", back_populates="user")

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str) -> None:
        self._password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        return bcrypt.check_password_hash(self.password, plaintext)


class Stats(db.Model):
    """
    Algunos campos con datos estadísticos sobre un usuario en relación al juego.
    """

    # Relación "One to One" (1:1)
    user_id = db.Column(db.String, db.ForeignKey("user.email"), primary_key=True)
    user = db.relationship("User", back_populates="stats")

    losses = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    playtime_mins = db.Column(db.Integer, default=0)

    @property
    def games(self):
        """
        Atributo derivado con el total de partidas jugadas.
        """

        return self.wins + self.losses


class PurchasableType(Enum):
    """
    La tienda tiene varias secciones, así que una compra puede ser de varios
    tipos.
    """

    BOARD = "board"
    PROFILE_PIC = "profile_pic"


class Purchase(db.Model):
    """
    Una compra realizada por un usuario en la tienda.
    """

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    type = db.Column(db.Enum(PurchasableType), nullable=False)

    # Relación "Many to One" (1:1)
    user_id = db.Column(
        db.String, db.ForeignKey("user.email", ondelete="CASCADE"), nullable=False
    )
    user = db.relationship("User", back_populates="purchases")


class GameManager:
    """"""


class Game:
    """"""


class Player:
    """"""


class Card:
    """"""


class Message:
    """"""

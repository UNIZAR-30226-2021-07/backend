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

import datetime
import json
import os
import re
from enum import Enum
from typing import Dict

from gatovid.exts import bcrypt, db

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
PROFILE_PICS_PATH = os.path.join(CUR_DIR, "assets", "profile_pics.json")
CARDS_PATH = os.path.join(CUR_DIR, "assets", "cards.json")
BOARDS_PATH = os.path.join(CUR_DIR, "assets", "boards.json")

PROFILE_PICS = json.loads(open(PROFILE_PICS_PATH, "r").read())
CARDS = json.loads(open(CARDS_PATH, "r").read())
BOARDS = json.loads(open(BOARDS_PATH, "r").read())


class User(db.Model):
    """
    Información de un usuario sobre su registro y perfil. También incluye
    relaciones con sus estadísticas y compras.
    """

    # Para la validación de campos
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 30
    MIN_NAME_LENGTH = 4
    MAX_NAME_LENGTH = 12
    EMAIL_REGEX = re.compile(r"[^@\s]+@[^@\s.]+(\.[^@\s.]+)+")
    NAME_REGEX = re.compile(
        r"[a-zA-Z0-9_]{" + str(MIN_NAME_LENGTH) + "," + str(MAX_NAME_LENGTH) + "}"
    )

    # Se usa su correo electrónico como clave primaria, de forma que se pueda
    # cambiar el email.
    email = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)

    # La contraseña es un campo privado porque su acceso es más complejo. Su
    # modificación requiere encriptarla previamente.
    _password = db.Column(db.String, nullable=False)

    coins = db.Column(db.Integer, default=0)

    picture = db.Column(db.Integer, default=0)
    board = db.Column(db.Integer, default=0)

    # Relación "One to One" (1:1)
    stats = db.relationship(
        "Stats", uselist=False, back_populates="user", cascade="all,delete"
    )
    # Relación "One to Many" (1:N)
    purchases = db.relationship("Purchase", back_populates="user", cascade="all,delete")

    def __str__(self) -> str:
        return f"(User {self.email})"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str) -> None:
        self._password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, plaintext: str) -> bool:
        return bcrypt.check_password_hash(self.password, plaintext)


class TokenBlacklist(db.Model):
    """
    Modelo para almacenar los tokens revocados.
    """

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    token = db.Column(db.String(500), unique=True, nullable=False)
    blacklisted_on = db.Column(db.DateTime, nullable=False)

    def __init__(self, token):
        self.token = token
        self.blacklisted_on = datetime.datetime.now()

    def __repr__(self):
        return f"<id: token: {self.token}>"

    @staticmethod
    def check_blacklist(auth_token):
        res = TokenBlacklist.query.filter_by(token=str(auth_token)).first()
        return res is not None


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

    def __str__(self) -> str:
        return f"(Stats for {self.user_id})"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def games(self):
        """
        Atributo derivado con el total de partidas jugadas.
        """

        return self.wins + self.losses


class PurchasableType(str, Enum):
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

    item_id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(PurchasableType), nullable=False)

    # Relación "Many to One" (N:1)
    user_id = db.Column(
        db.String, db.ForeignKey("user.email", ondelete="CASCADE"), primary_key=True
    )
    user = db.relationship("User", back_populates="purchases")

    def __str__(self) -> str:
        return f"(Purchase for {self.user_id})"

    def __repr__(self) -> str:
        return self.__str__()

    def as_dict(self) -> Dict[str, str]:
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        del d["user_id"]
        return d


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

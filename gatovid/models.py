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
from typing import Dict, List, Optional

from sqlalchemy.orm import validates

from gatovid.exts import bcrypt, db

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
PROFILE_PICS_PATH = os.path.join(CUR_DIR, "assets", "profile_pics.json")
CARDS_PATH = os.path.join(CUR_DIR, "assets", "cards.json")
BOARDS_PATH = os.path.join(CUR_DIR, "assets", "boards.json")

PROFILE_PICS = json.loads(open(PROFILE_PICS_PATH, "r").read())
BOARDS = json.loads(open(BOARDS_PATH, "r").read())
CARDS = json.loads(open(CARDS_PATH, "r").read())
BOT_PICTURE_ID = 7

# Rango de usuarios permitido en las partidas
MIN_MATCH_USERS = 2
MAX_MATCH_USERS = 6
# Máximo de turnos antes de expulsar a un usuario por estar AFK
MAX_AFK_TURNS = 3
# Máximo turno de cartas en la mano
MIN_HAND_CARDS = 3


class InvalidModelException(Exception):
    """
    Esta excepción se usa para indicar la creación de modelos inválidos, como
    por ejemplo un usuario con contraseña vacía.
    """


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

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.email == other.email

    def __hash__(self):
        return hash(self.email)

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, password: str) -> None:
        self.validate_password("password", password)

        self._password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, plaintext: Optional[str]) -> bool:
        if plaintext is None:
            return False

        return bcrypt.check_password_hash(self.password, plaintext)

    @validates("email")
    def validate_email(self, key: str, email: Optional[str]) -> None:
        if email is None:
            raise InvalidModelException("Email vacío")

        if not User.EMAIL_REGEX.fullmatch(email):
            raise InvalidModelException("Email incorrecto")

        return email

    @validates("name")
    def validate_name(self, key: str, name: Optional[str]) -> bool:
        if name is None:
            raise InvalidModelException("Nombre vacío")

        if not User.NAME_REGEX.fullmatch(name):
            raise InvalidModelException(
                "Nombre inválido: debe tener de 4 a 12 caracteres alfanuméricos"
                " o barra baja"
            )

        return name

    @validates("password")
    def validate_password(self, key: str, password: Optional[str]) -> None:
        if password is None:
            raise InvalidModelException("Contaseña vacía")

        if len(password) < User.MIN_PASSWORD_LENGTH:
            raise InvalidModelException(
                "Contraseña demasiado corta, debe tener al menos"
                f" {User.MIN_PASSWORD_LENGTH} caracteres"
            )

        if len(password) > User.MAX_PASSWORD_LENGTH:
            raise InvalidModelException(
                "Contraseña demasiado larga, debe tener como máximo"
                f" {User.MAX_PASSWORD_LENGTH} caracteres"
            )

        return password

    @validates("picture")
    def validate_picture(self, key: str, picture: Optional[int]) -> None:
        if picture is None:
            raise InvalidModelException("Foto de perfil vacía")

        if not isinstance(picture, int):
            try:
                picture = int(picture)
            except ValueError:
                raise InvalidModelException("Foto de perfil debería ser un entero")

        purchase = Purchase.query.filter_by(
            item_id=picture, user_id=self.email, type=PurchasableType.PROFILE_PIC
        ).first()
        if purchase is None:
            raise InvalidModelException("Foto de perfil no comprada")

        return picture

    @validates("board")
    def validate_board(self, key: str, board: Optional[int]) -> None:
        if board is None:
            raise InvalidModelException("Tablero vacío")

        if not isinstance(board, int):
            try:
                board = int(board)
            except ValueError:
                raise InvalidModelException("Tablero debería ser un entero")

        purchase = Purchase.query.filter_by(
            item_id=board, user_id=self.email, type=PurchasableType.BOARD
        ).first()
        if purchase is None:
            raise InvalidModelException("Tablero no comprado")

        return board


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
    type = db.Column(db.Enum(PurchasableType), nullable=False, primary_key=True)

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

    @staticmethod
    def get_item_list(item_type: PurchasableType) -> List[Dict[str, str]]:
        """
        Dado el tipo de objeto, devuelve la lista de objetos (JSON) con la
        información como el nombre o el precio.
        """
        if item_type == PurchasableType.PROFILE_PIC:
            return PROFILE_PICS
        if item_type == PurchasableType.BOARD:
            return BOARDS

    def get_price(self) -> int:
        """
        Devuelve el precio actual de esta compra. NOTE: no se tienen en cuenta
        los precios anteriores si el precio del objeto cambia.
        """
        item_list = self.get_item_list(self.type)
        return item_list[self.item_id]["cost"]

    @validates("item_id", "type")
    def validate_item_id(self, key: str, val) -> None:
        # Necesitamos validar los dos porque item_id depende del tipo.  Aún así,
        # no podemos validar los dos de vez, se hace "iterativamente".

        # Evitamos valores vacíos de entrada
        if val is None:
            raise InvalidModelException(f"Parámetro {key} vacío")

        if key == "item_id":
            try:
                val = int(val)
            except ValueError:
                raise InvalidModelException("El ID de objeto debe ser un número")
        else:
            try:
                val = PurchasableType(val)
            except ValueError:
                raise InvalidModelException("Tipo de objeto inválido")

        # Hacemos la comprobación en las dos iteraciones
        item_id = val if key == "item_id" else self.item_id
        item_type = val if key == "type" else self.type
        if None in (item_id, item_type):
            return val  # No validamos hasta la siguiente iteración

        # Imágenes reservadas
        if item_id == BOT_PICTURE_ID and item_type == PurchasableType.PROFILE_PIC:
            raise InvalidModelException("Imagen reservada")

        item_list = self.get_item_list(item_type)

        if item_id < 0 or item_id >= len(item_list):
            raise InvalidModelException("ID de objeto inválido")

        return val

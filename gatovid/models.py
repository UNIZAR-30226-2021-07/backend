"""
Modelos representativos de los datos en la base de datos y en la RAM para los
juegos.

NOTE: si este fichero crece considerablemente se puede convertir en un
directorio en vez de un único fichero.
"""

from enum import Enum

from gatovid.exts import db


class User(db.Model):
    """
    """

    id = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=True)


class Stats(db.Model):
    """
    """


class GameManager:
    """
    """


class Game:
    """
    """


class Player:
    """
    """


class Card:
    """
    """


class CardTypes(Enum):
    """
    """


class CardColors(Enum):
    """
    """


class Message:
    """
    """


class Pictures(Enum):
    """
    """


class Boards(Enum):
    """
    """

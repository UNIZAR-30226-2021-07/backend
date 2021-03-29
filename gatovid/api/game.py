"""
Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.
"""

from flask import Blueprint

mod = Blueprint("api_game", __name__, url_prefix="/game")


@mod.route("/", methods=["GET", "POST"])
def index():
    """
    TODO
    """

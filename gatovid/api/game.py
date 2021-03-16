"""
"""

from flask import Blueprint

mod = Blueprint("api_game", __name__, url_prefix="/game")


@mod.route("/", methods=["GET", "POST"])
def index():
    """
    TODO
    """

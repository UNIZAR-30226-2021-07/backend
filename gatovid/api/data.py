"""
"""

from flask import Blueprint, request

mod = Blueprint("api_data", __name__, url_prefix="/data")


@mod.route("/", methods=["GET", "POST"])
def index():
    """
    TODO
    """


@mod.route("/test", methods=["GET", "POST"])
def test():
    """
    TODO
    """

    return {"payload": request.form}

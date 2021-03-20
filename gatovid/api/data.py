"""
"""

from flask import Blueprint, request

from gatovid.exts import db
from gatovid.models import User

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

    user = db.session.query(User.email).first()

    return {
        "POST Payload": request.form,
        "GET Payload": request.args,
        "First user in database": {
            "email": user.email,
            "name": user.name,
            "password (hashed)": user.password,
            "coins": user.coins,
            "purchases": user.purchases,
            "stats": user.stats,
        },
    }

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
    user = db.session.query(User).first()

    return {
        "POST Payload": request.form,
        "GET Payload": request.args,
        "First user in database": {
            "email": user.email,
            "name": user.name,
            "password (hashed)": user.password,
            "coins": user.coins,
            "purchases": str(user.purchases),
            "stats": str(user.stats),
        },
    }


@mod.route("/signup", methods=["GET", "POST"])
def signup():
    username = request.args.get("username")
    email = request.args.get("email")
    password = request.args.get("password")

    if None in (username, email, password):
        return {
            "error": "Parámetro vacío",
        }

    # Comprobamos si existe ese nombre de usuario en la base de datos
    user = User.query.filter_by(name=username).first()
    if user is not None:
        return {
            "error": "El usuario ya existe",
            "Usuario": {
                "name": user.name,
                "email": user.email,
            },
        }
    # Comprobamos si existe una cuenta con ese email
    user = User.query.get(email)
    if user is not None:
        return {
            "error": "El email ya está en uso",
        }

    user = User(
        email=email,
        name=username,
        password=password,
    )

    db.session.add(user)
    db.session.commit()

    return {
        "User stored": {
            "email": user.email,
            "name": user.name,
            "password (hashed)": user.password,
            "coins": user.coins,
            "purchases": str(user.purchases),
            "stats": str(user.stats),
        },
    }

"""
"""

from flask import Blueprint, request, jsonify

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required

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


@mod.route("/login", methods=["GET", "POST"])
def login():
    email = request.args.get("email")
    password = request.args.get("password")

    if None in (email, password):
        return {
            "error": "Parámetro vacío",
        }

    # Comprobamos si existe un usuario con ese email
    user = User.query.get(email)
    if not user:
        return {
            "error": "El usuario no existe",
        }

    # Comprobamos si los hashes coinciden
    if user.check_password(password) is False:
        return {
            "error": "Contraseña incorrecta",
        }

    access_token = create_access_token(identity=email)
    return jsonify(access_Token=access_token)

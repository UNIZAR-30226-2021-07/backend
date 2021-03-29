"""
"""

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from gatovid.exts import db
from gatovid.models import TokenBlacklist, User

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
    data = request.args if request.method == "GET" else request.form

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if None in (username, email, password):
        return {
            "error": "Parámetro vacío",
        }

    # Comprobamos si existe ese nombre de usuario en la base de datos
    user = User.query.filter_by(name=username).first()
    if user is not None:
        return {
            "error": "El usuario ya existe",
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
        "user": {
            "email": user.email,
            "name": user.name,
        },
    }


@mod.route("/login", methods=["GET", "POST"])
def login():
    data = request.args if request.method == "GET" else request.form

    email = data.get("email")
    password = data.get("password")

    if None in (email, password):
        return {
            "error": "Parámetro vacío",
        }

    # Comprobamos si existe un usuario con ese email
    user = User.query.get(email)
    if user is None:
        return {
            "error": "El usuario no existe",
        }

    # Comprobamos si los hashes coinciden
    if not user.check_password(password):
        return {
            "error": "Contraseña incorrecta",
        }

    access_token = create_access_token(identity=email)
    return {
        "access_token": access_token,
    }


@mod.route("/logout", methods=["GET", "POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    blacklist_token = TokenBlacklist(token=jti)
    try:
        # insert the token
        db.session.add(blacklist_token)
        db.session.commit()
        return {"message": "Sesión cerrada con éxito"}
    except Exception:
        return {"error": "No se pudo cerrar sesión"}


@mod.route("/protected_test", methods=["GET", "POST"])
@jwt_required()
def protected():
    return {
        "email": get_jwt_identity(),
    }

"""
"""
import re

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

from gatovid.exts import db
from gatovid.models import TokenBlacklist, User

mod = Blueprint("api_data", __name__, url_prefix="/data")

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")
NAME_REGEX = re.compile(r"[a-zA-Z0-9_]{4,12}")


def revoke_token() -> bool:
    """
    Revoca un token, devolviendo verdadero en caso de que haya sido una
    operación exitosa, o falso en caso contrario.
    """

    jti = get_jwt()["jti"]
    blacklist_token = TokenBlacklist(token=jti)
    try:
        # Insertar el token baneado para el futuro
        db.session.add(blacklist_token)
        db.session.commit()
        return True
    except Exception:
        return False


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

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if None in (name, email, password):
        return {"error": "Parámetro vacío"}

    # Comprobamos que el email introducido es correcto
    if not EMAIL_REGEX.fullmatch(email):
        return {"error": "Email incorrecto"}

    # Comprobamos que el nombre cumple con los requisitos
    if not NAME_REGEX.fullmatch(name):
        return {"error": "El nombre no cumple con los requisitos"}

    if len(password) < 6:
        return {"error": "Contraseña demasiado corta"}

    if len(password) > 30:
        return {"error": "Contraseña demasiado larga"}

    user = User(
        email=email,
        name=name,
        password=password,
    )

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            db.session.rollback()
            return {"error": "Email o nombre ya en uso"}
        else:
            raise

    return {
        "user": {
            "email": user.email,
            "name": user.name,
        },
    }


@mod.route("/remove_user", methods=["GET", "POST"])
@jwt_required()
def remove_account():
    """
    Al borrar una cuenta se cierra también la sesión, garantizando que solo se
    podrá borrar una vez.
    """

    email = get_jwt_identity()
    user = User.query.get(email)

    if not revoke_token():
        return {"error": "No se pudo cerrar sesión"}

    db.session.delete(user)
    db.session.commit()

    return {"message": "Usuario eliminado con éxito"}


@mod.route("/login", methods=["GET", "POST"])
def login():
    data = request.args if request.method == "GET" else request.form

    email = data.get("email")
    password = data.get("password")

    if None in (email, password):
        return {"error": "Parámetro vacío"}

    # Comprobamos si existe un usuario con ese email
    user = User.query.get(email)
    if user is None:
        return {"error": "El usuario no existe"}

    # Comprobamos si los hashes coinciden
    if not user.check_password(password):
        return {"error": "Contraseña incorrecta"}

    access_token = create_access_token(identity=email)
    return {"access_token": access_token}


@mod.route("/logout", methods=["GET", "POST"])
@jwt_required()
def logout():
    if revoke_token():
        return {"message": "Sesión cerrada con éxito"}
    else:
        return {"error": "No se pudo cerrar sesión"}


@mod.route("/protected_test", methods=["GET", "POST"])
@jwt_required()
def protected():
    return {"email": get_jwt_identity()}

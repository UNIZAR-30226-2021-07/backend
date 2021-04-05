"""
Módulo con el REST API para la gestión de los datos de la base de datos, como
los usuarios, las estadísticas...
"""

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
from gatovid.models import InvalidModelException, TokenBlacklist, User
from gatovid.util import msg_err, msg_ok, route_get_or_post

mod = Blueprint("api_data", __name__, url_prefix="/data")


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


@route_get_or_post(mod, "/test")
def test(data):
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


@route_get_or_post(mod, "/signup")
def signup(data):
    try:
        user = User(
            email=data.get("email"),
            name=data.get("name"),
            password=data.get("password"),
        )
    except InvalidModelException as e:
        return msg_err(e)

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            db.session.rollback()
            return msg_err("Email o nombre ya en uso")
        else:
            raise

    return {
        "user": {
            "email": user.email,
            "name": user.name,
        },
    }


@route_get_or_post(mod, "/remove_user")
@jwt_required()
def remove_account(data):
    """
    Al borrar una cuenta se cierra también la sesión, garantizando que solo se
    podrá borrar una vez.
    """

    email = get_jwt_identity()
    user = User.query.get(email)

    if not revoke_token():
        return msg_err("No se pudo cerrar sesión")

    db.session.delete(user)
    db.session.commit()

    return msg_ok("Usuario eliminado con éxito")


@route_get_or_post(mod, "/modify_user")
@jwt_required()
def modify_user(data):
    """
    Al endpoint de modificación del usuario se le pasan aquellos campos a
    cambiar, todos siendo opcionales.

    No hace falta pasar el email porque al estar protegido se puede obtener a
    partir del token. De esta forma se asegura que no se modifican los perfiles
    de otros usuarios.
    """

    email = get_jwt_identity()
    user = User.query.get(email)

    modified = False
    for field in ("name", "password", "board", "picture"):
        new_val = data.get(field)
        if new_val is None:
            continue

        try:
            setattr(user, field, new_val)
        except InvalidModelException as e:
            return msg_err(e)

        modified = True

    if not modified:
        return msg_err("Ningún campo válido a modificar")

    db.session.commit()

    return msg_ok("Usuario modificado con éxito")


@route_get_or_post(mod, "/login")
def login(data):
    email = data.get("email")
    password = data.get("password")

    # Comprobamos si existe un usuario con ese email
    user = User.query.get(email)
    if user is None:
        return msg_err("El usuario no existe")

    # Comprobamos si los hashes coinciden
    if not user.check_password(password):
        return msg_err("Contraseña incorrecta")

    access_token = create_access_token(identity=email)
    return {"access_token": access_token}


@route_get_or_post(mod, "/logout")
@jwt_required()
def logout(data):
    if revoke_token():
        return msg_ok("Sesión cerrada con éxito")
    else:
        return msg_err("No se pudo cerrar sesión")


@route_get_or_post(mod, "/protected_test")
@jwt_required()
def protected(data):
    return {"email": get_jwt_identity()}


@route_get_or_post(mod, "/user_data")
@jwt_required()
def user_data(data):
    email = get_jwt_identity()
    user = User.query.get(email)

    return {
        "email": email,
        "name": user.name,
        "coins": user.coins,
        "picture": user.picture,
        "board": user.board,
        "purchases": [purchase.as_dict() for purchase in user.purchases],
    }


@route_get_or_post(mod, "/user_stats")
def user_stats(data):
    name = data.get("name")
    user = User.query.filter_by(name=name).first()
    if user is None:
        return msg_err("El usuario no existe")

    stats = user.stats

    return {
        "games": stats.games,
        "losses": stats.losses,
        "wins": stats.wins,
        "playtime_mins": stats.playtime_mins,
    }

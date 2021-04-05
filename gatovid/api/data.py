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

from gatovid.util import msg_ok, msg_err
from gatovid.exts import db
from gatovid.models import InvalidModelException, TokenBlacklist, User

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
        return msg_err("No se pudo cerrar sesión")

    db.session.delete(user)
    db.session.commit()

    return msg_ok("Usuario eliminado con éxito")


@mod.route("/modify_user", methods=["GET", "POST"])
@jwt_required()
def modify_user():
    """
    Al endpoint de modificación del usuario se le pasan aquellos campos a
    cambiar, todos siendo opcionales. Se considera por tanto que una petición
    vacía es errónea.

    No hace falta pasar el email porque al estar protegido se puede obtener a
    partir del token. De esta forma se asegura que no se modifican los perfiles
    de otros usuarios.
    """
    data = request.args if request.method == "GET" else request.form

    email = get_jwt_identity()
    user = data.get("name")
    password = data.get("password")
    board = data.get("board")
    picture = data.get("picture")

    if not all([user, password, board, picture]):
        return msg_err("Campos vacíos")

    user = User.query.get(email)

    db.session.delete(user)
    db.session.commit()

    return msg_ok("Usuario modificado con éxito")


@mod.route("/login", methods=["GET", "POST"])
def login():
    data = request.args if request.method == "GET" else request.form

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


@mod.route("/logout", methods=["GET", "POST"])
@jwt_required()
def logout():
    if revoke_token():
        return msg_ok("Sesión cerrada con éxito")
    else:
        return msg_err("No se pudo cerrar sesión")


@mod.route("/protected_test", methods=["GET", "POST"])
@jwt_required()
def protected():
    return {"email": get_jwt_identity()}


@mod.route("/user_data", methods=["GET", "POST"])
@jwt_required()
def user_data():
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


@mod.route("/user_stats", methods=["GET", "POST"])
def user_stats():
    data = request.args if request.method == "GET" else request.form

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

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
from gatovid.models import (
    InvalidModelException,
    PurchasableType,
    Purchase,
    Stats,
    TokenBlacklist,
    User,
)
from gatovid.util import get_logger, msg_err, msg_ok, route_get_or_post

mod = Blueprint("api_data", __name__, url_prefix="/data")
logger = get_logger("api.data.__init__")


def _revoke_token() -> bool:
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
    """
    Endpoint de prueba que realiza una petición a la base de datos y devuelve
    los argumentos que se le han pasado.

    .. warning:: Esto será eliminado en el futuro.
    """

    user = db.session.query(User).first()
    db.session.commit()

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


@route_get_or_post(mod, "/protected_test")
@jwt_required()
def protected(data):
    """
    Endpoint temporal para probar la autenticación con JWTs.

    .. warning:: Esto será eliminado en el futuro.
    """

    return {"email": get_jwt_identity()}


@route_get_or_post(mod, "/signup")
def signup(data):
    """
    Endpoint de registro de un usuario. Los parámetros deben cumplir las reglas
    de validación establecidas en :meth:`gatovid.models.User`.

    :param email: Dirección de correo electrónico
    :type email: ``str``
    :param name: Nombre del usuario
    :type name: ``str``
    :param password: Contraseña del usuario
    :type password: ``str``

    :return: Un objeto JSON con el nombre y correo del usuario registrado, como
        forma de verificación de la operación, o un error de validación.
    """

    try:
        user = User(
            email=data.get("email"),
            name=data.get("name"),
            password=data.get("password"),
        )
        initial_stats = Stats(user_id=user.email)
        initial_purchases = [
            Purchase(user_id=user.email, item_id=0, type=PurchasableType.BOARD),
            Purchase(user_id=user.email, item_id=0, type=PurchasableType.PROFILE_PIC),
        ]
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

    # Cuando el usuario ya existe se le puede añadir la tabla de estadísticas y
    # demás relaciones.
    db.session.add(initial_stats)
    for purchase in initial_purchases:
        db.session.add(purchase)
    db.session.commit()

    logger.info(f"User {user.name} has signed up")

    return {
        "user": {
            "email": user.email,
            "name": user.name,
        },
    }


@route_get_or_post(mod, "/remove_user")
@jwt_required()
def remove_user(data):
    """
    Endpoint autenticado de borrado de cuenta.

    Al borrar una cuenta se cierra también la sesión, garantizando que solo se
    podrá borrar una vez.

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario.
    """

    email = get_jwt_identity()
    user = db.session.query(User).get(email)

    if not _revoke_token():
        return msg_err("No se pudo cerrar sesión")

    db.session.delete(user)
    db.session.commit()

    logger.info(f"User {user.name} has been removed")

    return msg_ok("Usuario eliminado con éxito")


@route_get_or_post(mod, "/modify_user")
@jwt_required()
def modify_user(data):
    """
    Endpoint autenticado de modificación del usuario, al cual se le pasan
    aquellos campos a cambiar, todos siendo opcionales. Los parámetros deben
    cumplir las reglas de validación establecidas en
    :meth:`gatovid.models.User`.

    No hace falta pasar el email porque al estar protegido se puede obtener a
    partir del token. De esta forma se asegura que no se modifican los perfiles
    de otros usuarios.

    :param name: Nombre nuevo del usuario
    :type name: ``Optional[str]``
    :param password: Contraseña nueva del usuario
    :type password: ``Optional[str]``
    :param board: El identificador del nuevo tapete del usuario
    :type board: ``Optional[int]``
    :param picture: El identificador de la nueva foto del usuario
    :type picture: ``Optional[int]``

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario. Se considera un error el no
        indicar ninguno de los parámetros opcionales anteriores.
    """

    email = get_jwt_identity()
    user = db.session.query(User).get(email)

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
        return msg_err("Ningún campo a modificar")

    try:
        db.session.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            db.session.rollback()
            return msg_err("Nombre ya en uso")

    logger.info(f"User {user.name} has modified their profile")
    return msg_ok("Usuario modificado con éxito")


@route_get_or_post(mod, "/login")
def login(data):
    """
    Endpoint para iniciar la sesión con las credenciales de un usuario ya
    registrado. Debe cumplir los requisitos de :ref:`error_validacion`.

    :param email: Dirección de correo electrónico
    :type email: ``str``
    :param password: Contraseña
    :type password: ``str``

    :return: Un token de acceso en el campo ``access_token``, o un error de
        validación.
    """

    email = data.get("email")
    password = data.get("password")

    # Comprobamos si existe un usuario con ese email
    user = db.session.query(User).get(email)
    db.session.commit()
    if user is None:
        return msg_err("El usuario no existe")

    # Comprobamos si los hashes coinciden
    if not user.check_password(password):
        return msg_err("Contraseña incorrecta")

    access_token = create_access_token(identity=email)
    logger.info(f"User {user.name} has logged in")
    return {"access_token": access_token}


@route_get_or_post(mod, "/logout")
@jwt_required()
def logout(data):
    """
    Endpoint autenticado para cerrar la sesión.

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario.
    """

    logger.info(f"User {get_jwt_identity()} is logging out")
    if _revoke_token():
        return msg_ok("Sesión cerrada con éxito")
    else:
        return msg_err("No se pudo cerrar sesión", code=500)


@route_get_or_post(mod, "/user_data")
@jwt_required()
def user_data(data):
    """
    Endpoint autenticado para acceder a los datos personales de un usuario.

    :return: Un objeto JSON con los campos:

    * ``email: str``
    * ``name: str``
    * ``coins: int``
    * ``picture: int`` (identificador)
    * ``board: int`` (identificador)
    * ``purchases: List[{"item_id": str, "type": ("board" | "profile_pic")}]``
    """

    email = get_jwt_identity()
    user = db.session.query(User).get(email)
    db.session.commit()

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
    """
    Endpoint para acceder a las estadísticas de un usuario, dado su nombre.

    :param name: Nombre del usuario
    :type name: ``str``

    :return: Un objeto JSON con los campos ``games``, ``losses``, ``wins`` y
        ``playtime_mins``, todos enteros.
    """

    name = data.get("name")
    user = db.session.query(User).filter_by(name=name).first()
    db.session.commit()
    if user is None:
        return msg_err("El usuario no existe")

    stats = user.stats

    logger.info(f"User {name} has been accessed to their stats")
    return {
        "games": stats.games,
        "losses": stats.losses,
        "wins": stats.wins,
        "playtime_mins": stats.playtime_mins,
    }


@route_get_or_post(mod, "/shop_buy")
@jwt_required()
def shop_buy(data):
    """
    Endpoint para comprar un objeto en la tienda.

    :param id: Identificador del objeto
    :type id: ``int``
    :param type: Tipo del objeto ("board" | "profile_pic")
    :type type: ``str``

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario.
    """

    email = get_jwt_identity()
    user = db.session.query(User).get(email)

    item_id = data.get("id")
    item_type = data.get("type")

    try:
        purchase = Purchase(user_id=email, item_id=item_id, type=item_type)
    except InvalidModelException as e:
        return msg_err(e)

    price = purchase.get_price()
    if user.coins < price:
        return msg_err("No tienes suficientes patitas")

    user.coins -= price
    try:
        db.session.add(purchase)
        db.session.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            db.session.rollback()
            return msg_err("Objeto ya comprado")
        else:
            raise

    logger.info(f"User {user.name} has bought a shop item")
    return msg_ok("Objeto comprado con éxito")

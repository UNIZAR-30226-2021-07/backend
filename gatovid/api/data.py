"""
API de Datos
============

Errores y Validación
####################

Existen varios tipos de errores que pueden devolverse desde la API de datos:

1. :ref:`error_validacion` (400): la petición al servidor es inválida porque se
   le ha pasado uno o más parámetros inválidos, o su estructura no es la
   esperada.
2. :ref:`error_autenticacion` (401): un token ha sido usado de forma inválida:

3. Error interno (500-599): una excepción inesperada y que ha causado una
   terminación del servidor. No tendrá ningún mensaje que lo acompañe.

.. _error_validacion:

Errores de Validación
*********************

Todos los endpoints validan los parámetros que se le pasan. Generalmente, se
comprueba lo siguiente:

* Que su valor no sea nulo.
* Que el tipo sea el adecuado. Esto será importante solo cuando la variable sea
  algo distinto a una cadena.
* Comprobaciones lógicas

Casos específicos
-----------------

.. currentmodule:: gatovid.models

El correo electrónico tiene que cumplir la siguiente expresión regular:

.. autoattribute:: gatovid.models.User.EMAIL_REGEX

Y el nombre la siguiente:

.. autoattribute:: gatovid.models.User.NAME_REGEX

La longitud de la contraseña tendrá que estar entre los dos valores siguientes:

.. autoattribute:: gatovid.models.User.MIN_PASSWORD_LENGTH
.. autoattribute:: gatovid.models.User.MAX_PASSWORD_LENGTH

También puede deberse a otros errores lógicos, como que se intente asignar a un
usuario una foto de perfil o tapete que no haya comprado.

Cliente Básico
**************

Dadas las restricciones anteriores, se describe a continuación cómo sería un
cliente básico para acceder a la API de datos:

1. Hacer petición
2. Comprobar si hay un error
    1. Si no hay error se puede usar el valor devuelto
    2. Si hay error:
        1. Si es 401, será necesario refrescar el token y volver al punto 1.
        2. Si el código es 400:
            1. Si es fallo del usuario se le muestra el mensaje de error del campo
               `error`.
            2. Si es fallo del programador, tendrá que hacerse debug en el cliente y
               solucionarlo, ya que no es esperado que suceda. Se puede usar el
               campo `error` para ello.

        3. Si es 500, tendrá que hacerse debug en el backend y solucionarlo, que
           será donde se encuentre más información. En este caso no se puede usar el
           campo `error`, por tanto.
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
    """
    Endpoint de prueba que realiza una petición a la base de datos y devuelve
    los argumentos que se le han pasado.

    .. warning:: Esto será eliminado en el futuro.
    """

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
    :type email: `str`
    :param name: Nombre del usuario
    :type name: `str`
    :param password: Contraseña del usuario
    :type password: `str`

    :return: Un objeto JSON con el nombre y correo del usuario registrado, como
        forma de verificación de la operación, o un error de validación.
    """

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
def remove_user(data):
    """
    Endpoint autenticado de borrado de cuenta.

    Al borrar una cuenta se cierra también la sesión, garantizando que solo se
    podrá borrar una vez.

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario.
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
    Endpoint autenticado de modificación del usuario, al cual se le pasan
    aquellos campos a cambiar, todos siendo opcionales. Los parámetros deben
    cumplir las reglas de validación establecidas en
    :meth:`gatovid.models.User`.

    No hace falta pasar el email porque al estar protegido se puede obtener a
    partir del token. De esta forma se asegura que no se modifican los perfiles
    de otros usuarios.

    :param name: Nombre nuevo del usuario
    :type name: `Optional[str]`
    :param password: Contraseña nueva del usuario
    :type password: `Optional[str]`
    :param board: El identificador del nuevo tapete del usuario
    :type board: `Optional[int]`
    :param picture: El identificador de la nueva foto del usuario
    :type picture: `Optional[int]`

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario. Se considera un error el no
        indicar ninguno de los parámetros opcionales anteriores.
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
    """
    Endpoint para iniciar la sesión con las credenciales de un usuario ya
    registrado. Debe cumplir los requisitos de :ref:`error_validacion`.

    :param email: Dirección de correo electrónico
    :type email: `str`
    :param password: Contraseña
    :type password: `str`

    :return: Un token de acceso en el campo `access_token`, o un error de
        validación.
    """

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
    """
    Endpoint autenticado para cerrar la sesión.

    :return: Un mensaje descriptivo de la operación realizada correctamente, o
        un mensaje de error interno en caso contrario.
    """

    if revoke_token():
        return msg_ok("Sesión cerrada con éxito")
    else:
        return msg_err("No se pudo cerrar sesión", code=500)


@route_get_or_post(mod, "/user_data")
@jwt_required()
def user_data(data):
    """
    Endpoint autenticado para acceder a los datos personales de un usuario.

    :return: Un objeto JSON con los campos:

    * `email: str`
    * `name: str`
    * `coins: int`
    * `picture: int` (identificador)
    * `board: int` (identificador)
    * `purchases: List[{"item_id": str, "type": ("board" | "profile_pic")}]`
    """

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
    """
    Endpoint para acceder a las estadísticas de un usuario, dado su nombre.

    :param name: Nombre del usuario
    :type name: `str`

    :return: Un objeto JSON con los campos `games`, `losses`, `wins` y
        `playtime_mins`, todos enteros.
    """

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

import functools

from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.api.game.match import (
    MAX_MATCH_USERS,
    MM,
    GameLogicException,
    PrivateMatch,
    PublicMatch,
)
from gatovid.exts import socket
from gatovid.game.actions import Discard, Pass, PlayCard
from gatovid.models import User
from gatovid.util import get_logger

logger = get_logger("api.game.__init__")


MAX_CHAT_MSG_LEN = 240


def _requires_game(started=False):
    """
    Decorador para comprobar si el usuario está en una partida. Si started es
    True, se comprueba también que la partida ha empezado.
    """

    def deco(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            game = session.get("game")
            if not game:
                return {"error": "No estás en una partida"}

            match = MM.get_match(game)
            if not match:
                # FIXME: creo que esto no podría llegar a pasar, porque para que
                # la partida no exista, el usuario ha tenido que salir. Sino, se
                # retiene la partida.
                return {"error": "La partida no existe"}

            if started and not match.is_started():
                return {"error": "La partida no ha comenzado"}

            return f(*args, **kwargs)

        return wrapper

    return deco


@socket.on("connect")
def connect():
    """
    Devuelve falso si se prohibe la conexión del usuario porque no ha iniciado
    sesión.
    """

    try:
        # Comprobamos si el token es válido. Si el token es inválido, lanzará
        # una excepción.
        verify_jwt_in_request()
    except Exception:
        return False

    # Inicializamos la sesión del usuario
    email = get_jwt_identity()

    session["user"] = User.query.get(email)
    session["user"].sid = request.sid

    logger.info(f"New session with user {session['user'].name}")
    return True


def remove_from_public():
    code = session.get("game")
    if code is None:
        return

    match = MM.get_match(code)
    if match is None:
        return

    if not isinstance(match, PublicMatch):
        return

    leave()


@socket.on("disconnect")
def disconnect():
    # La sesión del usuario se limpia al reconectarse, aunque existen casos que
    # necesitan limpieza.
    logger.info(f"Ending session with user {session['user'].name}")

    # Puede estar buscando una partida pública
    if session["user"] in MM.users_waiting:
        MM.stop_waiting(session["user"])

    # NOTE: si el usuario está en una partida privada se cuenta como una
    # desconexión temporal y se podrá volver a unir.
    remove_from_public()


@socket.on("search_game")
def search_game():
    """
    Unión a una partida pública organizada por el servidor.

    :return: El cliente no recibirá respuesta hasta que el servidor haya
        encontrado oponentes contra los que jugar.

        Una vez encontrada una partida, hará un broadcast de
        :ref:`msg_found_game`.

        Si ya está buscando partida, se devolverá un :ref:`error <errores>`.
    """

    if session.get("game") is not None:
        return {"error": "El usuario ya está en una partida privada"}

    try:
        MM.wait_for_game(session["user"])
    except GameLogicException as e:
        return {"error": str(e)}


@socket.on("stop_searching")
def stop_searching():
    """
    Parar de buscar una partida pública organizada por el servidor.

    :return: Devuelve un mensaje de tipo :ref:`msg_stop_searching` si se ha
        podido cancelar la búsqueda.

        Si se produce cualquier error (por ejemplo, que el usuario no esté
        buscando partida) se devolverá un :ref:`error <errores>`.
    """

    if session["user"] in MM.users_waiting:
        MM.stop_waiting(session["user"])
        emit("stop_searching")
    else:
        return {"error": "No estás buscando partida"}


@socket.on("create_game")
def create_game():
    """
    Creación y unión automática a una partida privada.

    :return: Un mensaje de tipo :ref:`msg_create_game`.

        Si está buscando una partida pública, se devolverá un :ref:`error
        <errores>`.
    """

    if session.get("game") is not None:
        return {"error": "El usuario ya está en una partida privada"}

    try:
        game_code = MM.create_private_game(owner=session["user"])
    except GameLogicException as e:
        return {"error": str(e)}
    join(game_code)
    emit("create_game", {"code": game_code})


@socket.on("start_game")
@_requires_game()
def start_game():
    """
    Puesta en marcha de una partida privada.

    :return: Un broadcast de :ref:`msg_start_game`.

        Requiere que el usuario esté en una partida y que sea el líder o se
        devolverá un :ref:`error <errores>`. También deben haber al menos 2
        jugadores en total esperando la partida para empezarla.
    """

    game = session["game"]
    match = MM.get_match(game)

    # Comprobamos si el que empieza la partida es el creador
    try:
        if match.owner != session["user"]:
            return {"error": "Debes ser el lider para empezar partida"}
    except (AttributeError, TypeError):
        # Si la partida devuelta por el MM es una pública, no tiene sentido
        # empezar la partida (ya se encarga el manager)
        return {"error": "La partida no es privada"}

    if len(match.users) < 2:
        return {"error": "Se necesitan al menos dos jugadores"}

    match.start()


@socket.on("join")
def join(game_code):
    """
    Unión a una partida proporcionando un código de partida.

    Si se proporciona un código con minúsculas se intentará con el equivalente
    en mayúsculas.

    :param game_code: Código de partida
    :type game_code: ``str``

    :return: Si la partida es privada, un broadcast de :ref:`msg_users_waiting`.

        En cualquier caso, un broadcast de :ref:`msg_chat` indicando que el
        jugador se ha unido a la partida.

        Un jugador no se puede unir a una partida si ya está en otra o si ya
        está llena. En caso contrario se devolverá un :ref:`error <errores>`.
    """

    if session.get("game"):
        return {"error": "Ya estás en una partida"}

    if not isinstance(game_code, str):
        return {"error": "Tipo incorrecto para el código de partida"}

    # No importa si es minúsculas
    game_code = game_code.upper()

    # Restricciones para unirse a la sala
    match = MM.get_match(game_code)
    if match is None or len(match.users) > MAX_MATCH_USERS:
        return {"error": "La partida no existe o está llena"}

    # Guardamos la partida actual en la sesión
    session["game"] = game_code
    # Actualizamos los datos del usuario. NOTE: estos ya serán los
    # definitivos, no los puede modificar a mitad de partida.
    session["user"] = User.query.get(session["user"].email)
    session["user"].sid = request.sid

    # Unimos al usuario a la sesión de socketio
    join_room(game_code)

    # Comprobar si es una reconexión y en ese caso indicarle que empiece
    # directamente.
    can_rejoin, initial_update = match.check_rejoin(session["user"])
    if can_rejoin:
        logger.info(f"User {session['user']} reconnecting to game")
        # Actualizamos el SID del usuario y el nombre si lo ha cambiado
        try:
            match.update_user()
        except GameLogicException as e:
            # NOTE: No debería darse este error por la condición de
            # can_rejoin, pero por curarnos en salud.
            return {"error": str(e)}
        emit("start_game", room=session["user"].sid)
        emit("game_update", initial_update, room=session["user"].sid)
        return

    # Guardamos al jugador en la partida
    try:
        match.add_user(session["user"])
    except GameLogicException as e:
        return {"error": str(e)}

    if isinstance(match, PrivateMatch):
        # Si es una partida privada, informamos a todos los de la sala del nuevo
        # número de jugadores. El lider decidirá cuando iniciarla.
        emit("users_waiting", len(match.users), room=game_code)
    else:
        # Si es una partida pública, iniciamos la partida si ya están todos.
        # Si hay algún jugador que no se une a la partida, la partida acabará
        # empezando (si hay suficientes jugadores) debido al start_timer en
        # PublicMatch.
        if len(match.users) == match.num_users:
            match.start()

    emit(
        "chat",
        {
            "msg": session["user"].name + " se ha unido a la partida",
            "owner": "[GATOVID]",
        },
        room=game_code,
    )

    logger.info(f"User {session['user'].name} has joined the game {game_code}")


# NOTE: aunque parezca contra-intuitivo, salir de una partida no hace falta
# estar dentro de una.
#
# Esto es porque también se puede usar este endpoint de forma de limpieza. Por
# ejemplo cuando una partida se cancela a sí misma porque se queda sin
# jugadores, se habrán eliminado a los usuarios de esa partida pero igualmente
# el cliente tendrá que llamar para limpiar la sesión y hacer `leave_room` para
# poderse unir a otra partida.
@socket.on("leave")
def leave():
    """
    Salir de la partida actual.

    :return:
        * Si la partida no se borra porque quedan jugadores:

          - Un mensaje de tipo :ref:`msg_users_waiting`.
          - Un broadcast de :ref:`msg_chat` indicando que el jugador ha
            abandonado la partida.
          - Si se ha delegado el cargo de líder, el nuevo líder recibirá un
            mensaje de tipo :ref:`msg_game_owner`.
        * Si la partida se borra porque no quedan jugadores:

          - Si ya había terminado, un :ref:`error <errores>`.
          - Si no había terminado y se ha cancelado, un mensaje de tipo
            :ref:`msg_game_cancelled`.

        Requiere que el usuario esté en una partida o se devolverá un
        :ref:`error <errores>`.
    """

    # No hay partida de la que salir ni limpieza que hacer
    if session.get("game") is None:
        return {"error": "No hay ninguna partida de la que salir"}

    game_code = session["game"]
    leave_room(game_code)
    emit(
        "chat",
        {
            "msg": session["user"].name + " ha abandonado la partida",
            "owner": "[GATOVID]",
        },
        room=game_code,
    )
    del session["game"]

    match = MM.get_match(game_code)
    if match is None:
        return  # Limpieza de partidas ya canceladas, no hace falta seguir
    match.remove_user(session["user"])
    logger.info(f"User {session['user'].name} has left the game {game_code}")
    if len(match.users) == 0:
        match.end()
        MM.remove_match(game_code)
        return  # La partida ha acabado, no seguir

    emit("users_waiting", len(match.users), room=game_code)

    # Comprobar si hay que delegar el cargo de lider
    if isinstance(match, PrivateMatch):
        if match.owner == session["user"]:
            # Si él es el lider, delegamos el cargo de lider a otro jugador
            match.owner = match.users[0]

            emit(
                "chat",
                {
                    "msg": match.owner.name + " es el nuevo líder",
                    "owner": "[GATOVID]",
                },
                room=game_code,
            )

            # Mensaje solo al nuevo dueño de la sala
            emit("game_owner", room=match.owner.sid)


@socket.on("pause_game")
@_requires_game(started=True)
def pause_game(paused):
    """
    Pausa o reanuda una partida privada.

    :param paused: Pausar la partida
    :type paused: ``bool``

    Requiere que el usuario esté en una partida privada y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si no se cumplen los requisitos comentados anteriormente, se devolverá
        un :ref:`error <errores>`.
    """

    if paused is None or type(paused) != bool:
        return {"error": "Parámetro incorrecto"}

    # TODO: Si la pausa pasa del tiempo límite comentado anteriormente, la
    # partida se reanuda automáticamente, y el jugador que no esté se le
    # irán pasando los turnos.

    match = MM.get_match(session["game"])
    name = session["user"].name

    if not isinstance(match, PrivateMatch):
        return {"error": "No estás en una partida privada"}

    try:
        match.set_paused(paused, paused_by=name)
    except GameLogicException as e:
        return {"error": str(e)}


@socket.on("chat")
@_requires_game(started=True)
def chat(msg):
    """
    Enviar un mensaje al chat de la partida.

    :param msg: Mensaje a enviar
    :type msg: ``str``

    :return: Broadcast de un mensaje :ref:`msg_chat`.

        Se borrarán en el mensaje todos los espacios anteriores y posteriores.

        Si el usuario no está en una partida empezada se devolverá un
        :ref:`error <errores>`.

        Se devolverá un :ref:`error <errores>` también en caso de que el mensaje
        supere la longitud máxima de caracteres establecida, o si es vacío tras
        quitar los espacios innecesarios:

        .. autoattribute:: gatovid.api.game.MAX_CHAT_MSG_LEN
    """

    if not isinstance(msg, str):
        return {"error": "Tipo incorrecto para el mensaje"}

    msg = msg.strip()
    if len(msg) == 0:
        return {"error": "Mensaje vacío"}

    if len(msg) > MAX_CHAT_MSG_LEN:
        return {"error": "Mensaje demasiado largo"}

    emit(
        "chat",
        {
            "msg": msg,
            "owner": session["user"].name,
        },
        room=session["game"],
    )

    logger.info(
        f"New message at game {session['game']} from user {session['user'].name}"
    )


@socket.on("play_discard")
@_requires_game(started=True)
def play_discard(card):
    """
    Descarta la carta indicada de la mano del usuario. Esta acción se puede
    repetir varias veces hasta que se pase el turno de forma automática o con
    ``play_pass``.

    La carta a descartar se puede indicar con el índice de ésta en su mano.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :param card: La carta del usuario a descartar
    :type card: int

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`. También se devolverá uno en caso de que el jugador no tenga
        cartas restantes para descartar o si la carta indicada no existe en la
        mano del jugador.
    """

    if not isinstance(card, int):
        return {"error": "Tipo incorrecto para la carta"}

    match = MM.get_match(session["game"])
    name = session["user"].name

    try:
        match.run_action(name, Discard(card))
    except GameLogicException as e:
        return {"error": str(e)}


@socket.on("play_pass")
@_requires_game(started=True)
def play_pass():
    """
    .. warning:: Este endpoint está en construcción aún.

    Pasa el turno del usuario.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`.
    """

    match = MM.get_match(session["game"])
    name = session["user"].name

    try:
        match.run_action(name, Pass())
    except GameLogicException as e:
        return {"error": str(e)}


@socket.on("play_card")
@_requires_game(started=True)
def play_card(data):
    """
    .. warning:: Este endpoint está en construcción aún.

    Juega una carta de su mano.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :param data: Diccionario con datos sobre la carta a jugar. Todas las cartas
        deberán tener un campo ``slot`` (``int``) con el slot de la carta jugada
        en la mano del jugador. Adicionalmente, algunas cartas en concreto
        tendrán parámetros específicos:

        * Órgano, Virus y Medicina:
            * ``target`` (``str``): nombre del jugador destino
            * ``organ_pile`` (``int``): número de pila del jugador destino
        * Tratamientos:
            * Transplante:
                * ``targets`` (``List[str]``): lista con los nombres de los dos
                  jugadores.
            * Ladrón de Órganos:
                * ``target`` (``str``): nombre del jugador destino
            * Error médico:
                * ``target`` (``str``): nombre del jugador destino

    :type data: Dict

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`.
    """

    match = MM.get_match(session["game"])
    name = session["user"].name

    try:
        match.run_action(name, PlayCard(data))
    except GameLogicException as e:
        return {"error": str(e)}

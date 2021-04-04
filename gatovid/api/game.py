"""
Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.
"""

from functools import wraps

from flask import session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.exts import socket
from gatovid.match import MAX_MATCH_PLAYERS, MM
from gatovid.models import User


def requires_game(f):
    """
    Decorador para comprobar si el usuario está en una partida.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        game = session.get("game")
        if not game:
            return {"error": "No estás en una partida"}

        if not MM.get_match(game):
            return {"error": "La partida no existe"}

        return f(*args, **kwargs)

    return wrapper


def requires_game_started(f):
    """
    Decorador para comprobar si el usuario está en una partida.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        game = session.get("game")
        if not game:
            return {"error": "No estás en una partida"}

        match = MM.get_match(game)
        if not match:
            return {"error": "La partida no existe"}

        if not match.started:
            return {"error": "La partida no ha comenzado"}

        return f(*args, **kwargs)

    return wrapper


@socket.on("connect")
def connect():
    """
    Return False si queremos prohibir la conexión del usuario.
    """
    try:
        # Comprobamos si el token es válido. Si el token es inválido,
        # lanzará una excepción.
        verify_jwt_in_request()
    except Exception:
        return False

    # Inicializamos la sesión del usuario
    email = get_jwt_identity()

    session["user"] = User.query.get(email)

    return True


@socket.on("disconnect")
def disconnect():
    # La sesión del usuario se limpia al reconectarse, pero puede
    # estar metido en una partida.
    if session.get("game"):
        leave()


@socket.on("create_game")
def create_game():
    game_code = MM.create_private_game(owner=session["user"])
    join({"game": game_code})
    emit("create_game", {"code": game_code})


@socket.on("start_game")
@requires_game
def start_game():
    game = session["game"]
    match = MM.get_match(game)

    # Comprobamos si el que empieza la partida es el creador
    try:
        if match.owner.email != session["user"].email:
            return {"error": "Debes ser el lider para empezar partida"}
    except (AttributeError, TypeError):
        # Si la partida devuelta por el MM es una pública, no tiene
        # sentido empezar la partida (ya se encarga el manager)
        return {"error": "La partida no es privada"}

    match.started = True
    emit("start_game", room=game)


@socket.on("join")
def join(data):
    if session.get("game"):
        return {"error": "Ya estás en una partida"}

    game_code = data["game"]

    # Restricciones para unirse a la sala
    match = MM.get_match(game_code)
    if match is None or len(match.players) > MAX_MATCH_PLAYERS:
        return {"error": "La partida no existe o está llena"}

    # Guardamos la partida actual en la sesión
    session["game"] = game_code
    # y en la partida
    match.players.add(session["user"])

    # Lo unimos a la sesión de socketio
    join_room(game_code)

    emit(
        "chat",
        {
            "msg": session["user"].name + " has entered the room",
            "owner": "[GATOVID]",
        },
        room=game_code,
    )

    emit("players_waiting", len(match.players), room=game_code)


@socket.on("leave")
@requires_game
def leave():
    game_code = session["game"]
    leave_room(game_code)
    emit(
        "chat",
        {
            "msg": session["user"].name + " has left the room",
            "owner": "[GATOVID]",
        },
        room=game_code,
    )
    del session["game"]

    match = MM.get_match(game_code)
    match.players.remove(session["user"])

    if len(match.players) == 0:
        MM.remove_match(game_code)
    else:
        emit("players_waiting", len(match.players), room=game_code)


@socket.on("chat")
@requires_game_started
def chat(msg):
    emit(
        "chat",
        {
            "msg": msg,
            "owner": session["user"].name,
        },
        room=session["game"],
    )

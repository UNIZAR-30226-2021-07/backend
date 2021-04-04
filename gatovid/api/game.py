"""
Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.
"""

from functools import wraps

from flask import session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.exts import socket
from gatovid.models import User
from gatovid.match import MM, MAX_MATCH_PLAYERS

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
        emit("invalid token")
        return False

    # Inicializamos la sesión del usuario
    email = get_jwt_identity()

    session["user"] = User.query.get(email)

    return True


@socket.on("create_game")
def create_game():
    game_code = MM.create_private_game(owner=session["user"])
    emit("create_game", {"code": game_code})
    session["game"] = game_code
    join_room(game_code)


@socket.on("join")
def join(data):
    game_code = data['game']

    # Restricciones para unirse a la sala
    match = MM.get_match(game_code)
    if match is None or len(match.players) > MAX_MATCH_PLAYERS:
        emit(
            "join",
            {
                "error": "La partida no existe o está llena",
            },
        )
        return
    
    # Guardamos la partida actual en la sesión
    session["game"] = game_code

    join_room(game_code)

    emit(
        "chat",
        {
            "msg": session["user"].name + " has entered the room",
            "owner": None,
        },
        room=game_code,
    )


@socket.on("leave")
@requires_game
def leave():
    leave_room(session["game"])
    emit(
        "chat",
        {
            "msg": session["user"].name + " has left the room",
            "owner": None,
        },
        room=session["game"],
    )
    del session["game"]


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

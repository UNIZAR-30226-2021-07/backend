"""
Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.
"""

from flask import session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.exts import socket
from gatovid.models import User
from gatovid.match import MM, MAX_MATCH_PLAYERS


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
def leave():
    # Restricciones para salir de la sala (por si no está)
    if not session.get("game"):
        emit("chat", {"error": "No estás en una partida"})
        return

    leave_room(session["game"])
    emit(
        "chat",
        {
            "msg": session["user"].name + " has left the room",
            "owner": None,
        },
        room=session["game"],
    )

@socket.on("chat")
def chat(msg):
    if not session.get("game"):
        emit("chat", {"error": "No estás en una partida"})
        return

    emit(
        "chat",
        {
            "msg": msg,
            "owner": session["user"].name,
        },
        room=session["game"],
    )

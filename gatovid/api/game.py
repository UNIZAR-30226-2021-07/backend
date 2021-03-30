"""
Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.
"""

from flask import session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.exts import socket
from gatovid.models import User


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
def on_join(data):
    game = data["game"]
    # Guardamos la partida actual en la sesión
    session["game"] = game

    join_room(game)

    emit(session["user"].name + " has entered the room", room=game)


@socket.on("leave")
def on_leave(data):
    leave_room(session["game"])
    emit(session["user"].name + " has left the room", room=session["user"].game)


@socket.on("chat")
def chat(msg):
    emit("chat", {"msg": msg, "owner": session["user"].name}, room=session["game"])

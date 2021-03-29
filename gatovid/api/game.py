"""
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
        print("user not connected")
        emit("invalid token")
        return False

    # Inicializamos la sesión del usuario
    email = get_jwt_identity()

    session["user"] = User.query.get(email)

    print("user connected")
    return True


@socket.on("join")
def on_join(data):
    print("user joined: ", session["user"])

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
    print(session["game"])
    emit("chat", {"msg": msg, "owner": session["user"].name}, room=session["game"])

"""
"""

from flask_jwt_extended import jwt_required
from flask_socketio import emit

from gatovid.exts import socket

@socket.on('connect')
def connect():
    """
    Return False si queremos prohibir la conexión del usuario.
    """
    try:
        # Comprobamos si el token es válido. Si el token es inválido,
        # lanzará una excepción.
        verify_jwt_in_request()
    except:
        print("user not connected")
        emit("invalid token")
        return False

    print("user connected")
    return True
@socket.on("chat")
def chat(msg):
    emit("chat", msg)

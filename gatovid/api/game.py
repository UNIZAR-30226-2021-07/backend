"""
"""

from flask_socketio import emit
from flask_jwt_extended import jwt_required

from gatovid.exts import socket

@socket.on("chat")
@jwt_required()
def chat(msg):
    emit("chat", msg)

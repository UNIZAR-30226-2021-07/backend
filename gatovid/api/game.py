"""
"""

from flask_socketio import emit

from gatovid.exts import socket


@socket.on("chat")
def chat(msg):
    emit("chat", msg)

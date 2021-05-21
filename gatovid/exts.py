"""
Extensiones usadas en la aplicación, declaradas en un archivo distinto para
administrar correctamente las dependencias circulares.
"""

from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_session import Session
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# Base de datos
db = SQLAlchemy(
    session_options={
        "expire_on_commit": False,
    }
)
# Para el encriptado de datos
bcrypt = Bcrypt()
# Manager de sesiones con JWT
jwt = JWTManager()
# Manager de conexiones websocket
socket = SocketIO(cors_allowed_origins="*")
# Manager de sesiones para websocket
sess = Session()
# Cross Origins Requests
cors = CORS()

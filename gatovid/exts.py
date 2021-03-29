"""
Extensiones usadas en la aplicación, declaradas en un archivo distinto para
administrar correctamente las dependencias circulares.
"""

from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

# Base de datos
db = SQLAlchemy()
# Para el encriptado de datos
bcrypt = Bcrypt()
# Manager de sesiones con JWT
jwt = JWTManager()

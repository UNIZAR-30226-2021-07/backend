"""
Extensiones usadas en la aplicación, declaradas en un archivo distinto para
administrar correctamente las dependencias circulares.
"""

from flask_sqlalchemy import SQLAlchemy

# Base de datos
db = SQLAlchemy()

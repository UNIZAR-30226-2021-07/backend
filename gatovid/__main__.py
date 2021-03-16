import sys

from gatovid.app import app
from gatovid.create_db import db_init, db_reset

# Creación inicial de los datos
if len(sys.argv) > 1 and sys.argv[1] == "--create-db":
    db_reset()
    db_init()
    exit(0)

# Ejecución de la aplicación de forma convencional
app.run()

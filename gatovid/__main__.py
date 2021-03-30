"""
Punto de entrada para cuando se ejecuta `gatovid` con `python -m gatovid`.
"""

import sys

from gatovid.app import app, logger
from gatovid.create_db import db_init, db_reset

# Creación inicial de los datos
if len(sys.argv) > 1:
    cmd = sys.argv[1]
    code = 0

    if cmd == "--create-db":
        db_init()
    elif cmd == "--reset-db":
        db_reset()
    else:
        logger.error(f"Unknown command `{cmd}`")
        code = 1

    exit(code)

# Ejecución de la aplicación de forma convencional
app.run()

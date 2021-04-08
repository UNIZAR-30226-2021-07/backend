"""
Algunas funciones útiles a lo largo de todo el programa.
"""

import functools
import logging
from typing import Dict, Optional

from flask import Blueprint, request


def msg_ok(msg: any) -> Dict[str, str]:
    """
    Para la confirmación de éxito de peticiones con un mensaje.
    """

    return {"message": str(msg)}


def msg_err(
    msg: any, code: int = 400, payload: Optional[Dict[str, str]] = {}
) -> (Dict[str, str], int):
    """
    Para la notificación de error de una petición, posiblemente con más
    información.
    """

    ret = {"error": str(msg), **payload}

    return ret, code


def route_get_or_post(blueprint: Blueprint, rule: str):
    """
    Simplifica los endpoints GET + POST simples con un decorator
    """

    def decorator(func):
        # El orden importa, sino todos los endpoints tendrán el nombre "wrapped"
        @blueprint.route(rule, methods=["GET", "POST"])
        @functools.wraps(func)
        def wrapped():
            data = request.args if request.method == "GET" else request.form
            return func(data)

        return wrapped

    return decorator


def get_logger(name: str) -> logging.Logger:
    """
    El logger por defecto de Python no funciona con Flask, por lo que esta
    función ayuda a configurarlo para un módulo.

    Es necesario también configurar un logger por cada módulo, dado que de esta
    forma se sabe de dónde es el mensaje siempre.
    """

    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
    )

    return logger

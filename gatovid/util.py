"""
Algunas funciones útiles a lo largo de todo el programa.
"""

import datetime
import functools
import logging
import threading
from datetime import timedelta
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


class PausableTimer:
    """
    Wrapper sobre threading.Timer que permite pausar y continuar la ejecución
    del temporizador.
    """

    def __init__(self, interval: float, *args, **kwargs) -> None:
        self._timer = threading.Timer(interval, *args, **kwargs)
        self._interval = interval
        self._args = args
        self._kwargs = kwargs

        self._elapsed = timedelta()
        self._started_at = None
        self._paused = False

    def is_started(self) -> bool:
        return self._started_at is not None

    def is_paused(self) -> bool:
        return self._paused

    def start(self) -> None:
        self._started_at = datetime.now()
        self._timer.start()

    def pause(self) -> None:
        if not self.is_started():
            raise ValueError("Timer not started")

        if self.is_paused():
            raise ValueError("Timer already paused")

        self._elapsed += datetime.now() - self._started_at
        self._paused = True
        self._timer.cancel()

    def resume(self) -> None:
        if not self.is_started():
            raise ValueError("Timer not started")

        if not self.is_paused():
            raise ValueError("Timer already running")

        remaining = self._interval - self._elapsed
        self._started_at = datetime.now()
        self._timer = threading.Timer(remaining, *self._args, **self._kwargs)
        self._timer.start()
        self._paused = False

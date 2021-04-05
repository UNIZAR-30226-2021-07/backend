from . import data, game

from typing import Dict, Optional


def msg_ok(msg: any) -> Dict[str, str]:
    """
    Para la confirmación de éxito de peticiones con un mensaje.
    """

    return {"message": str(msg)}


def msg_err(msg: any, payload: Optional[Dict[str, str]] = {}) -> (Dict[str, str], int):
    """
    Para la notificación de error de una petición, posiblemente con más
    información.
    """

    ret = {
        "error": str(msg),
        **payload
    }

    return ret, 400

"""
Módulo de los datos de las partidas.
"""

import queue
from datetime import datetime

from gatovid.models import User


def choose_code() -> str:
    """
    Devuelve un código sin usar y lo registra para que no pueda ser
    reutilizado.
    """

    return "1234"

class Match():
    """
    Información de una partida.
    """

    def __init__(self):
        self.start_time = 0
        self.started = False
        self.paused = False

        # Todas las partidas requieren un código identificador por las
        # salas de socketio. NOTE: se podrían usar códigos de formatos
        # distintos para que no hubiera colisiones, pero no creo que
        # sea necesario.
        self.code = choose_code()


class PrivateMatch(Match):
    """
    Información de una partida privada, a la que solo se puede unir
    con código y el lider tiene que decidir cuándo comenzar.
    """

    def __init__(self, owner: User):
        super().__init__()

        self.owner = owner

class PublicMatch(Match):
    """
    Información de una partida pública, gestionada completamente por
    el sistema gestor de partidas.
    """

class MatchManager():
    def __init__(self, ):
        # Cola de usuarios buscando una partida pública
        self.users_waiting = queue.Queue()
        # Cola de partidas esperando nuevos usuarios
        self.games_waiting = queue.Queue()

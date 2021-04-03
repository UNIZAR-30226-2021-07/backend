"""
Módulo de los datos de las partidas.
"""

import queue
import random
import string
from datetime import datetime

from gatovid.models import User

matches = dict()
MAX_MATCH_PLAYERS = 6

def gen_code(chars=string.ascii_uppercase + string.digits, N=4) -> str:
    """
    Devuelve un código de longitud N usando los caracteres
    especificados.
    """
    return ''.join(random.choices(chars, k=N))
    

def choose_code() -> str:
    """
    Devuelve un código sin usar y lo registra para que no pueda ser
    reutilizado.
    """

    code = gen_code()
    while matches.get(code):
        code = gen_code()

    return code


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
        # distintos para que no hubiera colisiones entre partidas
        # públicas y privadas, pero no creo que sea necesario.
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
    def __init__(self):
        # Cola de usuarios buscando una partida pública
        self.users_queue = queue.Queue()
        # Cola de partidas esperando nuevos usuarios
        self.games_queue = queue.Queue()

        self.users_waiting = set()


    def wait_for_game(self, user_sid: str):
        """
        Añade al usuario a la cola de usuarios esperando partida.
        """
        self.users_queue.put(user_sid)


    def stop_waiting(self, user_sid: str):
        """
        Elimina al usuario de la lista de usuarios eperando partida.
        Se necesita por si un usuario se desconecta a mitad de la
        búsqueda.

        La cola de Python no permite acceso aleatorio, por lo que se
        usará un set de usuarios esperando. Cuando se retire un
        usuario de la cola se comprobará si sigue esperando en dicho
        set.
        """

        self.users_waiting.remove(user_sid)


MM = MatchManager()
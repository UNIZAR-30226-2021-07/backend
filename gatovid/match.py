"""
Módulo de los datos de las partidas.
"""

from collections import deque
import random
import string
import threading
from datetime import datetime
from typing import List

from gatovid.exts import db, socket
from gatovid.models import User

matches = dict()
MIN_MATCH_PLAYERS = 2
MAX_MATCH_PLAYERS = 6
# Tiempo de espera hasta que se intenta empezar la partida
TIME_UNTIL_START = 5


def gen_code(chars=string.ascii_uppercase + string.digits, N=4) -> str:
    """
    Devuelve un código de longitud N usando los caracteres especificados.
    """

    return "".join(random.choices(chars, k=N))


def choose_code() -> str:
    """
    Devuelve un código sin usar y lo registra para que no pueda ser reutilizado.
    """

    code = gen_code()
    while matches.get(code):
        code = gen_code()

    return code


class Match:
    """
    Información de una partida.
    """

    def __init__(self) -> None:
        self.start_time = 0
        self._started = False
        self.paused = False
        self.players: List[User] = []

        # Todas las partidas requieren un código identificador por las salas de
        # socketio. NOTE: se podrían usar códigos de formatos distintos para que
        # no hubiera colisiones entre partidas públicas y privadas, pero no creo
        # que sea necesario.
        self.code = choose_code()

    @property
    def started(self) -> bool:
        return self._started

    @started.setter
    def started(self, started: bool) -> None:
        self._started = started
        if started:
            self.start_time = datetime.now()
        else:
            elapsed = datetime.now() - self.start_time
            elapsed_mins = int(elapsed.total_seconds() / 60)

            for player in self.players:
                player.stats.playtime_mins += elapsed_mins
            db.session.commit()

    def add_player(self, player: User) -> None:
        # Aseguramos que el usuario no está dos veces
        if player not in self.players:
            self.players.append(player)


class PrivateMatch(Match):
    """
    Información de una partida privada, a la que solo se puede unir con código y
    el lider tiene que decidir cuándo comenzar.
    """

    def __init__(self, owner: User) -> None:
        super().__init__()

        self.owner = owner


class PublicMatch(Match):
    """
    Información de una partida pública, gestionada completamente por el sistema
    gestor de partidas.
    """

    def __init__(self, num_players: int = 0) -> None:
        super().__init__()

        self.num_players = num_players


def test():
    print("timer")

class MatchManager:

    def __init__(self) -> None:
        # Cola de usuarios buscando una partida pública
        self.users_waiting = deque()
        # Temporizador para el tiempo de pánico para generar una partida. Se
        # generará una partida con un número de jugadores menor a 6.
        self.timer = None

    def wait_for_game(self, user: User) -> None:
        """
        Añade al usuario a la cola de usuarios esperando partida.
        """

        # No añadimos al usuario si ya está esperando.
        # FIXME: podría dar error si no cambia el sid del usuario, habría que
        # actualizar el objeto usuario en tal caso.
        if user in self.users_waiting:
            return

        self.users_waiting.append(user)

        # Si ya existía un timer, lo cancelamos -> además, esto asegura que no
        # entrará el callback a mitad de comprobación de crear partida
        if self.timer:
            self.timer.cancel()

        # Si la cola tiene el máximo de jugadores para una partida, se crea una
        # partida para todos.
        if len(self.users_waiting) >= MAX_MATCH_PLAYERS:
            self.create_public_game()            
        else:
            # Creamos un timer
            self.timer = threading.Timer(TIME_UNTIL_START, self.matchmaking_check)
            self.timer.start()
            
    def matchmaking_check(self):
        if len(self.users_waiting) >= MIN_MATCH_PLAYERS:
            self.create_public_game()            

    def stop_waiting(self, user: User) -> None:
        """
        Elimina al usuario de la cola de usuarios esperando partida. Se necesita
        por si un usuario se desconecta a mitad de la búsqueda.
        """

        self.users_waiting.remove(user)

    def create_public_game(self) -> None:
        # Obtener los jugadores esperando
        players = self.get_waiting()

        # Creamos la partida
        new_match = PublicMatch(num_players=len(players))
        code = new_match.code
        # Añadimos la partida a la lista de partidas
        matches[code] = new_match

        # Avisar a todos los jugadores de la partida
        for player in players:
            socket.emit("found_game", {"code": code}, room=player.sid)


    def create_private_game(self, owner: User) -> None:
        new_match = PrivateMatch(owner=owner)
        matches[new_match.code] = new_match
        return new_match.code

    def remove_game(self, code: str) -> None:
        del matches[code]

    def get_match(self, code: str) -> Match:
        return matches.get(code)

    def remove_match(self, code: str) -> None:
        # Eliminar con seguridad (para evitar crashes)
        matches.pop(code, None)

    def get_waiting(self):
        """
        Devuelve el máximo de jugadores (y los elimina de la cola de espera)
        intentando completar una partida. Si no hay suficientes jugadores para
        una partida, devuelve una lista vacía y no los elimina de la cola.
        """

        waiting = []
        max_to_play = min(len(self.users_waiting), MAX_MATCH_PLAYERS)

        for i in range(max_to_play):
            waiting.append(self.users_waiting.popleft())

        return waiting


MM = MatchManager()

"""
Módulo de los datos de las partidas.
"""

import random
import string
import threading
from collections import deque
from datetime import datetime
from typing import Set

from gatovid.exts import db, socket
from gatovid.models import User

matches = dict()
MIN_MATCH_PLAYERS = 2
MAX_MATCH_PLAYERS = 6
# Tiempo de espera hasta que se intenta empezar la partida
TIME_UNTIL_START = 5


class GameLogicException(Exception):
    """
    Esta excepción se usa para indicar casos erróneos o inesperados en el juego.
    """


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
        self.started = False
        self.paused = False
        self.players: Set[User] = set()

        # Todas las partidas requieren un código identificador por las salas de
        # socketio. NOTE: se podrían usar códigos de formatos distintos para que
        # no hubiera colisiones entre partidas públicas y privadas, pero no creo
        # que sea necesario.
        self.code = choose_code()

    def calc_coins(self, position: int) -> int:
        """
        Calcula las monedas obtenidos según la posición final, según la fórmula
        establecida:

        Sea N el número de jugadores de la partida, el jugador en puesto i
        ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo N
        * 10, y el último 0.
        """

        N = len(self.players)
        return 10 * (N - 1)

    def is_started(self) -> bool:
        return self._started

    def start(self) -> None:
        """
        La partida solo se puede iniciar una vez, por lo que esta operación es
        más limitada que un setter.
        """

        self.started = True
        self.start_time = datetime.now()
        socket.emit("start_game", room=self.code)

    def end(self) -> None:
        """
        Termina la partida y guarda las estadísticas para todos los usuarios.
        """

        elapsed = datetime.now() - self.start_time
        elapsed_mins = int(elapsed.total_seconds() / 60)

        for player in self.players:
            position = 1  # TODO tras la implementación del juego
            player.coins += self.calc_coins(position)
            player.stats.playtime_mins += elapsed_mins
            if position == 1:
                player.stats.wins += 1
            else:
                player.stats.losses += 1

        db.session.commit()

        socket.emit("game_ended", room=self.code)

    def add_player(self, player: User) -> None:
        """
        Añade un usuario a la partida.

        Puede darse una excepción si la partida ya ha empezado o si ya está en
        la partida anteriormente.
        """

        if self.is_started():
            raise GameLogicException("La partida ya ha empezado")

        if player in self.players:
            raise GameLogicException("El usuario ya está en la partida")

        self.players.add(player)


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

        # Número de jugadores a la hora de hacer el matchmaking. Para comprobar
        # si están todos los jugadores que se habían organizado.
        self.num_players = num_players

        # Timer para empezar la partida si en TIME_UNTIL_START segundos no se
        # han conectado todos los jugadores.
        self.start_timer = threading.Timer(TIME_UNTIL_START, self.start_check)

    def start(self):
        # Cancelamos el timer si sigue
        self.start_timer.cancel()

        super().start()

    def start_check(self):
        """
        Comprobación de si la partida puede comenzar tras haber dado un tiempo a
        los jugadores para que se conecten. Si es posible, la partida empezará.
        """

        if len(self.players) >= MIN_MATCH_PLAYERS:
            # Empezamos la partida
            self.start()


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

        # Si siguen quedando jugadores en la cola, configuramos el timer.
        if len(self.users_waiting) > 0:
            # Creamos un timer
            self.timer = threading.Timer(TIME_UNTIL_START, self.matchmaking_check)
            self.timer.start()

    def matchmaking_check(self):
        """
        Comprobación de si se puede crear una partida pública "de emergencia"
        (con menos jugadores que el máximo). La partida se crea si es posible.
        """

        if len(self.users_waiting) >= MIN_MATCH_PLAYERS:
            self.create_public_game()

    def stop_waiting(self, user: User) -> None:
        """
        Elimina al usuario de la cola de usuarios esperando partida. Se necesita
        por si un usuario se desconecta a mitad de la búsqueda.
        """

        self.users_waiting.remove(user)

        # Si ya no hay mas jugadores esperando, cancelamos el timer
        if len(self.users_waiting) == 0:
            self.timer.cancel()

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

        # Ponemos un timer para empezar la partida, por si no se unen todos
        new_match.start_timer.start()

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

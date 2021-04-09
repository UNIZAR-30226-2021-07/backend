"""
Módulo de los datos sobre las partidas actuales y el sistema de matchmaking.
"""

import random
import string
import threading
from collections import deque
from typing import List, Optional

from gatovid.exts import socket
from gatovid.game import Game
from gatovid.models import User

matches = dict()
MIN_MATCH_USERS = 2
MAX_MATCH_USERS = 6
# Tiempo de espera hasta que se intenta empezar la partida
TIME_UNTIL_START = 5


class GameLogicException(Exception):
    """
    Esta excepción se usa para indicar casos erróneos o inesperados en el juego.
    """


def _gen_code(chars=string.ascii_uppercase + string.digits, N=4) -> str:
    """
    Devuelve un código de longitud N usando los caracteres especificados.
    """

    return "".join(random.choices(chars, k=N))


def choose_code() -> str:
    """
    Devuelve un código sin usar y lo registra para que no pueda ser reutilizado.
    """

    code = _gen_code()
    while matches.get(code):
        code = _gen_code()

    return code


class Match:
    """
    Información de una partida. La lógica del juego se guarda en la clase
    `Game`, que estará inicializado únicamente si la partida ha comenzado.
    """

    def __init__(self) -> None:
        self.users: List[User] = []
        self._game: Optional[Game] = None
        self._started_lock = threading.Lock()

        # Todas las partidas requieren un código identificador por las salas de
        # socketio. NOTE: se podrían usar códigos de formatos distintos para que
        # no hubiera colisiones entre partidas públicas y privadas, pero no creo
        # que sea necesario.
        self.code = choose_code()

    def is_started(self) -> bool:
        """
        La partida se considera iniciada cuando ya se ha inicializado el juego,
        que se auto-administra en su clase y siempre se considera iniciado.
        """

        return self._game is not None

    def start(self) -> None:
        """
        La partida solo se puede iniciar una vez, por lo que esta operación es
        más limitada que un setter.
        """

        with self._started_lock:
            if self.is_started():
                return
            self._game = Game(self.users)

        socket.emit("start_game", room=self.code)

    def end(self) -> None:
        """
        Finaliza la partida en caso de que no haya terminado ya.
        """

        if not self.is_started() or not self._game.is_finished():
            socket.emit("game_cancelled", room=self.code)
            return

    def add_user(self, user: User) -> None:
        """
        Añade un usuario a la partida.

        Puede darse una excepción si la partida ya ha empezado o si ya está en
        la partida anteriormente.
        """

        if self.is_started():
            raise GameLogicException("La partida ya ha empezado")

        if user in self.users:
            raise GameLogicException("El usuario ya está en la partida")

        self.users.append(user)


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

    def __init__(self, num_users: int = 0) -> None:
        super().__init__()

        # Número de jugadores a la hora de hacer el matchmaking. Para comprobar
        # si están todos los jugadores que se habían organizado.
        self.num_users = num_users

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

        if len(self.users) >= MIN_MATCH_USERS:
            # Empezamos la partida
            self.start()


class MatchManager:
    def __init__(self) -> None:
        # Cola de usuarios buscando una partida pública
        self.users_waiting = deque()
        # Temporizador para el tiempo de pánico para generar una partida. Se
        # generará una partida con un número de jugadores menor a 6.
        self._timer = None

        # True si se ha realizado el check. Sirve para no acceder a la misma
        # zona de código dos veces seguidas.
        self._checked = False
        self._checked_lock = threading.Lock()

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
        if self._timer:
            self._timer.cancel()

        with self._checked_lock:
            if self._checked:
                self._checked = False
                return
            self._checked = True

        # Si la cola tiene el máximo de jugadores para una partida, se crea una
        # partida para todos.
        if len(self.users_waiting) >= MAX_MATCH_USERS:
            self.create_public_game()

        # Si siguen quedando jugadores en la cola, configuramos el timer.
        if len(self.users_waiting) > 0:
            # Creamos un timer
            self._timer = threading.Timer(TIME_UNTIL_START, self.matchmaking_check)
            self._timer.start()

        self._checked = False

    def matchmaking_check(self):
        """
        Comprobación de si se puede crear una partida pública "de emergencia"
        (con menos jugadores que el máximo). La partida se crea si es posible.
        """

        with self._checked_lock:
            if self._checked:
                self._checked = False
                return
            self._checked = True

        if len(self.users_waiting) >= MIN_MATCH_USERS:
            self.create_public_game()

    def stop_waiting(self, user: User) -> None:
        """
        Elimina al usuario de la cola de usuarios esperando partida. Se necesita
        por si un usuario se desconecta a mitad de la búsqueda.
        """

        self.users_waiting.remove(user)

        # Si ya no hay mas jugadores esperando, cancelamos el timer
        if len(self.users_waiting) == 0:
            self._timer.cancel()

    def create_public_game(self) -> None:
        # Obtener los jugadores esperando
        users = self.get_waiting()

        # Creamos la partida
        new_match = PublicMatch(num_users=len(users))
        code = new_match.code
        # Añadimos la partida a la lista de partidas
        matches[code] = new_match

        # Avisar a todos los jugadores de la partida
        for user in users:
            socket.emit("found_game", {"code": code}, room=user.sid)

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
        max_to_play = min(len(self.users_waiting), MAX_MATCH_USERS)

        for i in range(max_to_play):
            waiting.append(self.users_waiting.popleft())

        return waiting


MM = MatchManager()

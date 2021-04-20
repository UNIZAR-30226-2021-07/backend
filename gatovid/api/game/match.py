"""
Módulo de los datos sobre las partidas actuales y el sistema de matchmaking.
"""

import random
import threading
from collections import deque
from typing import Dict, List, Optional

from gatovid.exts import db, socket
from gatovid.game import Action, Game, GameLogicException
from gatovid.models import User
from gatovid.util import get_logger

logger = get_logger(__name__)
matches = dict()
MIN_MATCH_USERS = 2
MAX_MATCH_USERS = 6
# Tiempo de espera hasta que se intenta empezar la partida
TIME_UNTIL_START = 5
# Caracteres permitidos para los códigos de las partidas.
CODE_ALLOWED_CHARS = "ACDEFGHJKLMNPQRSTUVWXY345679"


def _gen_code(chars=CODE_ALLOWED_CHARS, N=4) -> str:
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

        logger.info(f"Match {self.code} has started")

        socket.emit("start_game", room=self.code)

    def run_action(self, action: Action) -> None:
        """
        Ejecuta una acción cualquiera del juego.
        """

        if not self.is_started():
            raise GameLogicException("El juego no ha comenzado")

        all_status = self._game.run_action(action)
        for status in all_status:
            if status.finished:
                self.update_stats(status)

            socket.emit("game_update", status, room=self.user.sid)

    def end(self) -> None:
        """
        Finaliza la partida en caso de que no haya terminado ya.
        """

        if not self.is_started() or not self._game.is_finished():
            socket.emit("game_cancelled", room=self.code)

        logger.info(f"Match {self.code} has ended")

    def update_stats(self, user: User, status: Dict) -> None:
        """
        Una vez terminada la partida, se pueden actualizar las estadísticas de
        cada usuario.
        """

        user.stats.playtime_mins += status["playtime_mins"]

        leaderboard = status["leaderboard"][user.name]
        user.coins += leaderboard["coins"]
        if leaderboard["position"] == 1:
            user.stats.wins += 1
        else:
            user.stats.losses += 1

        db.session.commit()

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

    def end(self):
        # Cancelamos el timer si sigue
        self.start_timer.cancel()

        super().end()

    def start_check(self):
        """
        Comprobación de si la partida puede comenzar tras haber dado un tiempo a
        los jugadores para que se conecten. Si es posible, la partida empezará,
        y sino se cancela la partida por esperar demasiado.
        """

        if len(self.users) >= MIN_MATCH_USERS:
            # Empezamos la partida
            self.start()
        else:
            # La cancelamos
            logger.info(f"Public match {self.code} has been cancelled")
            self.end()


class MatchManager:
    def __init__(self) -> None:
        # Cola de usuarios buscando una partida pública
        self.users_waiting = deque()
        # Temporizador para el tiempo de pánico para generar una partida. Se
        # generará una partida con un número de jugadores menor a 6. Será
        # activado únicamente cuando se tengan suficientes usuarios para
        # comenzar una partida.
        self._public_timer = None
        # El servidor es secuencial, excepto en el caso de las partidas
        # públicas, que tienen timers que pueden modificar el estado desde un
        # thread distinto.
        self._public_lock = threading.Lock()

    def wait_for_game(self, user: User) -> None:
        """
        Añade al usuario a la cola de usuarios esperando partida.
        """

        with self._public_lock:
            # No añadimos al usuario si ya está esperando.
            # FIXME: podría dar error si no cambia el sid del usuario, habría
            # que actualizar el objeto usuario en tal caso.
            if user in self.users_waiting:
                raise GameLogicException(
                    "El usuario ya está esperando a una partida pública"
                )

            self.users_waiting.append(user)
            logger.info(f"User {user.name} is waiting for a game")

            # Si la cola tiene el máximo de jugadores para una partida, se crea
            # una partida para todos.
            if len(self.users_waiting) >= MAX_MATCH_USERS:
                self.create_public_game()
                return

            # En caso contrario, si se ha llegado al mínimo de usuarios se
            # inicia el timer.
            if len(self.users_waiting) == MIN_MATCH_USERS:
                self._public_timer = threading.Timer(
                    TIME_UNTIL_START, self.matchmaking_check
                )
                self._public_timer.start()

    def matchmaking_check(self):
        """
        Comprobación de si se puede crear una partida pública "de emergencia"
        (con menos jugadores que el máximo). La partida se crea si es posible.
        """

        with self._public_lock:
            if len(self.users_waiting) >= MIN_MATCH_USERS:
                self.create_public_game()

    def stop_waiting(self, user: User) -> None:
        """
        Elimina al usuario de la cola de usuarios esperando partida.
        """

        with self._public_lock:
            self.users_waiting.remove(user)

            # Si ya no hay suficientes jugadores esperando, se cancela el timer.
            if len(self.users_waiting) < MIN_MATCH_USERS:
                self._public_timer.cancel()
                self._public_timer = None

    def create_public_game(self) -> None:
        # Se cancela el timer si es necesario.
        if self._public_timer is not None:
            self._public_timer.cancel()
            self._public_timer = None

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
        logger.info(f"Public match {code} has been created")
        new_match.start_timer.start()

    def create_private_game(self, owner: User) -> None:
        if owner in self.users_waiting:
            raise GameLogicException(
                "El usuario ya está esperando a una partida pública"
            )

        new_match = PrivateMatch(owner=owner)
        matches[new_match.code] = new_match
        logger.info(f"Private match {new_match.code} has been created by {owner.name}")
        return new_match.code

    def remove_game(self, code: str) -> None:
        del matches[code]

    def get_match(self, code: str) -> Optional[Match]:
        return matches.get(code)

    def remove_match(self, code: str) -> None:
        # Eliminar con seguridad (para evitar crashes)
        matches.pop(code, None)

    def get_waiting(self) -> List[User]:
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

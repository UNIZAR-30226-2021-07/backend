"""
Módulo de los datos sobre las partidas actuales y el sistema de matchmaking.
"""

import random
import threading
from collections import deque
from typing import Dict, List, Optional

from gatovid.exts import db, socket
from gatovid.game import Action, Game, GameLogicException, GameUpdate
from gatovid.models import MAX_MATCH_USERS, MIN_MATCH_USERS, User
from gatovid.util import Timer, get_logger

logger = get_logger(__name__)
matches = dict()
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

    def _resume_paused(self):
        logger.info("Pause time expirated, resuming game...")
        self.set_paused(False, self._game._paused_by)

    def set_paused(self, val: bool, paused_by: str) -> None:
        update = self._game.set_paused(
            val, paused_by, resume_callback=self._resume_paused
        )
        if update is not None:
            self.broadcast_update(update)

    def is_paused(self) -> bool:
        self._game.is_paused()

    def get_user(self, name: str) -> Optional[User]:
        try:
            return next(filter(lambda u: u.name == name, self.users))
        except StopIteration:
            return None

    def _turn_passed_auto(
        self, update: Optional[GameUpdate], kicked: Optional[str], finished: bool
    ) -> None:
        """
        Callback invocado cuando la partida pasa de turno automáticamente por el
        timer. Esta acción posiblemente expulse a un usuario de la partida, en
        cuyo caso `kicked` no será `None`.

        Cuando se hayan expulsado suficientes jugadores hasta no poderse seguir
        jugando, `finished` será `True` (los demás parámetros `None`) y se
        cancelará la partida.
        """

        if finished:
            logger.info(f"Not enough players to continue in {self.code}")
            self.end(cancel=True)
            return

        self.send_update(update)

        if kicked is not None:
            # Se elimina al usuario de la partida. No hace falta añadirlo al
            # game_update porque ya se incluye en el `update` de este callback.
            # Importante hacer esto después del `send_update` para que se envíe
            # al usuario reemplazado también.
            kicked_user = self.get_user(kicked)
            self.users.remove(kicked_user)

    def start(self) -> None:
        """
        La partida solo se puede iniciar una vez, por lo que esta operación es
        más limitada que un setter.

        Primero se envía un mensaje especial de inicio de la partida,
        start_game.

        Posteriormente, se inicia la partida tanto por parte del juego (con la
        lógica, como las cartas de cada jugador, etc), como por parte de la
        partida (que tiene que enviar al cliente información de los usuarios,
        como su tablero).

        Notar que esto último se tiene que enviar en un mismo mensaje al
        cliente, y no se puede dividir en dos; originalmente la información
        sobre los jugadores como sus fotos debería haber ido en start_game.
        """

        if self.is_started():
            return

        enable_ai = isinstance(self, PublicMatch)
        self._game = Game(self.users, self._turn_passed_auto, enable_ai)

        # Mensaje especial de inicio de la partida
        logger.info(f"Match {self.code} has started")
        socket.emit("start_game", room=self.code)

        # game_update con el inicio del juego
        update = self._game.start()
        # game_update con el inicio de la partida
        match_update = self._match_update()

        # Unión de ambos game_update
        update.merge_with(match_update)
        self.send_update(update)

    def _match_update(self) -> GameUpdate:
        """
        Genera un game_update con información sobre la partida para cada
        jugador.
        """

        update = GameUpdate(self._game)
        for current_user in self.users:
            data = {"players": []}
            for user in self.users:
                # Información genérica del resto de usuarios
                user_data = {
                    "name": user.name,
                    "picture": user.picture,
                }

                # Para el mismo usuario que recibe el mensaje, se envía también
                # su tablero.
                if user == current_user:
                    user_data["board"] = user.board

                data["players"].append(user_data)

            update.add(current_user.name, data)

        return update

    def send_update(self, update: GameUpdate) -> None:
        """
        Envía un game_update a cada uno de los participantes de la partida.
        """

        for user in self.users:
            status = update.get(user.name)
            if status == {}:
                continue

            socket.emit("game_update", status, room=user.sid)

    def broadcast_update(self, update: GameUpdate) -> None:
        """
        Envía un mismo game_update a todos los participantes de la partida.
        """

        socket.emit("game_update", update.get_any(), room=self.code)

    def run_action(self, caller: str, action: Action) -> None:
        """
        Ejecuta una acción cualquiera del juego.
        """

        if not self.is_started():
            raise GameLogicException("El juego no ha comenzado")

        update = self._game.run_action(caller, action)
        self.send_update(update)

        if self._game.is_finished():
            for user in self.users:
                self.update_stats(user, update.get(user.name))

    def end(self, cancel: bool = False) -> None:
        """
        Finaliza la partida en caso de que no haya terminado ya.

        Si `cancel` es verdadero, se interpreta como que la partida ha sido
        cancelada forzosamente y por tanto se enviará un mensaje de terminación
        temprana a los usuarios de la partida.
        """

        if cancel:
            self.cancel()

        # Se termina manualmente el juego interno, pero al ser cancelado no
        # se actualizarán los datos de los jugadores ni se enviará el
        # game_update.
        if self.is_started() and not self._game.is_finished():
            _ = self._game.finish()

        # Se elimina a sí misma del gestor de partidas
        MM.remove_match(self.code)

        logger.info(f"Match {self.code} has ended")

    def update_stats(self, user: User, status: Dict) -> None:
        """
        Una vez terminada la partida, se pueden actualizar las estadísticas de
        cada usuario.
        """

        # Los objetos están lazy-loaded, necesitamos recuperar una versión
        # modificable de user para poder editar su atributo stats.
        user = User.query.get(user.email)
        user.stats.playtime_mins += status["playtime_mins"]

        leaderboard = status["leaderboard"][user.name]
        user.coins += leaderboard["coins"]
        if leaderboard["position"] == 1:
            user.stats.wins += 1
        else:
            user.stats.losses += 1

        db.session.commit()

    def check_rejoin(self, user: User) -> (bool, Optional[GameUpdate]):
        """
        Para comprobar si un usuario se puede volver a unir a la partida.
        """

        if isinstance(self, PublicMatch):
            return False, None

        if not self.is_started():
            return False, None

        if user not in self.users:
            return False, None

        update = GameUpdate(self._game)
        update.merge_with(self._game.full_update())
        update.merge_with(self._match_update())
        return True, update.get(user.name)

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

    def update_user(self, user: User) -> None:
        """
        Actualiza la información del usuario, como el SID (cambia en
        la reconexión) o el nombre si lo ha modificado antes de
        reconectarse.

        Puede darse una excepción el usuario no se encuentra en la partida.
        """

        for (i, u) in enumerate(self.users):
            if u == user:
                self.users[i] = user
                return

        raise GameLogicException("El usuario no está en la partida")

    def remove_user(self, user: User) -> None:
        try:
            self.users.remove(user)
        except ValueError:
            return

        if self.is_started():
            update = self._game.remove_player(user.name)
            if self._game.is_finished():
                self.end(cancel=True)
            else:
                self.send_update(update)

    def cancel(self) -> None:
        logger.info(f"Match {self.code} is being cancelled")
        socket.emit("game_cancelled", room=self.code)


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
        self.start_timer = Timer(TIME_UNTIL_START, self.start_check)
        self.start_lock = threading.Lock()

    # NOTE: se declaran de forma separada y privada los métodos `_start` y
    # `_end`. Esto es porque para los métodos públicos `start` y `end` es
    # necesario hacer lock para evitar problemas de concurrencia con el timer,
    # pero el mismo timer también necesita acceso a esas funciones. Por tanto,
    # para evitar un deadlock el timer accederá a las versiones sin lock, y las
    # interfaces públicas sí que usarán el lock.

    def _start(self):
        logger.info(
            f"Starting public game {self.code}" f" with {len(self.users)} users"
        )

        # Cancelamos el timer si sigue
        self.start_timer.cancel()

        super().start()

    def _end(self, cancel: bool = False):
        # Cancelamos el timer si sigue
        self.start_timer.cancel()

        super().end(cancel)

    def start(self):
        with self.start_lock:
            self._start()

    def end(self, cancel: bool = False):
        with self.start_lock:
            self._end(cancel)

    def start_check(self):
        """
        Comprobación de si la partida puede comenzar tras haber dado un tiempo a
        los jugadores para que se conecten. Si es posible, la partida empezará,
        y sino se cancela la partida por esperar demasiado.

        Como esta parte se realiza de forma concurrente, es necesario usar el
        lock de inicio de turno y asegurarse que después de obtenerlo no se ha
        iniciado la partida ya.
        """

        logger.info("Public match timer triggered")

        with self.start_lock:
            if self.is_started():
                logger.info("Timer skipping check; game already started")
                return

            # Empezamos la partida únicamente si hay suficientes usuarios
            if len(self.users) >= MIN_MATCH_USERS:
                self._start()
            else:
                self._end(cancel=True)


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
                self._public_timer = Timer(TIME_UNTIL_START, self.matchmaking_check)
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
            logger.info(f"User {user.name} has stopped searching")

            not_enough_users = len(self.users_waiting) < MIN_MATCH_USERS
            timer_running = self._public_timer is not None
            if not_enough_users and timer_running:
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
        logger.info(f"Removing {code} from matches")
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

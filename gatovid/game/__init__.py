"""
Implementación de la lógica del juego.
"""

import random
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.actions import Action
from gatovid.game.body import Body
from gatovid.game.cards import DECK, Card

# Exportamos GameLogicException
from gatovid.game.common import GameLogicException, GameUpdate
from gatovid.models import User
from gatovid.util import PausableTimer, get_logger

logger = get_logger(__name__)

# Tiempo de espera hasta que se reanuda la partida si está pausada.
TIME_UNTIL_RESUME = 15
# Tiempo máximo del turno
TIME_TURN_END = 30
# Máximo de turnos antes de expulsar a un usuario por estar AFK
MAX_AFK_TURNS = 3


@dataclass(init=False)
class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    name: str
    position: Optional[int]
    hand: List[Card]
    body: Body
    afk_turns: int
    kicked: bool

    def __init__(self, name: str) -> None:
        self.name = name
        self.position = None
        self.hand = []
        self.body = Body()
        # Turnos consecutivos que el usuario ha estado AFK
        self.afk_turns = 0
        # Una vez se expulse al jugador
        self.kicked = False

    def has_finished(self) -> bool:
        return self.position is not None

    def get_card(self, slot: int) -> Card:
        try:
            return self.hand[slot]
        except IndexError:
            raise GameLogicException("Slot no existente en la mano del jugador")

    def remove_card(self, slot: int) -> None:
        try:
            del self.hand[slot]
        except IndexError:
            raise GameLogicException("Slot no existente en la mano del jugador")

    def add_card(self, card: Card) -> None:
        self.hand.append(card)


class Game:
    """
    Información global sobre la partida y su estado, de forma desacoplada a la
    base de datos.

    Los jugadores se guardan en una lista, y se sabe el turno actual con el
    índice en esta.
    """

    def __init__(self, users: List[User], turn_callback, enable_ai: bool) -> None:
        self.players = [Player(user.name) for user in users]
        self.deck: List[Card] = []
        self._start_time = datetime.now()
        self._enabled_ai = enable_ai

        self._turn = 0
        self._turn_timer = None
        self._turn_lock = threading.Lock()
        self._turn_number = 0
        # El callback del timer se llamará cuando se cambie el turno de la
        # partida de forma automática con el timer. Incluirá el `game_update` y
        # si algún usuario ha sido expulsado de la partida.
        self._turn_callback = turn_callback

        self._paused = False
        self._paused_by = ""
        self._paused_lock = threading.Lock()
        self._paused_timer = None

        self._finished = False
        self._players_finished = 0
        # Indica la fase de descarte, en la que no se podrá hacer otra cosa
        # excepto seguir descartando o pasar el turno.
        self.discarding = False

    def start(self) -> GameUpdate:
        """
        Inicializa la baraja, la reordena de forma aleatoria, y reparte 3 cartas
        a cada jugador, iterando de forma similar a cómo se haría en la vida
        real. También elige de forma aleatoria el turno inicial.

        Devuelve un game_update con el estado actual del juego.
        """

        logger.info("Setting up game")

        self.deck = DECK.copy()
        random.shuffle(self.deck)

        for i in range(3):
            for player in self.players:
                self.draw_card(player)

        self._turn = random.randint(0, len(self.players) - 1)
        logger.info(f"First turn is for {self.turn_player().name}")
        self._start_turn_timer()

        # Genera el estado inicial con las manos y turno
        update = GameUpdate(self)
        update.repeat({"current_turn": self.turn_player().name})
        update.add_for_each(lambda player: {"hand": player.hand})
        return update

    def is_finished(self) -> bool:
        return self._finished

    def get_player(self, user_name: str) -> Player:
        for player in self.players:
            if player.name == user_name:
                return player

        raise GameLogicException("El jugador no está en la partida")

    def set_paused(
        self, paused: bool, paused_by: str, resume_callback
    ) -> Optional[GameUpdate]:
        with self._paused_lock:
            if self._paused == paused:
                return None

            # Solo el jugador que ha pausado la partida puede volver a reanudarla.
            if self._paused and self._paused_by != paused_by:
                raise GameLogicException(
                    "Solo el jugador que inicia la pausa puede reanudar"
                )

            # Si la pausa pasa del tiempo límite comentado anteriormente, la
            # partida se reanuda automáticamente
            if paused:
                # Se para mientras tanto el timer del turno
                self._turn_timer.pause()

                # Iniciamos un timer
                self._pause_timer = threading.Timer(TIME_UNTIL_RESUME, resume_callback)
                self._pause_timer.start()

                logger.info(f"Game paused by {paused_by}")
            else:
                # Continúa el timer del turno
                self._turn_timer.resume()

                self._pause_timer.cancel()
                logger.info("Game resumed")

            self._paused = paused
            self._paused_by = paused_by

            update = GameUpdate(self)
            update.repeat(
                {
                    "paused": paused,
                    "paused_by": paused_by,
                }
            )
            return update

    def is_paused(self) -> bool:
        self._paused

    def run_action(self, caller: str, action: Action) -> [Dict]:
        """
        Llamado ante cualquier acción de un jugador en la partida. Devolverá el
        nuevo estado de la partida por cada jugador, o en caso de que ya hubiera
        terminado anteriormente o estuviera pausada, un error.

        Se terminará el turno automáticamente en caso de que no haya quedado el
        usuario en fase de descarte.
        """

        with self._turn_lock:
            if self._finished:
                raise GameLogicException("El juego ya ha terminado")

            if self._paused:
                raise GameLogicException("El juego está pausado")

            if self.players[self._turn].name != caller:
                raise GameLogicException("No es tu turno")

            player = self.get_player(caller)
            update = action.apply(player, game=self)

            # TODO: revisar fin de partida
            if self._players_finished == len(self.players) - 1:
                finish_update = self.finish()
                update.merge_with(finish_update)

            if not self.discarding and not self._finished:
                end_update = self._end_turn()
                update.merge_with(end_update)

            return update

    def draw_card(self, player: Player) -> None:
        """
        Roba una carta del mazo para el jugador.
        """

        logger.info(f"{player.name} draws a card")

        drawn = self.deck.pop()
        player.hand.append(drawn)

    def _end_turn(self) -> [Dict]:
        """
        Tiene en cuenta que si el jugador al que le toca el turno no tiene
        cartas en la mano, deberá ser skipeado. Antes de pasar el turno el
        jugador automáticamente robará cartas hasta tener 3.

        Es posible, por tanto, que el fin de turno modifique varias partes de la
        partida, incluyendo las manos, por lo que se devuelve un game_update
        completo.
        """

        update = [{}] * len(self.players)

        # Se reestablecen los turnos AFK del usuario que ha terminado
        # correctamente la partida. No se hará para los posibles jugadores sean
        # skipeados.
        self.turn_player().afk_turns = 0

        while True:
            # TODO: si el usuario está kickeado se le debería pasar el turno o
            # la IA debería jugar por él.

            logger.info(f"{self.turn_player().name}'s turn has ended")
            self._turn_number += 1

            # Roba cartas hasta tener 3, se actualiza el estado de ese jugador
            # en concreto.
            while len(self.turn_player().hand) < 3:
                self.draw_card(self.turn_player())
            for u, player in zip(update, self.players):
                if player == self.turn_player():
                    u["hand"] = self.turn_player().hand
                    break

            # Siguiente turno, y actualización del estado a todos los jugadores
            #
            # No se le pasará el turno a un jugador que ya ha terminado la
            # partida.
            while True:
                self._turn = (self._turn + 1) % len(self.players)
                if not self.turn_player().has_finished():
                    break
            new_turn = {"current_turn": self.turn_player().name}
            turn_update = [new_turn] * len(self.players)
            update = self._merge_updates(update, turn_update)
            logger.info(f"{self.turn_player().name}'s turn has started")

            # Continúa pasando el turno si el jugador siguiente no tiene cartas
            # disponibles.
            if len(self.turn_player().hand) != 0:
                break
            logger.info(f"{self.turn_player().name} skipped (no cards)")

        self._start_turn_timer()

        return update

    def _timer_end_turn(self):
        """
        Termina el turno automáticamente por parte del timer.

        El turno es controlado tanto de forma manual con `run_action` como de
        forma automática en este método. Como la ejecución es secuencial por
        usar locks entre ambas fuentes, se pueden dar las siguientes
        situaciones, que podrían provocar comportamiento indeseado a tener en
        cuenta:

        1. run_action
        2. _timer_end_turn

        1. _timer_end_turn
        2. run_action

        El segundo caso no sería un problema, porque se pasaría el turno
        automáticamente con el timer, y posteriormente el usuario con el turno
        anterior intentaría hacer una acción que terminase el turno, como por
        ejemplo jugar una carta. Sin embargo, en `run_action` ya se comprueba
        que el jugador que lo invoca es el que tiene el turno, y se producirá un
        error.

        El primer caso, sin embargo, sí que puede producir una condición de
        carrera. Es posible que el timer salte justo cuando se esté terminando
        un turno de forma manual en `run_action`, en cuyo caso al terminar
        `run_action` se llamaría a `_timer_end_turn` y se volvería a pasar el
        turno (de forma incorrecta).

        Para mitigar la anterior condición de carrera, es necesario asegurarse
        en esta función que antes y después de tenerse el lock no haya cambiado
        el turno ya. Esto no se puede comprobar comparando el nombre del usuario
        que tiene el turno, ya que es posible que después de pasar el turno le
        toque al mismo usuario otra vez porque los demás no tengan cartas. Es
        por ello por lo que se mantiene un contador con el número de turno, que
        adicionalmente puede tener otros usos.
        """

        initial_turn = self._turn_number
        with self._turn_lock:
            # El turno ha cambiado externamente al obtener el lock.
            if self._turn_number != initial_turn:
                return

            # Expulsión de jugadores AFK
            kicked = None
            self.turn_player().afk_turns += 1
            if self.turn_player().afk_turns == MAX_AFK_TURNS:
                kicked = self.turn_player().name
                self.turn_player().kicked = True

            # Terminación automática del turno
            update = self._end_turn()

            # Notificación de que ha terminado el turno automáticamente,
            # posiblemente con un usuario nuevo expulsado.
            self._turn_callback(update, kicked)

    def _start_turn_timer(self):
        """
        Reinicia el temporizador de pase de turno automático.
        """

        if self._turn_timer is not None:
            self._turn_timer.cancel()

        self._turn_timer = PausableTimer(TIME_TURN_END, self._timer_end_turn)
        self._turn_timer.start()

    def turn_player(self) -> Player:
        """
        Devuelve el nombre del usuario con el turno actual.
        """

        return self.players[self._turn]

    def _playtime_mins(self) -> int:
        """
        Devuelve el tiempo de juego de la partida.
        """

        elapsed = datetime.now() - self._start_time
        return int(elapsed.total_seconds() / 60)

    def _leaderboard(self) -> Dict:
        """
        Calcula los resultados de la partida hasta el momento, incluyendo las
        monedas obtenidas para cada jugador según la posición final, siguiendo
        la fórmula establecida:

          Sea N el número de jugadores de la partida, el jugador en puesto i
          ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo
          N * 10, y el último 0.
        """

        leaderboard = {}
        N = len(self.players)

        for player in self.players:
            # No entrará en el top si si ha abandonado la partida y o si es el
            # último jugador.
            if not player.has_finished() or player.kicked:
                continue

            leaderboard[player.name] = {
                "position": player.position,
                "coins": 10 * (N - player.position),
            }

        return leaderboard

    def player_finished(self, player: Player) -> None:
        """
        Finaliza la partida para un jugador en concreto.
        """

        if player.has_finished():
            raise GameLogicException("El jugador ya ha terminado")

        self._players_finished + 1
        player.position = self._players_finished

        logger.info(f"{player.name} has finished at position {player.position}")

    def finish(self) -> GameUpdate:
        """
        Finaliza el juego y devuelve un game_update.
        """

        logger.info("Game has finished")

        self._finished = True
        if self._turn_timer is not None:
            self._turn_timer.cancel()
        if self._paused_timer is not None:
            self._paused_timer.cancel()

        update = GameUpdate(self)
        update.repeat(
            {
                "finished": True,
                "leaderboard": self._leaderboard(),
                "playtime_mins": self._playtime_mins(),
            }
        )
        return update

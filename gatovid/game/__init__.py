"""
Implementación de la lógica del juego.
"""

import random
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.actions import Action, Discard
from gatovid.game.body import Body
from gatovid.game.cards import DECK, Card

# Exportamos GameLogicException
from gatovid.game.common import GameLogicException, GameUpdate
from gatovid.models import (
    BOT_PICTURE_ID,
    MAX_AFK_TURNS,
    MIN_HAND_CARDS,
    MIN_MATCH_USERS,
    User,
)
from gatovid.util import Timer, get_logger

logger = get_logger(__name__)

# Tiempo de espera hasta que se reanuda la partida si está pausada.
TIME_UNTIL_RESUME = 15
# Tiempo máximo del turno
TIME_TURN_END = 30


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
    is_ai: bool

    def __init__(self, name: str) -> None:
        self.name = name
        self.position = None
        self.hand = []
        self.body = Body()
        # Turnos consecutivos que el usuario ha estado AFK
        self.afk_turns = 0
        # Un jugador podrá ser reemplazado por la IA
        self.is_ai = False

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
        self._bots_num = 0

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

    def __del__(self) -> None:
        """
        Destructor que termina la partida si no se ha hecho ya anteriormente.
        """

        if not self._finished:
            self.finish()

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
        update.merge_with(self.current_turn_update())
        update.merge_with(self.hands_update())
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
                self._pause_timer = Timer(TIME_UNTIL_RESUME, resume_callback)
                self._pause_timer.start()

                logger.info(f"Game paused by {paused_by}")
            else:
                # Continúa el timer del turno
                self._turn_timer.resume()

                self._pause_timer.cancel()
                logger.info("Game resumed")

            self._paused = paused
            self._paused_by = paused_by
            return self.pause_update()

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
            try:
                update = action.apply(player, game=self)
            except GameLogicException as e:
                logger.info(f"Error running action: {e}")
                raise

            # TODO: revisar fin de partida
            if self._players_finished == len(self.players) - 1:
                finish_update = self.finish()
                update.merge_with(finish_update)

            if not self.discarding and not self._finished:
                end_update = self._end_turn()
                update.merge_with(end_update)

            # Se reestablecen los turnos AFK del usuario que ha terminado
            # correctamente la partida.
            player.afk_turns = 0

            return update

    def draw_card(self, player: Player) -> None:
        """
        Roba una carta del mazo para el jugador.
        """

        logger.info(f"{player.name} draws a card")

        drawn = self.deck.pop()
        player.hand.append(drawn)

    def _end_turn(self) -> GameUpdate:
        """
        Tiene en cuenta que si el jugador al que le toca el turno no tiene
        cartas en la mano, deberá ser skipeado. Antes de pasar el turno el
        jugador automáticamente robará cartas hasta tener 3.

        Es posible, por tanto, que el fin de turno modifique varias partes de la
        partida, incluyendo las manos, por lo que se devuelve un game_update
        completo.
        """

        update = GameUpdate(self)

        # Termina la fase de descarte si estaba activada
        self.discarding = False

        while True:
            # TODO: si el usuario está kickeado se le debería pasar el turno o
            # la IA debería jugar por él.

            logger.info(f"{self.turn_player().name}'s turn has ended")
            self._turn_number += 1

            # Roba cartas hasta tener las necesarias, se actualiza el estado de
            # ese jugador en concreto.
            while len(self.turn_player().hand) < MIN_HAND_CARDS:
                self.draw_card(self.turn_player())
            update.add(
                player_name=self.turn_player().name,
                value={"hand": self.turn_player().hand},
            )

            self._advance_turn()
            logger.info(f"{self.turn_player().name}'s turn has started")

            # Continúa pasando el turno si el jugador siguiente no tiene cartas
            # disponibles.
            if len(self.turn_player().hand) == 0:
                logger.info(f"{self.turn_player().name} skipped (no cards)")
                continue

            if self.turn_player().is_ai:
                # TODO: la IA debería jugar aquí, ya que se puede pasar su turno
                # automáticamente.
                continue

            break

        update.merge_with(self.current_turn_update())
        self._start_turn_timer()

        return update

    def _advance_turn(self):
        """
        Siguiente turno, y actualización del estado a todos los jugadores

        No se le pasará el turno a un jugador que ya ha terminado la partida.
        """

        while True:
            self._turn = (self._turn + 1) % len(self.players)
            if not self.turn_player().has_finished():
                break

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

            update = GameUpdate(self)

            self.turn_player().afk_turns += 1
            logger.info(
                f"Turn timeout for {self.turn_player().name}"
                f" ({self.turn_player().afk_turns} in a row)"
            )

            # Expulsión de jugadores AFK en caso de que esté activada la IA.
            kicked = None
            is_afk = self._enabled_ai and self.turn_player().afk_turns == MAX_AFK_TURNS
            if is_afk:
                kicked = self.turn_player().name
                logger.info(f"Player {kicked} is AFK")
                kick_update = self.remove_player(self.turn_player().name)
                update.merge_with(kick_update)

                # Si no quedan suficientes jugadores se acaba la partida.
                if self._finished:
                    self._turn_callback(None, None, True)
                    return
            else:
                # Al terminar un turno de forma automática se le tendrá que
                # descartar al jugador una carta de forma aleatoria, excepto
                # cuando esté en la fase de descarte.
                #
                # La carta ya se le robará de forma automática al terminar el
                # turno.
                if not self.discarding and len(self.turn_player().hand) > 0:
                    discarded = random.randint(0, len(self.turn_player().hand) - 1)
                    action = Discard(discarded)
                    discard_update = action.apply(self.turn_player(), game=self)
                    update.merge_with(discard_update)

            # Terminación automática del turno
            end_update = self._end_turn()
            update.merge_with(end_update)

            # Notificación de que ha terminado el turno automáticamente,
            # posiblemente con un usuario nuevo expulsado.
            self._turn_callback(update, kicked, False)

    def _start_turn_timer(self):
        """
        Reinicia el temporizador de pase de turno automático.
        """

        if self._turn_timer is not None:
            self._turn_timer.cancel()

        self._turn_timer = Timer(TIME_TURN_END, self._timer_end_turn)
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

    def remove_player(self, player_name: str) -> GameUpdate:
        """
        Elimina un jugador de la partida.

        Si está activada la IA el jugador es reemplazado por un bot, y en caso
        contrario se mueven sus cartas al inicio de la baraja y se elimina.

        El GameUpdate devuelto tendrá datos vacíos para el usuario que se ha
        eliminado para simplificar el problema.
        """

        update = GameUpdate(self)

        if self.is_finished():
            return update

        logger.info(f"Player {player_name} is being removed")
        player = self.get_player(player_name)

        if self._enabled_ai:
            player.is_ai = True
            self._bots_num += 1
        else:
            for card in player.hand:
                self.deck.insert(0, card)
            self.players.remove(player)

            # Si es su turno se pasa al siguiente
            if self.turn_player() == player:
                self._advance_turn()
                update.merge_with(self.current_turn_update())

        # Comprobando si quedan suficientes usuarios
        remaining = len(self.players)
        if self._enabled_ai:
            remaining -= self._bots_num
        if remaining < MIN_MATCH_USERS:
            finish_update = self.finish()
            update.merge_with(finish_update)

        update.merge_with(self.players_update())
        return update

    def player_finished(self, player: Player) -> None:
        """
        Finaliza la partida para un jugador en concreto.
        """

        if player.has_finished():
            raise GameLogicException("El jugador ya ha terminado")

        self._players_finished + 1
        player.position = self._players_finished

        logger.info(f"{player.name} has finished at position {player.position}")

    def players_update(self) -> GameUpdate:
        update = GameUpdate(self)

        players = []
        for player in self.players:
            data = {}

            if player.is_ai:
                data = {
                    "name": f"[BOT-{self._bots_num:02}]",
                    "picture": BOT_PICTURE_ID,
                    "is_ai": True,
                }
            else:
                data = {"name": player.name}

            players.append(data)

        update.repeat({"players": players})
        return update

    def hands_update(self) -> GameUpdate:
        update = GameUpdate(self)
        update.add_for_each(lambda player: {"hand": player.hand})
        return update

    def current_turn_update(self) -> GameUpdate:
        update = GameUpdate(self)
        update.repeat({"current_turn": self.turn_player().name})
        return update

    def finish_update(self) -> GameUpdate:
        update = GameUpdate(self)
        update.repeat(
            {
                "finished": True,
                "leaderboard": self._leaderboard(),
                "playtime_mins": self._playtime_mins(),
            }
        )
        return update

    def pause_update(self) -> GameUpdate:
        update = GameUpdate(self)
        update.repeat(
            {
                "paused": self._paused,
                "paused_by": self._paused_by,
            }
        )
        return update

    def bodies_update(self) -> GameUpdate:
        update = GameUpdate(self)
        update.add_for_each(lambda p: {"bodies": {p.name: p.body.piles}})
        return update

    def full_update(self) -> GameUpdate:
        update = GameUpdate(self)

        update.merge_with(self.bodies_update())
        update.merge_with(self.current_turn_update())
        update.merge_with(self.finish_update())
        update.merge_with(self.hands_update())
        update.merge_with(self.pause_update())
        update.merge_with(self.players_update())

        return update

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

        return self.finish_update()

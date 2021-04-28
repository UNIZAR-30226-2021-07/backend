"""
Implementación de la lógica del juego.
"""

import random
from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.actions import Action
from gatovid.game.body import Body
from gatovid.game.cards import DECK, Card

# Exportamos GameLogicException
from gatovid.game.common import GameLogicException
from gatovid.models import User
from gatovid.util import get_logger

logger = get_logger(__name__)


class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.position: Optional[int] = None
        self.hand: List[Card] = []
        self.body = Body()

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

    def __init__(self, users: List[User]) -> None:
        self.players = [Player(user.name) for user in users]
        self.deck: List[Card] = []
        self._turn = 0
        self._start_time = datetime.now()
        self._paused = False
        self._finished = False
        self._players_finished = 0
        # Indica la fase de descarte, en la que no se podrá hacer otra cosa
        # excepto seguir descartando o pasar el turno.
        self.discarding = False

        # TODO: Por el momento, se hace como que se juega y se termina la
        # partida.
        for i, player in enumerate(self.players):
            player.position = i + 1

    def start(self) -> Dict:
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

        # Genera el estado inicial con las manos y turno
        update = []
        for player in self.players:
            update.append({
                "hand": player.hand,
                "current_turn": self.turn_player().name,
            })

        return update

    def is_finished(self) -> bool:
        return self._finished

    def get_player(self, user_name: str) -> Player:
        for player in self.players:
            if player.name == user_name:
                return player

        raise GameLogicException("El jugador no está en la partida")

    def run_action(self, caller: str, action: Action) -> [Dict]:
        """
        Llamado ante cualquier acción de un jugador en la partida. Devolverá el
        nuevo estado de la partida por cada jugador, o en caso de que ya hubiera
        terminado anteriormente o estuviera pausada, un error.

        Se terminará el turno automáticamente en caso de que no haya quedado el
        usuario en fase de descarte.
        """

        if self._finished:
            raise GameLogicException("El juego ya ha terminado")

        if self._paused:
            raise GameLogicException("El juego está pausado")

        if self.players[self._turn].name != caller:
            raise GameLogicException("No es tu turno")

        player = self.get_player(caller)
        update = action.apply(player, game=self)

        if not self.discarding:
            end_update = self.end_turn()
            update = self._merge_updates(end_update, update)

        return update

    def draw_card(self, player: Player) -> None:
        """
        Roba una carta del mazo para el jugador.
        """

        logger.info(f"{player.name} draws a card")

        drawn = self.deck.pop()
        player.hand.append(drawn)

    def end_turn(self) -> [Dict]:
        """
        TODO: sistema de turnos

        Tiene en cuenta que si el jugador al que le toca el turno no tiene
        cartas en la mano, deberá ser skipeado. Antes de pasar el turno el
        jugador automáticamente robará cartas hasta tener 3.

        Es posible, por tanto, que el fin de turno modifique varias partes de la
        partida, incluyendo las manos, por lo que se devuelve un game_update
        completo.
        """

        update = [{}] * len(self.players)

        while True:
            # Roba cartas hasta tener 3, se actualiza el estado de ese jugador
            # en concreto.
            while len(self.turn_player().hand) < 3:
                self.draw_card(self.turn_player())
            for u, player in zip(update, self.players):
                if player == self.turn_player():
                    u["hand"] = self.turn_player().hand
                    break

            # Siguiente turno, y actualización del estado a todos los jugadores
            self._turn = (self._turn + 1) % len(self.players)
            new_turn = {"current_turn": self.turn_player().name}
            turn_update = [new_turn] * len(self.players)
            update = self._merge_updates(update, turn_update)

            logger.info("Current turn has ended")

            # Continúa pasando el turno si el jugador siguiente no tiene cartas
            # disponibles.
            if len(self.turn_player().hand) != 0:
                break
            logger.info(f"{self.turn_player().name} skipped (no cards)")

        return update

    def _merge_updates(self, update1: List[Dict], update2: List[Dict]) -> List[Dict]:
        """
        Mezcla dos game_update, donde `update2` tiene preferencia sobre
        `update1`.
        """

        nump = len(self.players)
        if len(update1) != nump or len(update2) != nump:
            raise Exception("Tamaños incompatibles mezclando game_updates")

        updates = []
        for u1, u2 in zip(update1, update2):
            updates.append({**u1, **u2})

        return updates

    def turn_player(self) -> Player:
        """
        Devuelve el nombre del usuario con el turno actual.
        """

        return self.players[self._turn]

    def _playtime_mins(self, game: "Game") -> int:
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
            if player.position is None:
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

    def finish(self, caller: Player) -> Dict:
        """
        Finaliza el juego y devuelve un game_update.
        """

        logger.info("Game has finished")

        self._finished = True

        update = {
            "finished": True,
            "leaderboard": self._leaderboard(),
            "playtime_mins": self._playtime_mins(),
        }
        return [update] * len(self.players)

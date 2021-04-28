"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict
from datetime import datetime

from gatovid.game.cards import DECK
from gatovid.game.common import GameLogicException

if TYPE_CHECKING:
    from gatovid.game import Game


class Action(ABC):
    @abstractmethod
    def apply(self, game: "Game") -> Dict:
        """"""


class StartGame(Action):
    """"""

    def apply(self, game: "Game") -> Dict:
        """
        Inicializa la baraja y reparte 3 cartas a cada jugador, iterando de
        forma similar a cómo se haría en la vida real.
        """

        game._deck = DECK.copy()

        for i in range(3):
            for player in game._players:
                drawn = game._deck.pop()
                player.hand.append(drawn)

        update = [player.hand for player in game._players]
        return update


class EndGame(Action):
    """"""

    def _playtime_mins(self, game: "Game") -> int:
        """
        Devuelve el tiempo de juego de la partida.
        """

        elapsed = datetime.now() - game._start_time
        return int(elapsed.total_seconds() / 60)

    def _leaderboard(self, game: "Game") -> Dict:
        """
        Calcula los resultados de la partida hasta el momento, incluyendo las
        monedas obtenidas para cada jugador según la posición final, siguiendo
        la fórmula establecida:

          Sea N el número de jugadores de la partida, el jugador en puesto i
          ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo
          N * 10, y el último 0.
        """

        leaderboard = {}
        N = len(self._players)

        for player in self._players:
            if player.position is None:
                continue

            leaderboard[player.name] = {
                "position": player.position,
                "coins": 10 * (N - player.position),
            }

        return leaderboard

    def apply(self, game: "Game") -> Dict:
        """"""
        game.end_turn()

        return {
            "finished": True,
            "leaderboard": self._leaderboard(game),
            "playtime_mins": self._playtime_mins(game),
        }


class Pass(Action):
    """"""

    def apply(self, game: "Game") -> Dict:
        """"""
        game.end_turn()


class Discard(Action):
    """"""

    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos descartar.
        self.slot = data.get("slot")

    def apply(self, game: "Game") -> Dict:
        """"""


class PlayCard(Action):
    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos jugar.
        self.slot = data.get("slot")
        # Todos los datos pasados por el usuario
        self.data = data

        if self.slot is None:
            raise GameLogicException("Slot vacío")

    def apply(self, caller: str, game: "Game") -> Dict:
        """"""
        player = game.get_player(caller)
        card = player.get_card(self.slot)
        return card.apply(self, game)
        # TODO: quitar carta de la mano

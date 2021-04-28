"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

from gatovid.game.cards import DECK
from gatovid.game.common import GameLogicException

if TYPE_CHECKING:
    from gatovid.game import Game, Player


class Action(ABC):
    """
    Clase base para implementar el patrón Command. Las interacciones con el
    juego toman lugar como "acciones", que modifican el estado del juego y
    devuelven un diccionario con los cambios realizados.

    Dependiendo de la acción ésta podrá ser llevada a cabo por un jugador o no.
    """

    @abstractmethod
    def apply(self, caller: Optional["Player"], game: "Game") -> Dict:
        """ """


class StartGame(Action):
    """ """

    def apply(self, caller: Optional["Player"], game: "Game") -> Dict:
        """
        Inicializa la baraja y reparte 3 cartas a cada jugador, iterando de
        forma similar a cómo se haría en la vida real.
        """

        game._deck = DECK.copy()

        for i in range(3):
            for player in game._players:
                drawn = game._deck.pop()
                player.hand.append(drawn)

        update = [{"hand": player.hand} for player in game._players]
        return update


class EndGame(Action):
    """ """

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

    def apply(self, caller: Optional["Player"], game: "Game") -> Dict:
        """ """

        game.end_turn()

        update = {
            "finished": True,
            "leaderboard": self._leaderboard(game),
            "playtime_mins": self._playtime_mins(game),
        }
        return [update] * len(game._players)


class Pass(Action):
    """ """

    def apply(self, caller: Optional["Player"], game: "Game") -> Dict:
        """ """

        game.end_turn()

        return {"current_turn": game.turn_name()}


class Discard(Action):
    """ """

    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos descartar.
        self.slot = data.get("slot")

    def apply(self, caller: Optional["Player"], game: "Game") -> Dict:
        """ """


class PlayCard(Action):
    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos jugar.
        self.slot = data.get("slot")
        # Todos los datos pasados por el usuario
        self.data = data

        if self.slot is None:
            raise GameLogicException("Slot vacío")

    def apply(self, caller: Optional["Player"], game: "Game") -> Dict:
        """ """

        card = caller.get_card(self.slot)
        return card.apply(self, game)
        # TODO: quitar carta de la mano

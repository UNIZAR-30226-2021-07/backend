"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

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
            for player in self._players:
                drawn = self._deck.pop()
                player.hand.append(drawn)


class EndGame(Action):
    """"""

    def apply(self, game: "Game") -> Dict:
        """"""
        game.end_turn()


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

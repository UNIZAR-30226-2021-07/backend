"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gatovid.game import Game

class Action:
    @abstractmethod
    def apply(self, game: "Game") -> None:
        """"""

class Pass(Action):
    """"""

    def apply(self, game: "Game") -> None:
        """"""
        game.end_turn()


class Discard(Action):
    """"""

    def __init__(self, data) -> None:
        # TODO: pillar slots
        self.cards = cards

    def apply(self, game: "Game") -> None:
        """"""


class PlayCard(Action):
    def apply(self, game: "Game") -> None:
        """"""
        card = player.get_card(slot)
        card.action(data)

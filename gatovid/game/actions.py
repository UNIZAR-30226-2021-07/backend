"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from gatovid.game.common import GameLogicException
from typing import TYPE_CHECKING, List
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from gatovid.game import Game

class Action(ABC):
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
    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos jugar.
        self.slot = data.get("slot")
        # Todos los datos pasados por el usuario
        self.data = data

        if self.slot is None:
            raise GameLogicException("Slot vacío")
        
    def apply(self, caller: str, game: "Game") -> None:
        """"""
        player = game.get_player(caller)
        card = player.get_card(slot)
        card.apply(self, game)

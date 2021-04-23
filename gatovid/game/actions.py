"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from gatovid.game.common import GameLogicException

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
        # Slot de la mano con la carta que queremos descartar.
        self.slot = data.get("slot")

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
        card = player.get_card(self.slot)
        card.apply(self, game)

"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

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
    def apply(self, caller: "Player", game: "Game") -> Dict:
        """ """


class Pass(Action):
    """ """

    def apply(self, caller: "Player", game: "Game") -> Dict:
        """ """

        game.end_turn()

        return {"current_turn": game.turn_name()}


class Discard(Action):
    """ """

    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos descartar.
        self.slots = data.get("slots")

    def apply(self, caller: "Player", game: "Game") -> Dict:
        """
        Descarta una o más cartas
        """


class PlayCard(Action):
    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos jugar.
        self.slot = data.get("slot")
        # Todos los datos pasados por el usuario
        self.data = data

        if self.slot is None:
            raise GameLogicException("Slot vacío")

    def apply(self, caller: "Player", game: "Game") -> Dict:
        """
        Juega una carta, siguiendo el orden de las reglas del juego.
        """

        # Obtiene la carta y la elimina de su mano
        card = caller.get_card(self.slot)
        caller.remove_card(self.slot)

        # Usa la carta
        update = card.apply(self, game)

        # Pasa el turno
        new_card = game.draw_card()
        caller.add_card(new_card)

        return {
            **update,
            "current_turn": game.turn_name()
        }

"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict

from gatovid.game.common import GameLogicException
from gatovid.util import get_logger

if TYPE_CHECKING:
    from gatovid.game import Game, Player


logger = get_logger(__name__)


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
    """
    Únicamente se pasará el turno para indicar que el usuario ha dejado de
    descartarse cartas. En el resto de los casos el proceso es automático.

    Por tanto, esta acción se limita a desactivar la fase de descarte, y ya se
    pasará el turno automáticamente en el juego.
    """

    def apply(self, caller: "Player", game: "Game") -> Dict:
        logger.info(f"{caller.name} stops discarding cards")

        game._discarding = False


class Discard(Action):
    """
    Descarta una única carta.
    """

    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos descartar.
        self.slot = data.get("slot")

    def apply(self, caller: "Player", game: "Game") -> Dict:
        logger.info(f"{caller.name} discards a card")

        # Activa la fase de descarte
        game._discarding = True

        # Elimina la carta de la mano del jugador y la añade al principio del
        # mazo.
        card = caller.hand[self.slot]
        del caller.hand[self.slot]
        game._deck.insert(0, card)

        update = [{}] * len(self._players)
        for u, player in zip(update, self._players):
            if player == self.turn_player():
                u["hand"] = self.turn_player().hand
                break

        return update


class PlayCard(Action):
    """
    Juega una carta, siguiendo el orden de las reglas del juego. La
    implementación se delegará a la carta en específico que se esté jugando,
    definido en las subclases de SimpleCard.
    """

    def __init__(self, data) -> None:
        # Slot de la mano con la carta que queremos jugar.
        self.slot = data.get("slot")
        # Todos los datos pasados por el usuario
        self.data = data

        if self.slot is None:
            raise GameLogicException("Slot vacío")

    def apply(self, caller: "Player", game: "Game") -> Dict:
        logger.info(f"{caller.name} plays a card")

        # No podrá jugar una carta si el mismo jugador está en proceso de
        # descarte.
        if game._discarding:
            raise GameLogicException("El jugador está en proceso de descarte")

        # Obtiene la carta y la elimina de su mano. No hace falta actualizar el
        # estado al eliminar la carta porque ya se hará cuando robe al final del
        # turno.
        card = caller.hand[self.slot]
        del caller.hand[self.slot]

        # Usa la carta
        update = card.apply(self, game)
        return update

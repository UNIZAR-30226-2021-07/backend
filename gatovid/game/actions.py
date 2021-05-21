"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from gatovid.game.common import GameLogicException, GameUpdate
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
    def apply(self, caller: "Player", game: "Game") -> (GameUpdate, Optional[str]):
        pass


class Pass(Action):
    """
    Únicamente se pasará el turno para indicar que el usuario ha dejado de
    descartarse cartas. En el resto de los casos el proceso es automático.

    Por tanto, esta acción se limita a desactivar la fase de descarte, y ya se
    pasará el turno automáticamente en el juego.
    """

    def apply(self, caller: "Player", game: "Game") -> (GameUpdate, Optional[str]):
        if not game.discarding:
            raise GameLogicException("El jugador no está en la fase de descarte")

        logger.info(f"{caller.name} stops discarding cards")

        game.discarding = False

        return GameUpdate(game), "un descarte"


class Discard(Action):
    """
    Descarta una única carta.
    """

    def __init__(self, position: int) -> None:
        self.position = position

    def apply(self, caller: "Player", game: "Game") -> (GameUpdate, Optional[str]):
        logger.info(f"{caller.name} discards their card at position {self.position}")

        # Activa la fase de descarte
        game.discarding = True

        if len(caller.hand) == 0:
            raise GameLogicException("El jugador no tiene cartas")

        # Elimina la carta de la mano del jugador y la añade al principio del
        # mazo, como indican las reglas del juego.
        caller.remove_card(self.position, return_to=game.deck)

        update = GameUpdate(game)
        update.add(caller.name, {"hand": caller.hand})
        # Ya se mostrará el mensaje al pasar de turno de forma condensada.
        return update, None


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
        # El jugador que usa la carta
        self.caller: "Player" = None

        if self.slot is None:
            raise GameLogicException("Slot vacío")

    def apply(self, caller: "Player", game: "Game") -> (GameUpdate, Optional[str]):
        logger.info(f"{caller.name} plays a card")

        # No podrá jugar una carta si el mismo jugador está en proceso de
        # descarte.
        if game.discarding:
            raise GameLogicException("El jugador está en proceso de descarte")

        self.caller = caller

        # Obtiene la carta y la elimina de su mano. No hace falta actualizar el
        # estado al eliminar la carta porque ya se hará cuando robe al final del
        # turno.
        card = caller.get_card(self.slot)

        # NOTE: no hay ninguna carta que intercambie manos de jugadores, en ese
        # caso habría que guardar el estado completo de la mano anterior y
        # borrar la carta (para que cuando se intercambiase no hubiera
        # problemas) y, en caso de fallo, restaurarla.

        # Usa la carta
        update, msg = card.apply(self, game)

        # Solo si hemos podido "aplicar" el comportamiento de la carta, la
        # quitaremos de la mano.
        if card.is_placeable():
            # No devolvemos la carta a la baraja (está puesta en un cuerpo).
            caller.remove_card(self.slot)
        else:
            caller.remove_card(self.slot, return_to=game.deck)
        return update, msg

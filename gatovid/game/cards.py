from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List
from gatovid.game.common import GameLogicException

if TYPE_CHECKING:
    from gatovid.game import Game
    from gatovid.game.actions import PlayCard


class Color(Enum):
    Red = "red"
    Green = "green"
    Blue = "blue"
    Yellow = "yellow"
    Any = "any"


@dataclass
class Card():
    pass

@dataclass
class SimpleCard(Card):
    """
    Clase genérica para órganos, virus y medicinas. Estos tres tienen
    un comportamiento similar, ya que actúan solo sobre una pila de
    cartas (en el cuerpo de un jugador).
    """

    color: Color

    def get_action_data(self, action: PlayCard, game: Game) -> None:
        """
        Extraer la información común para las cartas simples y
        realizar las comprobaciones correspondientes.
        """

        # Jugador donde queremos colocar la carta (en su cuerpo).
        target_name = action.data.get("target")
        # Pila de órgano donde se va a colocar la carta (dentro de dicho cuerpo).
        organ_pile_slot = action.data.get("organ_pile")

        if None in [self.target, self.organ_pile]:
            raise GameLogicException("Parámetro vacío")

        self.target = game.get_player(target_name)
        self.organ_pile = self.target.body.get_pile(organ_pile_slot)

        # Comprobamos si podemos colocar
        if not self.organ_pile.can_place(self):
            raise GameLogicException("No se puede colocar la carta ahí")

@dataclass
class Organ(SimpleCard):
    """"""
    pass

@dataclass
class Virus(SimpleCard):
    """"""
    pass


@dataclass
class Medicine(SimpleCard):
    """"""
    pass

@dataclass
class Treatment(Card):
    """
    Clase abstracta que contiene las cartas especiales (cartas de
    tratamiento). Estas realizan acciones muy variadas.
    """
    pass

@dataclass
class Transplant(Treatment):
    """"""
    pass

@dataclass
class OrganThief(Treatment):
    """"""
    pass


@dataclass
class Infection(Treatment):
    """"""
    pass

@dataclass
class LatexGlove(Treatment):
    """"""
    pass

@dataclass
class MedicalError(Treatment):
    """"""

    def __init__(self) -> None:
        super().__init__()


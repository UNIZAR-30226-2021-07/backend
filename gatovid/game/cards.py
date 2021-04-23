from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gatovid.game import Game


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
    Clase abstracta para órganos, virus y medicinas. Estos tres tienen
    un comportamiento similar, ya que actúan solo sobre una pila de
    cartas (en el cuerpo de un jugador).
    """
    color: Color


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


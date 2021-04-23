from abc import ABC, abstractmethod
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


class Action(ABC):
    def __init__(self) -> None:
        """"""

    @abstractmethod
    def apply(self, game: "Game") -> None:
        """"""


class Card(Action):
    """"""

    def __init__(self) -> None:
        """"""


class SimpleCard(Card):
    """
    Clase abstracta para órganos, virus y medicinas. Estos tres tienen
    un comportamiento similar, ya que actúan solo sobre una pila de
    cartas (en el cuerpo de un jugador).
    """

    def __init__(self, color: Color) -> None:
        self.color = color


class Organ(SimpleCard):
    """"""

    def __init__(self, color: Color) -> None:
        super().__init__(color)


class Virus(SimpleCard):
    """"""

    def __init__(self, color: Color) -> None:
        super().__init__(color)


class Medicine(SimpleCard):
    """"""

    def __init__(self, color: Color) -> None:
        super().__init__(color)


class Treatment(Card):
    """
    Clase abstracta que contiene las cartas especiales (cartas de
    tratamiento). Estas realizan acciones muy variadas.
    """

    def __init__(self) -> None:
        super().__init__()


class Transplant(Treatment):
    """"""

    def __init__(self) -> None:
        super().__init__()


class OrganThief(Treatment):
    """"""

    def __init__(self) -> None:
        super().__init__()


class Infection(Treatment):
    """"""

    def __init__(self) -> None:
        super().__init__()


class LatexGlove(Treatment):
    """"""

    def __init__(self) -> None:
        super().__init__()


class MedicalError(Treatment):
    """"""

    def __init__(self) -> None:
        super().__init__()


class Pass(Action):
    """"""

    def apply(self, game: "Game") -> None:
        """"""


class Draw(Action):
    """"""

    def apply(self, game: "Game") -> None:
        """"""


class Discard(Action):
    """"""

    def __init__(self, cards: List[Card]) -> None:
        self.cards = cards

    def apply(self, game: "Game") -> None:
        """"""

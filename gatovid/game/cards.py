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


class Action(ABC):
    def __init__(self) -> None:
        """"""

    @abstractmethod
    def apply(self, game: "Game") -> None:
        """"""


class Card(Action):
    """"""

    def __init__(self, id: int) -> None:
        self.id = id


class Organ(Card):
    """"""

    def __init__(self, id: int, color: Color) -> None:
        super().__init__(id)
        self.color = color


class Virus(Card):
    """"""

    def __init__(self, id: int, color: Color) -> None:
        super().__init__(id)
        self.color = color


class Medicine(Card):
    """"""

    def __init__(self, id: int, color: Color) -> None:
        super().__init__(id)
        self.color = color


class Treatment(Card):
    """"""

    def __init__(self, id: int) -> None:
        super().__init__(id)


class Transplant(Treatment):
    """"""

    def __init__(self, id: int) -> None:
        super().__init__(id)


class OrganThief(Treatment):
    """"""

    def __init__(self, id: int) -> None:
        super().__init__(id)


class Infection(Treatment):
    """"""

    def __init__(self, id: int) -> None:
        super().__init__(id)


class LatexGlove(Treatment):
    """"""

    def __init__(self, id: int) -> None:
        super().__init__(id)


class MedicalError(Treatment):
    """"""

    def __init__(self, id: int) -> None:
        super().__init__(id)


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

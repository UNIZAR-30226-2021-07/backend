from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from gatovid.game.common import GameLogicException

if TYPE_CHECKING:
    from gatovid.game import Game
    from gatovid.game.actions import PlayCard


class Color(str, Enum):
    Red = "red"
    Green = "green"
    Blue = "blue"
    Yellow = "yellow"
    Any = "any"


@dataclass
class Card:
    pass


@dataclass
class SimpleCard(Card):
    """
    Clase genérica para órganos, virus y medicinas. Estos tres tienen
    un comportamiento similar, ya que actúan solo sobre una pila de
    cartas (en el cuerpo de un jugador).
    """

    color: Color

    def get_action_data(self, action: "PlayCard", game: "Game") -> None:
        """
        Extraer la información común para las cartas simples y
        realizar las comprobaciones correspondientes.
        """

        # Jugador donde queremos colocar la carta (en su cuerpo).
        target_name = action.data.get("target")
        # Pila de órgano donde se va a colocar la carta (dentro de dicho cuerpo).
        organ_pile_slot = action.data.get("organ_pile")

        if None in (target_name, organ_pile_slot):
            raise GameLogicException("Parámetro vacío")

        if organ_pile_slot < 0 or organ_pile_slot > 3:
            raise GameLogicException("Slot inválido")

        self.target = game.get_player(target_name)
        self.organ_pile = self.target.body.get_pile(organ_pile_slot)

        if self.target is None:
            raise GameLogicException("El jugador no existe")

        # Comprobamos si podemos colocar
        if not self.organ_pile.can_place(self):
            raise GameLogicException("No se puede colocar la carta ahí")


@dataclass
class Organ(SimpleCard):
    """"""

    # Usado para la codificación JSON
    card_type: str = "organ"

    def apply(self, action: "PlayCard", game: "Game") -> None:
        self.get_action_data(action, game)

        self.organ_pile.set_organ(self)


@dataclass
class Virus(SimpleCard):
    """"""

    # Usado para la codificación JSON
    card_type: str = "virus"

    def apply(self, action: "PlayCard", game: "Game") -> None:
        super().get_action_data(action, game)

        # Comprobamos si hay que extirpar o destruir vacuna
        if self.organ_pile.is_infected():
            # Si está infectado -> se extirpa el órgano
            self.organ_pile.remove_organ()
        elif self.organ_pile.is_protected():
            # Si está protegido -> se destruye la vacuna
            self.organ_pile.pop_modifiers()
        else:  # Se infecta el órgano (se añade el virus a los modificadores)
            self.organ_pile.add_modifier(self)


@dataclass
class Medicine(SimpleCard):
    """"""

    # Usado para la codificación JSON
    card_type: str = "medicine"

    def apply(self, action: "PlayCard", game: "Game") -> None:
        super().get_action_data(action, game)

        # Comprobamos si hay que destruir un virus
        if self.organ_pile.is_infected():
            self.organ_pile.pop_modifiers()
        else:
            # Se proteje o se inmuniza el órgano (se añade la vacuna a los
            # modificadores)
            self.organ_pile.add_modifier(self)


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

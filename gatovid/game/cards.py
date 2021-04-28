from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from gatovid.game.common import GameLogicException
from gatovid.models import CARDS

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

    color: Optional[Color]

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

        self.target = game.get_player(target_name)
        self.organ_pile = self.target.body.get_pile(organ_pile_slot)

        # Comprobamos si podemos colocar
        if not self.organ_pile.can_place(self):
            raise GameLogicException("No se puede colocar la carta ahí")


@dataclass
class Organ(SimpleCard):
    """ """

    # Usado para la codificación JSON
    card_type: str = "organ"

    def apply(self, action: "PlayCard", game: "Game") -> Dict:
        self.get_action_data(action, game)

        self.organ_pile.set_organ(self)

        update = {
            "bodies": {
                self.target.name: {
                    "organ": self
                }
            }
        }
        return [update] * len(game._players)


@dataclass
class Virus(SimpleCard):
    """ """

    # Usado para la codificación JSON
    card_type: str = "virus"

    def apply(self, action: "PlayCard", game: "Game") -> Dict:
        self.get_action_data(action, game)

        # Comprobamos si hay que extirpar o destruir vacuna
        if self.organ_pile.is_infected():
            # Si está infectado -> se extirpa el órgano
            self.organ_pile.remove_organ()
        elif self.organ_pile.is_protected():
            # Si está protegido -> se destruye la vacuna
            self.organ_pile.pop_modifiers()
        else:  # Se infecta el órgano (se añade el virus a los modificadores)
            self.organ_pile.add_modifier(self)

        update = {
            "bodies": {
                self.target.name: {
                    "modifiers": self.organ_pile.modifiers
                }
            }
        }
        return [update] * len(game._players)


@dataclass
class Medicine(SimpleCard):
    """ """

    # Usado para la codificación JSON
    card_type: str = "medicine"

    def apply(self, action: "PlayCard", game: "Game") -> Dict:
        self.get_action_data(action, game)

        # Comprobamos si hay que destruir un virus
        if self.organ_pile.is_infected():
            self.organ_pile.pop_modifiers()
        else:
            # Se proteje o se inmuniza el órgano (se añade la vacuna a los
            # modificadores)
            self.organ_pile.add_modifier(self)

        update = {
            "bodies": {
                self.target.name: {
                    "modifiers": self.organ_pile.modifiers
                }
            }
        }
        return [update] * len(game._players)


@dataclass
class Treatment(Card):
    """
    Clase abstracta que contiene las cartas especiales (cartas de
    tratamiento). Estas realizan acciones muy variadas.
    """

    # Usado para la codificación JSON
    card_type: str = "treatment"

    pass


@dataclass
class Transplant(Treatment):
    """ """

    pass


@dataclass
class OrganThief(Treatment):
    """ """

    pass


@dataclass
class Infection(Treatment):
    """ """

    pass


@dataclass
class LatexGlove(Treatment):
    """ """

    pass


@dataclass
class MedicalError(Treatment):
    """ """


def parse_card(data: Dict) -> (object, Dict):
    """
    Devuelve los datos necesarios para la inicialización de una carta de los
    datos JSON.
    """

    # En el caso de cartas simples solo se necesita el color
    simple_cards = {
        "organ": Organ,
        "medicine": Medicine,
        "virus": Virus,
    }
    cls = simple_cards.get(data["type"])
    if cls is not None:
        return cls, {"color": data["color"]}

    # Si no es una carta simple es un tratamiento, que no tiene color
    treatment_cards = {
        "latex_glove": LatexGlove,
        "organ_thief": OrganThief,
        "infection": Infection,
        "medical_error": MedicalError,
        "transplant": Transplant,
    }
    cls = treatment_cards.get(data["treatment_type"])
    if cls is not None:
        return cls, {}

    raise GameLogicException(f"Couldn't parse card with data {data}")


def parse_deck(all_cards: List[Dict]) -> [SimpleCard]:
    """
    Incializa el mazo base con la información en el JSON de cartas.
    """

    deck = []

    for data in all_cards:
        cls, kwargs = parse_card(data)
        for i in range(data["total"]):
            card = cls(**kwargs)
            deck.append(card)

    return deck


DECK = parse_deck(CARDS)

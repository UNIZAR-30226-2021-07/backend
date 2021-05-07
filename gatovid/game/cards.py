from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from gatovid.game.common import GameLogicException, GameUpdate
from gatovid.models import CARDS
from gatovid.util import get_logger

if TYPE_CHECKING:
    from gatovid.game import Game
    from gatovid.game.actions import PlayCard


logger = get_logger(__name__)


class Color(str, Enum):
    Red = "red"
    Green = "green"
    Blue = "blue"
    Yellow = "yellow"
    All = "all"


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

    def piles_update(self, game: "Game") -> GameUpdate:
        """
        Genera un diccionario indicando cambios a la pila del target.
        """

        update = GameUpdate(game)
        update.repeat({"bodies": {self.target.name: self.target.body.piles}})
        return update


@dataclass
class Organ(SimpleCard):
    """
    Coloca un órgano para un jugador.

    TODO: es en este punto en el que se decide si un usuario ha ganado (cuando
    tiene uno de cada). Cuando hayan más tests hechos, llamar a player_finished.
    """

    # Usado para la codificación JSON
    card_type: str = "organ"

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        if self.target.name != action.caller.name:
            raise GameLogicException("No puedes colocar un órgano en otro cuerpo")

        logger.info(f"{self.color}-colored organ played over {self.target.name}")

        self.organ_pile.set_organ(self)

        return self.piles_update(game)


@dataclass
class Virus(SimpleCard):
    """ """

    # Usado para la codificación JSON
    card_type: str = "virus"

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        if self.target.name == action.caller.name:
            raise GameLogicException("No puedes colocar un virus en tu cuerpo")

        logger.info(f"{self.color}-colored virus played over {self.target.name}")

        # Comprobamos si hay que extirpar o destruir vacuna
        if self.organ_pile.is_infected():
            # Si está infectado -> se extirpa el órgano
            self.organ_pile.remove_organ()
        elif self.organ_pile.is_protected():
            # Si está protegido -> se destruye la vacuna
            self.organ_pile.pop_modifiers()
        else:  # Se infecta el órgano (se añade el virus a los modificadores)
            self.organ_pile.add_modifier(self)

        return self.piles_update(game)


@dataclass
class Medicine(SimpleCard):
    """ """

    # Usado para la codificación JSON
    card_type: str = "medicine"

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        if self.target.name != action.caller.name:
            raise GameLogicException("No puedes colocar una medicina en otro cuerpo")

        logger.info(f"{self.color}-colored medicine played over {self.target.name}")

        # Comprobamos si hay que destruir un virus
        if self.organ_pile.is_infected():
            self.organ_pile.pop_modifiers()
        else:
            # Se proteje o se inmuniza el órgano (se añade la vacuna a los
            # modificadores)
            self.organ_pile.add_modifier(self)

        return self.piles_update(game)


@dataclass
class Treatment(Card):
    """
    Clase abstracta que contiene las cartas especiales (cartas de
    tratamiento). Estas realizan acciones muy variadas.
    """

    # Usado para la codificación JSON
    card_type: str = "treatment"
    treatment_type: str = ""


@dataclass
class Transplant(Treatment):
    """ """

    treatment_type: str = "transplant"

    pass


@dataclass
class OrganThief(Treatment):
    """ """

    treatment_type: str = "organ_thief"

    pass


@dataclass
class Infection(Treatment):
    """ """

    treatment_type: str = "infection"

    pass


@dataclass
class LatexGlove(Treatment):
    """
    Todos los jugadores, excepto el que utiliza el guante, descartan su mano. Al
    comienzo de su siguiente turno, al no tener cartas, estos jugadores tan solo
    podrán robar una nueva mano, perdiendo así un turno de juego.
    """

    treatment_type: str = "latex_glove"

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        logger.info("latex-glove played")

        update = GameUpdate(game)

        for player in game.players:
            if player == action.caller:
                continue

            # Vaciamos la mano del oponente
            player.hand = []
            # Añadimos la mano vacía al GameUpdate
            update.add(player.name, {"hand": []})

        return update


@dataclass
class MedicalError(Treatment):
    """ """

    treatment_type: str = "medical_error"


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
    Incializa el mazo base con la información en el JSON de cartas, cada uno con
    una instancia distinta.
    """

    logger.info("Parsing deck JSON")

    deck = []

    for data in all_cards:
        cls, kwargs = parse_card(data)
        for i in range(data["total"]):
            card = cls(**kwargs)
            deck.append(card)

    return deck


DECK = parse_deck(CARDS)

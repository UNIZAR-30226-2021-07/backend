import random
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
    def is_placeable(self) -> bool:
        return False


@dataclass
class SimpleCard(Card):
    """
    Clase genérica para órganos, virus y medicinas. Estos tres tienen
    un comportamiento similar, ya que actúan solo sobre una pila de
    cartas (en el cuerpo de un jugador).
    """

    color: Optional[Color]

    def is_placeable(self) -> bool:
        return True

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
    """

    # Usado para la codificación JSON
    card_type: str = "organ"

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        if self.target.name != action.caller.name:
            raise GameLogicException("No puedes colocar un órgano en otro cuerpo")

        if not self.target.body.organ_unique(self):
            raise GameLogicException("No puedes colocar un órgano repetido")

        logger.info(f"{self.color}-colored organ played over {self.target.name}")

        self.organ_pile.set_organ(self)

        update = self.piles_update(game)

        # Comprobamos si ha ganado
        if action.caller.body.is_healthy():
            # Si tiene un cuerpo completo sano, se considera que ha ganado.
            finished_update = game.player_finished(action.caller)
            update.merge_with(finished_update)

        return update


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
            # Lo añadimos para que vuelva a la baraja
            self.organ_pile.add_modifier(self)
            # Si está infectado -> se extirpa el órgano
            self.organ_pile.remove_organ(return_to=game.deck)
        elif self.organ_pile.is_protected():
            # Lo añadimos para que vuelva a la baraja
            self.organ_pile.add_modifier(self)
            # Si está protegido -> se destruye la vacuna
            self.organ_pile.pop_modifiers(return_to=game.deck)
        else:
            # Se infecta el órgano (se añade el virus a los modificadores)
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
            # Lo añadimos para que vuelva a la baraja
            self.organ_pile.add_modifier(self)
            # Destruimos el virus
            self.organ_pile.pop_modifiers(return_to=game.deck)
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
    """
    Intercambia un órgano por otro entre dos jugadores cualesquiera.  No importa
    si el color de estos órganos es diferente, ni si están sanos, infectados o
    vacunados. Sencillamente el jugador cambia el órgano escogido por otro,
    siempre y cuando ninguno de los dos jugadores tenga dos órganos del mismo
    color ni éstos estén inmunizados.
    """

    treatment_type: str = "transplant"

    def get_action_data(self, action: "PlayCard", game: "Game") -> None:
        """ """
        # Jugadores entre los que queremos
        player1 = action.data.get("player1")
        player2 = action.data.get("player2")

        # Pilas de los jugadores a intercambiar
        pile_slot1 = action.data.get("pile_slot1")
        pile_slot2 = action.data.get("pile_slot2")

        if None in (self.player1, self.player2, self.pile_slot1, self.pile_slot2):
            raise GameLogicException("Parámetro vacío")

        self.player1 = game.get_player(player1)
        self.player2 = game.get_player(player2)

        self.organ_pile1 = self.player1.body.get_pile(pile_slot1)
        self.organ_pile2 = self.player2.body.get_pile(pile_slot2)

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        logger.info("transplant played")





@dataclass
class OrganThief(Treatment):
    """ """

    treatment_type: str = "organ_thief"

    pass


@dataclass
class Infection(Treatment):
    """
    Traslada tantos virus como puedas de tus órganos infectados a los órganos de
    los demás jugadores. No puedes utilizar el contagio sobre órganos vacunados
    o infectados, sólo podrás contagiar órganos libres.
    """

    treatment_type: str = "infection"

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        logger.info("infection played")

        # Diccionario: color -> lista de pilas con virus de ese color
        virus = dict()
        for color in Color:
            virus[color] = []

        # Listamos los virus que tiene en el cuerpo accediendo en orden
        # aleatorio a las pilas.
        for pile in random.sample(action.caller.body.piles, 4):
            if pile.is_infected():
                color = pile.get_top_color()
                virus[color].append(pile)

        # Lista de pilas libres de todos los jugadores
        candidates = []

        # Accederemos a los jugadores en orden aleatorio
        for player in random.sample(game.players, len(game.players)):
            # Eliminamos al caller de la iteracion
            if player == action.caller:
                continue

            # Añadimos las pilas libres a la lista de candidatas
            candidates.extend(list(filter(lambda p: p.is_free(), player.body.piles)))

        # Aplicamos un orden aleatorio también a las pilas candidatas
        for candidate_pile in random.sample(candidates, len(candidates)):
            color = candidate_pile.get_top_color()

            # Asignamos el primer virus de ese color y lo quitamos de los
            # posibles.

            if len(virus[color]) == 0:
                # Si no hay virus de ese color -> comprobamos si hay virus
                # multicolor
                if len(virus[Color.All]) > 0:
                    color = Color.All
                else:  # No tenemos opción
                    continue

            pile = virus[color].pop()
            # Eliminamos el virus del cuerpo del caller
            pile.pop_modifiers()
            # Lo colocamos en la pila candidata
            candidate_pile.add_modifier(Virus(color=color))

        # Por simplificar, devolvemos el cuerpo de todos los jugadores
        update = GameUpdate(game)
        for player in game.players:
            body_update = GameUpdate(game)
            body_update.repeat({"bodies": {player.name: player.body.piles}})
            update.merge_with(body_update)

        return update


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
            player.empty_hand(return_to=game.deck)
            # Añadimos la mano vacía al GameUpdate
            update.add(player.name, {"hand": []})

        return update


@dataclass
class MedicalError(Treatment):
    """
    Intercambia todo tu cuerpo por el de otro jugador, incluyendo órganos, virus
    y vacunas. No importa el número de cartas que cada uno tenga en la mesa.
    Cuando usas esta carta, los órganos inmunizados también son intercambiados.
    """

    treatment_type: str = "medical_error"

    def get_action_data(self, action: "PlayCard", game: "Game") -> None:
        # Jugador con el que queremos intercambiar el cuerpo
        self.target_name = action.data.get("target")
        if self.target_name in (None, ""):
            raise GameLogicException("Parámetro target vacío")

        self.target = game.get_player(self.target_name)

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        logger.info("medical-error played")

        update = GameUpdate(game)

        # Intercambiamos los cuerpos de ambos jugadores
        action.caller.body, self.target.body = self.target.body, action.caller.body
        # Añadimos los dos cuerpos al GameUpdate
        update.repeat(
            {
                "bodies": {
                    self.target.name: self.target.body.piles,
                    action.caller.name: action.caller.body.piles,
                },
            }
        )

        return update


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


def parse_deck(all_cards: List[Dict]) -> [Card]:
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

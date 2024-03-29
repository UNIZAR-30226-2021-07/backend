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

    def translate(self) -> str:
        """
        Traduce el color al español, con diferentes variaciones.
        """

        txts = {
            "Red": {
                "male": "rojo",
                "female": "roja",
            },
            "Blue": {
                "male": "azul",
                "female": "azul",
            },
            "Green": {
                "male": "verde",
                "female": "verde",
            },
            "Yellow": {
                "male": "amarillo",
                "female": "amarilla",
            },
            "All": {
                "male": "multicolor",
                "female": "multicolor",
            },
        }

        return txts[self.name]


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

        self.target = game.get_unfinished_player(target_name)
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
        update.msg = f"un órgano {self.color.translate()['male']}"
        return update


@dataclass
class Virus(SimpleCard):
    """
    Coloca un virus sobre otro jugador.
    """

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

        update = self.piles_update(game)
        update.msg = (
            f"un virus {self.color.translate()['male']} sobre {self.target.name}"
        )
        return update


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

        update = self.piles_update(game)
        update.msg = f"una medicina {self.color.translate()['female']}"
        return update


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
        player1 = action.data.get("target1")
        player2 = action.data.get("target2")

        # Pilas de los jugadores a intercambiar
        self.pile_slot1 = action.data.get("organ_pile1")
        self.pile_slot2 = action.data.get("organ_pile2")

        if None in (player1, player2, self.pile_slot1, self.pile_slot2):
            raise GameLogicException("Parámetro vacío")

        self.player1 = game.get_unfinished_player(player1)
        self.player2 = game.get_unfinished_player(player2)

        self.organ_pile1 = self.player1.body.get_pile(self.pile_slot1)
        self.organ_pile2 = self.player2.body.get_pile(self.pile_slot2)

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        # Comprobamos que las dos pilas tienen órgano
        if self.organ_pile1.is_empty() or self.organ_pile2.is_empty():
            raise GameLogicException("No puedes intercambiar órganos inexistentes")

        # Comprobamos que ninguno de los dos órganos está inmunizado
        if self.organ_pile1.is_immune() or self.organ_pile2.is_immune():
            raise GameLogicException("No puedes intercambiar órganos inmunes")

        # Comprobamos que no se haga un transplante a sí mismo.
        if self.player1 == self.player2:
            raise GameLogicException(
                "No puedes intercambiar óganos entre el mismo jugador"
            )

        # Comprobamos que ninguno de los dos jugadores tienen ya un órgano del
        # mismo color del órgano a añadir. NOTE: Ignoramos las pilas sobre las
        # que se va a reemplazar, porque no crean conflicto.
        if not (
            self.player1.body.organ_unique(
                self.organ_pile2.organ, ignored_piles=[self.pile_slot1]
            )
            and self.player2.body.organ_unique(
                self.organ_pile1.organ, ignored_piles=[self.pile_slot2]
            )
        ):
            raise GameLogicException("Ya tiene un órgano de ese color")

        logger.info("transplant played")

        update = GameUpdate(game)

        # Intercambiamos las pilas de ambos jugadores
        tmp = self.player1.body.piles[self.pile_slot1]
        self.player1.body.piles[self.pile_slot1] = self.player2.body.piles[
            self.pile_slot2
        ]
        self.player2.body.piles[self.pile_slot2] = tmp
        # Añadimos los dos cuerpos al GameUpdate
        update.repeat(
            {
                "bodies": {
                    self.player1.name: self.player1.body.piles,
                    self.player2.name: self.player2.body.piles,
                },
            }
        )

        update.msg = f"un Transplante entre {self.player1.name} y {self.player2.name}"
        return update


@dataclass
class OrganThief(Treatment):
    """
    Roba un órgano de otro jugador y añádelo a tu cuerpo. Puedes robar órganos
    sanos, vacunados o infectados, pero no inmunes. Recuerda que no puedes tener
    dos órganos del mismo color.
    """

    treatment_type: str = "organ_thief"

    def get_action_data(self, action: "PlayCard", game: "Game") -> None:
        """ """
        # Jugador objetivo
        target = action.data.get("target")
        # Pilas del jugador objetivo
        self.organ_pile_slot = action.data.get("organ_pile")

        if None in (target, self.organ_pile_slot):
            raise GameLogicException("Parámetro vacío")

        if type(target) is not str or type(self.organ_pile_slot) is not int:
            raise GameLogicException("Tipo de parámetro incorrecto")

        self.target = game.get_unfinished_player(target)

        self.organ_pile = self.target.body.get_pile(self.organ_pile_slot)

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        # Comprobamos que la pila tiene órgano
        if self.organ_pile.is_empty():
            raise GameLogicException("No puedes robar órganos inexistentes")

        # Comprobamos que ninguno de los dos órganos está inmunizado
        if self.organ_pile.is_immune():
            raise GameLogicException("No puedes robar órganos inmunes")

        # Comprobamos que el caller no tiene ya un órgano de ese color
        if not action.caller.body.organ_unique(self.organ_pile.organ):
            raise GameLogicException("Ya tienes un órgano de ese color")

        # Comprobamos que no se va a robar un órgano a sí mismo
        if action.caller == self.target:
            raise GameLogicException("No puedes robarte un órgano a ti mismo")

        # Obtenemos un espacio libre del caller
        self.empty_slot = None
        for (slot, pile) in enumerate(action.caller.body.piles):
            if pile.is_empty():
                self.empty_slot = slot
                break
        if self.empty_slot is None:
            raise GameLogicException("No tienes espacio libre")

        logger.info("organ-thief played")

        # Robamos la pila del target y la guardamos en el caller
        empty_pile = action.caller.body.piles[self.empty_slot]
        action.caller.body.piles[self.empty_slot] = self.organ_pile
        self.target.body.piles[self.organ_pile_slot] = empty_pile

        update = GameUpdate(game)
        # Añadimos el cuerpo del caller al GameUpdate
        update.repeat(
            {
                "bodies": {
                    self.target.name: self.target.body.piles,
                    action.caller.name: action.caller.body.piles,
                },
            }
        )

        update.msg = f"un Ladrón de Órganos sobre {self.target.name}"
        return update


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

        if all(map(lambda x: len(x) == 0, virus.values())):
            raise GameLogicException("No tienes virus disponibles")

        # Lista de pilas libres de todos los jugadores
        candidates = []

        # Accederemos a los jugadores en orden aleatorio
        unfinished = game.get_unfinished_players()
        random.shuffle(unfinished)
        for player in unfinished:
            # Eliminamos al caller de la iteración
            if player == action.caller:
                continue

            # Añadimos las pilas libres a la lista de candidatas
            candidates.extend(list(filter(lambda p: p.is_free(), player.body.piles)))

        if len(candidates) == 0:
            raise GameLogicException("No hay nadie que pueda recibir tus virus")

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

        update.msg = "un Contagio"
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

        for player in game.get_unfinished_players():
            if player == action.caller:
                continue

            # Vaciamos la mano del oponente
            player.empty_hand(return_to=game.deck)
            # Añadimos la mano vacía al GameUpdate
            update.add(player.name, {"hand": []})

        update.msg = "un Guante de Látex"
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

        self.target = game.get_unfinished_player(self.target_name)

    def apply(self, action: "PlayCard", game: "Game") -> GameUpdate:
        self.get_action_data(action, game)

        if action.caller == self.target:
            raise GameLogicException("No puedes intercambiar tu cuerpo contigo mismo")

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

        update.msg = f"un Error Médico sobre {self.target.name}"
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
    try:
        col = Color(data["color"])
    except ValueError:
        col = None  # Fallará con los tratamientos
    if cls is not None:
        return cls, {"color": col}

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

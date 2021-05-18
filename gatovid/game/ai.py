"""
Implementación de la inteligencia artificial que sustityue a los jugadores
desconectados en partidas públicas.

La IA se implementa en base a dos conceptos importantes:

* Se usa para simular jugadores normales, por lo que no debería tener acceso
  especial al juego.
* Debe ser eficiente. Incluso los algoritmos más ligeros de búsqueda en grafos
  como Hill-Climbing search requieren probar todas las posibles cartas,
  cada una dirigidas a cada posible jugador, lo cual puede ser un número
  demasiado grande.

Dado esto, la forma más sencilla de implementarlo es con un algoritmo que sigue
la siguiente estrategia con prioridades, a alto nivel:

1. Acciones especiales que se deben hacer siempre que sea posible
2. Superviviencia, para evitar perder en corto plazo
3. Avance, para evitar perder en largo plazo
4. Ataque a enemigos, para evitar que otros ganen
5. En caso de no poderse hacer nada, descartar y pasar turno

Notar, además, que para evitar tener que re-implementar la lógica de las cartas
para la IA, cada una de las acciones podrá devolver varios "intentos". Así al
probar cada uno de ellos, si da error por una condición más compleja se puede
continuar siguiendo el mismo orden. Tener que comprobar por ejemplo que al
lanzar una carta "Transplante" ninguno de los dos jugadores tenga dos órganos
del mismo color ni éstos estén inmunizados sería innecesario en este módulo.
"""

from typing import TYPE_CHECKING, Generator, List, Optional

from gatovid.game import GameLogicException
from gatovid.game.actions import Action, PlayCard
from gatovid.game.cards import (
    Card,
    Color,
    Infection,
    LatexGlove,
    MedicalError,
    Medicine,
    Organ,
    OrganThief,
    Treatment,
    Transplant,
)
from gatovid.util import get_logger

if TYPE_CHECKING:
    from gatovid.game import Game, Player


logger = get_logger(__name__)
ActionAttempts = Generator[List[Action], None, None]


def next_action(player: "Player", game: "Game") -> ActionAttempts:
    """
    Punto principal de entrada que devuelve intentos a realizar por la IA.
    """

    # Prioridad de las acciones, como se indica en el comentario del módulo:
    actions_priority = [
        _action_special,
        _action_survive,
        _action_advance,
        _action_attack,
        _action_pass,
    ]
    for func in actions_priority:
        # Itera todos los intentos de esa acción
        attempts = func(player, game)
        for actions in attempts:
            yield actions

    # Nunca deberia llegarse aquí, puesto que la acción de pasar siempre
    # funcionará.
    raise GameLogicException("Unreachable: no possible action found for the IA")


def _action_special(player: "Player", game: "Game") -> ActionAttempts:
    """
    Aplicar algunos tratamientos especiales.
    """

    latex_glove = _find_card(player, LatexGlove)
    if latex_glove is not None:
        yield [PlayCard({"slot": latex_glove})]


def _action_survive(player: "Player", game: "Game") -> ActionAttempts:
    """
    Tratar de curar tus propios órganos.
    """

    # Comprobamos si tenemos algún órgano que curar
    infected_piles = player.body.infected_piles()
    if len(infected_piles) == 0:
        return

    # Comprobamos si tenemos varios órganos que curar y tenemos el tratamiento
    # infección.
    infection = _find_card(player, Infection)
    if infection is not None and len(infected_piles) > 1:
        yield [PlayCard({"slot": infection})]

    # Comprobamos si tenemos alguna medicina para algún órgano
    medicines = _find_cards(player, Medicine)
    multicolored_medicine = None
    for organ_idx in infected_piles:
        organ: Organ = player.body.piles[organ_idx]

        for medicine_idx in medicines:
            medicine: Medicine = player.hand[medicine_idx]

            # Guardamos el slot donde hay una medicina multicolor por si se usa
            # luego.
            if medicine.color == Color.All:
                multicolored_medicine = medicine_idx

            # Si tenemos una medicina del mismo color que el órgano, podemos
            # curar directamente.
            if organ.get_top_color() == medicine.color:
                yield [
                    PlayCard(
                        {
                            "slot": medicine_idx,
                            "target": player.name,
                            "organ_pile": organ_idx,
                        }
                    )
                ]

    # Si no hemos podido encontrar una medicina del mismo color pero tenemos una
    # medicina multicolor
    if multicolored_medicine is not None:
        # Curamos el primer órgano.
        # NOTE: se podría hacer aleatorio, pero por hacerlo consistente.
        yield [
            PlayCard(
                {
                    "slot": multicolored_medicine,
                    "target": player.name,
                    "organ_pile": infected_piles[0],
                }
            )
        ]

    # Tratamientos curativos: "Transplante", que se puede usar para intercambiar
    # un órgano infectado por uno rival sano.

    # Tratamientos curativos: "Ladrón de Órganos", que puede robar órganos sanos
    # de un rival.

    # Tratamientos curativos: "Error Médico", que puede cambiar el cuerpo por el
    # de un enemigo en mejor estado.


def _action_advance(player: "Player", game: "Game") -> ActionAttempts:
    pass


def _action_attack(player: "Player", game: "Game") -> ActionAttempts:
    pass


def _action_pass(player: "Player", game: "Game") -> ActionAttempts:
    pass


def _iter_cards(player: "Player", kind: Card) -> Generator[int, None, None]:
    """
    Itera las cartas de un jugador que son del tipo especificado.
    """

    for card in player.hand:
        if isinstance(card, kind):
            yield card


def _find_matching_organ():
    pass


def _find_cards(player: "Player", kind: Card) -> List[int]:
    """
    Utilidad respecto a _iter_cards que devuelve todas las que son del tipo
    especificado.

    Si no se encuentra ninguna, se devolverá una lista vacía.
    """

    cards = []
    for card in _iter_cards(player, kind):
        cards.append(card)

    return cards


def _find_card(player: "Player", kind: Card) -> Optional[int]:
    """
    Utilidad respecto a _iter_cards que devuelve la primera carta del tipo
    especificado.

    Si no se encuentra ninguna, se devolverá None.
    """

    for card in _iter_cards(player, kind):
        return card

    return None

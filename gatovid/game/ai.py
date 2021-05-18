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
probar cada uno de ellos, si da error por un error más complejo se puede
continuar siguiendo el mismo orden. Tener que comprobar por ejemplo que al
lanzar una carta "Transplante" ninguno de los dos jugadores tenga dos órganos
del mismo color ni éstos estén inmunizados sería innecesario.
"""

from typing import TYPE_CHECKING, Generator, List

from gatovid.game import GameLogicException
from gatovid.game.actions import Action, PlayCard
from gatovid.game.cards import Color, Medicine, Organ

if TYPE_CHECKING:
    from gatovid.game import Game, Player


ActionAttempts = Generator[List[Action], None, None]


def next_move(player: "Player", game: "Game") -> ActionAttempts:
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

    treatments = find_card(player, "treatment", treatment_type="latex_glove")
    if len(treatments) > 0:
        yield [PlayCard({"slot": treatments[0]})]


def _action_survive(player: "Player", game: "Game") -> ActionAttempts:
    """
    Tratar de curar tus propios órganos.
    """

    # Comprobamos si tenemos algún órgano que curar
    to_heal = organs_to_heal()
    if len(to_heal) == 0:
        return None

    # Comprobamos si tenemos varios órganos que curar y tenemos el tratamiento
    # infección.
    infection = find_card(player, "treatment", treatment_type="latex_glove")
    if len(to_heal) > 1 and len(infection) > 0:
        return PlayCard(
            {
                "slot": infection[0],
            }
        )

    # Comprobamos si tenemos alguna medicina para algún órgano
    medicines = find_card(player, "medicine")
    multicolored_medicine = None
    for organ_idx in to_heal:
        organ: Organ = player.body.piles[organ_idx]

        for medicine_idx in medicines:
            medicine: Medicine = player.hand[medicine_idx]

            # Guardamos el slot donde hay una medicina multicolor por si
            # se usa luego.
            if medicine.color == Color.All:
                multicolored_medicine = medicine_idx

            # Si tenemos una medicina del mismo color que el órgano, podemos
            # curar directamente.
            if organ.get_top_color() == medicine.color:
                return PlayCard(
                    {
                        "slot": medicine_idx,
                        "target": player.name,
                        "organ_pile": organ_idx,
                    }
                )

    # Si no hemos podido encontrar una medicina del mismo color pero
    # tenemos una medicina multicolor
    if multicolored_medicine is not None:
        # Curamos el primer órgano. NOTE: se podría hacer aleatorio,
        # pero por hacerlo consistente.
        return PlayCard(
            {
                "slot": multicolored_medicine,
                "target": player.name,
                "organ_pile": to_heal[0],
            }
        )

    # Comprobamos si tenemos algún tratamiento que pueda curar algún
    # órgano.

    # No se ha encontrado forma de curarlo
    return None


def _action_advance(player: "Player", game: "Game") -> ActionAttempts:
    pass


def _action_attack(player: "Player", game: "Game") -> ActionAttempts:
    pass


def _action_pass(player: "Player", game: "Game") -> ActionAttempts:
    pass


def organs_to_heal(player: "Player") -> List[int]:
    """
    Devuelve una lista de slots de pilas que requieren curación.
    """

    is_infected = lambda i, p: p.is_infected()
    get_index = lambda i, p: i

    infected = filter(is_infected, enumerate(player.body.piles))
    return list(map(get_index, infected))


def find_card(
    player: "Player", card_type: str, treatment_type: str = None
) -> List[int]:
    """ """

"""
Implementación de la inteligencia artificial que sustityue a los jugadores
desconectados en partidas públicas.
"""

from typing import TYPE_CHECKING, Optional, List

from gatovid.game.actions import Action, PlayCard
from gatovid.game.cards import Color, Medicine, Organ

if TYPE_CHECKING:
    from gatovid.game import Game, Player


def next_action(player: "Player", game: "Game") -> [Action]:
    """
    Devuelve la acción a realizar por la IA.
    """

    # Prioridad de las acciones:
    # 0. Algunos tratamientos especiales
    # 1. Curar tus propios órganos
    # 2. Proteger / inmunizar tus propios órganos
    # 3. Colocar órganos
    # 4. Infectar / extirpar órganos ajenos

    actions_priority = [action_special_treatments, action_heal_self]
    for action_func in actions_priority:
        action = action_func(player, game)
        if action is not None:
            return action

    # TODO: Descartar cartas que no se vayan a usar
    # return Discard({ "slot": medicine_idx })


def action_special_treatments(player: "Player", game: "Game") -> Optional[Action]:
    """
    Aplicar algunos tratamientos especiales.
    """

    treatments = find_card_type(player, "treatment", tretment_type="latex_glove")
    if len(treatments) > 0:
        return PlayCard({
            "slot": treatments[0],
        })


def action_heal_self(player: "Player", game: "Game") -> Optional[Action]:
    """
    Tratar de curar tus propios órganos.
    """
    # Comprobamos si tenemos algún órgano que curar
    to_heal = organs_to_heal()
    if len(to_heal) == 0:
        return None

    # Comprobamos si tenemos varios órganos que curar y tenemos el tratamiento
    # infección.
    infection = find_card_type(player, "treatment", tretment_type="latex_glove")
    if len(to_heal) > 1 and len(infection) > 0:
        return PlayCard({
            "slot": infection[0],
        })

    # Comprobamos si tenemos alguna medicina para algún órgano
    medicines = find_card_type(player, "medicine")
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
                return PlayCard({
                    "slot": medicine_idx,
                    "target": player.name,
                    "organ_pile": organ_idx,
                })

    # Si no hemos podido encontrar una medicina del mismo color pero
    # tenemos una medicina multicolor
    if multicolored_medicine is not None:
        # Curamos el primer órgano. NOTE: se podría hacer aleatorio,
        # pero por hacerlo consistente.
        return PlayCard({
            "slot": multicolored_medicine,
            "target": player.name,
            "organ_pile": to_heal[0],
        })

    # Comprobamos si tenemos algún tratamiento que pueda curar algún
    # órgano.

    # No se ha encontrado forma de curarlo
    return None


def organs_to_heal(player: "Player") -> List[int]:
    """
    Devuelve una lista de slots de pilas que requieren curación.
    """

    is_infected = lambda i, p: p.is_infected()
    get_index = lambda i, p: i

    infected = filter(is_infected, enumerate(player.body.piles))
    return list(map(get_index, infected))


def find_card_type(player: "Player", card_type: str, treatment_type: str = None) -> List[int]:
    """ """

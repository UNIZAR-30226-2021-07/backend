"""
Implementación de la inteligencia artificial que sustityue a los jugadores
desconectados en partidas públicas.
"""

from typing import TYPE_CHECKING

from gatovid.game.actions import Action, PlayCard
from gatovid.game.cards import Color, Treatment, Medicine, Organ

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
def organs_to_heal(player: "Player") -> [int]:
    """
    Devuelve una lista de slots de pilas que requieren curación.
    """

    is_infected = lambda i,p: p.is_infected()
    get_index = lambda i,p : i

    infected = filter(is_infected, enumerate(player.body.piles))
    return list(map(get_index, infected))

def find_card_type(card_type: str, treatment_type: str = None) -> [int]:
    """ """

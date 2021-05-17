"""
Implementación de la inteligencia artificial que sustityue a los jugadores
desconectados en partidas públicas.
"""

from typing import TYPE_CHECKING

from gatovid.game.actions import Action, PlayCard
from gatovid.game.cards import Color, Treatment, Medicine, Organ

if TYPE_CHECKING:
    from gatovid.game import Game, Player

class IA:
    player: "Player"

    def __init__(self, player: "Player"):
        self.player = player

    def next_action(self, game: "Game") -> Action:
        """
        Devuelve la acción a realizar por la IA.
        """

        # Prioridad de las acciones:
        # 1. Curar tus propios órganos
        # 2. Proteger / inmunizar tus propios órganos
        # 3. Colocar órganos
        # 4. Infectar / extirpar órganos ajenos

    def find_card_type(self, card_type: str) -> [int]:
        """ """

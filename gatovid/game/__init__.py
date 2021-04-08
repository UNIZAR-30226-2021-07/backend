"""
Implementación de la lógica del juego.
"""

from typing import List, Dict, Optional
from datetime import datetime

from gatovid.game.actions import Action
from gatovid.game.model import User


class Game:
    """
    Información global sobre la partida y su estado.

    Los jugadores se guardan en una lista, y se sabe el turno actual con el
    ínice en esta.
    """

    def __init__(self, players: List[User]) -> None:
        self.discarded: List[int] = []
        self.deck: List[int] = []
        self.players: List[Player] = []
        self.turn = 0
        self.paused = False
        self.start_time = datetime.now()

    def run_action(self, action: Action) -> None:
        """
        Llamado ante cualquier acción de un jugador en la partida (?).
        """

    def calc_coins(self) -> Dict[User, int]:
        """
        Calcula las monedas obtenidas para cada jugador según la posición final,
        siguiendo la fórmula establecida:

        Sea N el número de jugadores de la partida, el jugador en puesto i
        ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo N
        * 10, y el último 0.
        """

        coins = {}

        for player in self.players:
            N = len(self.players)
            coins[player] = 10 * (N - player.position)

        return coins


class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.position: Optional[int] = None
        self.hand: List[int] = []

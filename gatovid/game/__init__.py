"""
Implementación de la lógica del juego.
"""

from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.cards import Action
from gatovid.models import User


class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.position: Optional[int] = None
        self.hand: List[int] = []


class Game:
    """
    Información global sobre la partida y su estado.

    Los jugadores se guardan en una lista, y se sabe el turno actual con el
    índice en esta.
    """

    def __init__(self, users: List[User]) -> None:
        self.discarded: List[int] = []
        self.deck: List[int] = []
        self.players = [Player(user.email) for user in users]
        self.turn = 0
        self.paused = False
        self.start_time = datetime.now()

    def run_action(self, action: Action) -> None:
        """
        Llamado ante cualquier acción de un jugador en la partida (?).
        """

    def playtime_mins(self) -> int:
        """
        Devuelve el tiempo de juego de la partida.
        """

        elapsed = datetime.now() - self.start_time
        return int(elapsed.total_seconds() / 60)

    def winners(self) -> Dict[int, Dict]:
        """
        Calcula los resultados de la partida, incluyendo las monedas obtenidas
        para cada jugador según la posición final, siguiendo la fórmula
        establecida:

          Sea N el número de jugadores de la partida, el jugador en puesto i
          ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo N
          * 10, y el último 0.
        """

        winners = {}
        N = len(self.players)

        for player in self.players:
            winners[player.user_id] = {
                "position": player.position,
                "coins": 10 * (N - player.position),
            }

        return winners

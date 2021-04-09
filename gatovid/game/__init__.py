"""
Implementación de la lógica del juego.
"""

from datetime import datetime
from typing import Dict, List, Optional

from gatovid.exts import db, socket
from gatovid.game.cards import Action
from gatovid.models import User


class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    def __init__(self, user: User) -> None:
        self.user = user
        self.position: Optional[int] = None
        self._hand: List[int] = []


class Game:
    """
    Información global sobre la partida y su estado.

    Los jugadores se guardan en una lista, y se sabe el turno actual con el
    índice en esta.
    """

    def __init__(self, users: List[User]) -> None:
        self._players = [Player(user) for user in users]
        self._discarded: List[int] = []
        self._deck: List[int] = []
        self._turn = 0
        self._paused = False
        self._start_time = datetime.now()
        self._finished = False

        # TODO: Por el momento, se hace como que se juega y se termina la
        # partida.
        for i, player in enumerate(self._players):
            player.position = i + 1
        self._finish()

    def is_finished(self) -> bool:
        return self._finished

    def _playtime_mins(self) -> int:
        """
        Devuelve el tiempo de juego de la partida.
        """

        elapsed = datetime.now() - self._start_time
        return int(elapsed.total_seconds() / 60)

    def _winners(self) -> Dict[int, Dict]:
        """
        Calcula los resultados de la partida, incluyendo las monedas obtenidas
        para cada jugador según la posición final, siguiendo la fórmula
        establecida:

          Sea N el número de jugadores de la partida, el jugador en puesto i
          ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo N
          * 10, y el último 0.
        """

        winners = {}
        N = len(self._players)

        for player in self._players:
            winners[player.user.name] = {
                "position": player.position,
                "coins": 10 * (N - player.position),
            }

        return winners

    def _finish(self) -> None:
        """
        Termina la partida, asigna las estadísticas a los jugadores y les
        notifica.
        """

        if self.is_finished():
            return

        self._finished = True
        mins = self._playtime_mins()
        winners = self._winners()

        for player in self._players:
            player.stats.playtime_mins += mins
            player.coins += winners[player.user.name]["coins"]
            if winners[player.email]["position"] == 1:
                player.stats.wins += 1
            else:
                player.stats.losses += 1

        db.session.commit()

        socket.emit("game_ended", winners, room=self.code)

    def run_action(self, action: Action) -> None:
        """
        Llamado ante cualquier acción de un jugador en la partida (?).
        """

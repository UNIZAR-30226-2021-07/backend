"""
Implementación de la lógica del juego.
"""

from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.cards import Action
from gatovid.models import User


class GameLogicException(Exception):
    """
    Esta excepción se usa para indicar casos erróneos o inesperados en el juego.
    """


class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.position: Optional[int] = None
        self.hand: List[int] = []


class Game:
    """
    Información global sobre la partida y su estado, de forma desacoplada a la
    base de datos.

    Los jugadores se guardan en una lista, y se sabe el turno actual con el
    índice en esta.
    """

    def __init__(self, users: List[User]) -> None:
        self._players = [Player(user.name) for user in users]
        self._discarded: List[int] = []
        self._deck: List[int] = []
        self._turn = 0
        self._start_time = datetime.now()
        self._paused = False
        self._finished = False

    def is_finished(self) -> bool:
        return self._finished

    def run_action(self, action: Action) -> [Dict]:
        """
        Llamado ante cualquier acción de un jugador en la partida. Devolverá el
        nuevo estado de la partida por cada jugador, o en caso de que ya hubiera
        terminado anteriormente o estuviera pausada, un error.
        """

        if self._game._finished:
            raise GameLogicException("El juego ya ha terminado")

        if self._game._paused:
            raise GameLogicException("El juego está pausado")

        # TODO: Por el momento, se hace como que se juega y se termina la
        # partida.
        for i, player in enumerate(self._players):
            player.position = i + 1
        self._finished = True

        status = []
        for player in self.players:
            status.append(self._generate_status(player))

        return status

    def _generate_status(self, player: Player) -> Dict:
        """
        Genera el estado para uno de los jugadores. Cada uno de ellos puede
        recibir uno diferente, dado que solo tendrán acceso a sus propias
        cartas, por ejemplo.
        """

        return {
            "finished": self._finished,
            "current_turn": self._players[self._turn].name,
            "hands": self._hands(),
            "leaderboard": self._leaderboard(),
            "playtime_mins": self._playtime_mins(),
        }

    def _playtime_mins(self) -> int:
        """
        Devuelve el tiempo de juego de la partida.
        """

        elapsed = datetime.now() - self._start_time
        return int(elapsed.total_seconds() / 60)

    def _leaderboard(self) -> Dict:
        """
        Calcula los resultados de la partida hasta el momento, incluyendo las
        monedas obtenidas para cada jugador según la posición final, siguiendo
        la fórmula establecida:

          Sea N el número de jugadores de la partida, el jugador en puesto i
          ganará 10 * (N - i) monedas en la partida. El primero será por ejemplo
          N * 10, y el último 0.
        """

        leaderboard = {}
        N = len(self._players)

        for player in self._players:
            if player.position is None:
                continue

            leaderboard[player.name] = {
                "position": player.position,
                "coins": 10 * (N - player.position),
            }

        return leaderboard

    def _hands(self, recipient: Player) -> Dict:
        """
        Genera un diccionario con las manos de todos los jugadores, de forma que
        solo ellos tengan acceso a sus cartas.
        """

        hands = {}

        for player in self._players:
            hands[player.name] = {
                "organs": [],
                "effects": [],
            }

            if player == recipient:
                hands[player.name]["hand"] = player.hand
            else:
                hands[player.name]["num_cards"] = len(player.hand)

        return hands

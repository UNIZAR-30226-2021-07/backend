"""
Implementación de la lógica del juego.
"""

from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.actions import Action
from gatovid.game.body import Body
from gatovid.game.cards import Card, DECK

# Exportamos GameLogicException
from gatovid.game.common import GameLogicException
from gatovid.models import User


class Player:
    """
    Información sobre un usuario ya unido a la partida, con sus cartas y
    detalles sobre su estado.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.position: Optional[int] = None
        self.hand: List[Card] = []
        self.body = Body()

    def get_card(self, slot: int) -> Card:
        return self.hand[slot]


class Game:
    """
    Información global sobre la partida y su estado, de forma desacoplada a la
    base de datos.

    Los jugadores se guardan en una lista, y se sabe el turno actual con el
    índice en esta.
    """

    def __init__(self, users: List[User]) -> None:
        # TODO: atributos públicos
        self._players = [Player(user.name) for user in users]
        self._discarded: List[Card] = []
        self._deck: List[Card] = []
        self._turn = 0
        self._start_time = datetime.now()
        self._paused = False
        self._finished = False
        self._players_finished = 0

        # TODO: Por el momento, se hace como que se juega y se termina la
        # partida.
        for i, player in enumerate(self._players):
            player.position = i + 1

    def start(self) -> Dict:
        """
        Inicializa la baraja y reparte 3 cartas a cada jugador, iterando de
        forma similar a cómo se haría en la vida real.

        Devuelve un game_update con el estado actual del juego.
        """

        self._deck = DECK.copy()

        for i in range(3):
            for player in self._players:
                drawn = self._deck.pop()
                player.hand.append(drawn)

        update = [{"hand": player.hand} for player in self._players]
        return update

    def is_finished(self) -> bool:
        return self._finished

    def get_player(self, user_name: str) -> Player:
        for player in self._players:
            if player.name == user_name:
                return player

        raise GameLogicException("El jugador no está en la partida")

    def run_action(self, caller: str, action: Action) -> [Dict]:
        """
        Llamado ante cualquier acción de un jugador en la partida. Devolverá el
        nuevo estado de la partida por cada jugador, o en caso de que ya hubiera
        terminado anteriormente o estuviera pausada, un error.
        """

        if self._finished:
            raise GameLogicException("El juego ya ha terminado")

        if self._paused:
            raise GameLogicException("El juego está pausado")

        if self._players[self._turn].name != caller:
            raise GameLogicException("No es tu turno")

        player = self.get_player(caller)
        update = action.apply(player, game=self)
        return update

    def end_turn(self) -> [Dict]:
        self._finished = True

    def turn_name(self) -> str:
        """
        Devuelve el nombre del usuario con el turno actual.
        """

        return self._players[self._turn].name

    def _playtime_mins(self, game: "Game") -> int:
        """
        Devuelve el tiempo de juego de la partida.
        """

        elapsed = datetime.now() - game._start_time
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

    def player_finished(self, player: Player) -> None:
        """
        Finaliza la partida para un jugador en concreto.
        """

        if player.position is not None:
            raise GameLogicException("El jugador ya ha terminado")

        self._players_finished + 1
        player.position = self._players_finished

    def finish(self, caller: Player) -> Dict:
        """
        Finaliza el juego y devuelve un game_update.
        """

        self._finished = True

        update = {
            "finished": True,
            "leaderboard": self._leaderboard(),
            "playtime_mins": self._playtime_mins(),
        }
        return [update] * len(self._players)

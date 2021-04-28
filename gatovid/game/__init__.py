"""
Implementación de la lógica del juego.
"""

from datetime import datetime
from typing import Dict, List, Optional

from gatovid.game.actions import Action
from gatovid.game.body import Body
from gatovid.game.cards import Card

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

        # TODO: Por el momento, se hace como que se juega y se termina la
        # partida.
        for i, player in enumerate(self._players):
            player.position = i + 1

    def is_finished(self) -> bool:
        return self._finished

    def get_player(self, user_name: str) -> Player:
        for player in self._players:
            if player.name == user_name:
                return player

        raise GameLogicException("El jugador no está en la partida")

    def run_action(self, caller: Optional[str], action: Action) -> [Dict]:
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

        player = None
        if caller is not None:
            player = self.get_player

        update = action.apply(player, game=self)
        return update

    def end_turn(self) -> [Dict]:
        self._finished = True

    def turn_name(self) -> str:
        """
        Devuelve el nombre del usuario con el turno actual.
        """

        return self._players[self._turn].name

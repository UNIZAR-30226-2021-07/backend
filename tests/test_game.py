"""
Tests para la lógica del juego
"""

from gatovid.api.game.match import MM
from gatovid.create_db import (
    GENERIC_USERS_EMAIL,
    GENERIC_USERS_NAME,
    GENERIC_USERS_PASSWORD,
    NUM_GENERIC_USERS,
)
from gatovid.game.cards import Color, Medicine, Organ, Virus
from gatovid.util import get_logger

from .base import WsTestClient

logger = get_logger(__name__)

users_data = []
for i in range(NUM_GENERIC_USERS):
    users_data.append(
        {
            "email": GENERIC_USERS_EMAIL.format(i),
            "password": GENERIC_USERS_PASSWORD,
        }
    )


class GameTest(WsTestClient):
    def create_game(self, players=6):
        clients = []
        for i in range(players):
            clients.append(self.create_client(users_data[i]))

        # Creamos la partida
        callback_args = clients[0].emit("create_game", callback=True)

        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Unimos a los clientes a la partida
        for client in clients[1:]:
            callback_args = client.emit("join", code, callback=True)
            self.assertNotIn("error", callback_args)

        # Empezamos la partida
        callback_args = clients[0].emit("start_game", callback=True)
        self.assertNotIn("error", callback_args)

        return clients, code

    def test_play_card(self):
        """
        TODO: Modificar este test cuando se implemente el sistema de turnos.
        """
        clients, code = self.create_game()

        # TODO: Se debería acceder al endpoint directamente, pero no está hecha
        # la inicialización de la partida, así que no puedo probar a usar la
        # mano sin inicializarla yo.
        game = MM.get_match(code).get_game()

        leader_player = None
        for player in game._players:
            if player.name == GENERIC_USERS_NAME.format(0):
                leader_player = player
                break

        leader_player.hand = [
            Organ(color=Color.Red),
            Virus(color=Color.Red),
            Medicine(color=Color.Red),
        ]

        # TODO: cuando los turnos existan: solo puede jugar carta el jugador al
        # que le toque
        game._turn = 0

        callback_args = clients[0].emit(
            "play_card",
            {
                "slot": 0,
                "target": GENERIC_USERS_NAME.format(0),  # itself
                "organ_pile": 0,
            },
            callback=True,
        )
        self.assertNotIn("error", callback_args)

        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        self.assertIn("bodies", args)
        self.assertEqual(
            args["bodies"][0]["piles"],
            [
                {"_modifiers": [], "_organ": {"card_type": "organ", "color": "red"}},
                None,
                None,
                None,
            ],
        )

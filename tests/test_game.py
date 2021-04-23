"""
Tests para la lógica del juego
"""

import time
from typing import Dict, List, Optional

from gatovid.create_db import (
    GENERIC_USERS_EMAIL,
    GENERIC_USERS_NAME,
    GENERIC_USERS_PASSWORD,
    NUM_GENERIC_USERS,
)
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
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Unimos a los clientes a la partida
        for client in clients[1:]:
            callback_args = client.emit("join", code, callback=True)
            self.assertNotIn("error", callback_args)
        
        # Empezamos la partida
        callback_args = clients[0].emit("start_game", callback=True)
        self.assertNotIn("error", callback_args)

        return clients

    def test_play_card(self):
        clients = self.create_game()


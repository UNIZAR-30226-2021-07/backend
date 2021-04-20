"""
Tests para la conexión básica de websockets
"""

import time
from typing import Dict, Optional, List

from .base import WsTestClient

user_data = {
    "email": "test_user1@gmail.com",
    "password": "whatever1",
}

user2_data = {
    "email": "test_user2@gmail.com",
    "password": "whatever2",
}

user3_data = {
    "email": "test_user3@gmail.com",
    "password": "whatever3",
}


class WsTest(WsTestClient):
    matchmaking_delay = 0.0

    def set_matchmaking_time(self, delay: float):
        """
        Para los tests se parchea el tiempo de espera para el inicio de la
        partida, evitando que se tenga que esperar a que acabe.
        """

        import gatovid.api.game.match

        gatovid.api.game.match.TIME_UNTIL_START = delay
        self.matchmaking_delay = delay

    def wait_matchmaking_time(self):
        time.sleep(self.matchmaking_delay * 1.2)

    def parse_json_args(self, args):
        return dict((key, arg[key]) for arg in args for key in arg)

    def get_msg_in_received(
        self, received: List, msg_type: str, json: bool = False
    ) -> (Optional[Dict], Optional[List[Dict]]):
        """
        Devuelve la primera aparición de un mensaje de tipo `msg_type` en
        `received`.
        """
        raw = next(iter(filter(lambda msg: msg["name"] == msg_type, received)), None)
        args = raw["args"]

        if raw and raw.get("args") and json:
            args = self.parse_json_args(raw["args"])

        return raw, args

    def test_connect(self):
        client = self.create_client(user_data)
        self.assertIsNotNone(client)

        client2 = self.create_client(user2_data)
        self.assertIsNotNone(client2)

    def test_create_game(self):
        client = self.create_client(user_data)

        # Creamos la partida y vemos si el servidor devuelve error
        callback_args = client.emit("create_game", callback=True)
        self.assertNotIn("error", callback_args)

        # Comprobamos que el servidor nos ha devuelto el código de partida
        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        self.assertIsNotNone(msg)
        self.assertIn("code", args)

        code = args["code"]
        self.assertEqual(len(code), 4)
        self.assertEqual(type(code), str)

    def test_join_private_game(self):
        client = self.create_client(user_data)

        # Creamos la partida y vemos si el servidor devuelve error
        callback_args = client.emit("create_game", callback=True)
        self.assertNotIn("error", callback_args)

        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Creamos el usuario que se unirá a la partida
        client2 = self.create_client(user2_data)
        self.assertIsNotNone(client2)

        # El cliente 2 se une a la partida. Probamos primero que se puede unir
        # con un código en minúsculas.
        callback_args = client2.emit("join", code.lower(), callback=True)
        self.assertNotIn("error", callback_args)
        callback_args = client2.emit("leave", callback=True)
        self.assertNotIn("error", callback_args)

        # El cliente 2 se une a la partida por segunda vez, con un código en
        # mayúsculas.
        callback_args = client2.emit("join", code, callback=True)
        self.assertNotIn("error", callback_args)

        received = client2.get_received()
        msg, args = self.get_msg_in_received(received, "users_waiting")
        self.assertIsNotNone(msg)
        users_waiting = args[0]
        self.assertEqual(users_waiting, 2)

        # Un intento de crear una partida debería devolver un error
        callback_args = client.emit("create_game", callback=True)
        self.assertIn("error", callback_args)
        callback_args = client.emit("search_game", callback=True)
        self.assertIn("error", callback_args)

    def test_start_private_game(self):
        client = self.create_client(user_data)
        client2 = self.create_client(user2_data)

        # Creamos la partida
        client.emit("create_game", callback=True)

        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Probamos si puede empezar la partida con solo 1 jugador
        callback_args = client.emit("start_game", callback=True)
        self.assertIn("error", callback_args)

        # El cliente 2 se une a la partida
        client2.emit("join", code, callback=True)

        # Probamos si puede empezar la partida alguien que no es el lider
        callback_args = client2.emit("start_game", callback=True)
        self.assertIn("error", callback_args)

        # La iniciamos ahora con el lider
        callback_args = client.emit("start_game", callback=True)
        self.assertNotIn("error", callback_args)

    def test_chat(self):
        client = self.create_client(user_data)
        client2 = self.create_client(user2_data)

        # Creamos la partida
        callback_args = client.emit("create_game", callback=True)

        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # El cliente 2 se une a la partida
        callback_args = client2.emit("join", code, callback=True)
        # Empezamos la partida
        callback_args = client.emit("start_game", callback=True)
        # Ignoramos los mensajes recibidos hasta el momento (sino, se
        # acumularán los mensajes de chat de unirse a partida, etc)
        received = client.get_received()
        received = client2.get_received()

        # Emitimos un mensaje de chat desde el cliente 2
        msg = "Hola buenas"
        owner = "test_user2"
        callback_args = client2.emit("chat", msg, callback=True)
        self.assertNotIn("error", callback_args)

        # Comprobamos que los 2 reciben el mensaje de chat
        received = client.get_received()
        _, args = self.get_msg_in_received(received, "chat", json=True)
        self.assertIn("msg", args)
        self.assertIn("owner", args)

        received = client2.get_received()
        _, args2 = self.get_msg_in_received(received, "chat", json=True)
        self.assertIn("msg", args2)
        self.assertIn("owner", args2)

        self.assertEqual(args["msg"], msg)
        self.assertEqual(args2["msg"], msg)
        self.assertEqual(args["owner"], owner)
        self.assertEqual(args2["owner"], owner)

        # Mensaje vacío falla
        msg = "          "
        callback_args = client2.emit("chat", msg, callback=True)
        self.assertIn("error", callback_args)

        # Mensaje demasiado largo falla
        msg = "test" * 1000
        callback_args = client2.emit("chat", msg, callback=True)
        self.assertIn("error", callback_args)

    def test_matchmaking(self):
        self.set_matchmaking_time(0.5)

        client = self.create_client(user_data)
        client2 = self.create_client(user2_data)

        # El primer usuario puede entrar y esperar, pero no comenzará la partida
        # hasta que hayan al menos dos.
        callback_args = client.emit("search_game", callback=True)
        self.assertNotIn("error", callback_args)
        self.wait_matchmaking_time()
        received = client.get_received()
        self.assertEqual(len(received), 0)

        # Se une un segundo usuario y espera el tiempo necesario. Ahora sí que
        # se encontrará una partida.
        callback_args = client2.emit("search_game", callback=True)
        self.assertNotIn("error", callback_args)
        self.wait_matchmaking_time()
        for client in (client, client2):
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "found_game", json=True)
            self.assertIn("code", args)

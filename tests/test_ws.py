"""
Tests para la conexión básica de websockets
"""

from .base import WsTestClient

_user_data = {
    "email": "test_user1@gmail.com",
    "password": "whatever1",
}

_user2_data = {
    "email": "test_user2@gmail.com",
    "password": "whatever2",
}

_user3_data = {
    "email": "test_user3@gmail.com",
    "password": "whatever3",
}


class SessionsTest(WsTestClient):
    def parse_json_args(self, args):
        return dict((key, arg[key]) for arg in args for key in arg)

    def get_msg_in_received(self, received, msg_type: str, json: bool = False):
        """
        Devuelve la primera aparición de un mensaje de tipo `msg_type` en `received`.
        """
        raw = next(iter(filter(lambda msg: msg["name"] == msg_type, received)), None)
        args = raw["args"]

        if raw and raw.get("args") and json:
            args = self.parse_json_args(raw["args"])

        return raw, args

    def test_connect(self):
        client = self.create_client(_user_data)
        self.assertIsNotNone(client)

        client2 = self.create_client(_user2_data)
        self.assertIsNotNone(client2)

    def test_create_game(self):
        client = self.create_client(_user_data)

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
        client = self.create_client(_user_data)

        # Creamos la partida y vemos si el servidor devuelve error
        callback_args = client.emit("create_game", callback=True)
        self.assertNotIn("error", callback_args)

        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Creamos el usuario que se unirá a la partida
        client2 = self.create_client(_user2_data)
        self.assertIsNotNone(client2)

        # El cliente 2 se une a la partida
        callback_args = client2.emit("join", code, callback=True)
        self.assertNotIn("error", callback_args)

        received = client2.get_received()
        msg, args = self.get_msg_in_received(received, "users_waiting")
        self.assertIsNotNone(msg)
        users_waiting = args[0]
        self.assertEqual(users_waiting, 2)

    def test_start_private_game(self):
        client = self.create_client(_user_data)
        client2 = self.create_client(_user2_data)

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
        client = self.create_client(_user_data)
        client2 = self.create_client(_user2_data)

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
        msg, args = self.get_msg_in_received(received, "chat", json=True)
        self.assertIn("msg", args)
        self.assertIn("owner", args)

        received = client2.get_received()
        msg, args2 = self.get_msg_in_received(received, "chat", json=True)
        self.assertIn("msg", args2)
        self.assertIn("owner", args2)

        self.assertTrue(args["msg"] == msg)
        self.assertTrue(args2["msg"] == msg)
        self.assertTrue(args["owner"] == owner)
        self.assertTrue(args2["owner"] == owner)

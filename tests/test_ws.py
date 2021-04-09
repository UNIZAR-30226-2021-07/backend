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

    def args_to_dict(self, args):
        return dict((key, arg[key]) for arg in args for key in arg)        

    def get_msg_in_received(self, received, msg_type : str):
        """
        Devuelve la primera aparición de un mensaje de tipo `msg_type` en `received`.
        """
        raw = next(iter(filter(lambda msg: msg['name'] == msg_type, received)), None)
        args = dict()
        if raw:
            args = self.args_to_dict(raw['args'])

        return raw, args

    def test_connect(self):
        client = self.create_client(_user_data)
        self.assertIsNotNone(client)

    def test_create_game(self):
        client = self.create_client(_user_data)
        self.assertIsNotNone(client)

        # Creamos la partida y vemos si el servidor devuelve error
        callback_args = client.emit("create_game", callback=True)
        self.assertNotIn("error", callback_args)

        # Comprobamos que el servidor nos ha devuelto el código de partida
        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game")
        self.assertIsNotNone(msg)
        self.assertIn('code', args)

        

import time
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from flask_testing import TestCase

import gatovid.api.game.match
import gatovid.game
from gatovid.app import app
from gatovid.create_db import (
    GENERIC_USERS_EMAIL,
    GENERIC_USERS_NAME,
    GENERIC_USERS_PASSWORD,
    NUM_GENERIC_USERS,
    db_reset,
    db_test_data,
)
from gatovid.exts import db, socket

DEFAULT_TIME_TURN_END = gatovid.game.TIME_TURN_END
DEFAULT_TIME_UNTIL_RESUME = gatovid.game.TIME_UNTIL_RESUME
DEFAULT_TIME_UNTIL_START = gatovid.api.game.match.TIME_UNTIL_START


class BaseTestCase(TestCase):
    """
    Clase básica para realizar tests con Flask y la base de datos.
    """

    def create_app(self):
        app.config.from_object("gatovid.config.TestingConfig")
        return app

    def setUp(self):
        db_reset()
        db_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def assertRequestErr(self, resp, code=None):
        msg = f"description: {resp.json}"
        if code is None:
            self.assertGreaterEqual(resp.status_code, 400, msg=msg)
            self.assertLessEqual(resp.status_code, 599, msg=msg)
        else:
            self.assertEqual(resp.status_code, code, msg=msg)

        self.assertIn("error", resp.json)

    def assertRequestOk(self, resp, code=None):
        msg = f"description: {resp.json}"
        if code is None:
            self.assertGreaterEqual(resp.status_code, 200, msg=msg)
            self.assertLessEqual(resp.status_code, 299, msg=msg)
        else:
            self.assertEqual(resp.status_code, code, msg=msg)

        self.assertNotIn("error", resp.json)


class GatovidTestClient(BaseTestCase):
    """
    Clase para realizar tests, extendida con un cliente HTTP para realizar
    peticiones desde cualquier test de forma sencilla.
    """

    def request(
        self,
        url: str,
        data: Dict[str, str] = None,
        headers: Dict[str, str] = None,
        method: str = "GET",
    ) -> Dict[str, str]:
        """
        Petición genérica al API de Gatovid
        """

        if method == "GET":
            # Se añaden los parámetros de `data` a los de la URL
            if data is not None:
                url_parts = list(urlparse(url))
                query = dict(parse_qsl(url_parts[4]))
                query.update(data)
                url_parts[4] = urlencode(query)
                url = urlunparse(url_parts)

            response = self.client.get(url, headers=headers)
        elif method == "POST":
            response = self.client.post(url, data=data, headers=headers)
        else:
            raise Exception("not supported")

        return response

    def auth_headers(self, token: str) -> Dict[str, str]:
        return {"Authorization": "Bearer " + token}

    def request_token(self, data: Dict[str, str]) -> Dict[str, str]:
        return self.request("/data/login", data=data)

    def revoke_token(self, token: str) -> Dict[str, str]:
        return self.request("/data/logout", headers=self.auth_headers(token))

    def token_use(self, token: str) -> Dict[str, str]:
        return self.request("/data/protected_test", headers=self.auth_headers(token))

    def request_signup(self, data: Dict[str, str]) -> Dict[str, str]:
        return self.request("/data/signup", data=data)

    def request_remove(self, token: str, data: Dict[str, str]) -> Dict[str, str]:
        return self.request(
            "/data/remove_user", data=data, headers=self.auth_headers(token)
        )

    def request_modify(self, token: str, data: Dict[str, str]) -> Dict[str, str]:
        return self.request(
            "/data/modify_user", data=data, headers=self.auth_headers(token)
        )

    def request_stats(self, name: str) -> Dict[str, str]:
        return self.request("/data/user_stats", data={"name": name})

    def request_data(self, token: str) -> Dict[str, str]:
        return self.request("/data/user_data", headers=self.auth_headers(token))

    def request_coins(self, token: str) -> int:
        data = self.request("/data/user_data", headers=self.auth_headers(token))
        return int(data.json["coins"])

    def request_shop_buy(
        self, item_id: int, item_type: str, token: str
    ) -> Dict[str, str]:
        return self.request(
            "/data/shop_buy",
            data={
                "id": item_id,
                "type": item_type,
            },
            headers=self.auth_headers(token),
        )


class WsTestClient(GatovidTestClient):
    """
    Clase para realizar tests, extendida con un cliente websocket para
    realizar peticiones desde cualquier test de forma sencilla.
    """

    clients = []
    matchmaking_delay = 0.0

    users_data = [
        {
            "name": GENERIC_USERS_NAME.format(i),
            "email": GENERIC_USERS_EMAIL.format(i),
            "password": GENERIC_USERS_PASSWORD,
        }
        for i in range(NUM_GENERIC_USERS)
    ]

    player_names = [GENERIC_USERS_NAME.format(i) for i in range(NUM_GENERIC_USERS)]

    def create_app(self):
        self.app = super().create_app()
        return self.app

    def tearDown(self):
        super().tearDown()

        for client in self.clients:
            try:
                client.disconnect()
            except RuntimeError:
                # Ignoramos si el cliente no se ha conectado
                pass

        self.reset_timeouts()

    def reset_timeouts(self) -> None:
        """
        Reinicia los timeouts establecidos para las pruebas de forma manual.
        """

        self.set_matchmaking_time(DEFAULT_TIME_UNTIL_START)
        self.set_pause_timeout(DEFAULT_TIME_UNTIL_RESUME)
        self.set_turn_timeout(DEFAULT_TIME_TURN_END)

    def create_client(self, user_data: Dict[str, str]):
        resp = self.request_token(user_data)

        self.assertRequestOk(resp)
        self.assertIn("access_token", resp.json)

        client = socket.test_client(
            self.app, headers=self.auth_headers(resp.json["access_token"])
        )

        # Lo guardamos para poder "limpiarlo" más tarde
        self.clients.append(client)
        return client

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
        if raw is None:
            return None, None

        args = raw["args"]

        if raw and raw.get("args") and json:
            args = self.parse_json_args(raw["args"])

        return raw, args

    def set_matchmaking_time(self, delay: float):
        """
        Para los tests se parchea el tiempo de espera para el inicio de la
        partida, evitando que se tenga que esperar a que acabe.
        """

        import gatovid.api.game.match

        gatovid.api.game.match.TIME_UNTIL_START = delay
        self.matchmaking_delay = delay

    def wait_matchmaking_time(self):
        """
        Espera el tiempo de inicio de una partida, con un pequeño margen para el
        procesamiento en el backend.
        """

        time.sleep(self.matchmaking_delay * 1.2)

    def set_pause_timeout(self, delay: float):
        """
        Para los tests se parchea el tiempo de timeout de las pausas, evitando
        que se tenga que esperar a que acabe.
        """

        import gatovid.game

        gatovid.game.TIME_UNTIL_RESUME = delay
        self.pause_timeout = delay

    def wait_pause_timeout(self):
        """
        Espera el tiempo de reanudar automático, con un pequeño margen para el
        procesamiento en el backend.
        """

        time.sleep(self.pause_timeout * 1.2)

    def set_turn_timeout(self, delay: float):
        """
        Para los tests se parchea el tiempo de timeout de los turnos, evitando
        que se tenga que esperar a que acabe.
        """

        import gatovid.game

        gatovid.game.TIME_TURN_END = delay
        self.turn_time = delay

    def wait_turn_timeout(self):
        """
        Espera el tiempo de turno, con un pequeño margen para el procesamiento
        en el backend.
        """

        time.sleep(self.turn_time * 1.2)

    def create_game(self, players=6):
        clients = []
        for i in range(players):
            clients.append(self.create_client(self.users_data[i]))

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

    def get_game_update(self, client) -> Dict:
        received = client.get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        return args

    def discard_ok(self, client, position: int = 0) -> Dict:
        callback_args = client.emit("play_discard", position, callback=True)
        self.assertNotIn("error", callback_args)
        args = self.get_game_update(client)
        self.assertIn("hand", args)
        self.assertNotIn("current_turn", args)
        return args

    def discard_err(self, client, position: int) -> Dict:
        callback_args = client.emit("play_discard", position, callback=True)
        self.assertIn("error", callback_args)
        return callback_args

    def pass_ok(self, client) -> Dict:
        callback_args = client.emit("play_pass", callback=True)
        self.assertNotIn("error", callback_args)
        args = self.get_game_update(client)
        self.assertIn("hand", args)
        return args

    def pass_err(self, client) -> Dict:
        callback_args = client.emit("play_pass", callback=True)
        self.assertIn("error", callback_args)
        return callback_args

    def get_current_turn(self, client) -> str:
        received = client.get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        return args["current_turn"]

    def get_current_turn_client(self, clients):
        current_turn = self.get_current_turn(clients[0])
        for user, client in zip(self.users_data, clients):
            if user["name"] == current_turn:
                return client

        raise Exception("Couldn't find client with current turn")

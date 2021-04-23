"""
Tests para la conexión básica de websockets
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


class WsTest(WsTestClient):
    def test_connect(self):
        client = self.create_client(users_data[0])
        self.assertIsNotNone(client)

        client2 = self.create_client(users_data[1])
        self.assertIsNotNone(client2)

    def test_create_game(self):
        client = self.create_client(users_data[0])

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
        client = self.create_client(users_data[0])

        # Creamos la partida y vemos si el servidor devuelve error
        callback_args = client.emit("create_game", callback=True)
        self.assertNotIn("error", callback_args)

        received = client.get_received()
        msg, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Creamos el usuario que se unirá a la partida
        client2 = self.create_client(users_data[1])
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
        client = self.create_client(users_data[0])
        client2 = self.create_client(users_data[1])

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
        client = self.create_client(users_data[0])
        client2 = self.create_client(users_data[1])

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
        owner = GENERIC_USERS_NAME.format(1)
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

    def test_matchmaking_time_limited(self):
        """
        Comprueba que el timer funciona para asignar partidas una vez pasado el
        tiempo máximo.
        """

        self.set_matchmaking_time(0.5)

        client = self.create_client(users_data[0])
        client2 = self.create_client(users_data[1])
        client3 = self.create_client(users_data[2])

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

        # Si otro usuario comienza a buscar partida tampoco encontrará porque ya
        # no hay disponibles.
        callback_args = client3.emit("search_game", callback=True)
        self.assertNotIn("error", callback_args)
        self.wait_matchmaking_time()
        received = client3.get_received()
        self.assertEqual(len(received), 0)

    def test_matchmaking_timer_cancel(self):
        """
        Comprueba que no hay problemas al cancelar el timer por no tenerse
        suficientes usuarios de nuevo.
        """

        self.set_matchmaking_time(0.5)

        client = self.create_client(users_data[0])
        client2 = self.create_client(users_data[1])

        # Se unen dos usuarios, por lo que comenzará el timer.
        callback_args = client.emit("search_game", callback=True)
        self.assertNotIn("error", callback_args)
        callback_args = client2.emit("search_game", callback=True)
        self.assertNotIn("error", callback_args)

        # Rápidamente se sale un usuario
        callback_args = client2.emit("stop_searching", callback=True)
        self.assertNotIn("error", callback_args)

        self.wait_matchmaking_time()

        # El primero de ellos no habrá encontrado partida
        received = client.get_received()
        self.assertEqual(len(received), 0)

        # Y el segundo solo habrá recibido la confirmación de que
        # stop_searching.
        received = client2.get_received()
        _, args = self.get_msg_in_received(received, "stop_searching", json=True)
        self.assertEqual(args, [])
        _, args = self.get_msg_in_received(received, "found_game", json=True)
        self.assertEqual(args, None)

    def test_matchmaking_total(self):
        """
        Comprueba que al llegar a 6 usuarios se inicia una partida
        automáticamente.
        """

        self.set_matchmaking_time(0.5)

        clients = []
        for i in range(7):
            clients.append(self.create_client(users_data[i]))

        # Encontrarán partida todos menos el último, que ya es el séptimo y se
        # queda fuera.
        for client in clients:
            callback_args = client.emit("search_game", callback=True)
            self.assertNotIn("error", callback_args)
        self.wait_matchmaking_time()

        for client in clients[:-1]:
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "found_game", json=True)
            self.assertIn("code", args)
        received = clients[-1].get_received()
        self.assertEqual(len(received), 0)

    def test_troll_user(self):
        """
        Comprueba que 2 usuarios encontrarán partida aunque haya un "troll"
        buscando y cancelando.
        """

        clients = []
        for i in range(2):
            clients.append(self.create_client(users_data[i]))

        troll = self.create_client(users_data[2])

        # Establecemos un tiempo de inicio de partida ínfimo.
        self.set_matchmaking_time(0.5)

        # Los 2 usuarios con buena intención buscarán partida normalmente.
        for client in clients:
            callback_args = client.emit("search_game", callback=True)
            self.assertNotIn("error", callback_args)

        for i in range(2):
            callback_args = troll.emit("search_game", callback=True)
            self.assertNotIn("error", callback_args)
            time.sleep(0.1)
            callback_args = troll.emit("stop_searching", callback=True)
            self.assertNotIn("error", callback_args)
            time.sleep(0.1)

        # Esperamos un tiempo adicional hasta que se complete el
        # tiempo de creación; pero no dejándole tiempo a que cree otro
        # timer (por si en algún futuro se toca el matchmaking).
        time.sleep(0.3)

        code = None
        for client in clients:
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "found_game", json=True)
            self.assertIn("code", args)
            if code:  # Comprobamos que han entrado a la misma partida
                self.assertEqual(code, args["code"])

        # Comprobamos que el troll no ha encontrado partida (porque finalmente
        # ha cancelado).
        received = troll.get_received()
        msg, _ = self.get_msg_in_received(received, "found_game", json=True)
        self.assertIsNone(msg)

    def test_match_management_full(self):
        """
        Prueba un caso en el que se busca partida repetidamente siguiendo el
        proceso completo:

        Públicas:

        1. Iniciar sesión
        2. Buscar juego
        3. Encontrar juego
        4. Unirse a juego
        5. Salir de juego
        6. Cerrar sesión

        Privadas:

        1. Iniciar sesión
        2. Crear juego o unirse al existente
        3. Salir de juego
        4. Cerrar sesión
        """

        self.set_matchmaking_time(0.5)

        def new_public_game(client1, client2):
            logger.info(">> Joining public game")

            # Encuentran una partida
            for client in (client1, client2):
                callback_args = client.emit("search_game", callback=True)
                self.assertNotIn("error", callback_args)
            self.wait_matchmaking_time()

            # Se unen a la partida
            for client in (client1, client2):
                received = client.get_received()
                _, args = self.get_msg_in_received(received, "found_game", json=True)
                self.assertIn("code", args)
                callback_args = client.emit("join", args["code"], callback=True)
                self.assertNotIn("error", callback_args)

        def new_private_game(client1, client2):
            logger.info(">> Joining private game")

            # Uno de ellos crea una partida una partida
            callback_args = client1.emit("create_game", callback=True)
            self.assertNotIn("error", callback_args)
            received = client1.get_received()
            _, args = self.get_msg_in_received(received, "create_game", json=True)
            code = args["code"]

            # El otro se une a la partida
            callback_args = client2.emit("join", code, callback=True)
            self.assertNotIn("error", callback_args)

        for new_game in (new_public_game, new_private_game):
            for i in range(5):
                client1 = self.create_client(users_data[0])
                client2 = self.create_client(users_data[1])

                new_game(client1, client2)

                # Se salen de la partida. En este caso sí que puede haber un error,
                # en caso de que se cancele la partida automáticamente y se intente
                # salir de ella de nuevo.
                for client in (client1, client2):
                    client1.emit("leave", callback=True)

                del client1, client2

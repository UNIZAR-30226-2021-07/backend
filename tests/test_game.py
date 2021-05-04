"""
Tests para la lógica del juego
"""

import random
import time

from gatovid.create_db import GENERIC_USERS_NAME
from gatovid.util import get_logger

from .base import WsTestClient

logger = get_logger(__name__)


class GameTest(WsTestClient):
    def get_current_turn(self, client) -> str:
        received = client.get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        return args["current_turn"]

    def test_start_game(self):
        """
        Comprueba el protocolo de inicio de la partida.
        """

        clients, code = self.create_game()

        for cur_client_num, client in enumerate(clients):
            # Primero debería haberse recibido un mensaje de `start_game`
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "start_game", json=True)
            self.assertIsNotNone(args)

            # Después, debería haberse recibido un mensaje con el estado inicial
            # del juego.
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertIsNotNone(args)

            # La mano y el turno serán aleatorios
            self.assertIn("hand", args)
            self.assertIn("current_turn", args)

            # Los jugadores de la partida sí que se pueden saber
            self.assertIn("players", args)
            expected_players = []
            for client_num in range(len(clients)):
                # Cada jugador tendrá su información básica, y él mismo habrá
                # recibido su tablero.
                data = {
                    "name": GENERIC_USERS_NAME.format(client_num),
                    "picture": 0,
                }
                if client_num == cur_client_num:
                    data["board"] = 0
                expected_players.append(data)

            self.assertEqual(args["players"], expected_players)

    def test_pause(self):
        """
        Cualquier usuario de la partida podrá realizar una pausa. En ese momento
        la partida quedará pausada para todos los jugadores de la misma.
        """
        clients, code = self.create_game()

        for (i, client) in enumerate(clients):
            # Ignoramos los eventos anteriores
            _ = client.get_received()

            # Pausamos
            callback_args = client.emit("pause_game", True, callback=True)
            self.assertNotIn("error", callback_args)

            received = client.get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertIn("paused", args)
            self.assertEqual(args["paused"], True)
            self.assertIn("paused_by", args)
            self.assertEqual(args["paused_by"], GENERIC_USERS_NAME.format(i))

            # Reanudamos
            callback_args = client.emit("pause_game", False, callback=True)
            self.assertNotIn("error", callback_args)

    def test_resume(self):
        """
        El usuario que realiza la pausa es el único capaz de volver a
        reanudarla.
        """
        clients, code = self.create_game()

        # Ignoramos los eventos anteriores
        _ = clients[0].get_received()
        _ = clients[1].get_received()
        _ = clients[2].get_received()

        # Pausamos con el cliente 0
        callback_args = clients[0].emit("pause_game", True, callback=True)
        self.assertNotIn("error", callback_args)

        # Otro jugador espera recibir pausa
        received = clients[1].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertIn("paused", args)
        self.assertEqual(args["paused"], True)
        self.assertIn("paused_by", args)
        self.assertEqual(args["paused_by"], GENERIC_USERS_NAME.format(0))

        # Intentamos reanudar con el cliente 2
        callback_args = clients[2].emit("pause_game", False, callback=True)
        self.assertIn("error", callback_args)

        # Otro jugador no espera recibir reanudacion
        received = clients[1].get_received()
        self.assertEqual(received, [])

        # Reanudamos con el cliente 0
        callback_args = clients[0].emit("pause_game", False, callback=True)
        self.assertNotIn("error", callback_args)

        # Otro jugador espera recibir reanudacion
        received = clients[1].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertIn("paused", args)
        self.assertEqual(args["paused"], False)
        self.assertIn("paused_by", args)
        self.assertEqual(args["paused_by"], GENERIC_USERS_NAME.format(0))

    def test_auto_resume(self):
        """
        TODO: Si la pausa supera un tiempo límite, la partida se reanuda
        automáticamente.
        """
        clients, code = self.create_game()

        # Establecemos el tiempo para que se cancele la pausa a 1 segundo para
        # no tener que esperar tanto.
        self.set_pause_timeout(1)

        # Pausamos con el cliente 0
        callback_args = clients[0].emit("pause_game", True, callback=True)
        self.assertNotIn("error", callback_args)

        # Ignoramos los eventos anteriores
        _ = clients[1].get_received()

        # Esperamos al tiempo de expiración de la pausa
        self.wait_pause_timeout()

        # Otro jugador espera recibir pausa
        received = clients[1].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertIn("paused", args)
        self.assertEqual(args["paused"], False)
        self.assertIn("paused_by", args)
        self.assertEqual(args["paused_by"], GENERIC_USERS_NAME.format(0))

    def test_auto_pass(self):
        """
        Comprueba que el turno se pasa automáticamente después de alcanzar el
        tiempo límite de un turno.

        Notar que no se puede asumir el orden del turno, así que únicamente se
        comprueba si ha cambiado.
        """

        self.set_turn_timeout(0.2)
        clients, code = self.create_game()

        # Ciclo de turnos completo
        start_turn = self.get_current_turn(clients[0])
        for i in range(len(clients)):
            self.wait_turn_timeout()
            end_turn = self.get_current_turn(clients[0])
            self.assertNotEqual(start_turn, end_turn)
            start_turn = end_turn

    def test_auto_pass_with_pause(self):
        """
        Comprueba que el turno se pasa automáticamente de forma correcta aun
        cuando se pausa la partida.
        """

        self.set_turn_timeout(0.5)
        clients, code = self.create_game()

        def pause():
            callback_args = clients[0].emit("pause_game", True, callback=True)
            self.assertNotIn("error", callback_args)

        def check_no_new_turn():
            received = clients[0].get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            if args is not None:
                self.assertNotIn("current_turn", args)

        # Ciclo de turnos completo
        start_turn = self.get_current_turn(clients[0])
        for i in range(len(clients)):
            # Pausa, se duerme, reanuda y vuelve a dormirse varias veces hasta
            # que termina el turno.
            logger.info(">> Waiting new turn")
            for i in range(5):
                logger.info(f">> Iteration {i} of 5, slept {0.1 * 1.2 * i} total")
                check_no_new_turn()
                pause()
                # El tiempo dormido entre pausas no debería contar
                time.sleep(random.uniform(0.1, 0.5))
                check_no_new_turn()
                pause()
                time.sleep(0.1 * 1.2)

            logger.info(">> Done waiting")
            end_turn = self.get_current_turn(clients[0])
            self.assertNotEqual(start_turn, end_turn)
            start_turn = end_turn

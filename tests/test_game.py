"""
Tests para la lógica del juego
"""

import time

from gatovid.create_db import GENERIC_USERS_NAME
from gatovid.util import get_logger

from gatovid.game import Body, Card
from gatovid.game.cards import Color, Organ

from .base import WsTestClient

logger = get_logger(__name__)


class GameTest(WsTestClient):
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

            args = self.get_game_update(client)
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
        args = self.get_game_update(clients[1])
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
        args = self.get_game_update(clients[1])
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
        args = self.get_game_update(clients[1])
        self.assertIn("paused", args)
        self.assertEqual(args["paused"], False)
        self.assertIn("paused_by", args)
        self.assertEqual(args["paused_by"], GENERIC_USERS_NAME.format(0))

    def test_auto_pass(self):
        """
        Comprueba que el turno se pasa automáticamente después de alcanzar el
        tiempo límite de un turno.

        Al pasar el turno de forma automática se debería descartar una carta y
        robar una nueva.

        Notar que no se puede asumir el orden del turno, así que únicamente se
        comprueba si ha cambiado.
        """

        self.set_turn_timeout(0.2)
        clients, code = self.create_game()

        start_turn = self.get_current_turn(clients[0])

        # Ciclo de turnos completo a partir del cliente que tenga el turno
        # inicial.
        for i in range(len(clients)):
            self.clean_messages(clients)
            client = self.get_client_from_name(clients, start_turn)

            self.wait_turn_timeout()
            args = self.get_game_update(client)
            self.assertIn("hand", args)
            self.assertIn("current_turn", args)

            end_turn = args["current_turn"]
            self.assertNotEqual(start_turn, end_turn)
            start_turn = end_turn

    def test_auto_pass_with_pause(self):
        """
        Comprueba que el turno se pasa automáticamente de forma correcta aun
        cuando se pausa la partida.
        """

        self.set_turn_timeout(0.3)
        clients, code = self.create_game()

        def pause(paused):
            callback_args = clients[0].emit("pause_game", paused, callback=True)
            self.assertNotIn("error", callback_args)

        def recv_pause():
            """
            Lee los mensajes recibidos, asegurando que únicamente se tiene uno
            de pausa en el buzón.
            """

            args = self.get_game_update(clients[0])
            self.assertIn("paused", args)
            self.assertIn("paused_by", args)
            self.assertNotIn("current_turn", args)
            self.assertEqual(clients[0].get_received(), [])

        # Ciclo de turnos completo
        start_turn = self.get_current_turn(clients[0])
        self.assertEqual(clients[0].get_received(), [])
        # Pausa, se duerme, reanuda y vuelve a dormirse varias veces hasta
        # que termina el turno.
        logger.info(">> Waiting new turn")
        for i in range(4):
            # El tiempo dormido entre pausas no debería contar
            pause(True)
            recv_pause()
            time.sleep(0.4)
            pause(False)
            recv_pause()

            time.sleep(0.05)
            logger.info(f">> Iteration {i + 1}/4 done, slept {0.1 * (i + 1)}/0.2s")

        # Duerme el tiempo restante como margen fuera del bucle
        time.sleep(0.15)
        logger.info(">> Done waiting")

        end_turn = self.get_current_turn(clients[0])
        self.assertNotEqual(start_turn, end_turn)
        self.assertEqual(clients[0].get_received(), [])

    def test_discard(self):
        """
        Comprueba que la acción de descarte funciona correctamente.
        """

        clients, code = self.create_game()
        client = self.get_current_turn_client(clients)
        self.clean_messages(clients)

        # Inicialmente no se puede pasar porque no está en fase de descarte.
        logger.info("Attempting pass that should fail")
        self.pass_err(client)

        # Descarta una carta de forma correcta
        logger.info("Discarding in test")
        args = self.discard_ok(client, 2)
        self.assertEqual(len(args["hand"]), 2)

        # Descarta una carta que no existe en la mano del jugador (la tercera,
        # porque ha sido descartada anteriormente)
        self.discard_err(client, 2)

        args = self.discard_ok(client, 0)
        self.assertEqual(len(args["hand"]), 1)
        self.discard_err(client, 1)
        self.discard_err(client, 2)

        # Notar que al descartar la posición de las cartas también cambia
        args = self.discard_ok(client, 0)
        self.assertEqual(len(args["hand"]), 0)
        # Se queda sin cartas e intenta descartar.
        self.discard_err(client, 0)
        self.discard_err(client, 1)
        self.discard_err(client, 2)
        self.discard_err(client, 3)

        # Pasa de turno, tendrá ahora 3 cartas de nuevo
        logger.info("Passing next turn")
        args = self.pass_ok(client)
        self.assertIn("current_turn", args)
        self.assertEqual(len(args["hand"]), 3)

        # Ya no puede pasar ni descartar
        args = self.discard_err(client, 0)
        args = self.pass_err(client)

    def test_auto_pass_discard(self):
        """
        Comprueba que si un usuario se olvida de pasar el turno se le descarta
        una carta y roba. Si el jugador está descartando esto no se debería
        hacer.

        Como no se puede asumir que las cartas robadas sean diferentes a las
        descartadas, no se puede saber si se ha descartado una adicional al
        final del turno, y por tanto es imposible hacer un test unitario de
        esto.
        """

        self.set_turn_timeout(0.5)
        clients, code = self.create_game()

        # Se tiene que acceder a la partida directamente para tener la mano del
        # jugador actual.
        from gatovid.api.game.match import MM

        match = MM.get_match(code)
        game = match._game
        current_player = game.turn_player()
        start_hand = [id(card) for card in current_player.hand]

        # Caso base (cambia la mano al final):
        client = self.get_current_turn_client(clients)
        client.get_received()  # Limpia recibidos

        # Espera el tiempo de partida y comprueba que la mano no sea la misma,
        # comparando las instancias y no los datos de las cartas.
        self.wait_turn_timeout()
        end_hand = [id(card) for card in current_player.hand]
        self.assertNotEqual(start_hand, end_hand)

        # Caso de descarte (no cambia la mano al final):
        client = self.get_current_turn_client(clients)
        client.get_received()  # Limpia recibidos

        # Descarte de 2 cartas
        self.discard_ok(client)
        self.discard_ok(client)

        current_player = game.turn_player()
        start_hand = [id(card) for card in current_player.hand]
        # Espera a fin de turno y se asegura que la última carta que quedaba (en
        # la posición 0) no ha sido modificada, es decir, que únicamente se han
        # descartado las dos cartas indicadas en el proceso de descarte.
        # esperado.
        self.wait_turn_timeout()
        end_hand = [id(card) for card in current_player.hand]
        self.assertEqual(start_hand[0], end_hand[0])

    def test_player_finished(self):
        """
        Comprueba que si se reconoce cuando un jugador gana una partida.
        """

        b = Body()
        b.piles[1].set_organ(Organ(color=Color.Red))
        b.piles[2].set_organ(Organ(color=Color.Green))
        b.piles[3].set_organ(Organ(color=Color.Blue))
        callback_args, response, turn_player = self.place_card(
            target_body=b,
            card=Organ(color=Color.Yellow),
            place_in_self=True,
        )

        self.assertNotIn("error", callback_args)
        _, args = self.get_msg_in_received(response, "game_update", json=True)
        self.assertIn("player_won", args)
        self.assertEqual(args["player_won"], turn_player.name)

"""
Tests para el manejo de conexiones de las partidas Se añade a continuación un
resumen de la funcionalidad de abandono y la funcionalidad de reconexión.

El botón de abandonar es pulsado:
- Pública: es eliminado y no se puede volver; el jugador es reemplazado por la
  IA.
- Privada: es eliminado y no se puede volver; las cartas del jugador van a la
  baraja.

Desconexión por error o botón de reanudar más tarde pulsado:
- Pública: no se puede volver a jugar.
- Privada: se puede volver a la partida y no habrá pasado nada porque en
  partidas privadas no se eliminan jugadores AFK.
"""

import time
from typing import Optional

from gatovid.create_db import GENERIC_USERS_NAME
from gatovid.util import get_logger

from .base import WsTestClient

logger = get_logger(__name__)


class ConnTest(WsTestClient):
    def active_wait_turns(self, clients, total_skips: int, turn_timeout: float) -> int:
        # Para saber el orden de los turnos
        starting_turn = self.get_current_turn_client(clients)
        turn = clients.index(starting_turn)

        self.clean_messages(clients)
        for i in range(total_skips):
            while True:
                received = clients[0].get_received()
                if len(received) > 0:
                    self.assertEqual(len(received), 1)
                    break

                time.sleep(turn_timeout / 3)  # Para evitar saturar al servidor

            turn = (turn + 1) % len(clients)
            expected = GENERIC_USERS_NAME.format(turn)
            logger.info(f">> Turn {i + 1} skipped, {expected} now playing")

            _, args = self.get_msg_in_received(
                received, "game_update", json=True, last=True
            )
            self.assertEqual(args.get("current_turn"), expected)

        return turn

    def turn_iter(
        self, clients, num_turns: int, callback, initial_turn: Optional[int] = None
    ) -> int:
        """
        Método para evitar boilerplate al iterar turnos de forma ordenada
        """

        turn = initial_turn
        if turn is None:
            starting_turn = self.get_current_turn_client(clients)
            turn = clients.index(starting_turn)

        for i in range(num_turns):
            callback(turn, i, clients[turn])
            turn = (turn + 1) % len(clients)

        return turn

    def check_game_is_cancelled(self, client) -> None:
        received = client.get_received()
        _, args = self.get_msg_in_received(received, "game_cancelled", json=True)
        self.assertIsNotNone(args)

    def check_user_has_abandoned(self, client, code: str, can_pause: bool) -> None:
        """
        El cliente ha sido eliminado de la partida y por tanto no podrá
        jugar ya; la pausa no funcionará, por ejemplo.
        """

        if can_pause:
            callback_args = client.emit("pause_game", True, callback=True)
            self.assertIn("error", callback_args)

        # Ya no se puede jugar
        callback_args = client.emit("play_discard", 0, callback=True)
        self.assertIn("error", callback_args)

        # Tampoco podrá volver a entrar a la partida
        callback_args = client.emit("join", code, callback=True)
        self.assertIn("error", callback_args)

    def check_connection_works(self, client, start: bool, public: bool = False) -> None:
        """
        Test básico de funcionamiento. Se puede dividir en dos pasos con `start`
        y si se indica `public` se hará todo a la vez y sin pausar.
        """

        # Se pueden descartar cartas sin problemas
        if public or start:
            # En la primera iteración descarta
            callback_args = client.emit("play_discard", 0, callback=True)
            self.assertNotIn("error", callback_args)

        if public or not start:
            # Y en la segunda iteración pasa el turno
            callback_args = client.emit("play_pass", callback=True)
            self.assertNotIn("error", callback_args)

        if not public:
            # Se puede pausar y reanudar sin problemas
            callback_args = client.emit("pause_game", True, callback=True)
            self.assertNotIn("error", callback_args)
            callback_args = client.emit("pause_game", False, callback=True)
            self.assertNotIn("error", callback_args)

    def test_kicked_public(self):
        """
        Comprueba el caso en el que se elimina al usuario por estar AFK, y
        también cuando la partida es cancelada cuando se queda sin suficientes
        usuarios.
        """

        self.set_matchmaking_time(3)
        timeout = 0.1
        self.set_turn_timeout(timeout)
        clients, code = self.create_public_game()

        # Iteración completa antes de que el primer usuario sea eliminado.
        total_skips = len(clients) * 2
        logger.info(f">> Skipping {total_skips} turns")
        turn = self.active_wait_turns(clients, total_skips, timeout)

        # En la siguiente iteración los usuarios son eliminados
        logger.info(">> Starting player removal loop")
        for i in range(len(clients) - 1):
            client = clients[turn]
            self.wait_turn_timeout()

            self.check_user_has_abandoned(client, code, can_pause=False)

            # Todos salen de la partida para limpiar la sesión.
            callback_args = client.emit("leave", callback=True)
            self.assertNotIn("error", callback_args)

            # Se continúa con el siguiente usuario a ser kickeado
            turn = (turn + 1) % len(clients)

        # El último usuario en intentarlo no podrá porque se habrá borrado la
        # partida.
        last_client = clients[turn]
        self.check_game_is_cancelled(last_client)

    def test_abandon_private(self):
        """
        Comprueba el abandono manual de una partida privada.
        """

        timeout = 0.1
        self.set_turn_timeout(timeout)
        clients, code = self.create_game()

        # Iterando más de 3 turnos para asegurarse de que ninguno de ellos es
        # eliminado de la partida.
        total_skips = len(clients) * 4
        logger.info(f">> Skipping {total_skips} turns")
        turn = self.active_wait_turns(clients, total_skips, timeout)

        def turn_works(turn, i, client):
            # Descarta e intenta pausar, debería funcionar
            self.check_connection_works(client, start=True)
            # Pasa turno e intenta pausar
            self.check_connection_works(client, start=False)

        def turn_doesnt_work(turn, i, client):
            # El último usuario en intentarlo no podrá porque se habrá borrado la
            # partida.
            if i == len(clients) - 1:
                self.check_game_is_cancelled(client)
                return

            self.clean_messages(clients)
            callback_args = client.emit("leave", callback=True)
            self.assertNotIn("error", callback_args)
            self.check_user_has_abandoned(client, code, can_pause=True)

            # Comprueba que los demás usuarios hayan recibido un mensaje con los
            # jugadores una vez abandona (en caso de que la partida no se vaya a
            # cancelar).
            if i != len(clients) - 2:
                next_turn = (turn + 1) % len(clients)
                other_client = clients[next_turn]

                print(f"Next: {next_turn}")
                args = self.get_game_update(other_client)
                self.assertIsNotNone(args)
                self.assertIn("players", args)

        logger.info(">> Starting loop that should work")
        turn = self.turn_iter(clients, len(clients), turn_works, initial_turn=turn)

        # Ahora se abandona manualmente y ya no se podrá hacer nada en la
        # partida.
        logger.info(">> Leaving match")
        self.turn_iter(clients, len(clients), turn_doesnt_work, initial_turn=turn)

    def test_abandon_public(self):
        """
        Comprueba el abandono manual de una partida pública.
        """

        self.set_matchmaking_time(0.5)
        self.set_turn_timeout(0.1)
        clients, code = self.create_public_game()

        # Ahora se abandona manualmente y ya no se podrá hacer nada en la
        # partida.
        for client in clients:
            callback_args = client.emit("leave", callback=True)
            self.assertNotIn("error", callback_args)

            # Ya no se puede jugar
            callback_args = client.emit("play_discard", 0, callback=True)
            self.assertIn("error", callback_args)

            # Ya no se puede pausar
            callback_args = client.emit("pause_game", True, callback=True)
            self.assertIn("error", callback_args)

            # Ni volverse a unir a la partida
            callback_args = client.emit("join", code, callback=True)
            self.assertIn("error", callback_args)

    def test_disconnect_public(self):
        """
        Abandonar una partida pública supone que no se puede volver.
        """

        self.set_matchmaking_time(0.5)
        clients, code = self.create_public_game()

        # Para saber el orden de los turnos
        starting_turn = self.get_current_turn_client(clients)
        turn = clients.index(starting_turn)

        for i in range(len(clients) - 1):
            logger.info(f">> Trying as usual for turn {turn}")
            # Antes de la desconexión funciona correctamente
            client = clients[turn]
            self.check_connection_works(client, start=True, public=True)

            logger.info(">> Trying after reconnect")
            # Reconexión, no debería funcionar
            client = self.client_reconnect(clients, client)
            callback_args = client.emit("join", code, callback=True)
            self.assertIn("error", callback_args)

            turn = (turn + 1) % len(clients)

        # El último usuario en intentarlo no podrá porque se habrá borrado la
        # partida.
        last_client = clients[turn]
        self.check_game_is_cancelled(last_client)

    def test_disconnect_private(self):
        """
        El jugador podrá reanudar el juego en cualquier momento antes de que
        acabe.
        """

        self.set_turn_timeout(0.5)
        clients, code = self.create_game()

        # Para saber el orden de los turnos
        starting_turn = self.get_current_turn_client(clients)
        turn = clients.index(starting_turn)

        for i in range(len(clients)):
            logger.info(">> Trying as usual")
            # Antes de la desconexión funciona correctamente
            client = clients[turn]
            self.check_connection_works(client, start=True)

            logger.info(">> Trying after reconnect")

            # Reconexión
            client = self.client_reconnect(clients, client)
            clients[turn] = client
            next_turn = (turn + 1) % len(clients)

            # Unión de nuevo a la partida
            self.clean_messages(clients)
            callback_args = client.emit("join", code, callback=True)
            self.assertNotIn("error", callback_args)

            # Tendría que llegar directamente un start_game y después un
            # game_update con el estado completo del juego.
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "start_game", json=True)
            self.assertIsNotNone(args)
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertIsNotNone(args)
            self.assertIn("hand", args)
            self.assertIn("players", args)
            self.assertIn("paused", args)
            self.assertIn("bodies", args)
            self.assertIn("current_turn", args)
            self.assertIn("finished", args)

            # Comprobaciones simples
            self.check_connection_works(client, start=False)

            # Comprobación de que recibe mensajes de otros
            self.clean_messages(clients)
            callback_args = clients[next_turn].emit("pause_game", True, callback=True)
            self.assertNotIn("error", callback_args)
            # Compara el mensaje propio con el del cliente que ha re-entrado
            received = clients[next_turn].get_received()
            _, expected = self.get_msg_in_received(received, "game_update", json=True)
            received = clients[turn].get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertEqual(args, expected)
            # Restaura la pausa
            callback_args = clients[next_turn].emit("pause_game", False, callback=True)
            self.assertNotIn("error", callback_args)

            turn = next_turn

    def test_reconnect_when_joining(self):
        """
        Comprueba un caso especial de desconexión antes de que la partida
        privada sea comenzada.
        """

        client_leader = self.create_client(self.users_data[0])
        client = self.create_client(self.users_data[1])

        # Creamos la partida
        callback_args = client_leader.emit("create_game", callback=True)
        received = client_leader.get_received()
        _, args = self.get_msg_in_received(received, "create_game", json=True)
        code = args["code"]

        # Antes de unirse se reconecta
        client = self.client_reconnect([client_leader, client], client)

        # Unión a la partida
        callback_args = client.emit("join", code, callback=True)
        self.assertNotIn("error", callback_args)

        # Empezamos la partida sin problemas
        callback_args = client_leader.emit("start_game", callback=True)
        self.assertNotIn("error", callback_args)

    def test_reconnect_when_searching(self):
        """
        Comprueba un caso especial de desconexión antes de que la partida
        pública sea comenzada.
        """

        self.set_matchmaking_time(0.5)

        client_leader = self.create_client(self.users_data[0])
        client = self.create_client(self.users_data[1])

        # Ambos buscan partida y entran juntos a la misma.
        for client in (client_leader, client):
            callback_args = client.emit("search_game", callback=True)
            self.assertNotIn("error", callback_args)

        # Antes de unirse se reconecta
        client = self.client_reconnect([client_leader, client], client)

        # Ahora no debería encontrarse partida porque se ha perdido un usuario
        self.wait_matchmaking_time()
        received = client_leader.get_received()
        _, args = self.get_msg_in_received(received, "found_game", json=True)
        self.assertIsNone(args)

        # Vuelve a buscar partida
        callback_args = client.emit("search_game", callback=True)
        self.assertNotIn("error", callback_args)
        self.wait_matchmaking_time()

        # Ahora sí que comienza la partida
        code = None
        for client in (client_leader, client):
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "found_game", json=True)
            self.assertIn("code", args)
            code = args["code"]
            callback_args = client.emit("join", code, callback=True)
            self.assertNotIn("error", callback_args)

    def leave_pause(self):
        """
        Comprueba el caso en el que si el usuario que ha pausado la partida
        abandona, se des-pausa la partida.
        """

        self.set_turn_timeout(0.5)
        clients, code = self.create_game()
        self.clean_messages(clients)

        # Un usuario pausa y los demás reciben el mensaje
        callback_args = clients[0].emit("pause_game", True, callback=True)
        self.assertNotIn("error", callback_args)
        args = self.get_game_update(clients[1])
        self.assertEqual(
            args, {"paused": True, "paused_by": GENERIC_USERS_NAME.format(0)}
        )

        # Ahora abandona la partida y debería tenerse otro mensaje
        callback_args = clients[0].emit("leave", callback=True)
        self.assertNotIn("error", callback_args)
        args = self.get_game_update(clients[1])
        self.assertEqual(args.get("paused"), False)
        self.assertEqual(args.get("paused_by"), GENERIC_USERS_NAME.format(0))

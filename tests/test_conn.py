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

from gatovid.util import get_logger

from .base import WsTestClient

logger = get_logger(__name__)


class ConnTest(WsTestClient):
    def abandon_and_check(self, clients, code: str, can_pause: bool) -> None:
        """
        Método genérico para pruebas en las que se abandona la partida de forma
        manual y se comprueba que el comportamiento es el esperado.
        """

        # Ahora se abandona manualmente y ya no se podrá hacer nada en la
        # partida.
        for client in clients:
            callback_args = client.emit("leave", callback=True)
            self.assertNotIn("error", callback_args)

            # Ya no se puede jugar
            callback_args = client.emit("play_discard", True, callback=True)
            self.assertIn("error", callback_args)

            if can_pause:
                # Ya no se puede pausar
                callback_args = client.emit("pause_game", True, callback=True)
                self.assertIn("error", callback_args)

            # Ni volverse a unir a la partida
            callback_args = client.emit("join", code, callback=True)
            self.assertIn("error", callback_args)

    def check_connection_works(self, client, start: bool, can_pause: bool = True):
        # Se pueden descartar cartas sin problemas
        if start:
            # En la primera iteración descarta
            callback_args = client.emit("play_discard", True, callback=True)
            self.assertNotIn("error", callback_args)
        else:
            # Y en la segunda iteración pasa el turno
            callback_args = client.emit("play_pass", callback=True)
            self.assertNotIn("error", callback_args)

        if can_pause:
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

        self.set_matchmaking_time(0.2)
        self.set_turn_timeout(0.1)
        clients, code = self.create_public_game()

        # Para saber el orden de los turnos
        starting_turn = self.get_current_turn_client(clients)
        turn = clients.index(starting_turn)

        # Iteración completa antes de que el primer usuario sea eliminado.
        logger.info(">> Getting ready for players to be removed")
        self.clean_messages(clients)
        for i in range(2):  # Itera 2 veces
            for i in range(len(clients) - 1):  # Por cada cliente
                self.wait_turn_timeout()

        # En la siguiente iteración los usuarios son eliminados
        logger.info(">> Starting player removal loop")
        for i in range(len(clients)):
            client = clients[turn]
            self.wait_turn_timeout()

            # El cliente ha sido eliminado de la partida y por tanto no podrá
            # jugar ya; la pausa no funcionará, por ejemplo.
            callback_args = client.emit("pause_game", True, callback=True)
            self.assertIn("error", callback_args)

            # Ya no se puede jugar
            callback_args = client.emit("play_discard", True, callback=True)
            self.assertIn("error", callback_args)

            # Tampoco podrá volver a entrar a la partida
            callback_args = client.emit("join", code, callback=True)
            self.assertIn("error", callback_args)

            # Si se cancela la partida no hace falta hacer más, pero en caso
            # contrario el protocolo establece que tendrán que salir ellos
            # manualmente.
            received = clients[turn].get_received()
            _, args = self.get_msg_in_received(received, "game_cancelled", json=True)
            callback_args = client.emit("leave", callback=True)
            if args is None:
                # Si no se ha cancelado irá con éxito
                self.assertNotIn("error", callback_args)
            else:
                # En caso contrario se recibirá un error
                self.assertIn("error", callback_args)

            # Se continúa con el siguiente usuario a ser kickeado
            turn = (turn + 1) % len(clients)

    def test_abandon_private(self):
        """
        Comprueba el abandono manual de una partida privada.
        """

        timeout = 0.1
        self.set_turn_timeout(timeout)
        clients, code = self.create_game()

        # Iterando más de 3 turnos para asegurarse de que ninguno de ellos es
        # eliminado de la partida.
        time.sleep(timeout * len(clients) * 4)

        # Para saber el orden de los turnos
        starting_turn = self.get_current_turn_client(clients)
        turn = clients.index(starting_turn)

        logger.info(">> Starting loop that should work")
        for i in range(len(clients)):
            client = clients[turn]

            # Se pueden descartar cartas sin problemas
            callback_args = client.emit("play_discard", True, callback=True)
            self.assertNotIn("error", callback_args)
            callback_args = client.emit("play_pass", callback=True)
            self.assertNotIn("error", callback_args)

            # Se puede pausar y reanudar sin problemas
            callback_args = client.emit("pause_game", True, callback=True)
            self.assertNotIn("error", callback_args)
            callback_args = client.emit("pause_game", False, callback=True)
            self.assertNotIn("error", callback_args)

            turn = (turn + 1) % len(clients)

        self.abandon_and_check(clients, code, can_pause=True)

    def test_abandon_public(self):
        """
        Comprueba el abandono manual de una partida pública.
        """

        self.set_matchmaking_time(0.2)
        self.set_turn_timeout(0.1)
        clients, code = self.create_public_game()
        self.abandon_and_check(clients, code, can_pause=False)

    def test_disconnect_public(self):
        """
        Abandonar una partida pública supone que no se puede volver.
        """

        self.set_matchmaking_time(0.2)
        clients, code = self.create_public_game()

        # Para saber el orden de los turnos
        starting_turn = self.get_current_turn_client(clients)
        turn = clients.index(starting_turn)

        for i in range(len(clients)):
            logger.info(">> Trying as usual")
            # Antes de la desconexión funciona correctamente
            client = clients[turn]
            self.check_connection_works(client, start=True, can_pause=False)

            logger.info(">> Trying after reconnect")
            # Reconexión, no debería funcionar
            client = self.client_reconnect(clients, client)
            callback_args = client.emit("join", code, callback=True)
            self.assertIn("error", callback_args)

            turn = (turn + 1) % len(clients)

    def test_disconnect_private(self):
        """
        El jugador podrá reanudar el juego en cualquier momento antes de que
        acabe.
        """

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
            self.assertIn("bodies", args)
            self.assertIn("current_turn", args)
            self.assertIn("finished", args)

            # Comprobaciones simples
            self.check_connection_works(client, start=False)

            turn = (turn + 1) % len(clients)

    def test_reconnect_when_joining(self):
        """
        Comprueba un caso extremo de desconexión antes de que la partida sea
        comenzada.
        """

        # TODO

        clients = []
        for i in range(2):
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

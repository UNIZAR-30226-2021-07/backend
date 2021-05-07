"""
Tests para el manejo de conexiones de las partidas Se añade a continuación un
resumen de la funcionalidad de abandono y la funcionalidad de reconexión.

El botón de abandonar es pulsado:
- Pública: es eliminado y no se puede volver; el jugador es reemplazado por la
  IA.
- Privada: es eliminado y no se puede volver; las cartas del jugador van a la
  baraja.

Desconexión por error o botón de reanudar más tarde pulsado:
- Pública: se puede volver a la partida antes de que el jugador sea eliminado
  por considerarse AFK al pasar 3 turnos sin jugar, en cuyo caso es reemplazado
  por la IA.
- Privada: se puede volver a la partida y no habrá pasado nada porque en
  partidas privadas no se eliminan jugadores AFK.
"""

from gatovid.util import get_logger

from .base import WsTestClient

logger = get_logger(__name__)


class ConnTest(WsTestClient):
    def test_abandon_public(self):
        """
        Comprueba el abandono manual de una partida pública.
        """

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
        Se da el caso únicamente de forma manual.
        """

    def test_temporary_abandon_public(self):
        """
        Si el jugador que abandona temporalmente entra antes del tercer turno
        puede continuar jugando.
        """

    def test_temporary_abandon_private(self):
        """
        El jugador podrá reanudar el juego en cualquier momento antes de que
        acabe.
        """

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
        self.set_turn_timeout(0.5)
        clients, code = self.create_public_game()

        def active_turn_wait(client):
            print("STARTING")
            while True:
                received = client.get_received()
                if len(received) == 0:
                    continue

                print(received)
                _, args = self.get_msg_in_received(received, "game_update", json=True)
                if args is None:
                    continue
                if args.get("current_turn") is not None:
                    print("DONE")
                    return

        # Iteración completa antes de que el primer usuario sea eliminado.
        #
        # Tiene que ser más preciso que en el resto de tests porque es
        # acumulado, por lo que no se usa self.wait_turn_timeout() sino una
        # espera activa. Esto no debería ser un gran problema porque el tiempo
        # de espera es bajo.
        logger.info(">> Getting ready for players to be removed")
        self.clean_messages(clients)
        for i in range(2):  # Itera 2 veces
            for i in range(len(clients)):  # Por cada cliente
                self.wait_turn_timeout()
                print("repeated", clients[0].get_received())
                # active_turn_wait(clients[0])

            print("iter",clients[1].get_received())

        # En la siguiente iteración los usuarios son eliminados
        logger.info(">> Starting player removal loop")
        for i in range(len(clients)):
            self.clean_messages(clients)
            active_turn_wait(clients[0])

            client = self.get_current_turn_client(clients)
            print(client.get_received())

            # Intenta hacer cualquier acción pero devolverá un error
            received = clients[0].get_received()
            print(received)

            # Se continúa con el siguiente usuario a ser kickeado
            self.clean_messages(clients)
            clients.remove(client)

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

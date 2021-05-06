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

from .base import WsTestClient

# logger = get_logger(__name__)


class CardsTest(WsTestClient):
    def test_abandon_public(self):
        """
        Se puede dar el caso de abandono en una pública al estar AFK o de forma
        manual. Cuando la partida se quede con menos de 2 usuarios será
        cancelada.
        """

        self.set_matchmaking_time(0.2)
        clients, code = self.create_game()

        # Iteración completa antes de que el primer usuario sea eliminado
        for i in range(2):
            for i in range(len(clients)):
                self.wait_turn_timeout()

        # En la siguiente iteración los usuarios son eliminados
        for i in range(len(clients)):
            client = self.get_current_turn_client(clients)
            print(client.get_received())
            self.wait_turn_timeout()

            # Intenta hacer cualquier acción pero devolverá un error

            # Se continúa con el siguiente usuario a ser kickeado
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

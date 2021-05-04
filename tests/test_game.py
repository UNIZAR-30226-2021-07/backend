"""
Tests para la lógica del juego
"""

from gatovid.api.game.match import MM
from gatovid.create_db import (
    GENERIC_USERS_EMAIL,
    GENERIC_USERS_NAME,
    GENERIC_USERS_PASSWORD,
    NUM_GENERIC_USERS,
)
from gatovid.game.cards import Color, Medicine, Organ, Virus

from .base import WsTestClient

users_data = []
for i in range(NUM_GENERIC_USERS):
    users_data.append(
        {
            "email": GENERIC_USERS_EMAIL.format(i),
            "password": GENERIC_USERS_PASSWORD,
        }
    )


class GameTest(WsTestClient):
    player_names = [GENERIC_USERS_NAME.format(i) for i in range(NUM_GENERIC_USERS)]

    def create_game(self, players=6):
        clients = []
        for i in range(players):
            clients.append(self.create_client(users_data[i]))

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


    def test_card_interactions_infect_cure(self):
        """
        Se prueba a colocar un órgano, infectarlo y curarlo.
        """

        card_order = [
            Organ(color=Color.Red),
            Virus(color=Color.Red),
            Medicine(color=Color.Red),
        ]

        expected_pile_states = [
            # Se coloca el órgano en la pila
            {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
            # Se infecta el órgano
            {
                "modifiers": [{"card_type": "virus", "color": "red"}],
                "organ": {"card_type": "organ", "color": "red"},
            },
            # Se cura el órgano con la medicina
            {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
        ]

        self.check_card_interactions(card_order, expected_pile_states)

    def check_card_interactions(self, card_order, expected_pile_states):
        """
        Se prueba la secuencia de cartas card_order en la pila 0 del jugador 0
        y se comprueba que la interacción sea la deseada (expected_pile_states).
        """
        clients, code = self.create_game()

        # Primero se tendrá el game_update inicial
        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        # Obtenemos el cliente al que le toca

        game = MM.get_match(code)._game

        target = None
        for (i, card) in enumerate(card_order):
            turn_name = args["current_turn"]
            # Elegimos al primer jugador como el objetivo
            if target is None:
                target = turn_name

            turn_client = clients[self.player_names.index(args["current_turn"])]
            turn_player = next(filter(lambda p: p.name == turn_name, game.players))

            turn_player.hand[0] = card

            # Ignoramos los mensajes anteriores en un cliente cualquiera
            _ = clients[5].get_received()

            # Colocamos la carta en el jugador target. Las cartas se colocarán
            # en el orden de testing_hand y se espera que resulten en la pila 0
            # == expected_pile_states[i]
            callback_args = turn_client.emit(
                "play_card",
                {
                    "slot": 0,  # Las cartas en orden
                    "target": target,
                    "organ_pile": 0,
                },
                callback=True,
            )
            self.assertNotIn("error", callback_args)

            # Recibimos en un cliente cualquiera
            received = clients[5].get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertNotIn("error", args)

            self.assertIn("bodies", args)
            self.assertEqual(
                args["bodies"][target][0],  # Miramos la pila 0 del target
                expected_pile_states[i],
            )

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

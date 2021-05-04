"""
Tests para la lógica del juego
"""

from gatovid.api.game.match import MM
from gatovid.create_db import GENERIC_USERS_NAME, NUM_GENERIC_USERS
from gatovid.game.cards import Color, Medicine, Organ, Virus

from .base import WsTestClient


class CardsTest(WsTestClient):
    player_names = [GENERIC_USERS_NAME.format(i) for i in range(NUM_GENERIC_USERS)]

    def test_interactions_cure(self):
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

    def test_interactions_medicine_destroy(self):
        """
        Se prueba a destruir una vacuna.
        """

        card_order = [
            Organ(color=Color.Red),
            Medicine(color=Color.Red),
            Virus(color=Color.Red),
        ]

        expected_pile_states = [
            # Se coloca el órgano en la pila
            {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
            # Se protege el órgano
            {
                "modifiers": [{"card_type": "medicine", "color": "red"}],
                "organ": {"card_type": "organ", "color": "red"},
            },
            # Se destruye la medicina
            {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
        ]

        self.check_card_interactions(card_order, expected_pile_states)

    def test_interactions_immunize(self):
        """
        Se prueba a inmunizar un órgano.
        """

        card_order = [
            Organ(color=Color.Red),
            Medicine(color=Color.Red),
            Medicine(color=Color.Red),
        ]

        expected_pile_states = [
            # Se coloca el órgano en la pila
            {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
            # Se protege el órgano
            {
                "modifiers": [{"card_type": "medicine", "color": "red"}],
                "organ": {"card_type": "organ", "color": "red"},
            },
            # Se inmuniza el órgano
            {
                "modifiers": [
                    {"card_type": "medicine", "color": "red"},
                    {"card_type": "medicine", "color": "red"},
                ],
                "organ": {"card_type": "organ", "color": "red"},
            },
        ]

        self.check_card_interactions(card_order, expected_pile_states)

    def test_interactions_remove(self):
        """
        Se prueba a extirpar un órgano.
        """

        card_order = [
            Organ(color=Color.Red),
            Virus(color=Color.Red),
            Virus(color=Color.Red),
        ]

        expected_pile_states = [
            # Se coloca el órgano en la pila
            {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
            # Se infecta el órgano
            {
                "modifiers": [{"card_type": "virus", "color": "red"}],
                "organ": {"card_type": "organ", "color": "red"},
            },
            # Se extirpa el órgano
            {"modifiers": [], "organ": None},
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

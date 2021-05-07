"""
Tests para la lógica del juego
"""

from gatovid.api.game.match import MM
from gatovid.create_db import GENERIC_USERS_NAME, NUM_GENERIC_USERS
from gatovid.game.body import Body, OrganPile
from gatovid.game.cards import Color, Medicine, Organ, Virus

from .base import WsTestClient


class CardsTest(WsTestClient):
    player_names = [GENERIC_USERS_NAME.format(i) for i in range(NUM_GENERIC_USERS)]

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

        game = MM.get_match(code)._game

        # Usaremos al cliente 0 como target
        target = game.players[0].name

        for (i, card) in enumerate(card_order):
            # Cambiamos el turno según la carta para cumplir las restricciones
            # de no colocar medicina en el cuerpo de otros, etc.
            if isinstance(card, Organ) or isinstance(card, Medicine):
                game._turn = 0
            elif isinstance(card, Virus):
                game._turn = 1

            # Obtenemos el cliente al que le toca
            turn_player = game.players[game._turn]
            turn_client = clients[self.player_names.index(turn_player.name)]

            turn_player.hand[0] = card

            # Ignoramos los mensajes anteriores en un cliente cualquiera
            _ = clients[5].get_received()

            # Colocamos la carta en el jugador target. Las cartas se colocarán
            # en el orden de testing_hand y se espera que resulten en la pila 0
            # == expected_pile_states[i]
            callback_args = turn_client.emit(
                "play_card",
                {
                    "slot": 0,
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

    def check_can_place(self, target_body, card, place_in_self=False, can_place=True):
        """
        Se prueba a colocar la carta `card` en el cuerpo de otro jugador
        distinto (si `place_in_self` es True, el otro jugador es el mismo que
        usa la carta). El cuerpo inicial del jugador donde se va a colocar la
        carta será `target_body`.
        """
        clients, code = self.create_game()

        # Primero se tendrá el game_update inicial
        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        game = MM.get_match(code)._game

        turn_name = args["current_turn"]
        turn_client = clients[self.player_names.index(args["current_turn"])]
        turn_player = next(filter(lambda p: p.name == turn_name, game.players))
        if place_in_self:
            other_player = turn_player
        else:
            other_player = next(filter(lambda p: p.name != turn_name, game.players))

        turn_player.hand[0] = card
        other_player.body = target_body

        # Ignoramos los eventos anteriores
        _ = turn_client.get_received()

        # Intentamos colocar la carta en el jugador
        callback_args = turn_client.emit(
            "play_card",
            {
                "slot": 0,
                "target": other_player.name,
                "organ_pile": 0,
            },
            callback=True,
        )
        if can_place:
            self.assertNotIn("error", callback_args)
        else:
            self.assertIn("error", callback_args)

        received = turn_client.get_received()
        if can_place:
            self.assertNotEqual(received, [])
        else:
            # No recibimos el game_update
            self.assertEqual(received, [])

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

    def test_interactions_cure_multicolored(self):
        """
        Se prueba a colocar un órgano, infectarlo y curarlo alternando cartas
        multicolor.
        """

        self.check_card_interactions(
            card_order=[
                Organ(color=Color.All),
                Virus(color=Color.Red),
                Medicine(color=Color.Red),
            ],
            expected_pile_states=[
                # Se coloca el órgano en la pila
                {"modifiers": [], "organ": {"card_type": "organ", "color": "all"}},
                # Se infecta el órgano
                {
                    "modifiers": [{"card_type": "virus", "color": "red"}],
                    "organ": {"card_type": "organ", "color": "all"},
                },
                # Se cura el órgano con la medicina
                {"modifiers": [], "organ": {"card_type": "organ", "color": "all"}},
            ],
        )

        self.check_card_interactions(
            card_order=[
                Organ(color=Color.Red),
                Virus(color=Color.All),
                Medicine(color=Color.Green),
            ],
            expected_pile_states=[
                # Se coloca el órgano en la pila
                {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
                # Se infecta el órgano
                {
                    "modifiers": [{"card_type": "virus", "color": "all"}],
                    "organ": {"card_type": "organ", "color": "red"},
                },
                # Se cura el órgano con la medicina
                {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
            ],
        )

        self.check_card_interactions(
            card_order=[
                Organ(color=Color.Red),
                Virus(color=Color.Red),
                Medicine(color=Color.All),
            ],
            expected_pile_states=[
                # Se coloca el órgano en la pila
                {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
                # Se infecta el órgano
                {
                    "modifiers": [{"card_type": "virus", "color": "red"}],
                    "organ": {"card_type": "organ", "color": "red"},
                },
                # Se cura el órgano con la medicina
                {"modifiers": [], "organ": {"card_type": "organ", "color": "red"}},
            ],
        )

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

    def test_organ_on_others(self):
        """
        Se prueba que no se pueda colocar un órgano en el cuerpo de otro
        jugador.
        """
        self.check_can_place(
            target_body=Body(),
            card=Organ(color=Color.Red),
            place_in_self=False,
            can_place=False,
        )

    def test_organ_repeated(self):
        """
        Se prueba que no se pueda colocar un órgano repetido en el cuerpo.
        """
        b = Body()
        b.piles[1].set_organ(Organ(color=Color.Red))

        test_cases = [
            {
                "organ": Organ(color=Color.Red),
                "body": Body._from_data(
                    piles=[
                        OrganPile(),
                        OrganPile._from_data(organ=Organ(color=Color.Red)),
                        OrganPile(),
                        OrganPile(),
                    ]
                ),
                "can_place": False,
            },
            {
                "organ": Organ(color=Color.Green),
                "body": Body._from_data(
                    piles=[
                        OrganPile(),
                        OrganPile._from_data(organ=Organ(color=Color.Red)),
                        OrganPile._from_data(organ=Organ(color=Color.Blue)),
                        OrganPile(),
                    ]
                ),
                "can_place": True,
            },
            {
                "organ": Organ(color=Color.All),
                "body": Body._from_data(
                    piles=[
                        OrganPile(),
                        OrganPile._from_data(organ=Organ(color=Color.Red)),
                        OrganPile._from_data(organ=Organ(color=Color.Blue)),
                        OrganPile(),
                    ]
                ),
                "can_place": True,
            },
        ]

        for test in test_cases:
            self.check_can_place(
                target_body=test["body"],
                card=test["organ"],
                place_in_self=True,
                can_place=test["can_place"],
            )

    def test_modifier_on_empty_pile(self):
        """
        Se prueba que no se pueda colocar un modificador sin un órgano en la
        base de la pila.
        """
        self.check_can_place(
            target_body=Body(),
            card=Medicine(color=Color.Red),
            place_in_self=True,
            can_place=False,
        )

    def test_medicine_on_others(self):
        """
        Se prueba que no se pueda colocar una vacuna a otro jugador, para evitar
        errores de los jugadores.
        """
        b = Body()
        b.piles[0].set_organ(Organ(color=Color.Red))

        self.check_can_place(
            target_body=b,
            card=Medicine(color=Color.Red),
            place_in_self=False,
            can_place=False,
        )

    def test_virus_on_self(self):
        """
        Se prueba que no se pueda colocar un virus a ti mismo, para evitar
        errores de los jugadores.
        """
        b = Body()
        b.piles[0].set_organ(Organ(color=Color.Red))

        self.check_can_place(
            target_body=b,
            card=Virus(color=Color.Red),
            place_in_self=True,
            can_place=False,
        )

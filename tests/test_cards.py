"""
Tests para la lógica del juego
"""

import random
from dataclasses import asdict

from gatovid.api.game.match import MM
from gatovid.create_db import GENERIC_USERS_NAME, NUM_GENERIC_USERS
from gatovid.game.body import Body, OrganPile
from gatovid.game.cards import Color, LatexGlove, MedicalError, Infection, Medicine, Organ, Virus

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
                "body": Body.from_data(
                    piles=[
                        OrganPile(),
                        OrganPile.from_data(organ=Organ(color=Color.Red)),
                        OrganPile(),
                        OrganPile(),
                    ]
                ),
                "can_place": False,
            },
            {
                "organ": Organ(color=Color.Green),
                "body": Body.from_data(
                    piles=[
                        OrganPile(),
                        OrganPile.from_data(organ=Organ(color=Color.Red)),
                        OrganPile.from_data(organ=Organ(color=Color.Blue)),
                        OrganPile(),
                    ]
                ),
                "can_place": True,
            },
            {
                "organ": Organ(color=Color.All),
                "body": Body.from_data(
                    piles=[
                        OrganPile(),
                        OrganPile.from_data(organ=Organ(color=Color.Red)),
                        OrganPile.from_data(organ=Organ(color=Color.Blue)),
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

    def test_treatment_latex_glove(self):
        """
        Se prueba a usar el tratamiento Guante de látex y se comprueba que el
        resto de jugadores han descartado las cartas, mientras que el jugador
        que lanza el tratamiento conserva su mano (excepto la carta de
        tratamiento).
        """
        # HACK: Establecemos siempre la misma semilla para evitar el caso en el
        # que el random genere una mano igual a la que se tenia anteriormente.
        random.seed(10)
        clients, code = self.create_game()

        # Primero se tendrá el game_update inicial
        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        game = MM.get_match(code)._game
        # Forzamos el turno al client 0
        game._turn = 0

        turn_player = game.players[game._turn]
        turn_player.hand[0] = LatexGlove()
        last_hand = list(map(asdict, turn_player.hand.copy()))

        # Ignoramos los eventos anteriores en el resto de jugadores y guardamos
        # la mano anterior de estos.
        for client in clients[1:]:
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            # Guardamos en el cliente la mano anterior (para iterar facilmente)
            client.last_hand = args["hand"].copy()

        # Usamos la carta desde el cliente 0
        callback_args = clients[0].emit(
            "play_card",
            {
                "slot": 0,
            },
            callback=True,
        )
        self.assertNotIn("error", callback_args)

        for client in clients[1:]:
            # Comprobamos que al resto de jugadores les ha borrado la mano (se
            # habrán robado nuevas cartas al saltarles el turno).
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertNotIn("error", args)

            self.assertIn("hand", args)
            self.assertNotEqual(args["hand"], client.last_hand)

        # Comprobamos que el cliente que la lanza conserva su mano
        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        self.assertIn("hand", args)
        self.assertEqual(args["hand"][0], last_hand[1])
        self.assertEqual(args["hand"][1], last_hand[2])

    def test_treatment_medical_error(self):
        """
        Se prueba a usar el tratamiento Error Médico.
        """
        clients, code = self.create_game()

        caller_name = GENERIC_USERS_NAME.format(0)
        target_name = GENERIC_USERS_NAME.format(1)

        # Primero se tendrá el game_update inicial
        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        game = MM.get_match(code)._game
        # Forzamos el turno al client 0
        game._turn = 0

        caller_player = game.players[game._turn]
        caller_player.hand[0] = MedicalError()
        caller_player.body = Body.from_data(
            piles=[
                OrganPile(),
                OrganPile.from_data(organ=Organ(color=Color.Red)),
                OrganPile.from_data(
                    organ=Organ(color=Color.Blue),
                    modifiers=[
                        Virus(color=Color.Blue),
                    ],
                ),
                OrganPile(),
            ]
        )
        clients[0].last_body = asdict(caller_player.body)["piles"]

        # Ignoramos los eventos anteriores con el target
        received = clients[1].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        # Guardamos en el cliente el cuerpo anterior
        clients[1].last_body = asdict(Body())["piles"]

        # Ignoramos los eventos anteriores con el resto de los clientes
        for client in clients[2:]:
            _ = client.get_received()

        # Usamos la carta desde el cliente 0
        callback_args = clients[0].emit(
            "play_card",
            {
                "slot": 0,
                "target": target_name,
            },
            callback=True,
        )
        self.assertNotIn("error", callback_args)

        # Comprobamos que todos los clientes reciben los cuerpos intercambiados.
        for client in clients:
            received = client.get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertNotIn("error", args)

            self.assertIn("bodies", args)
            self.assertIn(caller_name, args["bodies"])
            self.assertIn(target_name, args["bodies"])
            self.assertEqual(args["bodies"][caller_name], clients[1].last_body)
            self.assertEqual(args["bodies"][target_name], clients[0].last_body)

    def test_treatment_infection(self):
        """
        Se prueba a usar el tratamiento Contagio.
        """
        clients, code = self.create_game(players=3)

        caller_name = GENERIC_USERS_NAME.format(0)

        # Primero se tendrá el game_update inicial
        received = clients[0].get_received()
        _, args = self.get_msg_in_received(received, "game_update", json=True)
        self.assertNotIn("error", args)

        game = MM.get_match(code)._game
        # Forzamos el turno al client 0
        game._turn = 0

        def organ(color: Color) -> OrganPile:
            return OrganPile.from_data(organ=Organ(color=color))

        def infected_organ(color: Color, virus_color: Color = None) -> OrganPile:
            if virus_color is None:
                virus_color = color

            return OrganPile.from_data(
                organ=Organ(color=color),
                modifiers=[
                    Virus(color=virus_color),
                ],
            )

        bodies = [
            {
                "have": [
                    infected_organ(Color.Yellow),
                    infected_organ(Color.Red, virus_color=Color.All),
                    infected_organ(Color.Blue),
                    # El virus de este no se debería colocar en ningún sitio
                    infected_organ(Color.Green),
                ],
                "expected": [
                    organ(Color.Yellow),
                    organ(Color.Red),
                    organ(Color.Blue),
                    infected_organ(Color.Green),
                ],
            },
            {
                "have": [
                    # Se debería colocar el multicolor
                    organ(Color.Red), 
                    # No se debería colocar en esta
                    infected_organ(Color.Green, virus_color=Color.All), 
                    OrganPile(),
                    organ(Color.Blue),
                ],
                "expected": [
                    infected_organ(Color.Red, virus_color=Color.All),
                    infected_organ(Color.Green, virus_color=Color.All),
                    OrganPile(),
                    infected_organ(Color.Blue),
                ],
            },
            {
                "have": [
                    OrganPile(),
                    # No se debería colocar en este
                    OrganPile.from_data(
                        organ=Organ(color=Color.Green),
                        modifiers=[Medicine(color=Color.Green)],
                    ),
                    OrganPile(),
                    organ(Color.Yellow),
                ],
                "expected": [
                    OrganPile(),
                    OrganPile.from_data(
                        organ=Organ(color=Color.Green),
                        modifiers=[Medicine(color=Color.Green)],
                    ),
                    OrganPile(),
                    infected_organ(Color.Yellow),
                ],
            },
        ]

        clients_order = map(lambda p: self.player_names.index(p.name), game.players)

        # Para todos los clientes, inicializamos su cuerpo al cuerpo de pruebas
        # y le damos la carta de contagio al cliente 0.
        for (i, which_client) in enumerate(clients_order):
            client = clients[which_client]
            player = game.players[i]

            player = game.players[0]
            if which_client == 0:
                player.hand[0] = Infection()
            player.body = Body.from_data(piles=bodies[i]["have"])

        # Ignoramos los eventos anteriores con los clientes
        for client in clients:
            _ = client.get_received()

        # Usamos la carta desde el cliente 0
        callback_args = clients[0].emit("play_card", {"slot": 0}, callback=True)
        self.assertNotIn("error", callback_args)

        # Comprobamos que todos los clientes reciben los cuerpos esperados.
        for (i, which_client) in enumerate(clients_order):
            client = clients[which_client]
            player = game.players[i]

            received = client.get_received()
            _, args = self.get_msg_in_received(received, "game_update", json=True)
            self.assertNotIn("error", args)

            self.assertIn("bodies", args)
            self.assertIn(player.name, args["bodies"])
            self.assertEqual(args["bodies"][player.name], bodies[i]["expected"])

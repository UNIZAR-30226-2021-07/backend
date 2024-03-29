from gatovid.game import Game, GameUpdate
from gatovid.models import User

from .base import GatovidTestClient

USERS = [
    User(name="test_1"),
    User(name="test_2"),
]


class UpdateTest(GatovidTestClient):
    def get_game(self) -> Game:
        game = Game(users=USERS, turn_callback=self.empty_callback, enable_ai=False)
        return game

    def test_full(self):
        """
        Comprueba que un GameUpdate es lo esperado tras una secuencia de
        operaciones.
        """

        game = self.get_game()
        game.start()

        update = GameUpdate(game)
        self.assertEqual(update.as_dict(), {"test_1": {}, "test_2": {}})

        update.repeat({"hand": 1234})
        self.assertEqual(
            update.as_dict(), {"test_1": {"hand": 1234}, "test_2": {"hand": 1234}}
        )

        update.add_for_each(lambda p: {"thing": p.name})
        self.assertEqual(
            update.as_dict(),
            {
                "test_1": {"hand": 1234, "thing": "test_1"},
                "test_2": {"hand": 1234, "thing": "test_2"},
            },
        )

        update.add("test_1", {"list": ["foo", "bar"]})
        self.assertEqual(
            update.as_dict(),
            {
                "test_1": {"hand": 1234, "thing": "test_1", "list": ["foo", "bar"]},
                "test_2": {"hand": 1234, "thing": "test_2"},
            },
        )

        update_test_1 = update.get("test_1")
        self.assertEqual(
            update_test_1,
            {"hand": 1234, "thing": "test_1", "list": ["foo", "bar"]},
        )

        new_update = GameUpdate(game)
        new_update.repeat({"from_new": 1.4})
        update.merge_with(new_update)
        self.assertEqual(
            update.as_dict(),
            {
                "test_1": {
                    "hand": 1234,
                    "thing": "test_1",
                    "list": ["foo", "bar"],
                    "from_new": 1.4,
                },
                "test_2": {"hand": 1234, "thing": "test_2", "from_new": 1.4},
            },
        )

    def test_repeated(self):
        """
        Comprueba el caso especial en el que los datos son los mismos para todos
        los usuarios para hacer un broadcast.
        """

        game = self.get_game()
        game.start()

        update = GameUpdate(game)
        self.assertTrue(update.is_repeated)

        update.repeat({"thing": "abc"})
        self.assertEqual(
            update.as_dict(), {"test_1": {"thing": "abc"}, "test_2": {"thing": "abc"}}
        )
        self.assertTrue(update.is_repeated)

        update.add("test_1", {"foo": "bar"})
        self.assertFalse(update.is_repeated)

        self.assertRaises(ValueError, lambda: update.get_any())

    def test_recursive_merge(self):
        """
        Comprueba que los mergeos de datos son recursivos y no únicamente del
        primer nivel.
        """

        game = self.get_game()
        game.start()

        update = GameUpdate(game)
        update.repeat({"bodies": {"marcuspkz": 1234}})
        update.repeat({"bodies": {"zebra": 444}})
        update.repeat({"bodies": {"becario": {"a": 1, "b": 2}}})
        update.repeat({"bodies": {"becario": {"a": 2, "c": 3}}})
        update.add("test_1", {"bodies": 1})
        update.add("test_2", {"hand": 1234.1234})
        self.assertEqual(
            update.as_dict(),
            {
                "test_1": {"bodies": 1},
                "test_2": {
                    "bodies": {
                        "marcuspkz": 1234,
                        "zebra": 444,
                        "becario": {"a": 2, "b": 2, "c": 3},
                    },
                    "hand": 1234.1234,
                },
            },
        )

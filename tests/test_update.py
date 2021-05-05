from gatovid.game import Game, GameUpdate
from gatovid.models import User

from .base import GatovidTestClient

USERS = [
    User(name="test_1"),
    User(name="test_2"),
]


class UpdateTest(GatovidTestClient):
    def get_game(self) -> Game:
        game = Game(users=USERS, turn_callback=lambda **kwargs: {}, enable_ai=False)
        return game

    def test_full(self):
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

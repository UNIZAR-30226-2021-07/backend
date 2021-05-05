from .base import GatovidTestClient

from gatovid.game import GameUpdate, Game
from gatovid.models import User

USERS = [
    User(name="test_1"),
    User(name="test_2"),
]


class UpdateTest(GatovidTestClient):
    def get_game(self) -> Game:
        game = Game(users=USERS, turn_callback=lambda: {}, enable_ai=False)
        return game

    def test_full(self):
        game = self.get_game()
        game.start()

        update = GameUpdate(game)
        self.assertEqual(update.as_dict(), {
            "test_1": {},
            "test_2": {}
        })

        new_update = GameUpdate(game)
        new_update.repeat({"hand": 1234})
        self.assertEqual(update.as_dict(), {
            "test_1": {"hand": 1234},
            "test_2": {"hand": 1234}
        })

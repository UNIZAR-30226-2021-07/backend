from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from gatovid.game import Game


class GameLogicException(Exception):
    """
    Esta excepción se usa para indicar casos erróneos o inesperados en el juego.
    """


@dataclass(init=False)
class GameUpdate:
    """
    Una clase para game_update por type safety y comodidad/legibilidad de uso.
    """

    game: "Game"
    _data: Dict

    def __init__(self, game: "Game") -> None:
        self.game = game
        # Los datos consisten en un diccionario con el nombre del jugador como
        # clave y su información en el valor.
        self._data = {}

        for player in self.game.players:
            self._data[player.name] = {}

    def __iter__(self):
        for player_name, value in self._data:
            yield player_name, value

    def as_dict(self) -> Dict:
        return self._data

    def get_any(self) -> Dict:
        """
        Asumiendo que los valores de cada jugador son iguales, lo devuelve. Esto
        es útil por ejemplo para hacer un broadcast del mismo mensaje.
        """

        expected_val = next(iter(self._data.values()))
        all_equal = all(val == expected_val for val in self._data.values())
        if not all_equal:
            raise ValueError("No todos los GameUpdate son iguales")

        return expected_val

    def get(self, player_name: str) -> Dict:
        return self._data[player_name]

    def add(self, player_name: str, value: Dict) -> None:
        self._data[player_name] = {**self._data[player_name], **value}

    def add_for_each(self, mapping) -> None:
        for player in self.game.players:
            old_data = self._data[player.name]
            new_data = mapping(player)
            self._data[player.name] = {**old_data, **new_data}

    def repeat(self, value: Dict) -> None:
        for player in self.game.players:
            old_data = self._data[player.name]
            self._data[player.name] = {**old_data, **value}

    def merge_with(self, other: "GameUpdate") -> None:
        if self.game != other.game:
            raise ValueError("Juegos incompatibles")

        if len(self._data) != len(other._data):
            raise ValueError("Tamaños incompatibles mezclando game_updates")

        for player in self.game.players:
            data_self = self.get(player.name)
            data_other = other.get(player.name)

            intersection = data_self.keys() & data_other.keys()
            if len(intersection) != 0:
                raise ValueError(f"Duplicate keys: {intersection}")

            self._data[player.name] = {**data_self, **data_other}

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from gatovid.game import Game


class GameLogicException(Exception):
    """
    Esta excepción se usa para indicar casos erróneos o inesperados en el juego.
    """


def merge_dict(d1: Dict, d2: Dict) -> None:
    """
    Modifies d1 in-place to contain values from d2.  If any value
    in d1 is a dictionary (or dict-like), *and* the corresponding
    value in d2 is also a dictionary, then merge them in-place.
    """

    for k, v2 in d2.items():
        v1 = d1.get(k)
        if isinstance(v1, dict) and isinstance(v2, dict):
            merge_dict(v1, v2)
        else:
            d1[k] = v2


@dataclass(init=False)
class GameUpdate:
    """
    Una clase para game_update por type safety y comodidad/legibilidad de uso.
    """

    game: "Game"
    _data: Dict

    def __init__(self, game: "Game", msg: str = None) -> None:
        self.game = game
        # Los datos consisten en un diccionario con el nombre del jugador como
        # clave y su información en el valor.
        self._data = {}
        # Para saber si todos los valores son los mismos
        self.is_repeated = True
        # Mensaje adicional, opcionalmente
        self.msg = msg

        for player in self.game.players:
            self._data[player.name] = {}

    def __iter__(self):
        for player_name, value in self._data:
            yield player_name, value

    def as_dict(self) -> Dict:
        return self._data

    def fmt_msg(self, caller: str) -> Optional[str]:
        if self.msg is None:
            return None

        return f"{caller} ha jugado {self.msg}"

    def get_any(self) -> Dict:
        """
        Asumiendo que los valores de cada jugador son iguales, lo devuelve. Esto
        es útil por ejemplo para hacer un broadcast del mismo mensaje.
        """

        if not self.is_repeated:
            raise ValueError("No todos los GameUpdate son iguales")

        first_val = next(iter(self._data.values()))
        return first_val

    def get(self, player_name: str) -> Dict:
        return self._data[player_name]

    def add(self, player_name: str, value: Dict) -> None:
        self.is_repeated = False
        if player_name in self._data:
            merge_dict(self._data[player_name], value)
        else:
            self._data[player_name] = value

    def add_for_each(self, mapping) -> None:
        self.is_repeated = False
        for player in self.game.players:
            merge_dict(self._data[player.name], mapping(player))

    def repeat(self, value: Dict) -> None:
        for player in self.game.players:
            merge_dict(self._data[player.name], value)

    def merge_with(self, other: "GameUpdate") -> None:
        if self.game != other.game:
            raise ValueError("Juegos incompatibles")

        if not other.is_repeated:
            self.is_repeated = False

        if self.msg is not None and other.msg is not None:
            raise ValueError("Mensajes incompatibles")

        if other.msg is not None:
            self.msg = self.msg

        merge_dict(self.as_dict(), other.as_dict())

"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from dataclasses import dataclass
from typing import List, Optional

from gatovid.game.cards import Color, Medicine, Organ, SimpleCard, Virus
from gatovid.game.common import GameLogicException


@dataclass(init=False)
class OrganPile:
    """
    Pila de cartas encima de un órgano.

    NOTE: se deberían usar las funciones para acceder a los atributos. Por
    cuestiones de exportado a JSON se tienen que declarar sin la convención de
    '_' antes del nombre.
    """

    organ: Optional[Organ]
    modifiers: List[SimpleCard]

    def __init__(self):
        # Órgano base de la pila sobre el que se añadirán modificadores.
        self.organ: Optional[Organ] = None
        # Modificadores (cartas simples) que infectan, protejen o inmunizan al
        # órgano.
        self.modifiers: List[SimpleCard] = []

    def set_organ(self, organ: Organ):
        """
        Establece el órgano como base de la pila.
        """
        self.organ = organ

    def remove_organ(self):
        """
        Extirpar el órgano. Se elimina el órgano de la base de la pila y las
        cartas modificadoras.
        """
        self.pop_modifiers()
        self.organ = None

    def add_modifier(self, modifier: SimpleCard):
        self.modifiers.append(modifier)

    def pop_modifiers(self):
        self.modifiers.clear()

    def is_empty(self) -> bool:
        return not self.organ

    def is_infected(self) -> bool:
        return len(self.modifiers) > 0 and isinstance(self.modifiers[0], Virus)

    def is_protected(self) -> bool:
        return len(self.modifiers) > 0 and isinstance(self.modifiers[0], Medicine)

    def is_immune(self) -> bool:
        return (
            len(self.modifiers) > 1
            and isinstance(self.modifiers[0], Medicine)
            and isinstance(self.modifiers[1], Medicine)
        )

    def has_possible_color(self, card: SimpleCard) -> bool:
        """
        Devuelve True si el color de la carta `card` es compatible con las
        cartas de la pila.
        """

        if len(self.modifiers) == 0:
            # Si no hay modificadores, comprobamos si el color del modificador es
            # compatible con el del órgano.
            last_color = self.organ.color
        else:
            # Si hay modificadores, comprobamos si el color es compatible con el
            # anterior modificador.
            last_color = self.modifiers[-1].color

        return last_color == card.color or Color.All in (last_color, card.color)

    def can_place(self, card: SimpleCard) -> bool:
        # Solo se puede colocar un órgano en un montón vacío
        if isinstance(card, Organ):
            return self.is_empty()
        elif self.is_empty():
            # No podemos añadir modificadores si no hay órgano.
            return False

        # Comprobamos si los colores son iguales o alguna de las dos es un color
        # comodín.
        if not self.has_possible_color(card):
            return False

        # Si el órgano ya está inmunizado, no se pueden colocar más cartas.
        if self.is_immune():
            return False

        return True


@dataclass(init=False)
class Body:
    """
    Información relativa al cuerpo de un jugador.
    """

    # Los elementos de la pila nunca serán nulos, pero posiblemente los miembros
    # dentro de `OrganPile` sí que estén vacíos.
    piles: List[OrganPile]

    def __init__(self):
        self.piles = []
        for i in range(4):
            self.piles.append(OrganPile())

    def get_pile(self, pile: int) -> OrganPile:
        if pile < 0 or pile > 3:
            raise GameLogicException("Slot de pila inválido")

        if self.piles[pile] is None:
            self.piles[pile] = OrganPile()
        return self.piles[pile]

    def organ_unique(self, organ: Organ) -> bool:
        """
        Devuelve True si el órgano no está repetido en el cuerpo.
        """
        if organ.color == Color.All:
            return True

        for pile in self.piles:
            if pile.organ is None:
                continue

            if pile.organ.color == organ.color:
                return False

        return True

"""
Implementación de los objetos que almacenan los cuerpos de los jugadores y las
pilas de cartas dentro de los cuerpos.
"""

from typing import List, Optional

from gatovid.game.cards import Color, Medicine, Organ, SimpleCard, Virus


class OrganPile:
    """
    Pila de cartas encima de un órgano.
    """

    def __init__(self):
        # Órgano base de la pila sobre el que se añadirán modificadores.
        self.organ: Optional[Organ] = None
        # Modificadores (cartas simples) que infectan, protejen o inmunizan.
        self.modifiers: List[SimpleCard] = []

    def set_organ(self, organ: Organ):
        """
        Establece el órgano como base de la pila.
        """
        self.organ = organ

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

    def can_place(self, card: SimpleCard) -> bool:
        return self.organ.color == card.color or Color.Any in [
            self.organ.color,
            card.color,
        ]


class Body:
    """
    Información relativa al cuerpo de un jugador.
    """

    def __init__(self):
        self.piles: List[OrganPile] = [OrganPile() for i in range(4)]

    def add_organ(self, organ: Organ):
        # TODO: Lanzar alguna excepción en caso de no encontrar un hueco
        for pile in self.piles:
            if self.is_empty():
                pile.set_organ(organ)
                return

    def get_pile(self, pile: int) -> OrganPile:
        # TODO: Lanzar excepción en caso de pila incorrecta
        return self.piles[pile]

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
        self._organ: Optional[Organ] = None
        # Modificadores (cartas simples) que infectan, protejen o inmunizan al
        # órgano.
        self._modifiers: List[SimpleCard] = []

    def set_organ(self, organ: Organ):
        """
        Establece el órgano como base de la pila.
        """
        self._organ = organ

    def remove_organ(self):
        """
        Extirpar el órgano. Se elimina el órgano de la base de la pila y las
        cartas modificadoras.
        """
        self.pop_modifiers()
        self._organ = None

    def add_modifier(self, modifier: SimpleCard):
        self._modifiers.append(modifier)

    def pop_modifiers(self):
        self._modifiers.clear()

    def is_empty(self) -> bool:
        return not self._organ

    def is_infected(self) -> bool:
        return len(self._modifiers) > 0 and isinstance(self._modifiers[0], Virus)

    def is_protected(self) -> bool:
        return len(self._modifiers) > 0 and isinstance(self._modifiers[0], Medicine)

    def is_immune(self) -> bool:
        return (
            len(self._modifiers) > 1
            and isinstance(self._modifiers[0], Medicine)
            and isinstance(self._modifiers[1], Medicine)
        )

    def can_place(self, card: SimpleCard) -> bool:
        # Solo se puede colocar un órgano en un montón vacío
        if isinstance(card, Organ):
            return self.is_empty()
        elif self.is_empty(): 
            # No podemos añadir modificadores si no hay órgano.
            return False

        # Comprobamos si los colores son iguales o alguna de las dos es un color
        # comodín.
        if (self._organ.color != card.color and
            Color.Any not in [self._organ.color, card.color]):
            return False

        # Si el órgano ya está inmunizado, no se pueden colocar más cartas.
        if self.is_immune():
            return False

        return True


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

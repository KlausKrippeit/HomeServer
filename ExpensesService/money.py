"""Geldbeträge als ganzzahlige Cent-Werte (keine Float-Arithmetik)."""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal('0.01')
MAX_CENTS = 10_000_000 * 100


@dataclass(frozen=True, order=True)
class Money:
    """Unveränderlicher Geldbetrag in Cent."""

    cents: int

    @classmethod
    def from_decimal(cls, value):
        """Erzeugt einen Betrag aus Decimal, kaufmännisch auf Cent gerundet."""
        quantized = Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
        return cls(int(quantized * 100))

    @classmethod
    def from_string(cls, text):
        """Liest '12,50' oder '12.50'."""
        try:
            return cls.from_decimal(Decimal(text.strip().replace(',', '.')))
        except InvalidOperation as error:
            raise ValueError('Gib einen gültigen Betrag ein.') from error

    @classmethod
    def from_legacy_float(cls, value):
        """Übernimmt Alt-Float-Werte über ihre kürzeste Textdarstellung."""
        return cls.from_decimal(Decimal(str(value)))

    def __add__(self, other):
        return Money(self.cents + other.cents)

    def to_decimal(self):
        return Decimal(self.cents) / 100

    def format(self):
        """Deutsche Darstellung ohne Währungssymbol, z. B. '1.234,50' -> '1234,50'."""
        sign = '-' if self.cents < 0 else ''
        euros, cents = divmod(abs(self.cents), 100)
        return f'{sign}{euros},{cents:02d}'

    def __str__(self):
        return f'{self.format()} €'


ZERO = Money(0)


def total(amounts):
    """Summiert Money-Werte; einzige Stelle für Summenbildung."""
    result = ZERO
    for amount in amounts:
        result = result + amount
    return result

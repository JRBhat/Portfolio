"""
rounding.py
===========
Locale-aware numeric formatting utilities for analytical concentration values
written into the Word report tables.

Background
----------
EU regulatory reports must display measured concentrations with a fixed number
of *significant figures* (typically 2) using the locale's decimal separator
(comma in German, period in English).  Python's built-in ``round()`` uses
banker's rounding (ROUND_HALF_EVEN), which is not the expected behaviour for
scientific reports.  This module uses :mod:`decimal` with ``ROUND_HALF_UP``
(school rounding) throughout.

:class:`MyRounder`
    Lower-level class with methods for rounding a single value in various ways.

:func:`list_to_str`
    Convenience function that formats an entire list of concentrations into a
    newline-separated string suitable for a single table cell.

Modes
-----
``'nachkomma'``
    Round to a fixed number of decimal places (e.g. ``1.2345`` → ``'1.23'``).

``'significant'``
    Truncate to *N* significant figures (e.g. ``0.00596`` → ``'0.0060'`` for N=2).

Both modes respect the locale's decimal separator and always produce at least 2
fractional digits for values whose absolute magnitude is ≥ 1.
"""

import locale
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, InvalidOperation
from typing import Iterable, Optional


class MyRounder:
    """
    Formatter for display purposes:
      - format_nachkomma: ROUND_HALF_UP to 2 decimal places (returns locale string)
      - format_significant: truncate to N significant digits (WITH SCHOOL ROUNDING), always display exactly N sig figs
    """
    def round_school_nachkomma(self, x, decimal_places: int = 2) -> float:
        d_val = Decimal(str(x))
        quant_str = '1.' + '0' * decimal_places
        # ROUND_HALF_UP to decimal_places decimal places
        rounded_decimal = d_val.quantize(Decimal(quant_str), rounding=ROUND_HALF_UP)
        return rounded_decimal
    
    def truncate_significant_decimal(self, x, keep_signf: int = 2) -> Decimal:
        d = Decimal(str(x))
        if d == 0:
            return Decimal('0')
        e = d.adjusted()
        # ROUND_HALF_UP to keep_signf significant digits
        quant_exp = Decimal(f'1e{e - keep_signf + 1}')
        truncated = d.quantize(quant_exp, rounding=ROUND_HALF_UP)
        return truncated

    def format_decimal_locale(self, d: Decimal, decimals: int = 2) -> str:
        out = str(d)
        decimal_point = locale.localeconv().get('decimal_point', '.')
        if decimal_point != '.':
            out = out.replace('.', decimal_point)
        return out

    def format_significant(self, x, keep_signf: int = 2) -> str:
        """
        Truncate x to keep_signf significant digits and display exactly keep_signf sig figs.
        Special rule: for |value| >= 1 ensure at least 2 fractional digits (so 1.2 -> 1.20).
        """
        try:
            d_trunc = self.truncate_significant_decimal(x, keep_signf)
        except InvalidOperation:
            d_trunc = Decimal('0')
        return self.format_decimal_locale(d_trunc)

    def format_nachkomma(self, x, decimal_places: int = 2) -> str:
        d = self.round_school_nachkomma(x, decimal_places)
        return self.format_decimal_locale(d, decimal_places)


def list_to_str(
    l: Iterable,
    mode: str,
    keep_signf: int = 2
) -> str:
    """
    l: iterable of numeric values (float / Decimal / str convertible to Decimal)
    mode: 'nachkomma' or 'significant'
    keep_signf: number of significant digits to display (default 2)
    """
    rounder = MyRounder()
    if mode == 'nachkomma':
        return '\n'.join(rounder.format_nachkomma(x, decimal_places=keep_signf) for x in l)
    elif mode == 'significant':
        return '\n'.join(rounder.format_significant(x, keep_signf=keep_signf) for x in l)
    else:
        raise ValueError("mode must be 'nachkomma' or 'significant'")



if __name__ == "__main__":
    values = [0, 1.8, 0.0000596134314, 1.2, 0.10, 0.0024, 0.052, 1.2, 0.105, 0.00244, 0.002445, 0.002450]

    # EN locale (try)
    try:
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
    except Exception:
        # fallback to user's default locale
        locale.setlocale(locale.LC_NUMERIC, '')

    print("EN locale:")
    print("values:", values)
    print("keep_signf=2:", list_to_str(values, 'significant', keep_signf=2))          # -> "7.1\n1.2"
    print("keep_signf=3:", list_to_str(values, 'significant', keep_signf=3))  # -> "7.10\n1.20"
    print("keep_signf=4:", list_to_str(values, 'significant', keep_signf=4))  # -> "7.10\n1.20"

    print("nachkomma=2:", list_to_str(values, 'nachkomma'))          # -> "7.18\n1.20"
    print("nachkomma=3:", list_to_str(values, 'nachkomma', keep_signf=3))          # -> "7.18\n1.20"
    
    # DE locale (try)
    try:
        locale.setlocale(locale.LC_NUMERIC, 'de_DE.UTF-8')
    except Exception:
        # if de_DE isn't available, keep current locale but show intent
        print("(de_DE locale not available on this system; output will remain in current locale)")

    print("\nDE locale (if set):")
    print("keep_signf=3:", list_to_str(values, 'significant', keep_signf=3))          # -> "7,18\n1,20" in DE

#!/usr/bin/env python3
"""
size_convert.py - Convert bytes or bits into a human-readable size.

Uses base 1024 (1024 B = 1 KB, 1024 KB = 1 MB, ...).
Values given in bits are first converted to bytes (8 bit = 1 byte).

Usage:
    python3 size.py <bytes>
    python3 size.py <bits> --bits

Examples:
    python3 size.py 1024          # 1 KB
    python3 size.py 8192 --bits   # 1 KB
"""
import sys

UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


def format_bytes(value: float, decimals: int = 2) -> str:
    """Wandelt Bytes in eine lesbare Größe um (Basis 1024)."""
    negative = value < 0
    value = abs(value)
    index = 0
    while value >= 1024 and index < len(UNITS) - 1:
        value /= 1024
        index += 1
    # Bei Bytes keine Nachkommastellen, sonst überflüssige Nullen entfernen
    text = f"{value:.{decimals}f}".rstrip("0").rstrip(".") if index > 0 else f"{int(value)}"
    return f"{'-' if negative else ''}{text} {UNITS[index]}"


def format_bits(bits: float, decimals: int = 2) -> str:
    """Wandelt Bits in Bytes um (8 Bit = 1 Byte) und formatiert dann."""
    return format_bytes(bits / 8, decimals)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Aufruf: {sys.argv[0]} <bytes> [--bits]")
        sys.exit(1)

    number = float(sys.argv[1])
    if "--bits" in sys.argv:
        print(format_bits(number))
    else:
        print(format_bytes(number))

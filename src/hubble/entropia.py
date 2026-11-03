"""Entropía por bloques (bits por byte, de 0 a 8).

Código y tablas sin comprimir suelen quedar muy por debajo de 7. Si casi todo el
fichero está por encima de ~7,5, lo más probable es que esté comprimido o cifrado,
y entonces el primer paso es averiguar cómo, no desensamblar.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

UMBRAL_ALTA = 7.5


@dataclass(frozen=True)
class Bloque:
    desplazamiento: int
    tamano: int
    entropia: float


def shannon(datos: bytes) -> float:
    if not datos:
        return 0.0
    n = len(datos)
    return -sum(c / n * math.log2(c / n) for c in Counter(datos).values())


def por_bloques(datos: bytes, tamano: int = 256) -> list[Bloque]:
    if tamano <= 0:
        raise ValueError("el tamaño de bloque debe ser positivo")
    return [Bloque(i, len(datos[i : i + tamano]), shannon(datos[i : i + tamano])) for i in range(0, len(datos), tamano)]


def proporcion_alta(bloques: list[Bloque], umbral: float = UMBRAL_ALTA) -> float:
    """Fracción de bytes en bloques por encima del umbral."""
    total = sum(b.tamano for b in bloques)
    return sum(b.tamano for b in bloques if b.entropia >= umbral) / total if total else 0.0

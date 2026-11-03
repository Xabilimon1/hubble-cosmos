"""Comparación de cabeceras entre ficheros del mismo tipo.

Con varios `.omd` a la vista, los bytes que no cambian suelen ser la «magia» y la
versión del formato, y los enteros que coinciden con el tamaño del fichero o que
apuntan dentro de él suelen ser longitudes y desplazamientos de secciones.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class Byte:
    desplazamiento: int
    constante: bool
    valores: tuple[int | None, ...]  # None si el fichero es más corto


@dataclass(frozen=True)
class Candidato:
    """Entero de 2 o 4 bytes que, en TODOS los ficheros, cumple la misma relación."""

    desplazamiento: int
    ancho: int
    orden: str  # "<" little-endian, ">" big-endian
    relacion: str  # "tamaño del fichero", "tamaño menos N", "apunta dentro del fichero"
    valores: tuple[int, ...]


def comparar(cabeceras: list[bytes], n: int = 64) -> list[Byte]:
    """Para cada uno de los primeros `n` bytes: si es igual en todos los ficheros."""
    salida = []
    for i in range(n):
        vals = tuple(c[i] if i < len(c) else None for c in cabeceras)
        constante = None not in vals and len(set(vals)) == 1
        salida.append(Byte(i, constante, vals))
    return salida


def candidatos(ficheros: list[bytes], n: int = 64) -> list[Candidato]:
    """Enteros en la cabecera relacionados con el tamaño de cada fichero.

    Solo se proponen relaciones que se cumplen en todos los ficheros, y un puntero
    solo si los valores no son todos iguales (un valor fijo es más bien una constante).
    """
    if len(ficheros) < 2:
        raise ValueError("hacen falta al menos dos ficheros para comparar")
    salida: list[Candidato] = []
    for ancho, formato in ((4, "I"), (2, "H")):
        for orden in ("<", ">"):
            for off in range(0, n - ancho + 1):
                if any(len(f) < off + ancho for f in ficheros):
                    continue
                vals = tuple(struct.unpack_from(orden + formato, f, off)[0] for f in ficheros)
                tamanos = [len(f) for f in ficheros]
                difs = {t - v for v, t in zip(vals, tamanos)}
                if len(difs) == 1:
                    d = difs.pop()
                    if d == 0:
                        rel = "tamaño del fichero"
                    elif 0 < d <= n:
                        rel = f"tamaño menos {d}"
                    else:
                        rel = ""
                    if rel:
                        salida.append(Candidato(off, ancho, orden, rel, vals))
                        continue
                if len(set(vals)) > 1 and all(n <= v < t for v, t in zip(vals, tamanos)):
                    salida.append(Candidato(off, ancho, orden, "apunta dentro del fichero", vals))
    return salida

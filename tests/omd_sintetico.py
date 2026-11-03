"""Construye `.omd` sintéticos con la estructura de contenedor observada en los kits.

Cada lista es una secuencia de (etiqueta, n, tam_registro, bytes_de_datos). Si
`bytes_de_datos` es None, la sección ocupa n * tam_registro bytes; si no, ocupa
exactamente esos bytes (secciones de longitud variable como IDE o STR).
"""

from __future__ import annotations

import struct

MAGIA = bytes.fromhex("434f4d4401000000307200001400000014000000464646465656565638000000")
TAM_CABECERA = 0x4C
TAM_ENTRADA = 32
FIN = 0xFFFFFFFF

Seccion = tuple[str, int, int, "int | None"]


def _relleno(n: int, rec: int, extra: int | None) -> bytes:
    return bytes(n * rec if extra is None else extra)


def construir(a: list[Seccion], b: list[Seccion], c: list[Seccion], marca: int = 2) -> bytes:
    """Fichero completo: cabecera, y por cada lista sus entradas seguidas de sus datos."""
    cuerpo = bytearray()
    inicios = []
    base = TAM_CABECERA
    for lista in (a, b, c):
        inicio = base + len(cuerpo)
        inicios.append(inicio)
        datos = inicio + TAM_ENTRADA * len(lista)
        entradas = bytearray()
        contenido = bytearray()
        for k, (etq, n, rec, extra) in enumerate(lista):
            sig = FIN if k == len(lista) - 1 else inicio + TAM_ENTRADA * (k + 1)
            entradas += struct.pack("<5I", marca, 0, TAM_ENTRADA, sig, datos + len(contenido))
            entradas += etq.encode("ascii").ljust(4, b"\x00") + struct.pack("<2I", n, rec)
            contenido += _relleno(n, rec, extra)
        cuerpo += entradas + contenido
    cabecera = MAGIA + struct.pack("<3I", *inicios) + bytes(TAM_CABECERA - len(MAGIA) - 12)
    return cabecera + bytes(cuerpo)


def registro(texto: bytes, valor: int = 0, bits: int = 64, resto: bytes = b"") -> bytes:
    """Un registro empaquetado: u32 valor + texto + NUL (+ restos), hasta acabar en un 0
    al final de una unidad: primero 8 bytes y luego de 4 (32 bits) o de 8 (64 bits)."""
    u = 8 if bits == 64 else 4
    crudo = struct.pack("<I", valor) + texto + b"\x00" + resto
    largo = 8
    while largo < len(crudo) or (crudo + bytes(largo))[largo - 1] != 0:
        largo += u
    return crudo.ljust(largo, b"\x00")


def binario(cuerpo: bytes, tipo: int = 1, bits: int = 64) -> bytes:
    """Un registro binario de SVL: u32 (tipo << 16 | longitud) + cuerpo, relleno hasta la unidad."""
    u = 8 if bits == 64 else 4
    crudo = struct.pack("<I", tipo << 16 | (4 + len(cuerpo))) + cuerpo
    return crudo.ljust(-(-len(crudo) // u) * u, b"\x00")


def empaquetar(registros: list[bytes], tam_registro: int, tope: int | None = None, sobrante: bytes = b"") -> bytes:
    """Sección empaquetada: u32 n, u16 nº de bloques y bloques (u16 tope, u16 tamaño, datos).
    Los registros no se parten entre bloques; `sobrante` va al final del último."""
    tope = 32 * tam_registro if tope is None else tope
    bloques: list[bytes] = [b""]
    for r in registros:
        if bloques[-1] and len(bloques[-1]) + len(r) > tope:
            bloques.append(b"")
        bloques[-1] += r
    bloques[-1] += sobrante
    salida = struct.pack("<IH", len(registros), len(bloques))
    for b in bloques:
        salida += struct.pack("<2H", 32 * tam_registro, len(b)) + b
    return salida


def minimo() -> bytes:
    """Un `.omd` pequeño con las tres listas y las tres secciones variables."""
    return construir(
        a=[("INC", 2, 24, None), ("CMD", 0, 36, None)],
        b=[("CTE", 1, 48, None), ("IDE", 3, 40, 50), ("STR", 2, 264, 30)],
        c=[("EID", 1, 40, None), ("SVL", 0, 10, 6)],
    )

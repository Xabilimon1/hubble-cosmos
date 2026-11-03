"""Texto incrustado en un binario: SQL, nombres de tablas, mensajes, métodos.

Los `.omd` de los kits de Base 100 guardan el texto en Windows-1252 (ó = 0xF3), que
es lo que se usa por defecto. Los datos de la BD en un servidor Unix pueden ir en
OEM (cp850: la opción «OEM to ANSI» del ODBC de MultiBase existe por eso). Se buscan
secuencias de caracteres imprimibles en la codificación indicada y, aparte, cadenas
UTF-16LE.
"""

from __future__ import annotations

from dataclasses import dataclass

CODIFICACIONES = ("cp850", "cp1252", "latin-1")


@dataclass(frozen=True)
class Cadena:
    desplazamiento: int
    texto: str
    codificacion: str


def _imprimible(c: str) -> bool:
    return c.isprintable()


def _tabla_imprimibles(codificacion: str) -> list[str | None]:
    """Carácter de cada byte (0-255) si es imprimible en esa codificación, si no None."""
    tabla: list[str | None] = []
    for b in range(256):
        c = bytes([b]).decode(codificacion, errors="replace")
        tabla.append(c if b >= 0x20 and c != "�" and _imprimible(c) else None)
    return tabla


def extraer(datos: bytes, minimo: int = 4, codificacion: str = "cp1252") -> list[Cadena]:
    """Secuencias de al menos `minimo` caracteres imprimibles de un byte."""
    if codificacion not in CODIFICACIONES:
        raise ValueError(f"codificación no admitida: {codificacion}")
    tabla = _tabla_imprimibles(codificacion)
    salida: list[Cadena] = []
    inicio, actual = 0, []
    for i, b in enumerate(datos):
        c = tabla[b]
        if c is not None:
            if not actual:
                inicio = i
            actual.append(c)
        else:
            if len(actual) >= minimo:
                salida.append(Cadena(inicio, "".join(actual), codificacion))
            actual = []
    if len(actual) >= minimo:
        salida.append(Cadena(inicio, "".join(actual), codificacion))
    return salida


def extraer_utf16(datos: bytes, minimo: int = 4) -> list[Cadena]:
    """Cadenas UTF-16LE de caracteres imprimibles (alineadas a 2 bytes)."""
    salida: list[Cadena] = []
    for alineacion in (0, 1):
        inicio, actual = 0, []
        for i in range(alineacion, len(datos) - 1, 2):
            c = datos[i : i + 2].decode("utf-16-le", errors="replace")
            if c != "�" and c >= " " and _imprimible(c) and ord(c) < 0x2500:
                if not actual:
                    inicio = i
                actual.append(c)
            else:
                if len(actual) >= minimo:
                    salida.append(Cadena(inicio, "".join(actual), "utf-16-le"))
                actual = []
        if len(actual) >= minimo:
            salida.append(Cadena(inicio, "".join(actual), "utf-16-le"))
    return sorted(salida, key=lambda c: c.desplazamiento)


PALABRAS_SQL = ("SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "CREATE", "INTO", "ORDER BY", "GROUP BY")


def parece_sql(texto: str) -> bool:
    """Heurística: contiene alguna palabra clave de SQL como palabra completa."""
    t = f" {texto.upper()} "
    return any(f" {p} " in t for p in PALABRAS_SQL)

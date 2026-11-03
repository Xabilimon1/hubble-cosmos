"""Secciones empaquetadas de un `.omd`: IDE (identificadores), STR (cadenas) y SVL.

Comprobado en los 1174 `.omd` de los kits 8.2–8.6 (ver docs/formato-omd.md):

- u32 número de registros, u16 número de bloques, y los bloques seguidos.
- Bloque: u16 tamaño sin empaquetar (32 × tamaño de registro), u16 bytes guardados,
  y los registros. Un registro no se parte entre bloques.
- Registro de texto (u32 = 0): los bytes del registro (u32 y texto terminado en NUL)
  sin los ceros del final, cortados en el primer límite de unidad cuyo último byte es
  0. El primer límite está a 8 bytes y los siguientes van de 4 en 4 (32 bits) o de 8
  en 8 (64 bits). IDE y STR solo tienen registros de texto.
- Registro binario (u32 ≠ 0, solo en SVL): los 16 bits bajos del u32 son su longitud
  en bytes, contando el u32, y los altos un tipo (0–13 y 65535, sin interpretar).
  Ocupa esa longitud redondeada a la unidad.
- Tras los n registros puede quedar algo al final del último bloque: en los kits, solo
  restos de comentarios de documentación (9 ficheros). No es un registro.

El texto de los kits está en Windows-1252 (ó = 0xF3).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from hubble.contenedor import FormatoError, Omd, regiones

PRIMER_LIMITE = 8
LISTA_DE = {"IDE": "B", "STR": "B", "SVL": "C"}


@dataclass(frozen=True)
class Registro:
    desplazamiento: int  # en el fichero
    datos: bytes  # tal como está guardado, con su relleno

    @property
    def valor(self) -> int:
        return struct.unpack_from("<I", self.datos)[0]

    @property
    def binario(self) -> bool:
        return self.valor != 0

    @property
    def tipo(self) -> int:
        return self.valor >> 16

    @property
    def longitud(self) -> int:
        """Bytes del registro binario, contando su u32 y sin el relleno."""
        return self.valor & 0xFFFF

    @property
    def cuerpo(self) -> bytes:
        """Lo que sigue al u32 de un registro binario, sin el relleno."""
        return self.datos[4 : self.longitud]

    def texto(self, codificacion: str = "cp1252") -> str:
        if self.binario:
            raise ValueError("un registro binario no tiene texto")
        cuerpo = self.datos[4:]
        return cuerpo[: cuerpo.find(b"\x00")].decode(codificacion)

    def completo(self, tam_registro: int) -> bytes:
        """El registro con todos sus bytes: lo guardado y ceros hasta `tam_registro`."""
        if len(self.datos) > tam_registro:
            raise FormatoError(f"registro de {len(self.datos)} bytes, más que su tamaño ({tam_registro})")
        return self.datos.ljust(tam_registro, b"\x00")


@dataclass(frozen=True)
class Bloque:
    desplazamiento: int
    sin_empaquetar: int
    guardado: int


@dataclass(frozen=True)
class Empaquetada:
    registros: tuple[Registro, ...]
    bloques: tuple[Bloque, ...]
    sobrante: tuple[tuple[int, bytes], ...]  # (desplazamiento, bytes) tras el último registro


def _unidad(bits: int) -> int:
    if bits not in (32, 64):
        raise ValueError(f"arquitectura desconocida: {bits} bits")
    return bits // 8


def _hasta_unidad_acabada_en_cero(datos: bytes, q: int, largo: int, u: int, fin_bloque: int) -> int:
    while q + largo <= fin_bloque and datos[q + largo - 1] != 0:
        largo += u
    if q + largo > fin_bloque:
        raise FormatoError(f"el registro de {q:#x} no termina dentro de su bloque (acaba en {fin_bloque:#x})")
    return largo


def leer(datos: bytes, inicio: int, fin: int, bits: int, binarios: bool = False) -> Empaquetada:
    """Lee la sección empaquetada que ocupa datos[inicio:fin].

    Con `binarios` (SVL), un u32 distinto de 0 abre un registro binario. Sin él (IDE,
    STR), todo registro empieza por un u32 a 0, y lo que no empieza así son restos de
    memoria del registro anterior que quedaron tras su NUL: se le añaden.
    """
    u = _unidad(bits)
    n, nbloques = struct.unpack_from("<IH", datos, inicio)
    p = inicio + 6
    registros: list[Registro] = []
    bloques: list[Bloque] = []
    sobrante: list[tuple[int, bytes]] = []
    for _ in range(nbloques):
        sin_empaquetar, guardado = struct.unpack_from("<2H", datos, p)
        bloques.append(Bloque(p, sin_empaquetar, guardado))
        q, fin_bloque = p + 4, p + 4 + guardado
        while q < fin_bloque:
            valor = struct.unpack_from("<I", datos, q)[0]
            if valor and not binarios:
                anterior = registros[-1] if registros else None
                if anterior is None or anterior.desplazamiento + len(anterior.datos) != q:
                    raise FormatoError(f"en {q:#x} hay restos sin un registro de texto delante")
                largo = _hasta_unidad_acabada_en_cero(datos, q, u, u, fin_bloque)
                registros[-1] = Registro(anterior.desplazamiento, anterior.datos + datos[q : q + largo])
                q += largo
                continue
            if len(registros) == n:
                break
            if valor:
                if valor & 0xFFFF < 4:
                    raise FormatoError(f"registro binario en {q:#x} con longitud {valor & 0xFFFF}, menor que su u32")
                largo = -(-(valor & 0xFFFF) // u) * u
                if q + largo > fin_bloque:
                    raise FormatoError(f"el registro de {q:#x} no termina dentro de su bloque (acaba en {fin_bloque:#x})")
            else:
                largo = _hasta_unidad_acabada_en_cero(datos, q, PRIMER_LIMITE, u, fin_bloque)
            registros.append(Registro(q, datos[q : q + largo]))
            q += largo
        if q < fin_bloque:
            sobrante.append((q, datos[q:fin_bloque]))
        p = fin_bloque
    if len(registros) != n:
        raise FormatoError(f"se declaran {n} registros y hay {len(registros)}")
    if p != fin:
        raise FormatoError(f"los bloques acaban en {p:#x} y la sección en {fin:#x}")
    return Empaquetada(tuple(registros), tuple(bloques), tuple(sobrante))


def de_omd(datos: bytes, omd: Omd, etiqueta: str) -> Empaquetada:
    """Lee la sección empaquetada `etiqueta` (IDE, STR o SVL) de un `.omd` ya leído."""
    if etiqueta not in LISTA_DE:
        raise ValueError(f"{etiqueta} no es una sección empaquetada")
    nombre = f"{LISTA_DE[etiqueta]}/{etiqueta}"
    for r in regiones(omd, len(datos)):
        if r.nombre == nombre:
            return leer(datos, r.inicio, r.fin, omd.bits, binarios=etiqueta == "SVL")
    return Empaquetada((), (), ())

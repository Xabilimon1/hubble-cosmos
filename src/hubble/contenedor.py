"""Contenedor de un `.omd`: cabecera y tres listas de secciones.

Estructura comprobada en los 1174 `.omd` de los kits de evaluación 8.2–8.6
(ver docs/formato-omd.md):

- Cabecera de 0x4C bytes que empieza por «COMD». En 0x08, un u32 con la versión del
  formato (0x7230 en los kits 8.2–8.6; 0x3211 en un Cosmos más antiguo de 32 bits). En
  0x20, 0x24 y 0x28, tres u32 LE con el desplazamiento de la primera entrada de las
  listas A, B y C.
- Cada lista son entradas de 32 bytes seguidas, y justo detrás los datos de sus
  secciones, también seguidos. Entrada: u32 marca, u32 (0), u32 tamaño de la
  entrada (32), u32 siguiente (0xFFFFFFFF al final), u32 desplazamiento de los
  datos, etiqueta de 3 letras + NUL, u32 número de registros, u32 tamaño de registro.
- Todas las secciones ocupan exactamente n × tamaño de registro salvo IDE y STR
  (lista B) y SVL (lista C), que ocupan menos o más (parecen empaquetadas). Aquí se
  llaman «variables» y de momento solo se delimitan.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

MAGIA = b"COMD"
TAM_CABECERA = 0x4C
TAM_ENTRADA = 32
FIN = 0xFFFFFFFF
NOMBRES_LISTAS = "ABC"
VARIABLES = frozenset({"B/IDE", "B/STR", "C/SVL"})

# Tamaño de registro (32 bits, 64 bits) de las secciones que cambian con la
# arquitectura. Sacados de los kits: todo fichero de un kit x86 usa el primero, y
# cada fichero usa o todos los de 32 o todos los de 64. Quedan fuera FOB (76 en 32
# bits, 144 o 152 en 64) y DPR/DST/DRE (a veces 0).
TAMANOS_POR_BITS = {
    "LIB": (12, 24), "INC": (12, 24), "EMO": (36, 40),
    "CTE": (24, 48), "CLA": (48, 88), "OBJ": (44, 80), "MOP": (64, 104), "MNU": (16, 32), "PAG": (16, 32),
    "FOR": (32, 64), "FTA": (56, 112), "FCT": (120, 208), "FJO": (24, 48), "FRC": (16, 32), "PCT": (120, 208),
    "PRO": (32, 64), "STM": (24, 48), "REF": (16, 32),
    "EPR": (4, 8), "EFT": (4, 8), "ECT": (4, 8), "ECL": (4, 8),
}
# Versión del formato (u32 de +0x08 de la cabecera). La de los kits 8.2–8.6 es 0x7230. La 0x3211 es la de un Cosmos
# más antiguo, solo de 32 bits: sus secciones miden como en 8.6 de 32 bits salvo FOR, FCT y PCT, más cortas
# (docs/formato-omd.md, «Formato 0x3211»). No hay compilador de esa versión: nada de ella se ha comprobado con vuelta.
VERSION_86, VERSION_3211 = 0x7230, 0x3211
TAMANOS_3211 = {"FOR": 28, "FCT": 112, "PCT": 112}


class FormatoError(ValueError):
    """El fichero no tiene la estructura de contenedor esperada."""


@dataclass(frozen=True)
class Seccion:
    etiqueta: str
    entrada: int  # desplazamiento de su entrada de 32 bytes
    marca: int
    datos: int
    n: int
    tam_registro: int


@dataclass(frozen=True)
class Omd:
    listas: tuple[tuple[Seccion, ...], ...]
    version: int = VERSION_86  # u32 de +0x08 de la cabecera

    def seccion(self, etiqueta: str) -> Seccion:
        for lista in self.listas:
            for s in lista:
                if s.etiqueta == etiqueta:
                    return s
        raise KeyError(etiqueta)

    @property
    def bits(self) -> int:
        """32 o 64: la arquitectura para la que se compiló, por los tamaños de registro. En el formato 0x3211, FOR, FCT
        y PCT tienen que medir lo de TAMANOS_3211 (y las demás, lo de 32 bits); en otro, lo de 8.6."""
        if self.version not in (VERSION_86, VERSION_3211):
            raise FormatoError(f"versión de formato {self.version:#x} desconocida")
        votos: set[int] = set()
        for lista in self.listas:
            for s in lista:
                if s.etiqueta not in TAMANOS_POR_BITS:
                    continue
                if self.version == VERSION_3211 and s.etiqueta in TAMANOS_3211:
                    if s.tam_registro != TAMANOS_3211[s.etiqueta]:
                        raise FormatoError(f"tamaño de registro {s.tam_registro} desconocido en {s.etiqueta} (formato 0x3211)")
                    votos.add(32)
                    continue
                t32, t64 = TAMANOS_POR_BITS[s.etiqueta]
                if s.tam_registro not in (t32, t64):
                    raise FormatoError(f"tamaño de registro {s.tam_registro} desconocido en {s.etiqueta}")
                votos.add(32 if s.tam_registro == t32 else 64)
        if len(votos) != 1:
            raise FormatoError("tamaños de registro de 32 y 64 bits a la vez" if votos else "sin secciones que digan la arquitectura")
        bits = votos.pop()
        if self.version == VERSION_3211 and bits != 32:
            raise FormatoError("formato 0x3211 con tamaños de registro de 64 bits")
        return bits


@dataclass(frozen=True)
class Region:
    inicio: int
    fin: int
    nombre: str
    variable: bool = False


def _lista(datos: bytes, off: int) -> tuple[Seccion, ...]:
    salida: list[Seccion] = []
    vistas: set[int] = set()
    while off != FIN:
        if off in vistas:
            raise FormatoError(f"lista de secciones en bucle en {off:#x}")
        if off + TAM_ENTRADA > len(datos):
            raise FormatoError(f"entrada de sección fuera del fichero en {off:#x}")
        vistas.add(off)
        marca, _, _, sig, desp = struct.unpack_from("<5I", datos, off)
        etiqueta = datos[off + 20 : off + 24].rstrip(b"\x00").decode("latin-1")
        n, rec = struct.unpack_from("<2I", datos, off + 24)
        salida.append(Seccion(etiqueta, off, marca, desp, n, rec))
        off = sig
    return tuple(salida)


def leer(datos: bytes) -> Omd:
    if len(datos) < TAM_CABECERA:
        raise FormatoError(f"fichero de {len(datos)} bytes, más corto que la cabecera ({TAM_CABECERA})")
    if datos[:4] != MAGIA:
        raise FormatoError(f"no empieza por COMD: {datos[:4].hex(' ')}")
    primeras = struct.unpack_from("<3I", datos, 0x20)
    return Omd(tuple(_lista(datos, off) for off in primeras), struct.unpack_from("<I", datos, 0x08)[0])


def regiones(omd: Omd, tamano: int) -> list[Region]:
    """Regiones seguidas que cubren el fichero de 0 a `tamano`.

    Las secciones vacías no aparecen. Una sección de tamaño fijo que no ocupa
    exactamente n × tamaño de registro es un error.
    """
    salida = [Region(0, omd.listas[0][0].entrada, "cabecera")]
    for k, lista in enumerate(omd.listas):
        nombre = NOMBRES_LISTAS[k]
        inicio = lista[0].entrada
        for j, s in enumerate(lista):
            if s.entrada != inicio + TAM_ENTRADA * j:
                raise FormatoError(f"la entrada {s.etiqueta} de la lista {nombre} no sigue a la anterior")
        fin_entradas = inicio + TAM_ENTRADA * len(lista)
        if lista[0].datos != fin_entradas:
            raise FormatoError(f"los datos de la lista {nombre} no empiezan tras sus entradas")
        salida.append(Region(inicio, fin_entradas, f"entradas {nombre}"))
        fin_lista = omd.listas[k + 1][0].entrada if k + 1 < len(omd.listas) else tamano
        for j, s in enumerate(lista):
            fin = lista[j + 1].datos if j + 1 < len(lista) else fin_lista
            ruta = f"{nombre}/{s.etiqueta}"
            if fin < s.datos:
                raise FormatoError(f"la sección {ruta} empieza después de donde acaba")
            variable = ruta in VARIABLES
            if not variable and fin - s.datos != s.n * s.tam_registro:
                raise FormatoError(
                    f"la sección {ruta} dice ocupar {s.n * s.tam_registro} bytes pero tiene {fin - s.datos}"
                )
            if fin > s.datos:
                salida.append(Region(s.datos, fin, ruta, variable))
    return salida

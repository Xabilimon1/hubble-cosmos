"""Inventario de una instalación: qué ficheros hay, de qué tipo y cuándo cambiaron.

Las fechas sirven para separar módulos de catálogo de los hechos a medida (se
compilan en momentos distintos) y la «firma» (primeros bytes) para ver qué
ficheros comparten formato aunque tengan otra extensión.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

BYTES_FIRMA = 16


@dataclass(frozen=True)
class Fichero:
    ruta: Path
    extension: str
    tamano: int
    modificado: datetime
    firma: bytes

    @property
    def firma_hex(self) -> str:
        return self.firma.hex(" ")


@dataclass(frozen=True)
class Grupo:
    extension: str
    ficheros: int
    bytes_totales: int
    firma_comun: bytes
    mas_antiguo: datetime
    mas_reciente: datetime


def recorrer(raiz: Path) -> list[Fichero]:
    """Todos los ficheros bajo `raiz` (sin seguir enlaces), ordenados por ruta."""
    salida: list[Fichero] = []
    for carpeta, _dirs, nombres in os.walk(raiz):
        for nombre in nombres:
            ruta = Path(carpeta) / nombre
            if ruta.is_symlink() or not ruta.is_file():
                continue
            st = ruta.stat()
            with ruta.open("rb") as f:
                firma = f.read(BYTES_FIRMA)
            salida.append(
                Fichero(
                    ruta=ruta.relative_to(raiz),
                    extension=ruta.suffix.lower() or "(sin extensión)",
                    tamano=st.st_size,
                    modificado=datetime.fromtimestamp(st.st_mtime),
                    firma=firma,
                )
            )
    return sorted(salida, key=lambda f: str(f.ruta))


def prefijo_comun(firmas: list[bytes]) -> bytes:
    """Bytes iniciales idénticos en todas las firmas (la «magia» del formato, si la hay)."""
    if not firmas:
        return b""
    n = min(len(f) for f in firmas)
    i = 0
    while i < n and all(f[i] == firmas[0][i] for f in firmas):
        i += 1
    return firmas[0][:i]


def agrupar(ficheros: list[Fichero]) -> list[Grupo]:
    """Resumen por extensión, de más a menos ficheros."""
    por_ext: dict[str, list[Fichero]] = defaultdict(list)
    for f in ficheros:
        por_ext[f.extension].append(f)
    grupos = [
        Grupo(
            extension=ext,
            ficheros=len(fs),
            bytes_totales=sum(f.tamano for f in fs),
            firma_comun=prefijo_comun([f.firma for f in fs]),
            mas_antiguo=min(f.modificado for f in fs),
            mas_reciente=max(f.modificado for f in fs),
        )
        for ext, fs in por_ext.items()
    ]
    return sorted(grupos, key=lambda g: (-g.ficheros, g.extension))

"""Compara cada programa de la batería con `b_base`, sección a sección.

Uso: uv run python lab/bateria/difer.py <dir con .omd y manifiesto.tsv>
Salida por programa: `ETQ:n→m` si cambia el número de registros, `ETQ≠` si solo cambian bytes.
"""
import sys
from pathlib import Path
from hubble import contenedor as C
d = Path(sys.argv[1])
man = dict(reversed(l.split("\t")) for l in (d / "manifiesto.tsv").read_text().splitlines())
def carga(nombre):
    h = man[nombre]; f = next(p for p in d.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == h.lower())
    b = f.read_bytes(); o = C.leer(b); secs = {}
    for lista in o.listas:
        for s in lista:
            secs[s.etiqueta] = (s.n, b[s.datos:s.datos + s.n * s.tam_registro])
    return secs
base = carga("b_base")
for nombre in man:
    if nombre == "b_base": continue
    v = carga(nombre); cambios = []
    for et in sorted(set(base) | set(v)):
        nb, db = base.get(et, (None, b"")); nv, dv = v.get(et, (None, b""))
        if nb != nv: cambios.append(f"{et}:{nb}→{nv}")
        elif db != dv: cambios.append(f"{et}≠")
    print(f"{nombre:18} {' '.join(cambios)}")

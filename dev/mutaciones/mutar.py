"""Rompe cada invariante por separado y comprueba que algún test falla."""
import os
import subprocess
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
src = raiz / "src/hubble"
M = [
    ("entropia", "        return 0.0\n    n = len", "        return 1.0\n    n = len"),
    ("entropia", "return -sum(", "return sum("),
    ("entropia", "if tamano <= 0:", "if tamano < 0:"),
    ("entropia", "if b.entropia >= umbral) / total", "if b.entropia > umbral) / total"),
    ("entropia", "return sum(b.tamano for b in bloques if b.entropia >= umbral) / total if total else 0.0",
     "return len([b for b in bloques if b.entropia >= umbral]) / len(bloques) if total else 0.0"),
    ("entropia", "/ total if total else 0.0", "/ total if total else 1.0"),
    ("inventario", "if ruta.is_symlink() or not ruta.is_file():", "if not ruta.is_file():"),
    ("inventario", "ruta.suffix.lower()", "ruta.suffix"),
    ("inventario", "ruta=ruta.relative_to(raiz),", "ruta=ruta,"),
    ("inventario", "return sorted(salida, key=lambda f: str(f.ruta))", "return salida"),
    ("inventario", "firma = f.read(BYTES_FIRMA)", "firma = f.read()"),
    ("inventario", "while i < n and", "while i < n - 1 and"),
    ("inventario", "key=lambda g: (-g.ficheros, g.extension)", "key=lambda g: (g.ficheros, g.extension)"),
    ("inventario", "bytes_totales=sum(f.tamano for f in fs)", "bytes_totales=len(fs)"),
    ("cadenas", "        else:\n            if len(actual) >= minimo:", "        else:\n            if len(actual) > minimo:"),
    ("cadenas", "    if len(actual) >= minimo:\n        salida.append(Cadena(inicio, \"\".join(actual), codificacion))\n    return",
     "    return"),
    ("cadenas", "return c.isprintable()", "return True"),
    ("cadenas", 'minimo: int = 4, codificacion: str = "cp1252"', 'minimo: int = 4, codificacion: str = "cp850"'),
    ("cadenas", "    if codificacion not in CODIFICACIONES:\n        raise", "    if False:\n        raise"),
    ("cadenas", "for alineacion in (0, 1):", "for alineacion in (0,):"),
    ("cadenas", "return any(f\" {p} \" in t for p in PALABRAS_SQL)", "return any(p in t for p in PALABRAS_SQL)"),
    ("cabeceras", "constante = None not in vals and len(set(vals)) == 1", "constante = len(set(vals)) == 1"),
    ("cabeceras", "elif 0 < d <= n:", "elif False:"),
    ("cabeceras", "if d == 0:", "if False:"),
    ("cabeceras", "for orden in (\"<\", \">\"):", "for orden in (\"<\",):"),
    ("cabeceras", "if len(set(vals)) > 1 and all(", "if all("),
    ("cabeceras", "all(n <= v < t for", "all(0 <= v < t for"),
    ("cabeceras", "all(n <= v < t for", "all(n <= v for"),
    ("cabeceras", "if len(ficheros) < 2:", "if len(ficheros) < 1:"),
]
vivos = 0
for mod, viejo, nuevo in M:
    p = src / f"{mod}.py"
    orig = p.read_text()
    if orig.count(viejo) != 1:
        print("NO ENCONTRADO", mod, repr(viejo[:60]))
        continue
    p.write_text(orig.replace(viejo, nuevo))
    try:
        r = subprocess.run(["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider"], cwd=raiz, capture_output=True, text=True, env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"})
    finally:
        p.write_text(orig)
    rojo = r.returncode != 0
    vivos += not rojo
    print("ROJO " if rojo else "VERDE", mod, "|", viejo.strip()[:60].replace("\n", " "))
print(f"{len(M)} mutaciones, {vivos} sobreviven")

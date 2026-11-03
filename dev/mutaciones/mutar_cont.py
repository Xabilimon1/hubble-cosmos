"""Mutaciones de contenedor.py: cada invariante roto por separado debe poner algún test en rojo."""
import os
import subprocess
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
p = raiz / "src/hubble/contenedor.py"
M = [
    ("        if off in vistas:\n", "        if False:\n"),
    ("if off + TAM_ENTRADA > len(datos):", "if off > len(datos):"),
    ("    if datos[:4] != MAGIA:\n", "    if False:\n"),
    ("    if len(datos) < TAM_CABECERA:\n", "    if False:\n"),
    ('.rstrip(b"\\x00").decode', ".decode"),
    ("            if s.entrada != inicio + TAM_ENTRADA * j:\n", "            if False:\n"),
    ("        if lista[0].datos != fin_entradas:\n", "        if False:\n"),
    ("            if fin < s.datos:\n", "            if False:\n"),
    ("variable = ruta in VARIABLES", "variable = True"),
    ("            if fin > s.datos:\n", "            if fin >= s.datos:\n"),
    ("fin_lista = omd.listas[k + 1][0].entrada if k + 1 < len(omd.listas) else tamano", "fin_lista = tamano"),
    ('VARIABLES = frozenset({"B/IDE", "B/STR", "C/SVL"})', 'VARIABLES = frozenset({"B/IDE", "B/STR"})'),
    ('salida = [Region(0, omd.listas[0][0].entrada, "cabecera")]', 'salida = [Region(0, TAM_CABECERA + 4, "cabecera")]'),
    ("primeras = struct.unpack_from(\"<3I\", datos, 0x20)", "primeras = struct.unpack_from(\">3I\", datos, 0x20)"),
    ("votos.add(32 if s.tam_registro == t32 else 64)", "votos.add(64 if s.tam_registro == t32 else 32)"),
    ("                if s.tam_registro not in (t32, t64):\n", "                if False:\n"),
    ("        if len(votos) != 1:\n", "        if not votos:\n"),
    ('"STM": (24, 48)', '"STM": (24, 40)'),
    ('"EPR": (4, 8)', '"EPR": (8, 4)'),
]
orig = p.read_text()
vivos = 0
entorno = os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "HUBBLE_KITS": os.environ.get("HUBBLE_KITS", "kits")}
for viejo, nuevo in M:
    if orig.count(viejo) != 1:
        print("NO ENCONTRADO", viejo.strip()[:60])
        continue
    p.write_text(orig.replace(viejo, nuevo))
    proc = subprocess.Popen(["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/test_contenedor.py", "tests/test_corpus.py"],
                            cwd=raiz, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=entorno, start_new_session=True)
    try:
        rojo = proc.wait(timeout=60) != 0
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, 9)  # mata también el pytest que lanza uv
        proc.wait()
        rojo = True  # se cuelga: también cuenta como detectado
    finally:
        p.write_text(orig)
    vivos += not rojo
    print("ROJO " if rojo else "VERDE", viejo.strip()[:70])
print(f"{len(M)} mutaciones, {vivos} sobreviven")

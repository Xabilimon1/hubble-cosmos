"""Mutaciones de empaquetado.py (base en verde, sin bytecode, matar el grupo si se cuelga)."""
import os
import subprocess
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
p = raiz / "src/hubble/empaquetado.py"
M = [
    ("PRIMER_LIMITE = 8", "PRIMER_LIMITE = 4"),
    ("return bits // 8", "return 8"),
    ("    if bits not in (32, 64):\n", "    if False:\n"),
    ('n, nbloques = struct.unpack_from("<IH", datos, inicio)', 'n, nbloques = struct.unpack_from("<HH", datos, inicio)'),
    ("    p = inicio + 6\n", "    p = inicio + 8\n"),
    ("q, fin_bloque = p + 4, p + 4 + guardado", "q, fin_bloque = p + 4, p + 4 + sin_empaquetar"),
    ("datos[q + largo - 1] != 0", "datos[q + largo] != 0"),
    ("    if q + largo > fin_bloque:\n        raise FormatoError(f\"el registro de {q:#x} no termina dentro de su bloque (acaba en {fin_bloque:#x})\")\n    return largo",
     "    return largo"),
    ("        if q < fin_bloque:\n            sobrante", "        if False:\n            sobrante"),
    ("    if len(registros) != n:\n", "    if False:\n"),
    ("    if p != fin:\n", "    if False:\n"),
    ("return cuerpo[: cuerpo.find(b\"\\x00\")].decode(codificacion)", "return cuerpo.rstrip(b\"\\x00\").decode(codificacion)"),
    ('def texto(self, codificacion: str = "cp1252")', 'def texto(self, codificacion: str = "cp850")'),
    ("        if len(self.datos) > tam_registro:\n", "        if False:\n"),
    ('    nombre = f"{LISTA_DE[etiqueta]}/{etiqueta}"', '    nombre = f"B/{etiqueta}"'),
    # binarios y restos
    ("            if valor and not binarios:\n", "            if False:\n"),
    ("registros[-1] = Registro(anterior.desplazamiento, anterior.datos + datos[q : q + largo])", "pass"),
    ("                if anterior is None or anterior.desplazamiento + len(anterior.datos) != q:\n", "                if anterior is None:\n"),
    ("            if len(registros) == n:\n                break", "            if False:\n                break"),
    ("                if valor & 0xFFFF < 4:\n", "                if False:\n"),
    ("largo = -(-(valor & 0xFFFF) // u) * u", "largo = valor & 0xFFFF"),
    ("                if q + largo > fin_bloque:\n                    raise", "                if False:\n                    raise"),
    ('return leer(datos, r.inicio, r.fin, omd.bits, binarios=etiqueta == "SVL")', "return leer(datos, r.inicio, r.fin, omd.bits, binarios=True)"),
    ('LISTA_DE = {"IDE": "B", "STR": "B", "SVL": "C"}', 'LISTA_DE = {"IDE": "B", "STR": "B", "SVL": "C", "CTE": "B"}'),
    ("        return self.valor >> 16", "        return self.valor >> 8"),
    ("        return self.datos[4 : self.longitud]", "        return self.datos[4:]"),
    ("        if self.binario:\n            raise", "        if False:\n            raise"),
]
orig = p.read_text()
vivos = 0
entorno = os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "HUBBLE_KITS": os.environ.get("HUBBLE_KITS", "kits")}
for viejo, nuevo in M:
    if orig.count(viejo) != 1:
        print("NO ENCONTRADO", viejo.strip()[:60])
        continue
    p.write_text(orig.replace(viejo, nuevo))
    proc = subprocess.Popen(["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/test_empaquetado.py", "tests/test_corpus.py"],
                            cwd=raiz, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=entorno, start_new_session=True)
    try:
        rojo = proc.wait(timeout=60) != 0
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, 9)
        proc.wait()
        rojo = True
    finally:
        p.write_text(orig)
    vivos += not rojo
    print("ROJO " if rojo else "VERDE", viejo.strip()[:70])
print(f"{len(M)} mutaciones, {vivos} sobreviven")

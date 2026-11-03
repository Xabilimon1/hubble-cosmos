"""Mutaciones de la línea de órdenes, mismo método que mutar.py."""
import os
import subprocess
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
p = raiz / "src/hubble/cli.py"
M = [
    ('| {"firma_comun": g.firma_comun.hex(" ")}', '| {"firma_comun": ""}'),
    ("cs = [c for c in cs if cadenas.parece_sql(c.texto)]", "pass"),
    ("cs.sort(key=lambda c: c.desplazamiento)", "cs.sort(key=lambda c: c.texto)"),
    ("salida.extend(sorted(x for x in p.rglob(\"*\") if x.is_file()))", "pass"),
    ('aviso = "  <- probablemente comprimido o cifrado" if alta > 0.8 else ""', 'aviso = ""'),
    ('marca = "  variable (sin descodificar)" if r["variable"] else ""', 'marca = ""'),
    ("        regiones = contenedor.regiones(omd, len(datos))\n    except contenedor.FormatoError as e:", "        regiones = contenedor.regiones(omd, len(datos))\n    except KeyError as e:"),
    ('{"lista": contenedor.NOMBRES_LISTAS[k], "datos"', '{"lista": "A", "datos"'),
    ('"regiones": [asdict(r) for r in regiones]', '"regiones": [asdict(r) for r in regiones[1:]]'),
    ('        salida["bits"] = omd.bits\n', '        salida["bits"] = 64\n'),
    ('salida["aviso"] = f"arquitectura desconocida: {e}"', 'salida["aviso"] = ""'),
    ('bits = f"{res[\'bits\']} bits" if res["bits"] else res["aviso"]', 'bits = res.get("aviso", "")'),
    ('        textos = [t for t in textos if t["texto"] and cadenas.parece_sql(t["texto"])]\n', "        pass\n"),
    ('s.add_argument("--seccion", choices=("STR", "IDE", "SVL"), default="STR")', 's.add_argument("--seccion", choices=("STR", "IDE", "SVL"), default="IDE")'),
    ("        emp = empaquetado.de_omd(datos, omd, seccion)\n    except contenedor.FormatoError as e:", "        emp = empaquetado.de_omd(datos, omd, seccion)\n    except KeyError as e:"),
    ("print(f\"{res['fichero']}\\t{t['indice']}\\t0x{t['desplazamiento']:08x}\\t{texto}\")", "print(f\"{res['fichero']}\\t{t['indice']}\\t{texto}\")"),
    ('            t |= {"tipo": r.tipo, "longitud": r.longitud}\n', "            pass\n"),
    ('texto = f"[binario: tipo {t[\'tipo\']}, {t[\'longitud\']} bytes]"', 'texto = "[binario]"'),
    ('"texto": None if r.binario else r.texto()}', '"texto": "" if r.binario else r.texto()}'),
    ('s.add_argument("--codificacion", choices=cadenas.CODIFICACIONES, default="cp1252")', 's.add_argument("--codificacion", choices=cadenas.CODIFICACIONES, default="cp850")'),
]
orig = p.read_text()
vivos = 0
for viejo, nuevo in M:
    if orig.count(viejo) != 1:
        print("NO ENCONTRADO", viejo[:60])
        continue
    p.write_text(orig.replace(viejo, nuevo))
    try:
        r = subprocess.run(["uv", "run", "pytest", "-q", "-x", "-p", "no:cacheprovider", "tests/test_cli.py"],
                           cwd=raiz, capture_output=True, text=True, env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"})
    finally:
        p.write_text(orig)
    rojo = r.returncode != 0
    vivos += not rojo
    print("ROJO " if rojo else "VERDE", viejo[:60])
print(f"{len(M)} mutaciones, {vivos} sobreviven")

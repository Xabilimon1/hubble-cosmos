"""Cobertura del lenguaje: qué palabras del fuente sabe escribir Hubble.

La lista sale del propio compilador: cosmakecon.exe lleva las cadenas de formato con que escribe el fuente
(«FONT "%s" %d%s%s», « PARENTGRID», « depend on »…), juntas entre «GRAMMAR %s» y «PROJECT_UNKNOWN». Cada palabra
de esa zona es una construcción posible de COOL. Una palabra está cubierta si aparece entera en src/hubble/*.py.
Es una medida aproximada (una palabra cubierta no garantiza todas sus variantes): la comprobación de verdad es
la vuelta completa de lab/bateria.

Uso: HUBBLE_KITS=… python3 -I lab/lenguaje/cobertura.py [--todas]
"""
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
# Palabras que no hace falta escribir tal cual (comprobado con las baterías; docs/formato-omd.md, 2026-10-31):
# las reservadas no distinguen mayúsculas (manual refer ref00005) y Hubble escribe la otra grafía, con los mismos bytes;
GRAFIAS = {"OF": "of", "RETURN": "return", "SELF": "self", "JavaClass": "javaclass"}
# opcional y sin huella en el .omd (ref00029: «function_identifier ::= [FUNCTION] identifier»);
OPCIONALES = {"function"}
# y las que no compilan en 8.6 en ninguna forma probada: no puede haber un .omd que las lleve.
NO_COMPILAN = {"SELFCLASS", "selfclass", "TICKS", "references", "joining"}
EXE = "extraido/86x64/Cosmos8.6x64eval/bin/cosmakecon.exe"


def cadenas(datos: bytes, minimo: int = 2) -> list[str]:
    return [m.group().decode("ascii") for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minimo, datos)]


def palabras_del_compilador(exe: Path) -> list[str]:
    zona = cadenas(exe.read_bytes())
    ini = next(i for i, c in enumerate(zona) if c.startswith("GRAMMAR %s"))
    fin = next(i for i in range(ini, len(zona)) if zona[i].startswith("PROJECT_UNKNOWN"))
    vistas: list[str] = []
    for c in zona[ini:fin]:
        for w in re.findall(r"[A-Za-z_]{2,}", re.sub(r"%l?[sdc]", " ", c)):
            if w not in vistas:
                vistas.append(w)
    return vistas


def main() -> None:
    kits = Path(os.environ.get("HUBBLE_KITS", RAIZ / "kits"))
    palabras = palabras_del_compilador(kits / EXE)
    src = "\n".join(p.read_text() for p in (RAIZ / "src/hubble").glob("*.py"))
    def esta(w):
        return re.search(r"(?<![A-Za-z_])" + re.escape(w) + r"(?![A-Za-z_])", src)

    faltan = [w for w in palabras if not esta(w) and not (w in GRAFIAS and esta(GRAFIAS[w])) and w not in OPCIONALES]
    imposibles = [w for w in faltan if w in NO_COMPILAN]
    faltan = [w for w in faltan if w not in NO_COMPILAN]
    print(f"{len(palabras)} palabras en el compilador; Hubble escribe {len(palabras) - len(faltan) - len(imposibles)}"
          f"; no compilan en 8.6 {len(imposibles)}; faltan {len(faltan)}")
    print("no compilan:", " ".join(imposibles))
    print("faltan:", " ".join(faltan))
    if "--todas" in sys.argv:
        print("todas:", " ".join(palabras))


if __name__ == "__main__":
    main()

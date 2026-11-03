"""Prueba con aplicaciones: descompila cada .omd de las carpetas dadas (por defecto, los proyectos del kit) y
cuenta, por carpeta, cuántos salen y por qué se para el resto.

Uso: HUBBLE_KITS=… python3 -I lab/lenguaje/proyectos.py [carpeta…]
(solo lee: no compila; la vuelta completa la hace lab/bateria). El repositorio: la carpeta .dbs de cada proyecto.
"""
import collections
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))
from hubble import descompilador, repositorio  # noqa: E402

PROYECTOS = "extraido/86x64/Cosmos8.6x64eval/projects"


def main() -> None:
    kits = Path(os.environ.get("HUBBLE_KITS", RAIZ / "kits"))
    carpetas = [Path(a) for a in sys.argv[1:]] or sorted(p for p in (kits / PROYECTOS).iterdir() if p.is_dir())
    motivos: collections.Counter[str] = collections.Counter()
    total = bien = 0
    for c in carpetas:
        omd = sorted(f for f in c.iterdir() if f.suffix.lower() == ".omd")
        if not omd:
            continue
        ok = 0
        dbs = next((p for p in sorted(c.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs"), None)
        catalogo = repositorio.Catalogo(dbs) if dbs else None
        for f in omd:
            try:
                descompilador.descompilar(f.read_bytes(), dbs.stem if dbs else "repositorio", catalogo)
                ok += 1
            except descompilador.NoSoportado as e:
                motivos[re.sub(r"\b\d+\b", "N", str(e))] += 1
        print(f"{c.name}: {ok}/{len(omd)}")
        total += len(omd)
        bien += ok
    print(f"total: {bien}/{total}")
    for m, n in motivos.most_common():
        print(f"{n:4} {m}")


if __name__ == "__main__":
    main()

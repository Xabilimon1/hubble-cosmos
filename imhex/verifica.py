"""Comprueba que el patrón de ImHex lee los mismos textos que Hubble.

Ejecuta `imhex --pl format` (la línea de comandos del lenguaje de patrones) sobre cada
`.omd` y compara, sección a sección, los registros de texto de `IDE`, `STR` y `SVL` con
los de `hubble.empaquetado`, byte a byte.

    uv run python imhex/verifica.py <carpeta del ejecutable de ImHex> <zip o carpeta>…
"""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote_to_bytes

from hubble import contenedor, empaquetado

PATRON = Path(__file__).resolve().parent / "omd.hexpat"


def _textos(nodo, etiqueta, salida):
    """Los textos de la sección `etiqueta` en la salida JSON del patrón, en orden."""
    if isinstance(nodo, dict):
        if nodo.get("tag") == etiqueta and isinstance(nodo.get("data"), dict):
            for registros in _buscar(nodo["data"], "records"):
                for r in registros:
                    if "text" in r:
                        # El JSON lleva el valor formateado: entre comillas, en codificación
                        # URL y con el NUL.
                        salida.append(unquote_to_bytes(r["text"])[1:-1].split(b"\0")[0])
        for v in nodo.values():
            _textos(v, etiqueta, salida)
    elif isinstance(nodo, list):
        for v in nodo:
            _textos(v, etiqueta, salida)


def _buscar(nodo, clave):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if k == clave:
                yield v
            else:
                yield from _buscar(v, clave)
    elif isinstance(nodo, list):
        for v in nodo:
            yield from _buscar(v, clave)


def diferencias(imhex: Path, patron: Path, datos: bytes) -> list[str]:
    """Lista vacía si el patrón y Hubble leen lo mismo; si no, qué difiere."""
    with tempfile.TemporaryDirectory() as tmp:
        entrada, salida = Path(tmp) / "m.omd", Path(tmp) / "m.json"
        entrada.write_bytes(datos)
        r = subprocess.run(
            [str(imhex / "imhex"), "--pl", "format", "-i", str(entrada), "-p", str(patron),
             "-o", str(salida), "-I", str(imhex / "includes"), "-f", "json"],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0 or not salida.exists():
            return [f"ImHex: {(r.stdout + r.stderr).strip()[:300]}"]
        arbol = json.loads(salida.read_text(errors="replace"))
    omd = contenedor.leer(datos)
    salida_: list[str] = []
    for etiqueta in ("IDE", "STR", "SVL"):
        esperado = [x.datos[4:].split(b"\0")[0] for x in empaquetado.de_omd(datos, omd, etiqueta).registros if not x.binario]
        visto: list[bytes] = []
        _textos(arbol, etiqueta, visto)
        if visto != esperado:
            salida_.append(f"{etiqueta}: ImHex lee {len(visto)} textos y Hubble {len(esperado)}")
    return salida_


def _omds(rutas):
    for ruta in map(Path, rutas):
        if ruta.suffix.lower() == ".zip":
            with zipfile.ZipFile(ruta) as zf:
                for n in zf.namelist():
                    if n.lower().endswith(".omd"):
                        yield f"{ruta.name}:{n}", zf.read(n)
        else:
            for f in sorted(ruta.rglob("*")):
                if f.suffix.lower() == ".omd":
                    yield str(f), f.read_bytes()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    imhex, rutas = Path(argv[0]), argv[1:]
    total = mal = 0
    for nombre, datos in _omds(rutas):
        total += 1
        d = diferencias(imhex, PATRON, datos)
        if d:
            mal += 1
            print(nombre, d, flush=True)
    print(f"{total - mal} de {total} iguales")
    return 1 if mal else 0


if __name__ == "__main__":
    sys.exit(main())

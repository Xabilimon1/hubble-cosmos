"""El patrón de ImHex (imhex/omd.hexpat) lee los mismos textos que Hubble.

Necesita ImHex: HUBBLE_IMHEX = carpeta del ejecutable (…/ImHex.app/Contents/MacOS).
Sin ella, o sin los kits, se salta. El corpus entero lo recorre imhex/verifica.py.
"""
import importlib.util
import os
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
IMHEX = os.environ.get("HUBBLE_IMHEX")
KITS = Path(os.environ.get("HUBBLE_KITS", RAIZ / "kits"))
PATRON = RAIZ / "imhex" / "omd.hexpat"

pytestmark = pytest.mark.skipif(not IMHEX, reason="sin HUBBLE_IMHEX")

# test1: 64 y 32 bits, con código y cadenas; configuration: 64 bits, con SVL (formulario).
MUESTRAS = [
    ("cosmos86x64eval.zip", "projects/NIF/test1.OMD"),
    ("cosmos86x86eval.zip", "projects/NIF/test1.OMD"),
    ("cosmos86x64eval.zip", "dbmanager/configuration.OMD"),
]


@pytest.fixture(scope="module")
def verifica():
    spec = importlib.util.spec_from_file_location("verifica", RAIZ / "imhex" / "verifica.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _leer(zip_, final):
    ruta = KITS / zip_
    if not ruta.exists():
        pytest.skip(f"no está {ruta}")
    with zipfile.ZipFile(ruta) as zf:
        nombres = [n for n in zf.namelist() if n.lower().endswith(final.lower())]
        assert len(nombres) == 1, nombres
        return zf.read(nombres[0])


@pytest.mark.parametrize(("zip_", "final"), MUESTRAS)
def test_textos_iguales_que_hubble(verifica, zip_, final):
    assert verifica.diferencias(Path(IMHEX), PATRON, _leer(zip_, final)) == []


def test_detecta_un_patron_que_lee_mal(verifica, tmp_path):
    malo = tmp_path / "malo.hexpat"
    malo.write_text(PATRON.read_text().replace("text_length(start, 8, end)", "text_length(start, 4, end)"))
    assert malo.read_text() != PATRON.read_text()
    assert verifica.diferencias(Path(IMHEX), malo, _leer(*MUESTRAS[0])) != []

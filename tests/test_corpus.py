"""Pruebas contra los kits de evaluación de Base 100 (no están en el repo).

Se buscan en $HUBBLE_KITS o en `kits/` en la raíz del repo; si no hay, se saltan.
"""

import collections
import os
import zipfile
from pathlib import Path

import pytest

from hubble import contenedor, empaquetado

KITS = Path(os.environ.get("HUBBLE_KITS", Path(__file__).resolve().parents[1] / "kits"))
ZIPS = sorted(KITS.glob("cosmos*eval.zip")) if KITS.is_dir() else []

pytestmark = pytest.mark.skipif(not ZIPS, reason=f"sin kits de evaluación en {KITS}")


def _omds():
    for z in ZIPS:
        with zipfile.ZipFile(z) as zf:
            for i in zf.infolist():
                if i.filename.lower().endswith(".omd"):
                    yield f"{z.name}:{i.filename}", zf.read(i)


@pytest.fixture(scope="module")
def corpus():
    return list(_omds())


def test_hay_corpus(corpus):
    assert len(corpus) >= 1000


def test_todo_omd_del_corpus_cubre_sus_bytes(corpus):
    fallos = []
    for nombre, datos in corpus:
        try:
            rs = contenedor.regiones(contenedor.leer(datos), len(datos))
        except contenedor.FormatoError as e:
            fallos.append((nombre, str(e)))
            continue
        if rs[0].inicio != 0 or rs[-1].fin != len(datos) or any(r.fin != s.inicio for r, s in zip(rs, rs[1:])):
            fallos.append((nombre, "regiones con hueco o solape"))
    assert fallos == []


def test_los_kits_x86_son_de_32_bits_y_los_x64_casi_todos_de_64(corpus):
    bits = collections.Counter((nombre.split(":")[0][-10:-8], contenedor.leer(d).bits) for nombre, d in corpus)
    assert set(bits) <= {("86", 32), ("64", 64), ("64", 32)}
    assert bits[("64", 64)] > 50 * bits[("64", 32)]


def test_ide_y_str_se_leen_en_todo_el_corpus(corpus):
    sobrantes = collections.Counter()
    for nombre, d in corpus:
        omd = contenedor.leer(d)
        for etq in ("IDE", "STR"):
            emp = empaquetado.de_omd(d, omd, etq)
            assert len(emp.registros) == omd.seccion(etq).n, (nombre, etq)
            sobrantes[etq] += bool(emp.sobrante)
    # Los restos de comentarios (auxiliar.omd, abseval.omd) se juntan con su registro
    assert sobrantes == {"IDE": 0, "STR": 0}


def test_svl_se_lee_en_todo_el_corpus_sin_sobrantes(corpus):
    tipos = collections.Counter()
    for nombre, d in corpus:
        omd = contenedor.leer(d)
        emp = empaquetado.de_omd(d, omd, "SVL")
        assert len(emp.registros) == omd.seccion("SVL").n and not emp.sobrante, nombre
        tipos.update("binario" if r.binario else "texto" for r in emp.registros)
    assert tipos["binario"] > 1000 and tipos["texto"] > 10 * tipos["binario"]


def test_svl_de_dbmanager_configuration(corpus):
    d = _uno(corpus, "dbmanager/configuration.omd")
    regs = empaquetado.de_omd(d, contenedor.leer(d), "SVL").registros
    textos = [r.texto() for r in regs if not r.binario]
    assert textos[0] == "Configuración" and textos[-2:] == ["Aceptar", "Cancelar"]
    assert "Mostar Conexiones ODBC en la lista de Conexiones" in textos  # «Mostar» es la errata del original
    assert [(r.tipo, r.longitud) for r in regs if r.binario] == [(1, 168)]


def test_str_de_abseval_no_pierde_su_ultimo_registro(corpus):
    # abseval.omd (x86) tiene restos de comentario en medio de STR; antes desplazaban
    # el último registro fuera de los n declarados
    (d,) = [d for nombre, d in corpus if nombre.startswith("cosmos86x86eval") and nombre.lower().endswith("calcalg/abseval.omd")]
    regs = empaquetado.de_omd(d, contenedor.leer(d), "STR").registros
    assert "Return the evaluation result, null if errors found" in regs[-1].texto()
    assert not any(r.texto().startswith("or\r\n") for r in regs)


def _uno(corpus, sufijo):
    (d,) = [d for nombre, d in corpus if nombre.startswith("cosmos86x64eval") and nombre.lower().endswith(sufijo)]
    return d


def test_str_de_test1_son_la_ruta_y_los_dos_literales(corpus):
    d = _uno(corpus, "projects/nif/test1.omd")
    textos = [r.texto() for r in empaquetado.de_omd(d, contenedor.leer(d), "STR").registros]
    assert textos == [r"C:\CosmosVersiones\cosmos742_x64\projects\NIF\test1.SMD", "12345678Z", "12345678S"]


def test_ide_de_security_sigue_el_orden_del_fuente(corpus):
    d = _uno(corpus, "demorestcosmos/security.omd")
    textos = [r.texto() for r in empaquetado.de_omd(d, contenedor.leer(d), "IDE").registros]
    assert textos == ["SECURITY", "authenticate", "username", "password", "domain", "retStr", "retStatus",
                      "retStatus", "STATUS_OK", "SetExecStatus", "retStatus", "retStr"]


def test_las_listas_tienen_siempre_las_mismas_etiquetas(corpus):
    vistas = {tuple(tuple(s.etiqueta for s in l) for l in contenedor.leer(d).listas) for _, d in corpus}
    assert vistas == {(
        ("LIB", "INC", "EMO", "ICO", "FON", "CMD"),
        ("CTE", "CLA", "OBJ", "MOP", "MNU", "PAG", "FOR", "FOB", "FTA", "FCT", "FJO", "FRC",
         "PCT", "DEC", "DTT", "ITV", "PRO", "STM", "REF", "DPR", "DST", "DRE", "IDE", "STR"),
        ("EOB", "EPR", "EFT", "ECT", "ECL", "EID", "SVL"),
    )}

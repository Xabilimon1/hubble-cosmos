import importlib.util
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "lab" / "bateria" / "genera.py"


@pytest.fixture(scope="module")
def genera():
    spec = importlib.util.spec_from_file_location("genera", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


BASE = (
    "CONSTANTS  begin\r\nend\r\nCODE BEGIN\r\n//{{CODEBEGIN\r\nmain\r\nobjects begin\r\n"
    "    a as integer\r\nend\r\nbegin\r\n    a = 1;\r\nend\r\n//{{CODEEND\r\nEND\r\n"
)


def test_base_tiene_la_forma_de_los_ejemplos_del_kit(genera, tmp_path):
    (tmp_path / "huecos.txt").write_text("\n".join(f"H{i}" for i in range(len(genera.P))))
    genera.main([str(tmp_path / "s"), str(tmp_path / "huecos.txt")])
    assert (tmp_path / "s" / "H0.SMD").read_bytes().decode("cp1252") == BASE


def test_manifiesto_un_programa_por_hueco_en_orden(genera, tmp_path):
    (tmp_path / "huecos.txt").write_text("\n".join(f"H{i}" for i in range(len(genera.P) + 3)))
    genera.main([str(tmp_path / "s"), str(tmp_path / "huecos.txt")])
    filas = (tmp_path / "s" / "manifiesto.tsv").read_text().splitlines()
    assert filas == [f"H{i}\t{n}" for i, n in enumerate(genera.P)]
    assert len(list((tmp_path / "s").glob("*.SMD"))) == len(genera.P)


def test_sin_huecos_suficientes_no_escribe_nada(genera, tmp_path):
    (tmp_path / "huecos.txt").write_text("H0\nH1\n")
    with pytest.raises(SystemExit):
        genera.main([str(tmp_path / "s"), str(tmp_path / "huecos.txt")])
    assert not (tmp_path / "s").exists()


def test_sin_tabuladores_ni_saltos_sueltos(genera):
    for nombre, fuente in genera.P.items():
        assert "\t" not in fuente and "\r" not in fuente, nombre


# --- vuelta.py: la tanda se repite con el fuente original de los descompilados que no compilan (proy, ALMAFAC3)

@pytest.fixture(scope="module")
def vuelta():
    spec = importlib.util.spec_from_file_location("vuelta", RUTA.with_name("vuelta.py"))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_caidos_repone_el_fuente_original_solo_de_los_descompilados_que_fallan(vuelta, tmp_path, capsys):
    """El informe de compila_lote.sh dice quién falló; solo cuentan los descompilados (PROVEE_ es una dependencia con
    su fuente original y falla por su cuenta). El descompilado se guarda aparte y su nombre, en el fichero de caídos."""
    informe, hechos, fuentes = tmp_path / "informe.tsv", tmp_path / "vuelta", tmp_path / "orig"
    hechos.mkdir(); fuentes.mkdir()
    informe.write_text("AUXILIAR\tfallo\tFatal Error (S2000) Actual font(FONT)\nCLIENTES\tok\nINICIO\tok-solo\n"
                       "PROVEE_\tfallo\tUnregistered module PROVEE_\n")
    for n in ("AUXILIAR", "CLIENTES", "INICIO", "PROVEE_"):
        (fuentes / f"{n}.SMD").write_bytes(b"original " + n.encode())
    for n in ("auxiliar", "clientes", "inicio"):
        (hechos / f"{n}.SMD").write_bytes(b"hubble " + n.encode())
    (tmp_path / "cuentan.txt").write_text("auxiliar\nclientes\ninicio\n")
    nombres = vuelta.caidos(informe, hechos, fuentes, tmp_path / "cuentan.txt", tmp_path / "caidos.txt")
    assert nombres == ["auxiliar"]
    assert capsys.readouterr().out.strip() == "auxiliar"
    assert (tmp_path / "caidos.txt").read_text() == "auxiliar\n"
    assert (hechos / "auxiliar.SMD").read_bytes() == b"original AUXILIAR"  # repuesto, con el nombre del descompilado
    assert (hechos / "caidos" / "auxiliar.SMD").read_bytes() == b"hubble auxiliar"  # el descompilado, aparte
    assert (hechos / "clientes.SMD").read_bytes() == b"hubble clientes"
    assert (hechos / "inicio.SMD").read_bytes() == b"hubble inicio"
    assert not (hechos / "PROVEE_.SMD").exists()


def test_caidos_sin_fallos_deja_el_fichero_vacio(vuelta, tmp_path, capsys):
    (tmp_path / "informe.tsv").write_text("A\tok\n")
    (tmp_path / "v").mkdir(); (tmp_path / "o").mkdir()
    (tmp_path / "cuentan.txt").write_text("a\n")
    assert vuelta.caidos(tmp_path / "informe.tsv", tmp_path / "v", tmp_path / "o", tmp_path / "cuentan.txt", tmp_path / "c.txt") == []
    assert (tmp_path / "c.txt").read_text() == "" and capsys.readouterr().out.strip() == ""
    assert not (tmp_path / "v" / "caidos").exists()


def test_compara_cuenta_los_caidos_como_que_no_compilan(vuelta, tmp_path, capsys):
    """Tras repetir la tanda, el .omd del caído es el de su fuente original (idéntico): no cuenta como vuelta."""
    o, n = tmp_path / "o", tmp_path / "n"
    o.mkdir(); n.mkdir()
    for d in (o, n):
        (d / "auxiliar.omd").write_bytes(b"x" * 64)
        (d / "clientes.omd").write_bytes(b"y" * 64)
    (tmp_path / "cuentan.txt").write_text("auxiliar\nclientes\n")
    (tmp_path / "caidos.txt").write_text("auxiliar\n")
    assert vuelta.compara(o, n, tmp_path / "cuentan.txt", tmp_path / "caidos.txt") == 1
    salida = capsys.readouterr().out
    assert "DISTINTO auxiliar: el descompilado no compila" in salida
    assert "1 de 1 idénticos byte a byte; 0 más idénticos salvo punteros de memoria; 1 distintos" in salida
    assert vuelta.compara(o, n, tmp_path / "cuentan.txt") == 0  # sin caídos (o sin el fichero), los dos cuentan
    assert vuelta.compara(o, n, tmp_path / "cuentan.txt", tmp_path / "no-existe.txt") == 0
    assert "2 de 2 idénticos" in capsys.readouterr().out

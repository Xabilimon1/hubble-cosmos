import json

import pytest

from hubble import cli
from omd_sintetico import minimo


@pytest.fixture
def carpeta(tmp_path):
    (tmp_path / "a.omd").write_bytes(b"COMD\x01" + b"\x00" * 3 + b"SELECT a FROM b\x00Menu\x00")
    (tmp_path / "b.omd").write_bytes(b"COMD\x02" + b"\x00" * 40)
    return tmp_path


def _json(capsys):
    return json.loads(capsys.readouterr().out)


def test_inventario_json(carpeta, capsys):
    cli.main(["inventario", str(carpeta), "--json"])
    salida = _json(capsys)
    (grupo,) = salida["grupos"]
    assert (grupo["extension"], grupo["ficheros"], grupo["firma_comun"]) == (".omd", 2, "43 4f 4d 44")
    assert [f["ruta"] for f in salida["ficheros"]] == ["a.omd", "b.omd"]


def test_cadenas_solo_sql(carpeta, capsys):
    cli.main(["cadenas", str(carpeta / "a.omd"), "--sql", "--json"])
    assert [c["texto"] for c in _json(capsys)["cadenas"]] == ["SELECT a FROM b"]


def test_cadenas_recorre_carpetas_y_ordena_por_desplazamiento(carpeta, capsys):
    cli.main(["cadenas", str(carpeta)])
    lineas = capsys.readouterr().out.splitlines()
    assert [l.split("\t")[1:] for l in lineas] == [
        ["0x00000000", "COMD"],
        ["0x00000008", "SELECT a FROM b"],
        ["0x00000018", "Menu"],
        ["0x00000000", "COMD"],
    ]


def test_cabeceras_marca_la_magia_como_constante(carpeta, capsys):
    cli.main(["cabeceras", str(carpeta), "-n", "8", "--json"])
    assert [b["constante"] for b in _json(capsys)["bytes"]] == [True] * 4 + [False] + [True] * 3


def test_entropia_avisa_si_parece_comprimido(tmp_path, capsys):
    (tmp_path / "x.bin").write_bytes(bytes(range(256)) * 4)
    cli.main(["entropia", str(tmp_path / "x.bin")])
    assert "probablemente comprimido o cifrado" in capsys.readouterr().out


def test_sin_orden_sale_con_error():
    with pytest.raises(SystemExit):
        cli.main([])


def test_secciones_json_lista_las_regiones(tmp_path, capsys):
    (tmp_path / "m.omd").write_bytes(minimo())
    cli.main(["secciones", str(tmp_path / "m.omd"), "--json"])
    (fichero,) = _json(capsys)
    regiones = fichero["regiones"]
    assert regiones[0] == {"inicio": 0, "fin": 0x4C, "nombre": "cabecera", "variable": False}
    assert [r["nombre"] for r in regiones if r["variable"]] == ["B/IDE", "B/STR", "C/SVL"]
    assert fichero["secciones"]["INC"] == {"lista": "A", "datos": 0x4C + 64, "n": 2, "tam_registro": 24, "marca": 2}
    assert [fichero["secciones"][e]["lista"] for e in ("CTE", "SVL")] == ["B", "C"]


def test_secciones_dice_la_arquitectura(tmp_path, capsys):
    (tmp_path / "m.omd").write_bytes(minimo())
    cli.main(["secciones", str(tmp_path / "m.omd"), "--json"])
    (fichero,) = _json(capsys)
    assert fichero["bits"] == 64
    cli.main(["secciones", str(tmp_path / "m.omd")])
    assert "64 bits" in capsys.readouterr().out.splitlines()[0]


def test_secciones_sin_arquitectura_sigue_dando_las_regiones(tmp_path, capsys):
    from omd_sintetico import construir

    raro = construir(a=[("INC", 0, 13, None)], b=[("IDE", 0, 40, 0)], c=[("SVL", 0, 10, 0)])
    (tmp_path / "m.omd").write_bytes(raro)
    cli.main(["secciones", str(tmp_path / "m.omd"), "--json"])
    (fichero,) = _json(capsys)
    assert fichero["bits"] is None and "INC" in fichero["aviso"] and fichero["regiones"]


def _omd_con_textos(tmp_path):
    from omd_sintetico import construir, empaquetar, registro
    from hubble import contenedor

    ide = empaquetar([registro(b"TEST1"), registro(b"nif")], 40)
    str_ = empaquetar([registro(b"C:\\x.SMD"), registro(b"select a from clientes"), registro(b"Atenci\xf3n")], 264)
    datos = construir(a=[("INC", 0, 24, None)], b=[("CTE", 0, 48, None), ("IDE", 2, 40, len(ide)), ("STR", 3, 264, len(str_))],
                      c=[("SVL", 0, 10, 6)])
    omd = contenedor.leer(datos)
    datos = bytearray(datos)
    for etq, contenido in (("IDE", ide), ("STR", str_)):
        datos[omd.seccion(etq).datos : omd.seccion(etq).datos + len(contenido)] = contenido
    (tmp_path / "m.omd").write_bytes(bytes(datos))
    return tmp_path / "m.omd"


def test_textos_da_las_cadenas_por_defecto(tmp_path, capsys):
    cli.main(["textos", str(_omd_con_textos(tmp_path)), "--json"])
    (fichero,) = _json(capsys)
    assert [t["texto"] for t in fichero["textos"]] == ["C:\\x.SMD", "select a from clientes", "Atención"]


def test_textos_de_identificadores(tmp_path, capsys):
    cli.main(["textos", str(_omd_con_textos(tmp_path)), "--seccion", "IDE", "--json"])
    (fichero,) = _json(capsys)
    assert [t["texto"] for t in fichero["textos"]] == ["TEST1", "nif"]


def test_textos_solo_sql(tmp_path, capsys):
    cli.main(["textos", str(_omd_con_textos(tmp_path)), "--sql"])
    lineas = capsys.readouterr().out.splitlines()
    assert len(lineas) == 1 and lineas[0].endswith("\tselect a from clientes")


def test_textos_texto_lleva_indice_y_desplazamiento(tmp_path, capsys):
    ruta = _omd_con_textos(tmp_path)
    cli.main(["textos", str(ruta)])
    primera = capsys.readouterr().out.splitlines()[0].split("\t")
    assert primera[0] == str(ruta) and primera[1] == "0" and primera[2].startswith("0x") and primera[3] == "C:\\x.SMD"


def _omd_con_svl(tmp_path):
    from omd_sintetico import binario, construir, empaquetar, registro

    svl = empaquetar([registro(b"Aceptar"), binario(bytes(12), tipo=1), registro(b"Cancelar")], 10)
    datos = construir(a=[("INC", 0, 24, None)], b=[("IDE", 0, 40, 0)], c=[("EID", 0, 40, None), ("SVL", 3, 10, len(svl))])
    from hubble import contenedor

    datos = datos[: contenedor.leer(datos).seccion("SVL").datos] + svl
    (tmp_path / "s.omd").write_bytes(datos)
    return tmp_path / "s.omd"


def test_textos_de_svl_marca_los_binarios(tmp_path, capsys):
    cli.main(["textos", str(_omd_con_svl(tmp_path)), "--seccion", "SVL", "--json"])
    (fichero,) = _json(capsys)
    assert [(t["texto"], t["binario"]) for t in fichero["textos"]] == [("Aceptar", False), (None, True), ("Cancelar", False)]
    assert (fichero["textos"][1]["tipo"], fichero["textos"][1]["longitud"]) == (1, 16)


def test_textos_de_svl_en_texto(tmp_path, capsys):
    cli.main(["textos", str(_omd_con_svl(tmp_path)), "--seccion", "SVL"])
    lineas = capsys.readouterr().out.splitlines()
    assert lineas[1].endswith("\t[binario: tipo 1, 16 bytes]") and lineas[2].endswith("\tCancelar")


def test_cadenas_usa_windows_1252_por_defecto(tmp_path, capsys):
    (tmp_path / "x.omd").write_bytes(b"\x00Condici\xf3n\x00")
    cli.main(["cadenas", str(tmp_path / "x.omd")])
    assert capsys.readouterr().out.rstrip().endswith("\tCondición")


def test_textos_avisa_si_no_es_omd(tmp_path, capsys):
    (tmp_path / "a.omd").write_bytes(b"no" * 50)
    cli.main(["textos", str(tmp_path / "a.omd"), "--json"])
    (fichero,) = _json(capsys)
    assert "COMD" in fichero["error"]


def test_secciones_texto_marca_las_variables(tmp_path, capsys):
    (tmp_path / "m.omd").write_bytes(minimo())
    cli.main(["secciones", str(tmp_path / "m.omd")])
    lineas = [l for l in capsys.readouterr().out.splitlines() if "B/IDE" in l]
    assert len(lineas) == 1 and "variable" in lineas[0]


def test_secciones_avisa_y_sigue_si_un_fichero_no_es_omd(tmp_path, capsys):
    (tmp_path / "a.omd").write_bytes(b"no es un omd" * 10)
    (tmp_path / "b.omd").write_bytes(minimo())
    cli.main(["secciones", str(tmp_path), "--json"])
    a, b = _json(capsys)
    assert "COMD" in a["error"] and "regiones" in b

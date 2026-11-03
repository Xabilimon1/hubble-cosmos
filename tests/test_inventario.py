from pathlib import Path

from hubble import inventario


def _escribir(raiz: Path, ruta: str, datos: bytes) -> None:
    p = raiz / ruta
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(datos)


def test_recorrer_entra_en_subcarpetas_y_ordena_por_ruta(tmp_path):
    _escribir(tmp_path, "b.omd", b"x")
    _escribir(tmp_path, "sub/a.omd", b"y")
    _escribir(tmp_path, "a.prj", b"z")
    rutas = [str(f.ruta) for f in inventario.recorrer(tmp_path)]
    assert rutas == ["a.prj", "b.omd", "sub/a.omd"]


def test_recorrer_ordena_por_ruta_completa_no_por_carpeta(tmp_path):
    # os.walk da antes los ficheros de la raíz que los de las subcarpetas
    _escribir(tmp_path, "b.omd", b"x")
    _escribir(tmp_path, "a/z.omd", b"y")
    rutas = [str(f.ruta) for f in inventario.recorrer(tmp_path)]
    assert rutas == ["a/z.omd", "b.omd"]


def test_recorrer_da_rutas_relativas_a_la_raiz(tmp_path):
    _escribir(tmp_path, "sub/m.omd", b"x")
    (f,) = inventario.recorrer(tmp_path)
    assert f.ruta == Path("sub/m.omd")


def test_recorrer_no_sigue_enlaces_simbolicos(tmp_path):
    _escribir(tmp_path, "real.omd", b"x")
    (tmp_path / "enlace.omd").symlink_to(tmp_path / "real.omd")
    assert [str(f.ruta) for f in inventario.recorrer(tmp_path)] == ["real.omd"]


def test_recorrer_pone_la_extension_en_minusculas(tmp_path):
    _escribir(tmp_path, "TRIPLE.OMD", b"x")
    _escribir(tmp_path, "LEEME", b"x")
    exts = {f.extension for f in inventario.recorrer(tmp_path)}
    assert exts == {".omd", "(sin extensión)"}


def test_recorrer_guarda_tamano_y_solo_los_primeros_bytes_como_firma(tmp_path):
    datos = bytes(range(40))
    _escribir(tmp_path, "m.omd", datos)
    (f,) = inventario.recorrer(tmp_path)
    assert f.tamano == 40
    assert f.firma == datos[: inventario.BYTES_FIRMA]


def test_prefijo_comun_corta_en_el_primer_byte_distinto():
    assert inventario.prefijo_comun([b"COMD\x01\x02", b"COMD\x01\x03", b"COMD\x01"]) == b"COMD\x01"


def test_prefijo_comun_sin_coincidencia_es_vacio():
    assert inventario.prefijo_comun([b"abc", b"xbc"]) == b""


def test_prefijo_comun_de_lista_vacia_es_vacio():
    assert inventario.prefijo_comun([]) == b""


def test_agrupar_suma_por_extension_y_ordena_de_mas_a_menos(tmp_path):
    _escribir(tmp_path, "a.omd", b"COMD1")
    _escribir(tmp_path, "b.omd", b"COMD22")
    _escribir(tmp_path, "c.prj", b"P")
    _escribir(tmp_path, "d.ini", b"I")
    grupos = inventario.agrupar(inventario.recorrer(tmp_path))
    assert [(g.extension, g.ficheros, g.bytes_totales) for g in grupos] == [
        (".omd", 2, 11),
        (".ini", 1, 1),
        (".prj", 1, 1),
    ]
    assert grupos[0].firma_comun == b"COMD"

import pytest

from hubble import cadenas


def test_extraer_encuentra_texto_con_su_desplazamiento():
    datos = b"\x00\x01SELECT * FROM clientes\x00\x02"
    (c,) = cadenas.extraer(datos)
    assert (c.desplazamiento, c.texto, c.codificacion) == (2, "SELECT * FROM clientes", "cp1252")


def test_extraer_descarta_las_secuencias_mas_cortas_que_el_minimo():
    datos = b"abc\x00abcd\x00"
    assert [c.texto for c in cadenas.extraer(datos, minimo=4)] == ["abcd"]


def test_extraer_recoge_la_cadena_que_llega_al_final_del_fichero():
    assert [c.texto for c in cadenas.extraer(b"\x00\x00final")] == ["final"]


def test_extraer_lee_los_acentos_en_cp850():
    # «Menú» en cp850: ú = 0xA3
    assert [c.texto for c in cadenas.extraer(b"\x00Men\xa3\x00", codificacion="cp850")] == ["Menú"]


def test_extraer_usa_windows_1252_por_defecto():
    # Así van los .omd de los kits: «Condición» con ó = 0xF3
    assert [c.texto for c in cadenas.extraer(b"\x00Condici\xf3n\x00")] == ["Condición"]


def test_extraer_lee_los_acentos_en_cp1252():
    # «Menú» en cp1252: ú = 0xFA
    assert [c.texto for c in cadenas.extraer(b"\x00Men\xfa\x00", codificacion="cp1252")] == ["Menú"]


def test_extraer_corta_en_los_bytes_de_control():
    assert [c.texto for c in cadenas.extraer(b"uno1\x0adosd")] == ["uno1", "dosd"]


def test_extraer_corta_en_el_byte_de_borrado():
    # 0x7F (DEL) está por encima de 0x20 pero no es imprimible en ninguna de las tres
    assert [c.texto for c in cadenas.extraer(b"abcd\x7fefgh")] == ["abcd", "efgh"]


def test_extraer_rechaza_una_codificacion_desconocida():
    with pytest.raises(ValueError):
        cadenas.extraer(b"abcd", codificacion="utf-8")


def test_extraer_utf16_en_posicion_par():
    datos = b"\x00\x00" + "Hola".encode("utf-16-le") + b"\x00\x00"
    (c,) = cadenas.extraer_utf16(datos)
    assert (c.desplazamiento, c.texto, c.codificacion) == (2, "Hola", "utf-16-le")


def test_extraer_utf16_en_posicion_impar():
    datos = b"\x01" + "Adiós".encode("utf-16-le") + b"\x00\x00"
    assert [(c.desplazamiento, c.texto) for c in cadenas.extraer_utf16(datos)] == [(1, "Adiós")]


def test_extraer_utf16_no_confunde_texto_de_un_byte():
    assert cadenas.extraer_utf16(b"ABCDEFGH") == []


@pytest.mark.parametrize(
    "texto",
    ["SELECT a FROM b", "select * from clientes where id = 1", "INSERT INTO t VALUES (1)", "x ORDER BY y"],
)
def test_parece_sql_reconoce_sentencias(texto):
    assert cadenas.parece_sql(texto)


@pytest.mark.parametrize("texto", ["selection", "Proveedores", "FROMAGE", "DELETED"])
def test_parece_sql_exige_palabra_completa(texto):
    assert not cadenas.parece_sql(texto)

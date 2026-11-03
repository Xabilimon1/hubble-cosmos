import struct

import pytest

from hubble import cabeceras


def test_comparar_marca_los_bytes_iguales_en_todos():
    bs = cabeceras.comparar([b"COMDa", b"COMDb"], n=5)
    assert [b.constante for b in bs] == [True, True, True, True, False]


def test_comparar_un_fichero_corto_no_cuenta_como_constante():
    bs = cabeceras.comparar([b"AB", b"A"], n=2)
    assert [b.constante for b in bs] == [True, False]
    assert bs[1].valores == (ord("B"), None)


def test_comparar_si_todos_son_cortos_el_byte_no_es_constante():
    bs = cabeceras.comparar([b"A", b"A"], n=2)
    assert [b.constante for b in bs] == [True, False]


def _con_entero(tamano: int, off: int, valor: int, fmt: str = "<I") -> bytes:
    datos = bytearray(tamano)
    struct.pack_into(fmt, datos, off, valor)
    return bytes(datos)


def _relaciones(cands, off, ancho, orden):
    return {c.relacion for c in cands if (c.desplazamiento, c.ancho, c.orden) == (off, ancho, orden)}


def test_candidatos_detecta_el_tamano_del_fichero():
    fs = [_con_entero(100, 8, 100), _con_entero(150, 8, 150)]
    assert "tamaño del fichero" in _relaciones(cabeceras.candidatos(fs, 16), 8, 4, "<")


def test_candidatos_detecta_tamano_menos_cabecera():
    fs = [_con_entero(100, 8, 100 - 12), _con_entero(150, 8, 150 - 12)]
    assert "tamaño menos 12" in _relaciones(cabeceras.candidatos(fs, 16), 8, 4, "<")


def test_candidatos_detecta_big_endian():
    fs = [_con_entero(100, 8, 100, ">I"), _con_entero(150, 8, 150, ">I")]
    assert "tamaño del fichero" in _relaciones(cabeceras.candidatos(fs, 16), 8, 4, ">")


def test_candidatos_detecta_punteros_que_cambian_entre_ficheros():
    fs = [_con_entero(100, 4, 40), _con_entero(150, 4, 90)]
    assert "apunta dentro del fichero" in _relaciones(cabeceras.candidatos(fs, 16), 4, 4, "<")


def test_candidatos_un_valor_fijo_no_es_puntero():
    fs = [_con_entero(100, 4, 40), _con_entero(150, 4, 40)]
    assert _relaciones(cabeceras.candidatos(fs, 16), 4, 4, "<") == set()


def test_candidatos_un_puntero_fuera_del_fichero_no_cuenta():
    fs = [_con_entero(100, 4, 40), _con_entero(150, 4, 200)]
    assert _relaciones(cabeceras.candidatos(fs, 16), 4, 4, "<") == set()


def test_candidatos_un_puntero_dentro_de_la_cabecera_no_cuenta():
    fs = [_con_entero(100, 4, 10), _con_entero(150, 4, 12)]
    assert _relaciones(cabeceras.candidatos(fs, 16), 4, 4, "<") == set()


def test_candidatos_exige_al_menos_dos_ficheros():
    with pytest.raises(ValueError):
        cabeceras.candidatos([b"\x00" * 64])

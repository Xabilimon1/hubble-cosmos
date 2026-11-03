import pytest

from hubble import entropia


def test_shannon_vacio_es_cero():
    assert entropia.shannon(b"") == 0.0


def test_shannon_un_solo_valor_es_cero():
    assert entropia.shannon(b"aaaa") == 0.0


def test_shannon_dos_valores_equiprobables_es_un_bit():
    assert entropia.shannon(b"ab" * 50) == pytest.approx(1.0)


def test_shannon_los_256_valores_son_ocho_bits():
    assert entropia.shannon(bytes(range(256))) == pytest.approx(8.0)


def test_por_bloques_parte_en_trozos_y_el_ultimo_puede_ser_corto():
    bloques = entropia.por_bloques(b"a" * 10, tamano=4)
    assert [(b.desplazamiento, b.tamano) for b in bloques] == [(0, 4), (4, 4), (8, 2)]


def test_por_bloques_calcula_la_entropia_de_cada_trozo():
    bloques = entropia.por_bloques(b"aaaa" + bytes(range(4)), tamano=4)
    assert [b.entropia for b in bloques] == [0.0, pytest.approx(2.0)]


@pytest.mark.parametrize("tamano", [0, -1])
def test_por_bloques_rechaza_tamano_no_positivo(tamano):
    with pytest.raises(ValueError, match="positivo"):
        entropia.por_bloques(b"abc", tamano)


def test_proporcion_alta_pondera_por_bytes_no_por_bloques():
    alto = entropia.Bloque(0, 300, 7.9)
    bajo = entropia.Bloque(300, 100, 2.0)
    assert entropia.proporcion_alta([alto, bajo]) == pytest.approx(0.75)


def test_proporcion_alta_incluye_el_umbral():
    assert entropia.proporcion_alta([entropia.Bloque(0, 10, entropia.UMBRAL_ALTA)]) == 1.0


def test_proporcion_alta_sin_bloques_es_cero():
    assert entropia.proporcion_alta([]) == 0.0

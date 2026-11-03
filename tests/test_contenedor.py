import struct

import pytest

from hubble import contenedor
from omd_sintetico import TAM_CABECERA, construir, minimo


def test_leer_da_las_tres_listas_en_orden():
    omd = contenedor.leer(minimo())
    assert [[s.etiqueta for s in lista] for lista in omd.listas] == [["INC", "CMD"], ["CTE", "IDE", "STR"], ["EID", "SVL"]]


def test_leer_da_desplazamiento_numero_y_tamano_de_registro():
    omd = contenedor.leer(minimo())
    inc, cmd = omd.listas[0]
    assert inc.datos == TAM_CABECERA + 2 * 32
    assert (inc.n, inc.tam_registro) == (2, 24)
    assert cmd.datos == inc.datos + 2 * 24


def test_seccion_por_etiqueta():
    omd = contenedor.leer(minimo())
    assert omd.seccion("STR").n == 2
    with pytest.raises(KeyError):
        omd.seccion("XYZ")


def _con_registros(stm: int, pro: int) -> bytes:
    # ICO y SVL miden lo mismo en 32 y en 64 bits: no cuentan
    return construir(a=[("ICO", 0, 82, None)], b=[("PRO", 0, pro, None), ("STM", 0, stm, None)], c=[("SVL", 0, 10, 0)])


def test_bits_32_por_los_tamanos_de_registro():
    assert contenedor.leer(_con_registros(stm=24, pro=32)).bits == 32


def test_bits_64_por_los_tamanos_de_registro():
    assert contenedor.leer(_con_registros(stm=48, pro=64)).bits == 64


def test_bits_rechaza_tamanos_mezclados():
    with pytest.raises(contenedor.FormatoError, match="32 y 64"):
        contenedor.leer(_con_registros(stm=24, pro=64)).bits


def test_bits_rechaza_un_tamano_desconocido():
    with pytest.raises(contenedor.FormatoError, match="STM"):
        contenedor.leer(_con_registros(stm=30, pro=32)).bits


def test_rechaza_otra_magia():
    datos = bytearray(minimo())
    datos[0:4] = b"XOMD"
    with pytest.raises(contenedor.FormatoError, match="COMD"):
        contenedor.leer(bytes(datos))


def test_rechaza_un_fichero_mas_corto_que_la_cabecera():
    with pytest.raises(contenedor.FormatoError, match="cabecera"):
        contenedor.leer(minimo()[: TAM_CABECERA - 1])


def test_rechaza_una_entrada_fuera_del_fichero():
    datos = bytearray(minimo())
    struct.pack_into("<I", datos, 0x24, len(datos) + 100)
    with pytest.raises(contenedor.FormatoError, match="fuera"):
        contenedor.leer(bytes(datos))


def test_rechaza_una_entrada_que_se_sale_por_el_final():
    datos = bytearray(minimo())
    struct.pack_into("<I", datos, 0x24, len(datos) - 8)  # empieza dentro, sus 32 bytes no caben
    with pytest.raises(contenedor.FormatoError, match="fuera"):
        contenedor.leer(bytes(datos))


def test_rechaza_una_lista_en_bucle():
    datos = bytearray(minimo())
    primera = struct.unpack_from("<I", datos, 0x20)[0]
    struct.pack_into("<I", datos, primera + 12, primera)  # «siguiente» apunta a sí misma
    with pytest.raises(contenedor.FormatoError, match="bucle"):
        contenedor.leer(bytes(datos))


def test_regiones_cubren_el_fichero_entero_sin_huecos_ni_solapes():
    datos = minimo()
    regiones = contenedor.regiones(contenedor.leer(datos), len(datos))
    assert regiones[0].inicio == 0
    assert regiones[-1].fin == len(datos)
    assert all(r.fin == s.inicio for r, s in zip(regiones, regiones[1:]))


def test_regiones_nombran_cabecera_entradas_y_secciones():
    datos = minimo()
    nombres = [r.nombre for r in contenedor.regiones(contenedor.leer(datos), len(datos))]
    assert nombres == [
        "cabecera", "entradas A", "A/INC",
        "entradas B", "B/CTE", "B/IDE", "B/STR",
        "entradas C", "C/EID", "C/SVL",
    ]


def test_regiones_omiten_secciones_vacias_de_tamano_fijo():
    datos = minimo()
    nombres = [r.nombre for r in contenedor.regiones(contenedor.leer(datos), len(datos))]
    assert "A/CMD" not in nombres


def test_regiones_marcan_variables_solo_ide_str_y_svl():
    datos = minimo()
    variables = {r.nombre for r in contenedor.regiones(contenedor.leer(datos), len(datos)) if r.variable}
    assert variables == {"B/IDE", "B/STR", "C/SVL"}


def test_regiones_dan_el_tamano_real_de_las_variables():
    datos = minimo()
    por_nombre = {r.nombre: r for r in contenedor.regiones(contenedor.leer(datos), len(datos))}
    assert por_nombre["B/IDE"].fin - por_nombre["B/IDE"].inicio == 50
    assert por_nombre["C/SVL"].fin - por_nombre["C/SVL"].inicio == 6


def test_regiones_rechazan_una_seccion_fija_que_ocupa_de_mas():
    # CTE dice tener 1 registro de 48 bytes, pero hasta IDE hay 60
    datos = construir(a=[("INC", 0, 24, None)], b=[("CTE", 1, 48, 60), ("IDE", 0, 40, 0)], c=[("SVL", 0, 10, 0)])
    with pytest.raises(contenedor.FormatoError, match="CTE"):
        contenedor.regiones(contenedor.leer(datos), len(datos))


def test_regiones_aceptan_variables_mas_cortas_que_n_por_registro():
    # Así son IDE y STR en los kits: 8 identificadores de 40 bytes en 98 bytes
    datos = construir(a=[("INC", 0, 24, None)], b=[("IDE", 8, 40, 98)], c=[("SVL", 0, 10, 6)])
    (ide,) = [r for r in contenedor.regiones(contenedor.leer(datos), len(datos)) if r.nombre == "B/IDE"]
    assert (ide.fin - ide.inicio, ide.variable) == (98, True)


def test_regiones_rechazan_entradas_que_no_van_seguidas():
    datos = bytearray(minimo())
    primera = struct.unpack_from("<I", datos, 0x24)[0]
    segunda = primera + 32
    struct.pack_into("<I", datos, primera + 12, segunda + 4)  # «siguiente» salta 4 bytes de más
    datos[segunda + 4 : segunda + 36] = datos[segunda : segunda + 32]
    with pytest.raises(contenedor.FormatoError, match="no sigue"):
        contenedor.regiones(contenedor.leer(bytes(datos)), len(datos))


def test_regiones_rechazan_datos_que_no_empiezan_tras_las_entradas():
    datos = bytearray(minimo())
    primera = struct.unpack_from("<I", datos, 0x20)[0]
    struct.pack_into("<I", datos, primera + 16, struct.unpack_from("<I", datos, primera + 16)[0] + 8)
    with pytest.raises(contenedor.FormatoError, match="no empiezan"):
        contenedor.regiones(contenedor.leer(bytes(datos)), len(datos))


def test_regiones_rechazan_una_variable_que_empieza_despues_de_la_siguiente():
    datos = bytearray(minimo())
    omd = contenedor.leer(bytes(datos))
    ide, str_ = omd.seccion("IDE"), omd.seccion("STR")
    struct.pack_into("<I", datos, str_.entrada + 16, ide.datos - 4)  # STR empieza antes que IDE
    with pytest.raises(contenedor.FormatoError, match="IDE"):
        contenedor.regiones(contenedor.leer(bytes(datos)), len(datos))


def test_regiones_rechazan_una_seccion_que_pisa_la_siguiente():
    # CTE dice tener 10 registros de 48 bytes, pero IDE empieza 48 bytes después
    datos = construir(a=[("INC", 0, 24, None)], b=[("CTE", 10, 48, 48), ("IDE", 0, 40, 0)], c=[("SVL", 0, 10, 0)])
    with pytest.raises(contenedor.FormatoError, match="CTE"):
        contenedor.regiones(contenedor.leer(datos), len(datos))

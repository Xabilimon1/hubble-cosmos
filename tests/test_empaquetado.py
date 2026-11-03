import struct

import pytest

from hubble import contenedor, empaquetado
from omd_sintetico import binario, construir, empaquetar, registro


def _leer(seccion: bytes, bits: int = 64) -> empaquetado.Empaquetada:
    return empaquetado.leer(seccion, 0, len(seccion), bits)


def _leer_svl(seccion: bytes, bits: int = 64) -> empaquetado.Empaquetada:
    return empaquetado.leer(seccion, 0, len(seccion), bits, binarios=True)


def test_registro_sintetico_mide_lo_que_en_los_kits():
    # Medidas sacadas de test1.omd y security.omd (64 bits)
    assert [len(registro(t)) for t in (b"nif", b"TEST1", b"Testea", b"authenticate")] == [8, 16, 16, 24]
    # En 32 bits, tras los 8 primeros bytes se avanza de 4 en 4
    assert len(registro(b"authenticate", bits=32)) == 20


def test_leer_da_los_textos_en_orden():
    sec = empaquetar([registro(t) for t in (b"TEST1", b"nif", b"Testea")], 40)
    assert [r.texto() for r in _leer(sec).registros] == ["TEST1", "nif", "Testea"]


def test_leer_en_32_bits_avanza_de_4_en_4():
    regs = [registro(t, bits=32) for t in (b"authenticate", b"nif", b"SetExecStatus")]
    assert [r.texto() for r in _leer(empaquetar(regs, 40), bits=32).registros] == ["authenticate", "nif", "SetExecStatus"]


def test_leer_32_bits_con_unidades_de_64_se_descuadra():
    regs = [registro(t, bits=32) for t in (b"authenticate", b"nif")]
    with pytest.raises(contenedor.FormatoError):
        _leer(empaquetar(regs, 40), bits=64)


def test_leer_junta_los_registros_de_varios_bloques():
    regs = [registro(f"id{k:02d}".encode()) for k in range(10)]
    emp = _leer(empaquetar(regs, 40, tope=48))  # cada registro ocupa 16: caben 3 por bloque
    assert [r.texto() for r in emp.registros] == [f"id{k:02d}" for k in range(10)]
    assert len(emp.bloques) == 4
    assert all(b.sin_empaquetar == 32 * 40 for b in emp.bloques)
    assert [b.guardado for b in emp.bloques] == [48, 48, 48, 16]


def test_leer_da_el_valor_de_cada_registro():
    # En los kits el u32 de un registro de texto es siempre 0; si no lo es, es binario
    sec = empaquetar([registro(b"a"), binario(bytes(4), tipo=2)], 10)
    assert [r.valor for r in _leer_svl(sec).registros] == [0, 2 << 16 | 8]


def test_texto_para_en_el_nul_aunque_haya_restos_detras():
    # Como en eticli.omd: el compilador deja basura de memoria tras el NUL
    sec = empaquetar([registro(b"abcde", resto=b"al"), registro(b"x")], 264)
    regs = _leer(sec).registros
    assert [r.texto() for r in regs] == ["abcde", "x"]
    assert regs[0].datos == b"\x00\x00\x00\x00abcde\x00al\x00\x00\x00\x00"


def test_restos_tras_un_nul_al_final_de_unidad_son_del_mismo_registro():
    # auxiliar.omd y abseval.omd: el NUL cae en el último byte de una unidad y detrás
    # sigue basura. Un registro de texto real empieza siempre por un u32 a 0; si lo que
    # viene no empieza así, es resto del anterior (en IDE y STR no hay binarios).
    roto = registro(b"abc", resto=b"al\r\n *")
    assert roto[:8] == b"\x00\x00\x00\x00abc\x00"
    sec = empaquetar([roto, registro(b"siguiente")], 264)
    emp = _leer(sec)
    assert [r.texto() for r in emp.registros] == ["abc", "siguiente"]
    assert emp.registros[0].datos == roto and not emp.sobrante


def test_rechaza_restos_al_principio_de_la_seccion():
    sec = empaquetar([b"al\r\n *\x00\x00"], 264)  # empieza por u32 ≠ 0 sin nada delante
    with pytest.raises(contenedor.FormatoError, match="restos"):
        _leer(sec)


def test_rechaza_restos_al_principio_de_un_bloque():
    # Un registro no se parte entre bloques: lo de un bloque nuevo no puede ser resto del anterior
    sec = empaquetar([registro(b"uno"), b"al\r\n *\x00\x00"], 264, tope=8)
    with pytest.raises(contenedor.FormatoError, match="restos"):
        _leer(sec)


def test_restos_al_final_del_ultimo_bloque_tambien_se_juntan():
    roto = registro(b"abc", resto=b"al\r\n *")
    emp = _leer(empaquetar([roto], 264))
    assert [r.texto() for r in emp.registros] == ["abc"] and not emp.sobrante


def test_con_binarios_los_restos_no_se_juntan_sino_que_abren_un_binario():
    # En SVL un u32 ≠ 0 es un registro binario: aquí «al\r\n» daría una longitud absurda
    roto = registro(b"abc", resto=b"al\r\n *")
    with pytest.raises(contenedor.FormatoError, match="bloque"):
        _leer_svl(empaquetar([roto, registro(b"x")], 264))


def test_texto_en_windows_1252_por_defecto():
    sec = empaquetar([registro(b"Condici\xf3n")], 264)
    assert _leer(sec).registros[0].texto() == "Condición"


def test_lo_que_sobra_tras_los_n_registros_no_es_un_registro():
    extra = registro(b"tres")  # empieza por u32 0: no es resto del anterior
    sec = empaquetar([registro(b"uno"), registro(b"dos")], 264, sobrante=extra)
    emp = _leer(sec)
    assert [r.texto() for r in emp.registros] == ["uno", "dos"]
    assert [s for _, s in emp.sobrante] == [extra]


def test_completo_rellena_hasta_el_tamano_de_registro():
    (r,) = _leer(empaquetar([registro(b"nif")], 40)).registros
    assert r.completo(40) == r.datos + bytes(32)
    with pytest.raises(contenedor.FormatoError):
        r.completo(4)


def test_desplazamiento_de_cada_registro_en_el_fichero():
    sec = b"\xaa" * 6 + empaquetar([registro(b"TEST1"), registro(b"nif")], 40)
    emp = empaquetado.leer(sec, 6, len(sec), 64)
    assert [r.desplazamiento for r in emp.registros] == [6 + 10, 6 + 10 + 16]


def test_rechaza_un_registro_que_se_sale_del_bloque():
    sec = bytearray(empaquetar([registro(b"TEST1")], 40))
    sec[-1] = 1  # el último byte ya no es 0: el registro no termina dentro del bloque
    with pytest.raises(contenedor.FormatoError, match="bloque"):
        _leer(bytes(sec))


def test_rechaza_menos_registros_de_los_declarados():
    sec = bytearray(empaquetar([registro(b"uno")], 40))
    struct.pack_into("<I", sec, 0, 2)
    with pytest.raises(contenedor.FormatoError, match="registros"):
        _leer(bytes(sec))


def test_rechaza_bloques_que_no_acaban_en_el_fin_de_la_seccion():
    sec = empaquetar([registro(b"uno")], 40) + b"\x00" * 8
    with pytest.raises(contenedor.FormatoError, match="acaban"):
        _leer(sec)


@pytest.mark.parametrize("bits", [16, 128])
def test_rechaza_arquitecturas_desconocidas(bits):
    with pytest.raises(ValueError):
        _leer(empaquetar([registro(b"uno")], 40), bits=bits)


def test_de_omd_lee_la_seccion_por_etiqueta():
    ide = empaquetar([registro(b"TEST1"), registro(b"nif")], 40)
    str_ = empaquetar([registro(b"C:\\x.SMD"), registro(b"12345678Z")], 264)
    datos = construir(a=[("INC", 0, 24, None)], b=[("CTE", 0, 48, None), ("IDE", 2, 40, len(ide)), ("STR", 2, 264, len(str_))],
                      c=[("SVL", 0, 10, 6)])
    omd = contenedor.leer(datos)
    datos = bytearray(datos)
    for etq, contenido in (("IDE", ide), ("STR", str_)):
        datos[omd.seccion(etq).datos : omd.seccion(etq).datos + len(contenido)] = contenido
    datos = bytes(datos)
    assert [r.texto() for r in empaquetado.de_omd(datos, omd, "STR").registros] == ["C:\\x.SMD", "12345678Z"]
    assert [r.texto() for r in empaquetado.de_omd(datos, omd, "IDE").registros] == ["TEST1", "nif"]


# --- Registros binarios (SVL) ---


def test_mezcla_registros_de_texto_y_binarios_en_orden():
    regs = [registro(b"Configuraci\xf3n"), binario(b"\x01\x02" * 16, tipo=1), registro(b"General")]
    emp = _leer_svl(empaquetar(regs, 10))
    assert [r.binario for r in emp.registros] == [False, True, False]
    assert emp.registros[0].texto() == "Configuración" and emp.registros[2].texto() == "General"


def test_un_binario_dice_su_tipo_y_su_longitud():
    (r,) = _leer_svl(empaquetar([binario(bytes(range(32)), tipo=7)], 10)).registros
    assert (r.tipo, r.longitud) == (7, 36)
    assert r.cuerpo == bytes(range(32))


def test_un_binario_se_rellena_hasta_la_unidad():
    # 4 + 30 = 34 bytes: 40 en 64 bits, 36 en 32 bits
    for bits, ocupa in ((64, 40), (32, 36)):
        regs = [binario(bytes(30), bits=bits), registro(b"sig", bits=bits)]
        emp = _leer_svl(empaquetar(regs, 10), bits=bits)
        assert len(emp.registros[0].datos) == ocupa
        assert emp.registros[1].texto() == "sig"


def test_texto_de_un_binario_es_un_error():
    (r,) = _leer_svl(empaquetar([binario(b"abcd")], 10)).registros
    with pytest.raises(ValueError):
        r.texto()


def test_rechaza_un_binario_de_longitud_menor_que_su_cabecera():
    sec = empaquetar([struct.pack("<I", 1 << 16 | 2).ljust(8, b"\x00")], 10)
    with pytest.raises(contenedor.FormatoError, match="longitud"):
        _leer_svl(sec)


def test_rechaza_un_binario_que_se_sale_del_bloque():
    sec = bytearray(empaquetar([binario(bytes(12))], 10))
    struct.pack_into("<I", sec, 10, 1 << 16 | 200)
    with pytest.raises(contenedor.FormatoError, match="bloque"):
        _leer_svl(bytes(sec))


def test_de_omd_lee_svl_de_la_lista_c():
    svl = empaquetar([registro(b"Aceptar"), binario(bytes(12)), registro(b"Cancelar")], 10)
    datos = construir(a=[("INC", 0, 24, None)], b=[("IDE", 0, 40, 0)], c=[("EID", 0, 40, None), ("SVL", 3, 10, len(svl))])
    omd = contenedor.leer(datos)
    datos = datos[: omd.seccion("SVL").datos] + svl
    textos = [r.texto() for r in empaquetado.de_omd(datos, omd, "SVL").registros if not r.binario]
    assert textos == ["Aceptar", "Cancelar"]


def test_de_omd_rechaza_secciones_que_no_van_empaquetadas():
    with pytest.raises(ValueError):
        empaquetado.de_omd(b"", None, "CTE")

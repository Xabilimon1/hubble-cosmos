"""Formato 0x3211 (versión de la cabecera; un Cosmos más antiguo, solo de 32 bits): FOR, FCT y PCT más cortos.

Sin datos de módulos reales de ese formato: los registros son sintéticos o salen de los .omd de 32 bits de los kits,
recortados a mano con `a_3211` (la inversa de `descompilador.de_3211`). Un módulo de 8.6 pasado así a 0x3211 tiene
que dar el mismo fuente, con el aviso fijo delante de los suyos.
"""
import os
import struct
from pathlib import Path

import pytest

from hubble import contenedor, descompilador
from omd_sintetico import MAGIA, construir

KITS = Path(os.environ.get("HUBBLE_KITS", Path(__file__).resolve().parents[1] / "kits"))
AVISO = "formato 0x3211: sin compilador de esta versión, no comprobado con vuelta"


def _version(datos: bytes, version: int) -> bytes:
    return datos[:8] + struct.pack("<I", version) + datos[12:]


def _secciones(for_=28, fct=112, pct=112, stm=24) -> bytes:
    return construir(a=[("ICO", 0, 82, None)], b=[("FOR", 0, for_, None), ("FCT", 0, fct, None), ("PCT", 0, pct, None),
                                                 ("STM", 0, stm, None)], c=[("SVL", 0, 10, 0)])


# --- contenedor
def test_lee_la_version_de_la_cabecera():
    assert MAGIA[8:12] == struct.pack("<I", 0x7230)
    assert contenedor.leer(_secciones(32, 120, 120)).version == contenedor.VERSION_86 == 0x7230
    assert contenedor.leer(_version(_secciones(), 0x3211)).version == contenedor.VERSION_3211 == 0x3211


def test_3211_es_de_32_bits_con_for_fct_y_pct_cortos():
    assert contenedor.leer(_version(_secciones(), 0x3211)).bits == 32


@pytest.mark.parametrize("tamanos, seccion", [((32, 112, 112), "FOR"), ((28, 120, 112), "FCT"), ((28, 112, 120), "PCT")])
def test_3211_no_admite_los_tamanos_de_86(tamanos, seccion):
    with pytest.raises(contenedor.FormatoError, match=f"{seccion} \\(formato 0x3211\\)"):
        contenedor.leer(_version(_secciones(*tamanos), 0x3211)).bits


def test_3211_no_admite_las_demas_de_64_bits():
    with pytest.raises(contenedor.FormatoError, match="32 y 64"):
        contenedor.leer(_version(_secciones(stm=48), 0x3211)).bits


def test_3211_sin_secciones_que_lo_digan_y_de_64_bits():
    # solo con secciones de 64 bits (ninguna de las cortas): no es 0x3211
    solo64 = construir(a=[("ICO", 0, 82, None)], b=[("STM", 0, 48, None)], c=[("SVL", 0, 10, 0)])
    with pytest.raises(contenedor.FormatoError, match="0x3211 con tamaños de registro de 64 bits"):
        contenedor.leer(_version(solo64, 0x3211)).bits


def test_86_no_admite_los_tamanos_de_3211():
    with pytest.raises(contenedor.FormatoError, match="desconocido en FOR"):
        contenedor.leer(_secciones()).bits


def test_version_desconocida():
    with pytest.raises(contenedor.FormatoError, match="versión de formato 0x3210 desconocida"):
        contenedor.leer(_version(_secciones(32, 120, 120), 0x3210)).bits


# --- registros
def test_for_de_3211_es_el_de_86_sin_su_ultimo_u32():
    crudo = struct.pack("<7I", 0x80000000, 0, 0x31000, 0x21400, 0x51200, 0x61200, 0x71200)
    assert descompilador.de_3211("FOR", crudo) == crudo + bytes(4)


def _fct(**campos) -> bytes:
    w = [0] * 28
    for o, v in campos.items():
        w[int(o[1:], 16) // 4] = v
    return struct.pack("<28I", *w)


def test_fct_de_3211_parte_el_u32_de_14_y_corre_el_resto_cuatro_bytes():
    w = [0xA0000040, 0x41000, 0x11000, 0x1000, 0x7, 0x30000] + [0x100 + i for i in range(6, 21)] + [0, 0, 0, 0x111, 0x40001, 0x22100, 0]
    salida = struct.unpack("<30I", descompilador.de_3211("FCT", struct.pack("<28I", *w)))
    assert salida[:5] == tuple(w[:5])
    assert salida[5:7] == (0, 3)  # u16 bajo de +0x14; número de control (u16 alto) en +0x18
    assert salida[7:29] == tuple(w[6:28])  # +0x18.. → +0x1C..
    assert salida[29] == 0


def test_pct_de_3211_igual_que_fct():
    crudo = _fct(x00=0x80000000, x0C=0x1100, x10=0x11, x14=0x20000, x18=0x41, x1C=0x50004, x20=0x110024, x48=0x91200, x50=0xC1900)
    salida = struct.unpack("<30I", descompilador.de_3211("PCT", crudo))
    assert (salida[5], salida[6], salida[7], salida[8], salida[9], salida[0x4C // 4], salida[0x54 // 4]) == \
        (0, 2, 0x41, 0x50004, 0x110024, 0x91200, 0xC1900)


@pytest.mark.parametrize("et, off", [("FCT", 0x54), ("FCT", 0x58), ("FCT", 0x5C), ("FCT", 0x6C),
                                     *(("PCT", o) for o in range(0x54, 0x70, 4))])
def test_campos_sin_comprobar_dan_no_soportado(et, off):
    with pytest.raises(descompilador.NoSoportado, match=f"datos sin mapa en \\['{off:#x}'\\]"):
        descompilador.de_3211(et, _fct(**{f"x{off:02X}": 1}))


@pytest.mark.parametrize("et, off", [("FCT", 0x60), ("FCT", 0x64), ("FCT", 0x68), ("PCT", 0x50)])
def test_campos_comprobados_pasan(et, off):
    assert struct.unpack_from("<I", descompilador.de_3211(et, _fct(**{f"x{off:02X}": 0x2100})), off + 4)[0] == 0x2100


def test_u16_bajo_de_14_da_no_soportado():
    with pytest.raises(descompilador.NoSoportado, match="u16 bajo de \\+0x14"):
        descompilador.de_3211("FCT", _fct(x14=0x1FFFF))


@pytest.mark.parametrize("et, largo", [("FOR", 32), ("FCT", 120), ("PCT", 108)])
def test_largo_que_no_es_el_de_3211(et, largo):
    with pytest.raises(descompilador.NoSoportado, match=f"de {largo} bytes"):
        descompilador.de_3211(et, bytes(largo))


# --- un .omd de 8.6 de 32 bits recortado a mano
def a_3211(datos: bytes) -> bytes:
    """El mismo módulo con FOR, FCT y PCT en el formato 0x3211 y la versión 0x3211 en la cabecera."""
    omd = contenedor.leer(datos)
    finales = [omd.listas[k + 1][0].entrada if k + 1 < 3 else len(datos) for k in range(3)]
    cuerpo, inicios = bytearray(), []
    for k, lista in enumerate(omd.listas):
        inicio = contenedor.TAM_CABECERA + len(cuerpo)
        inicios.append(inicio)
        contenidos = []
        for j, s in enumerate(lista):
            fin = lista[j + 1].datos if j + 1 < len(lista) else finales[k]
            bloque, rec = datos[s.datos:fin], s.tam_registro
            if s.etiqueta in contenedor.TAMANOS_3211:
                regs = [bloque[i * rec:(i + 1) * rec] for i in range(s.n)]
                bloque, rec = b"".join(_recorta(s.etiqueta, r) for r in regs), contenedor.TAMANOS_3211[s.etiqueta]
            contenidos.append((s, bloque, rec))
        pos = inicio + contenedor.TAM_ENTRADA * len(lista)
        for j, (s, bloque, rec) in enumerate(contenidos):
            sig = contenedor.FIN if j == len(lista) - 1 else inicio + contenedor.TAM_ENTRADA * (j + 1)
            cuerpo += struct.pack("<5I", s.marca, 0, contenedor.TAM_ENTRADA, sig, pos)
            cuerpo += s.etiqueta.encode("ascii").ljust(4, b"\0") + struct.pack("<2I", s.n, rec)
            pos += len(bloque)
        for _, bloque, _ in contenidos:
            cuerpo += bloque
    cabecera = datos[:8] + struct.pack("<I", 0x3211) + datos[12:0x20] + struct.pack("<3I", *inicios) + datos[0x2C:contenedor.TAM_CABECERA]
    return cabecera + bytes(cuerpo)


def _recorta(et: str, r: bytes) -> bytes:
    if et == "FOR":
        assert r[28:] == bytes(4)
        return r[:28]
    w = struct.unpack("<30I", r)
    assert w[5] >> 16 == 0 and w[6] >> 16 == 0 and w[29] == 0
    return struct.pack("<28I", *w[:5], w[5] | w[6] << 16, *w[7:29])


def _sin_mapa(datos: bytes) -> bool:
    """Si algún registro de 8.6 tiene algo donde el formato 0x3211 no se ha comprobado (o sea, NoSoportado al pasarlo)."""
    omd = contenedor.leer(datos)
    for et in ("FCT", "PCT"):
        try:
            s = omd.seccion(et)
        except KeyError:
            continue
        for i in range(s.n):
            w = struct.unpack_from("<30I", datos, s.datos + 120 * i)
            if w[5] or any(w[(o + 4) // 4] for o in descompilador.SIN_COMPROBAR_3211[et]):
                return True
    return False


CARPETAS = ("formularios", "paginas", "controles", "listas", "menus", "tablas", "grupos", "samples")


def _kits():
    carpetas = [KITS / "compilados" / f"{c}-86x86" for c in CARPETAS]
    if not all(c.is_dir() for c in carpetas):
        pytest.skip("sin los kits compilados de 32 bits")
    return sorted(p for c in carpetas for p in c.iterdir() if p.suffix.lower() == ".omd")


def test_los_kits_de_32_bits_pasados_a_3211_dan_el_mismo_fuente():
    iguales = rechazados = 0
    con_geometria_de_ide = False
    for p in _kits():
        datos = p.read_bytes()
        omd = contenedor.leer(datos)
        if not any(s.etiqueta in contenedor.TAMANOS_3211 and s.n for lista in omd.listas for s in lista):
            continue
        avisos: list = []
        try:
            fuente = descompilador.descompilar(datos, avisos=avisos)
        except (descompilador.NoSoportado, contenedor.FormatoError):
            continue
        assert AVISO not in avisos
        nuevos: list = []
        if _sin_mapa(datos):
            with pytest.raises(descompilador.NoSoportado, match="formato 0x3211"):
                descompilador.descompilar(a_3211(datos), avisos=nuevos)
            rechazados += 1
            continue
        assert descompilador.descompilar(a_3211(datos), avisos=nuevos) == fuente, p.name
        assert nuevos == [AVISO, *avisos], p.name
        iguales += 1
        con_geometria_de_ide |= p.stem.lower() == "ejdisableaceleradores"
    assert iguales > 800 and rechazados > 20, (iguales, rechazados)
    assert con_geometria_de_ide  # POSITION 256 39: la geometría de +0x1C/+0x20 no es una declaración


def test_aviso_solo_en_3211():
    p = KITS / "compilados" / "formularios-86x86"
    if not p.is_dir():
        pytest.skip("sin los kits compilados de 32 bits")
    for f in sorted(p.iterdir()):
        if f.suffix.lower() != ".omd" or _sin_mapa(datos := f.read_bytes()):
            continue
        avisos, nuevos = [], []
        try:
            descompilador.descompilar(datos, avisos=avisos)
        except descompilador.NoSoportado:
            continue
        descompilador.descompilar(a_3211(datos), avisos=nuevos)
        assert AVISO not in avisos and nuevos.count(AVISO) == 1
        return
    pytest.fail("ningún formulario de 32 bits se descompila")

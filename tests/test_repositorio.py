"""Catálogo de los repositorios (.dbs) y los objetos `x as tabla.columna`. Usan los proyectos del kit, fuera
del repo: si no están, se saltan."""
import os
import shutil
from pathlib import Path

import pytest

from hubble import descompilador, repositorio

KITS = Path(os.environ.get("HUBBLE_KITS", Path(__file__).resolve().parents[1] / "kits"))
PROYECTOS = KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "projects"
ALMAFAC = PROYECTOS / "ALMAFAC" / "almafac.dbs"
COMPILADOS = KITS / "compilados" / "almafac-86x64"  # ALMAFAC compilado con 8.6 (lab/lenguaje/compila_proyecto.sh)


def _kit(*rutas):
    for r in rutas:
        if not r.exists():
            pytest.skip(f"sin {r}")


def _omd(nombre: str) -> bytes:
    return next(p for p in COMPILADOS.iterdir() if p.name.lower() == nombre).read_bytes()


def test_catalogo_de_almafac():
    _kit(ALMAFAC)
    c = repositorio.Catalogo(ALMAFAC)
    tablas = {x.tabla for x in c.columnas}
    assert tablas == {"albaranes", "articulos", "clientes", "formpagos", "lineas", "proveedores", "provincias", "unidades"}
    articulos = [(x.nombre, x.tipo, x.longitud) for x in c.columnas if x.tabla == "articulos"]
    assert articulos[:5] == [("articulo", repositorio.SMALLINT, 2), ("proveedor", repositorio.INTEGER, 4),
                             ("descripcion", repositorio.CHAR, 15), ("pr_vent", repositorio.MONEY, 12 * 256 + 2),
                             ("pr_cost", repositorio.MONEY, 12 * 256 + 2)]
    assert len(c.columnas) == 59
    pr = next(x for x in c.columnas if x.nombre == "pr_cost")
    assert pr.en_omd() == ("Money", 12, 2)  # como lo deja 8.6 en +0x30


def test_catalogos_con_nombres_cortos_y_en_mayusculas():
    _kit(PROYECTOS / "AGENDA" / "agenda.dbs", PROYECTOS / "STOCKMDI" / "STOCK.DBS")
    assert {x.tabla for x in repositorio.Catalogo(PROYECTOS / "AGENDA" / "agenda.dbs").columnas} == {"agenda"}  # syscolum.dat
    assert "customers" in {x.tabla for x in repositorio.Catalogo(PROYECTOS / "STOCKMDI" / "STOCK.DBS").columnas}  # SYSCOLUMNS.DAT


def test_buscar_prefiere_el_nombre_y_las_tablas_dadas():
    _kit(ALMAFAC)
    c = repositorio.Catalogo(ALMAFAC)
    col, n = c.buscar("Char", 25, -1, "empresa")
    assert (col.tabla, col.nombre, n) == ("clientes", "empresa", 8)  # clientes va antes que proveedores
    col, _ = c.buscar("Char", 25, -1, "empresa", ("proveedores",))
    assert (col.tabla, col.nombre) == ("proveedores", "empresa")
    col, _ = c.buscar("Smallint", 0, -1, "existencias")  # el nombre manda sobre el orden (formpagos va antes)
    assert (col.tabla, col.nombre) == ("articulos", "existencias")
    col, _ = c.buscar("Smallint", 0, -1, "nada")
    assert col.nombre != "nada" and col.en_omd() == ("Smallint", 0, -1)
    assert c.buscar("Char", 99, -1) == (None, 0)


def test_fila_borrada(tmp_path):
    # Una fila que no acaba en \n está borrada: su columna no existe.
    _kit(ALMAFAC)
    dbs = tmp_path / "almafac.dbs"
    shutil.copytree(ALMAFAC, dbs)
    datos = bytearray((dbs / "syscolumns.dat").read_bytes())
    i = datos.index(b"existencias".ljust(18) + (156).to_bytes(4, "big"))
    datos[i + 28] = 0
    (dbs / "syscolumns.dat").write_bytes(bytes(datos))
    nombres = [(x.tabla, x.nombre) for x in repositorio.Catalogo(dbs).columnas]
    assert ("articulos", "existencias") not in nombres and ("articulos", "sobre_maximo") in nombres


def test_encontrar_la_carpeta_dbs():
    _kit(ALMAFAC)
    assert repositorio.encontrar("ALMAFAC", PROYECTOS / "ALMAFAC" / "clientes.OMD") == ALMAFAC.resolve()
    assert repositorio.encontrar("otro", PROYECTOS / "ALMAFAC" / "clientes.OMD") is None


def test_objetos_del_tipo_de_una_columna():
    # El .omd solo guarda el tipo (escala -1 en +0x30); la tabla sale de las que nombra el SQL del módulo
    # (PROVPROV: «from proveedores»), como en el fuente original.
    _kit(ALMAFAC, COMPILADOS)
    avisos = []
    texto = descompilador.descompilar(_omd("provprov.omd"), "almafac", repositorio.Catalogo(ALMAFAC), avisos)
    assert texto.startswith("REPOSITORY almafac\n")
    assert "    proveedor as proveedores.proveedor\n    empresa as proveedores.empresa\nEND\n" in texto
    assert "private CargaProvincia(provincia as provincias.provincia, VAR descripcion as Char," in texto
    assert any("empresa as proveedores.empresa: una de 8 columnas" in a for a in avisos)
    texto = descompilador.descompilar(_omd("provcli.omd"), "almafac", repositorio.Catalogo(ALMAFAC))
    assert "    empresa as clientes.empresa\n" in texto and "proveedores.empresa" not in texto


def test_struct_as_tabla_con_sus_miembros():
    # `custom is Struct as customers`: el .omd solo guarda los miembros (cada uno `x as customers.x`); son, en su
    # orden, las columnas de customers, y sale `Struct as customers` (la vuelta de samples da los mismos bytes).
    stock = KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "samples" / "stock.dbs"
    samples = KITS / "compilados" / "samples-86x64"
    _kit(stock, samples)
    f = next(p for p in samples.iterdir() if p.name.lower() == "cone15.omd")
    texto = descompilador.descompilar(f.read_bytes(), "stock", repositorio.Catalogo(stock))
    assert "\tcustom is Struct as customers\n" in texto


def test_sin_catalogo_no_se_inventa_el_tipo():
    # Antes un Char de columna salía como Char(25), que compila con escala 0: distinto sin avisar.
    _kit(COMPILADOS)
    with pytest.raises(descompilador.NoSoportado, match="hace falta el repositorio"):
        descompilador.descompilar(_omd("provprov.omd"), "almafac")


# --- máscaras del .crf (batería lab/bateria/likevar.py y copias del repositorio con un byte cambiado)
ALMAFAC4 = PROYECTOS / "almafac4" / "almafac.dbs"  # su .crf es de la versión 2
ALMAFAC_32 = KITS / "extraido" / "86x86" / "Cosmos8.6eval" / "projects" / "ALMAFAC" / "almafac.dbs"  # también v2
# en ALMAFAC.CRF (v1): +0x32 de los registros de columna 63 (precio_tipo), 11 (pr_cost), 12 (existencias) y 7
# (articulos.articulo); el +0x1E (coltype) del 11 y del 10 (pr_vent), el +0x14 (hereda) del 11 y el +0xC (nombre) del 10
MASCARA_PRECIO_TIPO, MASCARA_PR_COST, MASCARA_EXISTENCIAS, MASCARA_ARTICULO = 0xA8D0, 0x95B8, 0x9616, 0x9440
COLTYPE_PR_COST, NOMBRE_PR_VENT, HEREDA_PR_COST, COLTYPE_PR_VENT = 0x95A4, 0x9534, 0x959A, 0x9546


def _mascaras(dbs) -> dict:
    return {f"{c.tabla}.{c.nombre}": m for c, m in repositorio.Catalogo(dbs).mascaras.items()}


@pytest.mark.parametrize("dbs", [ALMAFAC, ALMAFAC4, ALMAFAC_32])
def test_mascaras_del_crf(dbs):
    # Las de precio_tipo (4) y fecha_tipo (5), de las que heredan: lo que copia LIKEVAR en el control (0x43, 0x55)
    _kit(dbs)
    m = _mascaras(dbs)
    assert {k for k, v in m.items() if v} == {"clientes.total_factura", "articulos.pr_vent", "articulos.pr_cost",
                                              "lineas.precio", "albaranes.fecha_albaran", "albaranes.fecha_envio",
                                              "albaranes.fecha_pago", "articulos.fec_ult_ent", "articulos.fec_ult_sal"}
    assert m["articulos.pr_cost"] == 4 and m["albaranes.fecha_pago"] == 5 and m["articulos.existencias"] == 0
    assert m["lineas.articulo"] == 0  # hereda de articulos.articulo
    assert m["clientes.direccion"] is None  # miembro de un tipo compuesto (dirpost): el .crf no la tiene suelta


def test_herencia_de_dos_saltos_no_se_sabe():
    _kit(ALMAFAC)  # proveedores.provincia → tipos_fijos.provincia → provincias.provincia: no visto compilado
    assert _mascaras(ALMAFAC)["proveedores.provincia"] is None


def _copia(tmp_path, cambios: dict[int, int]):
    tmp_path = tmp_path / f"copia{len(list(tmp_path.iterdir()))}"
    tmp_path.mkdir()
    dbs = tmp_path / "almafac.dbs"
    shutil.copytree(ALMAFAC, dbs)
    datos = bytearray((ALMAFAC.parent / "ALMAFAC.CRF").read_bytes())
    for o, v in cambios.items():
        datos[o] = v
    (tmp_path / "ALMAFAC.CRF").write_bytes(bytes(datos))
    return dbs


def test_mascara_con_un_byte_cambiado(tmp_path):
    # Lo mismo que dio el compilador con estas copias del repositorio (likevar.py)
    _kit(ALMAFAC)
    m = _mascaras(_copia(tmp_path, {MASCARA_PRECIO_TIPO: 3, MASCARA_EXISTENCIAS: 3, MASCARA_ARTICULO: 6}))
    assert m["articulos.pr_cost"] == 3 and m["clientes.total_factura"] == 3  # la del tipo del que heredan
    assert m["articulos.existencias"] == 3  # la suya: no hereda
    assert m["lineas.articulo"] == 6 and m["articulos.articulo"] == 6  # de la columna de otra tabla


def test_la_mascara_propia_no_cuenta_si_hereda(tmp_path):
    _kit(ALMAFAC)
    assert _mascaras(_copia(tmp_path, {MASCARA_PR_COST: 3}))["articulos.pr_cost"] == 4  # el compilador: 4


def test_crf_dudoso_no_da_mascara(tmp_path):
    _kit(ALMAFAC)
    assert _mascaras(_copia(tmp_path, {COLTYPE_PR_COST: 5}))["articulos.pr_cost"] is None  # otro tipo que el .dbs
    m = _mascaras(_copia(tmp_path, {NOMBRE_PR_VENT: 0x10}))  # pr_vent con el nombre de pr_cost: dos pr_cost
    assert m["articulos.pr_cost"] is None and m["articulos.pr_vent"] is None


def test_herencia_de_otra_clase_no_se_sabe(tmp_path):
    _kit(ALMAFAC)  # +0x14 = 2: no visto
    assert _mascaras(_copia(tmp_path, {HEREDA_PR_COST: 2}))["articulos.pr_cost"] is None


def test_crf_cortado_a_media_tabla(tmp_path):
    _kit(ALMAFAC)
    datos = (ALMAFAC.parent / "ALMAFAC.CRF").read_bytes()
    dbs = _copia(tmp_path, {})
    (dbs.parent / "ALMAFAC.CRF").write_bytes(datos[:0xA000])  # dentro de la tabla de columnas
    assert repositorio.Catalogo(dbs).mascaras is None


def test_sin_crf_o_de_otra_version(tmp_path):
    _kit(ALMAFAC)
    dbs = _copia(tmp_path, {8: 3})  # versión 3: no se sabe leer
    assert repositorio.Catalogo(dbs).mascaras is None
    (dbs.parent / "ALMAFAC.CRF").unlink()
    c = repositorio.Catalogo(dbs)
    assert c.mascaras is None and c.mascara(c.columnas[0]) is None


def test_crf_que_no_encaja(tmp_path):
    _kit(ALMAFAC)
    datos = (ALMAFAC.parent / "ALMAFAC.CRF").read_bytes()
    dbs = _copia(tmp_path, {})
    (dbs.parent / "ALMAFAC.CRF").write_bytes(datos[:0xB4BC])  # sin la tabla de detrás de la de columnas
    assert repositorio.Catalogo(dbs).mascaras is None


def test_buscar_con_mascara():
    _kit(ALMAFAC)
    c = repositorio.Catalogo(ALMAFAC)
    col, n = c.buscar("Money", 12, 2, "pr_cost", mascara=4)
    assert (col.tabla, col.nombre, n) == ("articulos", "pr_cost", 4)
    assert c.buscar("Money", 12, 2, "pr_cost", mascara=3) == (None, 0)
    assert c.buscar("Money", 12, 2, "pr_cost", mascara=0) == (None, 0)
    assert c.buscar("Date", 0, -1, mascara=0) == (None, 0)  # todas las fechas de ALMAFAC tienen la 5
    # Char(25): 6 con la máscara 0 sabida; sin ser estricta, también las 2 que no se sabe (clientes.apellidos y
    # clientes.direccion, de dirpost); con otra máscara, solo esas 2
    assert c.buscar("Char", 25, -1, mascara=0)[1] == 6
    col, n = c.buscar("Char", 25, -1, "direccion", mascara=0, estricta=False)
    assert (col.tabla, col.nombre, n) == ("clientes", "direccion", 8)
    assert c.buscar("Char", 25, -1, mascara=4, estricta=False)[1] == 2


def test_money_solo_entre_las_que_se_sabe(tmp_path):
    # Un Money de columna se escribe solo con una columna cuya máscara se sabe: pr_vent con otro coltype en el .crf
    # (no se sabe la suya) deja 3 candidatas de 4
    _kit(ALMAFAC)
    f = PROYECTOS / "ALMAFAC" / "LPROART.OMD"
    _kit(f)
    avisos = []
    descompilador.descompilar(f.read_bytes(), "almafac", repositorio.Catalogo(_copia(tmp_path, {COLTYPE_PR_VENT: 5})), avisos)
    assert any(a.startswith("pr_cost as articulos.pr_cost: una de 3 columnas") for a in avisos)

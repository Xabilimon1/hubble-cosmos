"""Línea de órdenes: `hubble <orden> ...`."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from hubble import cabeceras, cadenas, contenedor, descompilador, empaquetado, entropia, inventario, repositorio


def _ficheros(rutas: list[str]) -> list[Path]:
    salida: list[Path] = []
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            salida.extend(sorted(x for x in p.rglob("*") if x.is_file()))
        else:
            salida.append(p)
    return salida


def _json(obj) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


def orden_inventario(a: argparse.Namespace) -> None:
    fs = inventario.recorrer(Path(a.carpeta))
    grupos = inventario.agrupar(fs)
    if a.json:
        _json({"grupos": [asdict(g) | {"firma_comun": g.firma_comun.hex(" ")} for g in grupos],
               "ficheros": [asdict(f) | {"ruta": str(f.ruta), "firma": f.firma_hex} for f in fs]})
        return
    print(f"{len(fs)} ficheros en {a.carpeta}\n")
    print(f"{'extensión':<16}{'nº':>6}{'bytes':>14}  {'más antiguo':<17}{'más reciente':<17}firma común")
    for g in grupos:
        print(f"{g.extension:<16}{g.ficheros:>6}{g.bytes_totales:>14}  {g.mas_antiguo:%Y-%m-%d %H:%M}  "
              f"{g.mas_reciente:%Y-%m-%d %H:%M}  {g.firma_comun.hex(' ') or '-'}")


def orden_cadenas(a: argparse.Namespace) -> None:
    for ruta in _ficheros(a.ficheros):
        datos = ruta.read_bytes()
        cs = cadenas.extraer(datos, a.minimo, a.codificacion)
        if a.utf16:
            cs += cadenas.extraer_utf16(datos, a.minimo)
        if a.sql:
            cs = [c for c in cs if cadenas.parece_sql(c.texto)]
        cs.sort(key=lambda c: c.desplazamiento)
        if a.json:
            _json({"fichero": str(ruta), "cadenas": [asdict(c) for c in cs]})
            continue
        for c in cs:
            print(f"{ruta}\t0x{c.desplazamiento:08x}\t{c.texto}")


def orden_cabeceras(a: argparse.Namespace) -> None:
    rutas = _ficheros(a.ficheros)
    datos = [r.read_bytes() for r in rutas]
    bytes_ = cabeceras.comparar([d[: a.n] for d in datos], a.n)
    cands = cabeceras.candidatos(datos, a.n) if len(datos) >= 2 else []
    if a.json:
        _json({"ficheros": [str(r) for r in rutas], "bytes": [asdict(b) for b in bytes_], "candidatos": [asdict(c) for c in cands]})
        return
    print(f"{len(rutas)} ficheros. «==» = igual en todos.\n")
    for b in bytes_:
        vals = " ".join("--" if v is None else f"{v:02x}" for v in b.valores[:12])
        print(f"0x{b.desplazamiento:02x}  {'==' if b.constante else '  '}  {vals}")
    if cands:
        print("\nEnteros relacionados con el tamaño de cada fichero:")
        for c in cands:
            orden = "LE" if c.orden == "<" else "BE"
            print(f"  0x{c.desplazamiento:02x} u{c.ancho * 8} {orden}: {c.relacion}  {list(c.valores)[:6]}")


def orden_entropia(a: argparse.Namespace) -> None:
    for ruta in _ficheros(a.ficheros):
        bloques = entropia.por_bloques(ruta.read_bytes(), a.bloque)
        alta = entropia.proporcion_alta(bloques)
        if a.json:
            _json({"fichero": str(ruta), "proporcion_alta": alta, "bloques": [asdict(b) for b in bloques]})
            continue
        media = sum(b.entropia * b.tamano for b in bloques) / max(1, sum(b.tamano for b in bloques))
        aviso = "  <- probablemente comprimido o cifrado" if alta > 0.8 else ""
        print(f"{ruta}: media {media:.2f} bits/byte, {alta:.0%} en bloques ≥ {entropia.UMBRAL_ALTA}{aviso}")


def _secciones(ruta: Path) -> dict:
    datos = ruta.read_bytes()
    try:
        omd = contenedor.leer(datos)
        regiones = contenedor.regiones(omd, len(datos))
    except contenedor.FormatoError as e:
        return {"fichero": str(ruta), "error": str(e)}
    secciones = {
        s.etiqueta: {"lista": contenedor.NOMBRES_LISTAS[k], "datos": s.datos, "n": s.n,
                     "tam_registro": s.tam_registro, "marca": s.marca}
        for k, lista in enumerate(omd.listas)
        for s in lista
    }
    salida = {"fichero": str(ruta), "tamano": len(datos), "bits": None,
              "regiones": [asdict(r) for r in regiones], "secciones": secciones}
    try:
        salida["bits"] = omd.bits
    except contenedor.FormatoError as e:
        salida["aviso"] = f"arquitectura desconocida: {e}"
    return salida


def orden_secciones(a: argparse.Namespace) -> None:
    resultados = [_secciones(r) for r in _ficheros(a.ficheros)]
    if a.json:
        _json(resultados)
        return
    for res in resultados:
        if "error" in res:
            print(f"{res['fichero']}: no es un .omd legible: {res['error']}")
            continue
        bits = f"{res['bits']} bits" if res["bits"] else res["aviso"]
        print(f"{res['fichero']} ({res['tamano']} bytes, {bits})")
        for r in res["regiones"]:
            sec = res["secciones"].get(r["nombre"].partition("/")[2])
            detalle = f"{sec['n']} × {sec['tam_registro']}" if sec else ""
            marca = "  variable (sin descodificar)" if r["variable"] else ""
            print(f"  0x{r['inicio']:08x}-0x{r['fin']:08x} {r['fin'] - r['inicio']:>9}  {r['nombre']:<12}{detalle}{marca}")


def _textos(ruta: Path, seccion: str, solo_sql: bool) -> dict:
    datos = ruta.read_bytes()
    try:
        omd = contenedor.leer(datos)
        emp = empaquetado.de_omd(datos, omd, seccion)
    except contenedor.FormatoError as e:
        return {"fichero": str(ruta), "error": str(e)}
    textos = []
    for k, r in enumerate(emp.registros):
        t = {"indice": k, "desplazamiento": r.desplazamiento, "binario": r.binario, "texto": None if r.binario else r.texto()}
        if r.binario:
            t |= {"tipo": r.tipo, "longitud": r.longitud}
        textos.append(t)
    if solo_sql:
        textos = [t for t in textos if t["texto"] and cadenas.parece_sql(t["texto"])]
    return {"fichero": str(ruta), "seccion": seccion, "textos": textos}


def _catalogo(a: argparse.Namespace, ruta: Path, vistos: dict):
    """El catálogo del repositorio: el de --dbs, o la carpeta <repositorio>.dbs junto al módulo o encima."""
    carpeta = Path(a.dbs) if a.dbs else repositorio.encontrar(a.repositorio, ruta) if a.repositorio else None
    if carpeta is None:
        return None
    if carpeta not in vistos:
        vistos[carpeta] = repositorio.Catalogo(carpeta)
    return vistos[carpeta]


def orden_descompila(a: argparse.Namespace) -> None:
    fallos = 0
    catalogos: dict = {}
    for ruta in _ficheros(a.ficheros):
        avisos: list[str] = []
        try:
            fuente = descompilador.descompilar(ruta.read_bytes(), a.repositorio, _catalogo(a, ruta, catalogos), avisos)
        except (descompilador.NoSoportado, contenedor.FormatoError) as e:
            print(f"{ruta}: no se puede descompilar: {e}", file=sys.stderr)
            fallos += 1
            continue
        for aviso in avisos:
            print(f"{ruta}: aviso: {aviso}", file=sys.stderr)
        if a.o:
            salida = Path(a.o)
            salida.mkdir(parents=True, exist_ok=True)
            (salida / f"{ruta.stem}.SMD").write_bytes(fuente.replace("\n", "\r\n").encode("cp1252"))
        else:
            sys.stdout.write(fuente)
    if fallos:
        sys.exit(1)


def orden_textos(a: argparse.Namespace) -> None:
    resultados = [_textos(r, a.seccion, a.sql) for r in _ficheros(a.ficheros)]
    if a.json:
        _json(resultados)
        return
    for res in resultados:
        if "error" in res:
            print(f"{res['fichero']}: no es un .omd legible: {res['error']}")
            continue
        for t in res["textos"]:
            if t["binario"]:
                texto = f"[binario: tipo {t['tipo']}, {t['longitud']} bytes]"
            else:
                texto = t["texto"].replace("\r", "\\r").replace("\n", "\\n")
            print(f"{res['fichero']}\t{t['indice']}\t0x{t['desplazamiento']:08x}\t{texto}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="hubble", description="Análisis de aplicaciones MultiBase Cosmos")
    sub = p.add_subparsers(dest="orden", required=True)

    s = sub.add_parser("inventario", help="ficheros de una instalación agrupados por extensión")
    s.add_argument("carpeta")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=orden_inventario)

    s = sub.add_parser("cadenas", help="texto incrustado (SQL, tablas, mensajes)")
    s.add_argument("ficheros", nargs="+")
    s.add_argument("--minimo", type=int, default=4)
    s.add_argument("--codificacion", choices=cadenas.CODIFICACIONES, default="cp1252")
    s.add_argument("--utf16", action="store_true", help="buscar también UTF-16LE")
    s.add_argument("--sql", action="store_true", help="solo las que parecen SQL")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=orden_cadenas)

    s = sub.add_parser("cabeceras", help="bytes fijos y campos de tamaño/desplazamiento entre ficheros")
    s.add_argument("ficheros", nargs="+")
    s.add_argument("-n", type=int, default=64, help="bytes de cabecera a comparar")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=orden_cabeceras)

    s = sub.add_parser("entropia", help="entropía por bloques (¿comprimido o cifrado?)")
    s.add_argument("ficheros", nargs="+")
    s.add_argument("--bloque", type=int, default=256)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=orden_entropia)

    s = sub.add_parser("secciones", help="cabecera y secciones de un .omd, con lo que ocupa cada una")
    s.add_argument("ficheros", nargs="+")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=orden_secciones)

    s = sub.add_parser("textos", help="cadenas (STR), identificadores (IDE) o SVL de un .omd, en orden")
    s.add_argument("ficheros", nargs="+")
    s.add_argument("--seccion", choices=("STR", "IDE", "SVL"), default="STR")
    s.add_argument("--sql", action="store_true", help="solo las que parecen SQL")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=orden_textos)

    s = sub.add_parser("descompila", help="fuente COOL (.SMD) de un .omd (código y formularios; 32 y 64 bits)")
    s.add_argument("ficheros", nargs="+")
    s.add_argument("-o", metavar="DIR", help="escribir cada uno como DIR/<nombre>.SMD (cp1252, CRLF)")
    s.add_argument("--repositorio", metavar="NOMBRE", help="REPOSITORY de los módulos con tablas (el .omd no lo guarda)")
    s.add_argument("--dbs", metavar="DIR", help="carpeta .dbs del repositorio (por defecto, <NOMBRE>.dbs junto al "
                   "módulo o encima): de ella salen las columnas de los objetos `x as tabla.columna`")
    s.set_defaults(func=orden_descompila)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()

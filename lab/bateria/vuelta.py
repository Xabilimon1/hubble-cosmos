"""Vuelta completa: descompilar → recompilar en el laboratorio → comparar byte a byte.

Paso 1 (en el Mac): `vuelta.py descompila <dir .omd> <dir .SMD originales> <salida>`
    Descompila cada .omd y escribe el .SMD con el nombre del original (cp1252, CRLF).
    Los que usan algo que aún no se sabe leer van a <salida>/no_soportados.tsv.
Paso 2 (en x-server): compilar <salida> con compila_lote.sh **en la misma ruta de Windows**
    que el original (la ruta del fuente queda dentro del .omd).
Paso 2b (en el Mac): `vuelta.py caidos <informe .tsv> <dir descompilados> <dir .SMD originales> <cuentan> <salida>`
    Los descompilados que no compilaron se reponen con su fuente original para repetir la tanda
    (el compilador acumula los CMD/ICO/FON de la tanda; sin el caído, los demás salen cortos).
Paso 3 (en el Mac): `vuelta.py compara <dir .omd originales> <dir .omd recompilados> [nombres que cuentan] [caídos]`
    Dice cuáles salen idénticos y, de los demás, la primera sección que difiere. Los caídos
    siguen contando como «el descompilado no compila».
"""
import shutil
import sys
from pathlib import Path

from hubble import contenedor, empaquetado, repositorio
from hubble.descompilador import NoSoportado, descompilar


def _omds(d: Path) -> dict[str, Path]:
    return {p.stem.lower(): p for p in d.iterdir() if p.suffix.lower() == ".omd"}


def descompila(omds: Path, fuentes: Path, salida: Path) -> None:
    salida.mkdir(parents=True, exist_ok=True)
    nombres = {p.stem.lower(): p.name for p in fuentes.iterdir() if p.suffix.lower() == ".smd"}
    fallos, hechos, catalogos = [], 0, {}
    for stem, f in sorted(_omds(omds).items()):
        if stem not in nombres:
            continue
        # El .omd no guarda el REPOSITORY: se toma del fuente original (solo es contexto de
        # compilación, como el .prj).
        import re
        rep = re.search(r"^\s*REPOSITORY\s+(\w+)", (fuentes / nombres[stem]).read_text("cp1252"), re.I | re.M)
        # Su catálogo (<repositorio>.dbs junto a los fuentes), para los objetos `x as tabla.columna`.
        dbs = repositorio.encontrar(rep.group(1), fuentes / nombres[stem]) if rep else None
        if dbs and dbs not in catalogos:
            catalogos[dbs] = repositorio.Catalogo(dbs)
        try:
            texto = descompilar(f.read_bytes(), rep.group(1) if rep else None, catalogos.get(dbs))
        except NoSoportado as e:
            fallos.append(f"{stem}\t{e}")
            continue
        (salida / nombres[stem]).write_bytes(texto.replace("\n", "\r\n").encode("cp1252"))
        hechos += 1
    (salida / "no_soportados.tsv").write_text("".join(x + "\n" for x in fallos))
    print(f"{hechos} descompilados, {len(fallos)} no soportados")


def caidos(informe: Path, descompilados: Path, fuentes: Path, cuentan: Path, salida: Path) -> list[str]:
    """Los descompilados que no compilaron (`fallo` en el informe de compila_lote.sh, y solo los que cuentan) se
    reponen con su fuente original para repetir la tanda: el compilador acumula los CMD (y ICO, FON) de la tanda de
    `-smd`, y un módulo caído le quita a los demás lo que aporta (ALMAFAC3: `CMD: 17 → 16 registros` en 12 módulos
    por AUXILIAR e INICIO). El descompilado queda en <descompilados>/caidos/ y los nombres, en `salida`, para que
    `compara` los siga contando como «no compila»."""
    que_cuentan = set(cuentan.read_text().lower().split())
    nombres = []
    for linea in informe.read_text().splitlines():
        campos = linea.split("\t")
        if len(campos) >= 2 and campos[1] == "fallo" and campos[0].lower() in que_cuentan:
            nombres.append(campos[0].lower())
    originales = {p.stem.lower(): p for p in fuentes.iterdir() if p.suffix.lower() == ".smd"}
    hechos = {p.stem.lower(): p for p in descompilados.iterdir() if p.suffix.lower() == ".smd"}
    aparte = descompilados / "caidos"
    for n in nombres:
        aparte.mkdir(exist_ok=True)
        hechos[n].replace(aparte / hechos[n].name)
        shutil.copy(originales[n], hechos[n])
    salida.write_text("".join(n + "\n" for n in nombres))
    print(" ".join(nombres))
    return nombres


def _primera_diferencia(a: bytes, b: bytes) -> str:
    oa, ob = contenedor.leer(a), contenedor.leer(b)
    sa = {s.etiqueta: s for lista in oa.listas for s in lista}
    sb = {s.etiqueta: s for lista in ob.listas for s in lista}
    for et in sa:
        x, y = sa[et], sb[et]
        if x.n != y.n:
            return f"{et}: {x.n} → {y.n} registros"
    for et in sa:
        x, y = sa[et], sb[et]
        if et in ("IDE", "STR", "SVL"):
            continue
        if a[x.datos: x.datos + x.n * x.tam_registro] != b[y.datos: y.datos + y.n * y.tam_registro]:
            return f"{et}: mismos registros, otros bytes"
    return "solo IDE/STR/SVL o cabecera"


def _puntero_de_clase(w0: bytes, w40: bytes) -> bool:
    """`B is A` sin miembros, si A los tiene: en +0x40 de su CLA (+0x24 en 32 bits) un puntero de memoria en vez de la
    referencia a sus OBJ (sección 0x08)."""
    v = int.from_bytes(w40, "little")
    return w0[0] & 0x7F == 0x20 and v > 0x10000 and not (v & 0xFF == 0 and (v >> 8) & 0xFF == 0x08)


def _sin_punteros(datos: bytes) -> bytes:
    """Los punteros de memoria del compilador (+0x18 de los nodos de variable, de método, de control y de tabla)
    dependen de cómo quedó su memoria, no del programa: se ponen a cero para comparar."""
    omd = contenedor.leer(datos)
    ref = next(s for lista in omd.listas for s in lista if s.etiqueta == "REF")
    salida = bytearray(datos)
    if ref.tam_registro == 16:  # 32 bits: el mismo puntero, de 4 bytes, en +0x0C
        for k in range(ref.n):
            p = ref.datos + 16 * k
            control = salida[p] == 0x00 and salida[p + 1] in (0x31, 0x21)  # del formulario o `objeto.control`
            tabla = salida[p] == 0x30 and salida[p + 1] == 0x30
            if (salida[p] in (0x10, 0x20) or control or tabla) and int.from_bytes(salida[p + 0x0C: p + 0x10], "little") > 0x10000:
                salida[p + 0x0C: p + 0x10] = bytes(4)
            ancho = {0x60: 2, 0x70: 4, 0xA0: 4, 0xC0: 0}.get(salida[p])  # la basura de los literales, igual que en 64
            if ancho is not None and ancho < 4:
                basura = salida[p + 0x0C + ancho: p + 0x10]
                if basura != b"\xcc" * len(basura) and any(basura):
                    salida[p + 0x0C + ancho: p + 0x10] = b"\x01" * len(basura)
        # los de GRID (+0xA8 → +0x64) y de las clases de tabla (+0x28 → +0x14), como en 64 bits
        fct = next(s for lista in omd.listas for s in lista if s.etiqueta == "FCT")
        for k in range(fct.n):
            p = fct.datos + 120 * k
            if int.from_bytes(salida[p + 0x10: p + 0x12], "little") == 0x15:
                salida[p + 0x64: p + 0x68] = bytes(4)
        cla = next(s for lista in omd.listas for s in lista if s.etiqueta == "CLA")
        for k in range(cla.n):
            p = cla.datos + 48 * k
            if int.from_bytes(salida[p:p + 4], "little") == 0x8300002D:
                salida[p + 0x14: p + 0x18] = bytes(4)
            if _puntero_de_clase(salida[p:p + 4], salida[p + 0x24:p + 0x28]):
                salida[p + 0x24: p + 0x28] = bytes(4)
    if ref.tam_registro == 32:
        for k in range(ref.n):
            p = ref.datos + 32 * k
            control = salida[p] == 0x00 and salida[p + 1] in (0x31, 0x21)  # del formulario o `objeto.control`
            tabla = salida[p] == 0x30 and salida[p + 1] == 0x30  # `tabla.Metodo()`: +0x10 → su FTA
            if (salida[p] in (0x10, 0x20) or control or tabla) and int.from_bytes(salida[p + 0x18: p + 0x20], "little") > 0x10000:
                salida[p + 0x18: p + 0x20] = bytes(8)
            # Literales: la memoria sin limpiar tras el valor (la de los argumentos por defecto)
            # cuenta solo por si está o no, no por lo que valga.
            ancho = {0x60: 2, 0x70: 4, 0xA0: 4, 0xC0: 0}.get(salida[p])
            if ancho is not None:
                basura = salida[p + 0x18 + ancho: p + 0x20]
                if basura != b"\xcc" * len(basura) and any(basura):
                    salida[p + 0x18 + ancho: p + 0x20] = b"\x01" * len(basura)
        # Un GRID lleva en +0xA8 un puntero de memoria del compilador.
        fct = next(s for lista in omd.listas for s in lista if s.etiqueta == "FCT")
        if fct.tam_registro == 208:
            for k in range(fct.n):
                p = fct.datos + 208 * k
                if int.from_bytes(salida[p + 0x20: p + 0x22], "little") == 0x15:
                    salida[p + 0xA8: p + 0xB0] = bytes(8)
        # Las clases de tabla llevan en +0x28 un puntero de memoria del compilador.
        cla = next(s for lista in omd.listas for s in lista if s.etiqueta == "CLA")
        if cla.tam_registro == 88:
            for k in range(cla.n):
                p = cla.datos + 88 * k
                if int.from_bytes(salida[p:p + 4], "little") == 0x8300002D:
                    salida[p + 0x28: p + 0x30] = bytes(8)
                if _puntero_de_clase(salida[p:p + 4], salida[p + 0x40:p + 0x44]):
                    salida[p + 0x40: p + 0x48] = bytes(8)
    # Los binarios de SVL (columnas de las listas) también llevan punteros (de 8 bytes; de 4 en 32 bits):
    # valores entre 0x01000000 y 0x7FFFFFFF (por encima de cualquier color, 0x00BBGGRR).
    w = 4 if ref.tam_registro == 16 else 8
    for r in empaquetado.de_omd(datos, omd, "SVL").registros:
        if not r.binario:
            continue
        for o in range(w, len(r.datos) - w + 1, w):
            v = int.from_bytes(r.datos[o:o + w], "little")
            if 0x01000000 <= v <= 0x7FFFFFFF:
                salida[r.desplazamiento + o: r.desplazamiento + o + w] = bytes(w)
    return bytes(salida)


def compara(originales: Path, nuevos: Path, solo: Path | None = None, caidos: Path | None = None) -> int:
    """`solo`: fichero con los nombres que cuentan (los descompilados; los demás son dependencias, el fuente
    original compilado en los dos lados). `caidos`: los que no compilaron y se repitieron con su fuente original
    (orden `caidos`): su .omd es el del original y no cuenta, siguen siendo «el descompilado no compila»."""
    o, n = _omds(originales), _omds(nuevos)
    iguales, casi, distintos = 0, 0, []
    if caidos and caidos.exists():
        repuestos = set(caidos.read_text().lower().split())
        n = {s: p for s, p in n.items() if s not in repuestos}
    if solo:
        cuentan = set(solo.read_text().lower().split())
        n = {s: p for s, p in n.items() if s in cuentan}
        # el original compila y el descompilado no: también es un fallo (samples URLText, CURSOR mal colocado)
        distintos += [(s, "el descompilado no compila") for s in sorted(cuentan & set(o) - set(n))]
    for stem in sorted(n):
        a, b = o[stem].read_bytes(), n[stem].read_bytes()
        if a == b:
            iguales += 1
        elif _sin_punteros(a) == _sin_punteros(b):
            casi += 1
        else:
            distintos.append((stem, _primera_diferencia(a, b)))
    for stem, motivo in distintos:
        print(f"DISTINTO {stem}: {motivo}")
    print(f"{iguales} de {len(n)} idénticos byte a byte; {casi} más idénticos salvo punteros de memoria; {len(distintos)} distintos")
    return 0 if not distintos else 1


if __name__ == "__main__":
    orden, *args = sys.argv[1:]
    if orden == "descompila":
        descompila(*map(Path, args))
    elif orden == "caidos":
        caidos(*map(Path, args))
    elif orden == "compara":
        sys.exit(compara(*map(Path, args)))
    else:
        sys.exit(__doc__)

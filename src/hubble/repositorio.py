"""Catálogo de un repositorio (la carpeta `.dbs` de la base de datos): qué tablas y columnas hay y de qué tipo.

El `.omd` no guarda la tabla de un objeto declarado `x as tabla.columna`, solo el tipo ya resuelto: para
escribirlo hace falta una columna del mismo tipo, y sale de aquí.

Formato (el de los catálogos de Informix, del que viene MultiBase): `systables.dat` y `syscolumns.dat` son
filas de longitud fija, enteros en big-endian, cada una acabada en `\\n` (las que no, están borradas).
`syscolumns` se describe a sí misma: colname char(18), tabid integer, colno smallint, coltype smallint,
collength smallint. `systables` empieza por tabname char(18), owner char(8), dirpath char(64), tabid integer;
su longitud de fila sale de sus propias columnas en `syscolumns` (tabid 1).
"""
import struct
from dataclasses import dataclass
from pathlib import Path

# coltype (sin el 0x100 de NOT NULL) → bytes que ocupa en la fila (None: depende de collength)
CHAR, SMALLINT, INTEGER, FLOAT, SMALLFLOAT, DECIMAL, SERIAL, DATE, MONEY = range(9)
_TAM = {SMALLINT: 2, INTEGER: 4, FLOAT: 8, SMALLFLOAT: 4, SERIAL: 4, DATE: 4}
_FILA_SYSCOLUMNS = 29
PRIMERA_TABLA = 100  # tabid < 100: las del catálogo (systables, syscolumns…)


@dataclass(frozen=True)
class Columna:
    tabla: str
    nombre: str
    tipo: int  # coltype sin NOT NULL
    longitud: int  # collength (DECIMAL y MONEY: precisión * 256 + escala)
    no_nula: bool = False  # NOT NULL (0x100 de coltype)

    def en_omd(self) -> tuple[str, int, int] | None:
        """Clase y +0x30 (longitud, escala) que deja en el .omd un objeto `x as tabla.columna`
        (comprobado con 8.6 en ALMAFAC: CHAR, SMALLINT, INTEGER, SERIAL, DATE, MONEY); None si no se sabe."""
        if self.tipo == CHAR:
            return "Char", self.longitud, -1
        if self.tipo == SMALLINT:
            return "Smallint", 0, -1
        if self.tipo in (INTEGER, SERIAL):
            return "Integer", 0, -1
        if self.tipo == DATE:
            return "Date", 0, -1
        if self.tipo == MONEY:
            return "Money", self.longitud >> 8, self.longitud & 0xFF
        return None


def _tam(tipo: int, longitud: int) -> int:
    if tipo == CHAR:
        return longitud
    if tipo in (DECIMAL, MONEY):
        return (longitud >> 8) // 2 + 1
    return _TAM[tipo]


def _fichero(carpeta: Path, nombre: str) -> bytes:
    """Sin distinguir mayúsculas (SYSCOLUMNS.DAT) y también con el nombre corto de 8 letras (syscolum.dat)."""
    base, ext = nombre.split(".")
    for p in carpeta.iterdir():
        if p.name.lower() in (nombre, f"{base[:8]}.{ext}"):
            return p.read_bytes()
    raise FileNotFoundError(f"{carpeta}: sin {nombre}")


def _filas(datos: bytes, tam: int):
    for i in range(0, len(datos) - tam + 1, tam):
        if datos[i + tam - 1] == 0x0A:
            yield datos[i:i + tam]


CRF_MAGIA, CRF_CADENA = b"CRMMAGIC", b"\x00\x10\x00\x80"


def _valores_crf(carpeta: Path) -> set[str]:
    """Las cadenas de valores (`boolean values`/`enumerated`: «a|b|…») del `<nombre>.crf` junto a la carpeta `.dbs`.
    [hipótesis] Del formato solo se sabe que cada cadena va tras 00 10 00 80 y acaba en 0; las de valores llevan «|»
    (también las etiquetas, «Varon|Mujer»: no estorban). Sin .crf, ninguna."""
    crf = crf_de(carpeta)
    if crf is None:
        return set()
    datos = crf.read_bytes()
    if not datos.startswith(CRF_MAGIA):
        return set()
    salida, i = set(), datos.find(CRF_CADENA)
    while i >= 0:
        fin = datos.find(b"\0", i + 4)
        texto = datos[i + 4:fin].decode("cp1252", "replace") if fin > i + 4 else ""
        if "|" in texto:
            salida.add(texto)
        i = datos.find(CRF_CADENA, i + 4)
    return salida


# Tablas de registros del .crf, en este orden desde 0x40: nombres (de columna), textos (de tabla, etiquetas…), tablas y
# columnas. Cabecera de 0x18 bytes: u32 1, u32 capacidad, u32 cuántos…; luego `capacidad` registros. El tamaño en disco
# de cada registro, según la versión (u16 de +8): en la 2 la cabecera trae otro (el de memoria) y no vale. Medido en los
# 24 .crf de los kits (las 6 tablas encajan una tras otra), y el registro de columna leído con bytes compilados.
_CRF_TAMANOS = {1: (24, 260, 50, 94), 2: (38, 260, 50, 94)}
_CRF_EN_USO = b"\x00\x10\x00\x80"


def _tabla_crf(datos: bytes, o: int, tam: int) -> tuple[list[bytes | None], int]:
    """Los registros de la tabla que empieza en o (None los libres) y dónde empieza la siguiente."""
    if datos[o:o + 4] != b"\x01\x00\x00\x00":
        raise ValueError(f"sin cabecera de tabla en {o:#x}")
    cap, n = struct.unpack_from("<II", datos, o + 4)
    if n > cap or o + 0x18 + cap * tam > len(datos):
        raise ValueError(f"tabla en {o:#x} de {cap} registros que no cabe")
    regs = [datos[o + 0x18 + i * tam:o + 0x18 + (i + 1) * tam] for i in range(cap)]
    return [r if r[3] & 0x80 else None for r in regs], o + 0x18 + cap * tam


def base_del_crf(crf: Path) -> str | None:
    """El nombre de la base de datos (la carpeta `<nombre>.dbs`) que describe un `.crf`: el registro de la tabla de
    nombres (la primera, desde 0x40) que dice el u32 de +0x14 de la cabecera; el registro 0 es el del repositorio. En
    los 22 `.crf` de los kits con su `.dbs` al lado, siempre el nombre de esa carpeta: ALMAFAC.CRF → almafac,
    stock.crf → STOCK, agenda.crf → AGENDA (6) e INDODIC.CRF → indonesi (INDONESI.DBS; su UpkeepDict dice
    `REPOSITORY indodic`). None si no se sabe leer."""
    try:
        datos = crf.read_bytes()
        if not datos.startswith(CRF_MAGIA):
            return None
        version = struct.unpack_from("<H", datos, 8)[0]
        if version not in _CRF_TAMANOS:
            return None
        nombres, _ = _tabla_crf(datos, 0x40, _CRF_TAMANOS[version][0])
        i = struct.unpack_from("<I", datos, 0x14)[0]
    except (OSError, ValueError, struct.error):
        return None
    return _texto(nombres[i]) if i < len(nombres) else None


def crf_de(carpeta: Path) -> Path | None:
    """El `.crf` de una carpeta `.dbs`, a su lado: el del mismo nombre o, si no lo hay, el único cuya base de datos
    (`base_del_crf`) es esa carpeta (INDODIC.CRF de INDONESI.DBS)."""
    hermanos = [p for p in carpeta.parent.iterdir() if p.is_file() and p.suffix.lower() == ".crf"]
    mismo = next((p for p in hermanos if p.stem.lower() == carpeta.stem.lower()), None)
    if mismo is not None:
        return mismo
    suyos = [p for p in hermanos if (b := base_del_crf(p)) is not None and b.lower() == carpeta.stem.lower()]
    return suyos[0] if len(suyos) == 1 else None


def _texto(r: bytes | None) -> str | None:
    return r[4:].split(b"\0")[0].decode("cp1252") if r is not None and r[:4] == _CRF_EN_USO else None


def _huellas_crf(carpeta: Path, columnas: list[Columna]) -> dict[Columna, tuple[int | None, bool | None]] | None:
    """La máscara (MASK n) y el UPSHIFT de cada columna en el `<nombre>.crf` junto a la carpeta `.dbs`: lo que `LIKEVAR`
    copia en el control (la máscara, u16 alto de +0x20, nibble alto; el UPSHIFT, 0x40000 de +0x00). None sin .crf o
    con uno que no se sabe leer; None en una columna que no está o cuya huella no se sabe.

    Registro de columna (94 bytes; batería `likevar.py`, compilando con copias del .crf con un byte cambiado):
    +8 u32 su tabla (registro de la tabla de tablas, que en +0xC lleva el de textos con el nombre), +0xC u32 su nombre
    (registro de la de nombres), +0x14 u16 1 si hereda de otro registro de columna, +0x1A u32 cuál, +0x1E coltype,
    +0x24 u16 con 0x2 si la columna es UPSHIFT (solo en Char; batería `tablas.py`, `up_`, con copias de stock.crf con
    ese u16 cambiado: 0 → sin el bit, 2 → con él, 1 → sin él) y +0x32 u16 la máscara. Si hereda, la máscara vale la
    del registro del que hereda (la suya no cuenta): de un tipo del repositorio (`precio_tipo` de ALMAFAC) y de la
    columna de otra tabla (lineas.articulo de articulos.articulo). El UPSHIFT de una que hereda no se ha medido: vale
    si el suyo y el del padre coinciden (en los .crf de los kits, siempre); si no, None. Una herencia de dos saltos
    no se ha visto: None."""
    crf = crf_de(carpeta)
    if crf is None:
        return None
    datos = crf.read_bytes()
    tamanos = _CRF_TAMANOS.get(struct.unpack_from("<H", datos, 8)[0]) if datos.startswith(CRF_MAGIA) else None
    if tamanos is None:
        return None
    try:
        o, tablas = 0x40, []
        for tam in tamanos:
            regs, o = _tabla_crf(datos, o, tam)
            tablas.append(regs)
        _tabla_crf(datos, o, 16)  # la siguiente tiene que empezar justo donde acaba la de columnas
    except ValueError:
        return None
    nombres, textos, tabs, cols = tablas
    vistas: dict[tuple[str, str], list] = {}
    for r in cols:
        if r is None:
            continue
        if r[:4] != _CRF_EN_USO:
            return None
        t, nom, hereda, de, coltype, mascara = struct.unpack_from("<II", r, 8) + struct.unpack_from("<H", r, 0x14) + (
            struct.unpack_from("<I", r, 0x1A)[0], r[0x1E], struct.unpack_from("<H", r, 0x32)[0])
        upshift = bool(struct.unpack_from("<H", r, 0x24)[0] & 0x2) if coltype == CHAR else None  # en otros, no medido
        tabla = _texto(textos[i]) if t < len(tabs) and tabs[t] is not None and (
            i := struct.unpack_from("<I", tabs[t], 0xC)[0]) < len(textos) else None
        nombre = _texto(nombres[nom]) if nom < len(nombres) else None
        if tabla is None or nombre is None:
            continue
        if hereda == 1:
            padre = cols[de] if de < len(cols) else None
            ok = padre is not None and padre[:4] == _CRF_EN_USO and struct.unpack_from("<H", padre, 0x14)[0] == 0
            mascara = struct.unpack_from("<H", padre, 0x32)[0] if ok else None
            if not (ok and upshift is not None and padre[0x1E] == CHAR and bool(struct.unpack_from("<H", padre, 0x24)[0] & 0x2) == upshift):
                upshift = None
        elif hereda != 0:
            mascara = upshift = None
        vistas.setdefault((tabla.lower(), nombre.lower()), []).append((coltype, mascara, upshift))
    salida = {}
    for c in columnas:
        v = vistas.get((c.tabla.lower(), c.nombre.lower()), [])
        salida[c] = v[0][1:] if len(v) == 1 and v[0][0] == c.tipo else (None, None)  # sin dudas: una sola y del mismo tipo
    return salida


class Catalogo:
    def __init__(self, carpeta: Path):
        carpeta = Path(carpeta)
        cols = []
        for f in _filas(_fichero(carpeta, "syscolumns.dat"), _FILA_SYSCOLUMNS):
            tabid, colno, coltype, collen = struct.unpack(">ihhh", f[18:28])
            cols.append((tabid, colno, f[:18].decode("cp1252").rstrip(), coltype & 0xFF, collen, bool(coltype & 0x100)))
        fila = 1 + sum(_tam(t, n) for tabid, _, _, t, n, _ in cols if tabid == 1)
        nombres = {}
        for f in _filas(_fichero(carpeta, "systables.dat"), fila):
            nombres[struct.unpack_from(">i", f, 90)[0]] = f[:18].decode("cp1252").rstrip()
        if nombres.get(1) != "systables" or nombres.get(2) != "syscolumns":
            raise ValueError(f"{carpeta}: no parece un catálogo (systables {nombres.get(1)!r})")
        self.columnas = [Columna(nombres[tabid], nombre, t, n, nn) for tabid, _, nombre, t, n, nn in sorted(cols)
                         if tabid >= PRIMERA_TABLA and tabid in nombres]
        self.ultimas: list[Columna] = []  # las candidatas de la última búsqueda (buscar)
        self.valores = _valores_crf(carpeta)
        huellas = _huellas_crf(carpeta, self.columnas)  # None: sin .crf legible
        self.mascaras = {c: h[0] for c, h in huellas.items()} if huellas is not None else None  # columna → MASK del .crf
        self.upshifts = {c: h[1] for c, h in huellas.items()} if huellas is not None else None  # columna → UPSHIFT del .crf

    def tiene_valores(self, texto: str) -> bool:
        """Si la cadena de valores de una columna («V|M») está en el repositorio (el .crf): el compilador la copia."""
        return texto in self.valores

    def mascara(self, c: Columna) -> int | None:
        """La máscara de la columna en el .crf (None si no se sabe)."""
        return self.mascaras.get(c) if self.mascaras is not None else None

    def upshift(self, c: Columna) -> bool | None:
        """Si la columna es UPSHIFT en el .crf (None si no se sabe)."""
        return self.upshifts.get(c) if self.upshifts is not None else None

    def buscar(self, clase: str, largo: int, escala: int, preferida: str | None = None,
               tablas: tuple[str, ...] = (), mascara: int | None = None,
               estricta: bool = True, upshift: bool | None = None) -> tuple[Columna | None, int]:
        """Una columna que compila igual que el tipo dado, y cuántas lo hacen. Se prefiere la del mismo nombre
        y, entre ellas, la de una de `tablas` (las que ya usa el módulo); luego, el orden de tabla y columna.
        Con `mascara` (la que copió un LIKEVAR), solo las que la tienen en el .crf; si no es `estricta`, también
        las que no se sabe cuál tienen (las que tienen otra, nunca). Con `upshift` (si el LIKEVAR copió el bit),
        solo las que lo tienen igual en el .crf (STOCKMDI cust_rep: surname y company son Char(25) con la misma
        máscara y solo company es UPSHIFT). Con el bit, una columna con el UPSHIFT sin saber (herencia que no
        coincide, columna que el .crf no aclara, tipos sin medir) no vale; sin él, sigue valiendo como antes (ALMAFAC
        eticli: clientes.direccion) y el escritor lo avisa."""
        iguales = [c for c in self.columnas if c.en_omd() == (clase, largo, escala)
                   and (mascara is None or self.mascara(c) == mascara or not estricta and self.mascara(c) is None)
                   and (upshift is None or self.upshift(c) == upshift or not upshift and self.upshift(c) is None)]
        orden = sorted(iguales, key=lambda c: (c.nombre != preferida, c.tabla not in tablas))
        self.ultimas = orden  # las candidatas de la última búsqueda, en su orden (para los avisos)
        return (orden[0] if orden else None), len(iguales)


def encontrar(nombre: str, junto_a: Path) -> Path | None:
    """La carpeta `<nombre>.dbs` (sin distinguir mayúsculas) en la carpeta del módulo o en las de encima. Si no la hay,
    la de la base de datos del repositorio `<nombre>.crf` (`base_del_crf`), a su lado: INDODIC/UpkeepDict dice
    `REPOSITORY indodic` y su base es INDONESI.DBS."""
    carpetas = [Path(junto_a).resolve().parent, *Path(junto_a).resolve().parents][:4]
    for d in carpetas:
        for p in d.iterdir() if d.is_dir() else ():
            if p.is_dir() and p.name.lower() == f"{nombre.lower()}.dbs":
                return p
    for d in carpetas:
        for crf in d.iterdir() if d.is_dir() else ():
            if crf.is_file() and crf.name.lower() == f"{nombre.lower()}.crf" and (base := base_del_crf(crf)):
                return next((p for p in d.iterdir() if p.is_dir() and p.name.lower() == f"{base.lower()}.dbs"), None)
    return None

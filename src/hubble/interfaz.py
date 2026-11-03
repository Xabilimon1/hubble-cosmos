"""INTERFACE de los formularios: de los registros de FCT (controles), FON (fuentes) y SVL
(textos) a la sección INTERFACE del fuente COOL. Formato en docs/formato-omd.md
(«formularios»). Lo que no se sabe leer da NoSoportado.
"""
from __future__ import annotations

import struct

TIPOS = {1: "BUTTON", 2: "RADIO", 3: "CHECK", 4: "DROPLIST", 5: "DROPEDIT", 6: "EDIT", 7: "TEXT", 8: "BOX",
         0x0A: "PERCENT", 0x0D: "LIST", 0x0F: "BITMAP", 0x11: "PANEL", 0x15: "GRID", 0x17: "SPIN", 0x18: "SLIDER"}
DATOS = {0: "CHAR", 1: "SMALLINT", 2: "INTEGER", 3: "DECIMAL", 4: "TIME", 5: "DATE", 6: "DATETIME"}  # batería datos.py
CON_DATOS = {"EDIT", "DROPEDIT", "TEXT"}
# Comandos predefinidos (número de comando en el botón y en On Command).
COMANDOS = {0xFFEF: "Close", 0xFFF0: "AcceptEdit", 0xFFF1: "CancelEdit", 0xFFF3: "EditUpdate", 0xFFF4: "EditNew",
            0xFFF9: "Update", 0xFFFA: "Delete", 0xFFDC: "ResetFilters", 0xFFDD: "FilterByColumn",
            # batería lab/bateria/comandos.py (Previous, Print, Ok… no son predefinidos: van a CMD)
            0xFFEB: "QueryByForm", 0xFFED: "Query", 0xFFF2: "EditQueryLike", 0xFFFD: "Next", 0xFFFF: "First",
            0xFFFC: "Last", 0xFFE0: "AscendingSort", 0xFFDF: "DescendingSort", 0xFFE2: "HideColumn", 0xFFE1: "ShowAllColumns",
            0xFFF7: "New", 0xFFF8: "Add"}

TIPOS.update({0x16: "SPLIT", 0x0B: "TAB", 0x10: "BAR", 0x13: "USER", 0x14: "MENU", 0x1B: "MDICLIENT", 0x0C: "BUTTONGROUP", 0x0E: "BOXGROUP"})
GRUPOS = {"BUTTONGROUP", "BOXGROUP"}  # batería grupos.py
# ACTIVEX (Events.smd del kit 86x86; batería controles.py, ax_): `CLSID "x"` va donde el LABEL (+0x48, con su bit) y
# las PROPERTY, todas juntas en un texto `nombre=valor|…` donde los TAGS (+0x58, con su bit; sin PROPERTY, el texto
# vacío). Los dos bits están siempre. CLSID es obligatorio y va el último de los atributos; detrás solo PROPERTY
# (LABEL, NOLABEL, TAGS, BORDER, NOBORDER o ATTACH detrás no compilan; LABEL, NOLABEL y BACKGROUND, en ningún sitio).
TIPOS[0x1A] = "ACTIVEX"
# Lo visto delante de CLSID: DISABLED, INVISIBLE, FOREGROUND, FONT, ATTACH, NOBORDER y BORDER DOUBLE DOWN / ETCHED
# EXTRA n. Lo demás (CURSOR compila, pero no se ha visto su bit; BOLD, NOTABSTOP, COMMENT, PAGE…), NoSoportado
# (VISTOS_ACTIVEX y VISTOS_ACTIVEX_44, tras los bits).
# Borde de los elementos de un grupo, tras NUMBER: u16 alto de +0x20. Otro BORDER ahí no compila («Expecting black,
# hilight»), y en un BOXGROUP solo NOBORDER.
BORDES_GRUPO = {"BUTTONGROUP": {0x0C: "BORDER HILIGHT", 0x10: "BORDER BLACK", 0x40: "NOBORDER"}, "BOXGROUP": {0x40: "NOBORDER"}}
BARRAS = {1: "MENU", 2: "STATUS"}  # BARTYPE: u16 alto de +0x20 de un BAR
# PANELTYPE: u16 alto de +0x20 de un PANEL. MESSAGE: samples TREE1; OPERATION: batería datos.py (pop_), también
# dentro de un BAR, en el orden del editor visual (Victrpro.drw: «General|Comment|Message|EditMode|Operation»)
PANELES = {1: "COMMENT", 2: "MESSAGE", 3: "EDITMODE", 4: "OPERATION"}
BORDES_BOTON = {0x0C: "HILIGHT", 0x10: "BLACK"}  # BORDER …: u16 alto de +0x20 de un BUTTON
# NOBORDER de un BUTTON va en el mismo campo, no en los bits de siempre (samples NewLook, EJUPDATESTRING); como BORDER
# HILIGHT, delante del icono (detrás no compila: batería controles.py). DEFPUSH va detrás de los dos (samples NewLook).
SIN_BORDE_BOTON = 0x40

# Bits de +0x00 comunes a todos los controles.
EXTRA, DOUBLE, ETCHED, DOWN, NOBORDER, FRAME, NOLABEL = 0x3, 0x04, 0x08, 0x20, 0x40, 0x80, 0x800  # EXTRA n: 2 bits
LIKEVAR, AUTOSIZE, PASSWORD, UPSHIFT, DOWNSHIFT = 0x4000, 0x8000, 0x20000, 0x40000, 0x80000
DISABLED, INVISIBLE, BOLD = 0x100000, 0x400000, 0x800000
TAGS, LABEL, COMMENT, BASE = 0x20000000, 0x10000000, 0x40000000, 0x80000000
CONOCIDOS = (EXTRA | DOUBLE | ETCHED | DOWN | NOBORDER | FRAME | NOLABEL | LIKEVAR | AUTOSIZE | PASSWORD | UPSHIFT
             | DOWNSHIFT | DISABLED | INVISIBLE | BOLD | TAGS | LABEL | COMMENT | BASE)
# Bits de +0x00 que significan una cosa u otra según el tipo de control (batería controles.py).
B100, B200, B400, MULTILINE, ICON = 0x100, 0x200, 0x400, 0x1000, 0x2000
SCROLL_H, SCROLL_V = B100, B200            # LIST, DROPLIST, DROPEDIT, y EDIT sin icono
ICONO_IZQ, ICONO_VERTICAL = B100, B200     # con ICON: sin CENTER, VERTICAL
DEFPUSH, LABELLEFT, STRETCH, AUTOFIT = B400, B100, B100, ICON
RICHTEXTEDIT = B400  # EDIT: tras BORDER, LABEL y MULTILINE; delante de WRAP, PASSWORD y DATATYPE (batería controles.py)
TOPLEFT, TICKMARKS = B200, B400            # SLIDER (POINT TOPLEFT)
SPIN_COMMAND, SPIN_VERTICAL = B100, MULTILINE
BOTTOMRIGHT, VERTICAL = B100, MULTILINE    # SLIDER (POINT BOTTOMRIGHT), PERCENT y SLIDER (VERTICAL)
ETCHEDIN, ETCHEDOUT = B100, B200           # TEXT (uno u otro: juntos no compila)
PALIND, GRAYSCALE = B200, B400             # BITMAP (uno u otro)
MENU_VERTICAL = MULTILINE                  # control MENU; su ICON [CENTER] [VERTICAL] va sin número ni fichero
G_COLUMNS, G_MANUAL, G_RADIO = MULTILINE, UPSHIFT, DOWNSHIFT  # BUTTONGROUP y BOXGROUP: COLUMNS (sin él, ROWS), CLICKTYPE
FRAMEAUTOSIZE = 0x10000  # BUTTONGROUP y BOXGROUP (en BOX, BITMAP o EDIT no compila: batería controles.py, vw_)
BOX_SCROLL_H, BOX_SCROLL_V = 0x1000000, 0x2000000
BLACK = 0x10  # BORDER BLACK en BOX, BITMAP y TEXT, siempre delante (en un BUTTON va en +0x20; en un EDIT no compila)
PROPIOS = {
    "BUTTON": ICON | ICONO_IZQ | ICONO_VERTICAL | DEFPUSH,
    "BOX": ICON | ICONO_IZQ | ICONO_VERTICAL | BOX_SCROLL_H | BOX_SCROLL_V | BLACK,
    "EDIT": ICON | B100 | B200 | B400 | MULTILINE, "TEXT": MULTILINE | ETCHEDIN | ETCHEDOUT | BLACK, "CHECK": LABELLEFT,
    "RADIO": LABELLEFT, "BITMAP": STRETCH | AUTOFIT | PALIND | GRAYSCALE | BLACK, "SLIDER": TOPLEFT | BOTTOMRIGHT | TICKMARKS | VERTICAL,
    "PERCENT": TICKMARKS | VERTICAL, "SPLIT": VERTICAL, "MENU": ICON | ICONO_IZQ | ICONO_VERTICAL | MENU_VERTICAL, "SPIN": SPIN_COMMAND | SPIN_VERTICAL,
    "LIST": SCROLL_H | SCROLL_V, "DROPLIST": SCROLL_H | SCROLL_V, "DROPEDIT": SCROLL_H | SCROLL_V,
    "TAB": B100 | B400 | MULTILINE | ICON,  # FIXED WIDTH, LOWTAB, VERTICAL, ICON FILE
    "GRID": SCROLL_H | SCROLL_V | 0x10000,  # SCROLL, PARENTGRID
    "BUTTONGROUP": ICON | ICONO_IZQ | ICONO_VERTICAL | G_COLUMNS | FRAMEAUTOSIZE,
    "BOXGROUP": ICON | ICONO_IZQ | ICONO_VERTICAL | G_COLUMNS | FRAMEAUTOSIZE,
}
JUEGOS = {0: "Ansi", 134: "Gb2312", 161: "Greek", 162: "Turkish", 204: "Russian"}  # CHARSET (los vistos en el kit)
CON_ICONO = {"BUTTON", "BOX", "EDIT"}  # ICON n FILE "x": +0x70 = (n − 1) << 16 | índice en ICO
# Listas: bits de +0xA8 y CURSORTYPE (u16 alto de +0xB0; el bajo, nº de columnas).
LISTCOLS, SIMPLE, MULTIPLE, ICONO, SORTONCLICK = 0x1, 0x10, 0x30, 0x100, 0x400
# SORT: en un LIST, detrás de ICON FILE, ALLOWDRAG y ALLOWDROP y delante de SORTONCLICK y LISTTYPE; en DROPLIST y
# DROPEDIT, detrás de ICON FILE y DATATYPE y delante de TAGS y SHOW n LINES (en otro orden no compila: batería fct.py, so_)
ORDENADA = 0x200
CURSORES = {1: "FILE", 2: "SQL", 4: None, 5: "TREEVIEW"}
LISTAS = {"LIST", "DROPLIST", "DROPEDIT"}
# Del formulario (FCT 0).
SYSMENU, RESIZING, MAXIMIZE, MINIMIZE = 0x100, 0x200, 0x1000, 0x2000
THINCAPTION = 0x1  # solo en el formulario (en un control, 0x3 es EXTRA n); THINCAPTION en un control no compila
MENU_DEFECTO = 0x40000  # el formulario tiene `default menu` (FOR+0x30)
CONOCIDOS_FORM = (NOLABEL | DOUBLE | NOBORDER | SYSMENU | RESIZING | MAXIMIZE | MINIMIZE | THINCAPTION | LABEL | BASE
                  | MENU_DEFECTO)
# Bits de +0x44.
A_TOP, A_BOTTOM, A_LEFT, A_RIGHT = 0x1000, 0x2000, 0x4000, 0x8000
LISTA_DESPLEGABLE = 0x20000  # lo ponen solos DROPLIST y DROPEDIT
NOTABSTOP, CENTER, RIGHT, BUTTON, WRAP, DATETIMEPICKER = 0x200000, 0x400000, 0x800000, 0x1000000, 0x4000000, 0x10000000
STORE_STATUS, STORE_DESIGN, CURSOR = 0x80000, 0x100000, 0x8000000
SPIN, READONLY = 0x2000000, 0x40000000     # EDIT (SPIN va con BUTTON: «SPIN BUTTON»)
ALLOWDRAG, ALLOWDROP = 0x300, 0x10000      # LIST
CONOCIDOS_44 = (A_TOP | A_BOTTOM | A_LEFT | A_RIGHT | LISTA_DESPLEGABLE | NOTABSTOP | CENTER | RIGHT | BUTTON | WRAP
                | DATETIMEPICKER | STORE_STATUS | STORE_DESIGN | CURSOR)
# READONLY de DROPEDIT: detrás de DATATYPE y delante de CHECKMETHOD (batería formularios.py, vw_checkmethod_dropedit_readonly)
PROPIOS_44 = {"EDIT": SPIN | READONLY, "DROPEDIT": READONLY, "LIST": ALLOWDRAG | ALLOWDROP, "BOXGROUP": ALLOWDRAG}
SIN_COLOR, TRANSPARENTE = 0x80000000, 0xC0000000  # COLORREF (0x00BBGGRR) o uno de estos
# +0x70 de un control sin icono: 0xFFFFFFFF en estos, 0 en los demás.
SIN_ICONO = {"BUTTON": 0xFFFFFFFF, "BOX": 0xFFFFFFFF, "EDIT": 0xFFFFFFFF}
VISTOS_ACTIVEX = BASE | TAGS | LABEL | DISABLED | INVISIBLE | EXTRA | DOUBLE | ETCHED | DOWN | NOBORDER
VISTOS_ACTIVEX_44 = A_TOP | A_BOTTOM | A_LEFT | A_RIGHT  # ATTACH
# Campos de FCT que se leen (los demás tienen que estar a 0, o el control usa algo sin descifrar).
LEIDOS = {0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x3C, 0x40, 0x44, 0x48, 0x50, 0x54, 0x58, 0x60, 0x70, 0x78, 0x80, 0x88}
# +0xB8 de EDIT y DROPEDIT: CHECKMETHOD (el nombre del método, como texto en SVL; en 32 bits, +0x6C)
LEIDOS_TIPO = {"TEXT": {0xA0}, "EDIT": {0xA0, 0xB8}, "LIST": {0x68, 0xA8, 0xB0}, "DROPLIST": {0x68, 0xA8, 0xB0}, "DROPEDIT": {0x68, 0xA8, 0xB0, 0xB8}, "SLIDER": {0x68}, "PERCENT": {0x68},
               "TAB": {0x68}, "MENU": {0x24, 0x68}, "BUTTONGROUP": {0x68}, "BOXGROUP": {0x68},
               "GRID": {0x68, 0xA8}}  # GRID: +0x68 su binario de SVL (lo calcula el compilador); +0xA8, un puntero
PARENTGRID = 0x10000
# GRID: NOARROW, NOROWNUM y NOALLOWADD son los bits de PASSWORD, UPSHIFT y DOWNSHIFT (que en un GRID no compilan, delante
# ni detrás de PARENTGRID); se suman. Van detrás de PARENTGRID, en este orden y delante de AUTOSORT (en otro orden, o
# delante de PARENTGRID, no compilan: batería tablas.py, rj_).
G_NOARROW, G_NOROWNUM, G_NOALLOWADD = PASSWORD, UPSHIFT, DOWNSHIFT
TAB_FIXED, TAB_LOWTAB, TAB_VERTICAL = B100, B400, MULTILINE
LEIDOS_FORM = {0x00, 0x10, 0x28, 0x30, 0x38, 0x3C, 0x40, 0x44, 0x48, 0x50, 0x54, 0x58, 0x68, 0x88}  # +0x68: su CLA
FORM_ALLOWDROP = 0x400  # +0x44 del formulario
CLASE_CONTROL = "SimpleFormControl"  # +0x88 (ECL) de todos los controles vistos
FCT, SVL, FOB, CLA, ECL = 0x10, 0x21, 0x12, 0x07, 0x19


class Interfaz:
    SECCION = "FCT"  # la de los controles (en una página, PCT)
    fobs_de_columna: set[int] = frozenset()  # FOB Money/Decimal que el escritor sacó `as tabla.columna` por su máscara

    def __init__(self, m, no_soportado):
        self.m = m
        self.NoSoportado = no_soportado
        self.svl = self.m.registros_flujo("SVL")

    def u32(self, k, off):
        return self.m.u32("FCT", k, off)

    def ref(self, k, off, seccion):
        w = self.u32(k, off)
        if w == 0 or w & 0xFF or (w >> 8) & 0xFF != seccion:
            return None
        return w >> 16

    def texto_svl(self, k, off) -> str:
        i = self.ref(k, off, SVL)
        r = self.svl.get(i * 4) if i is not None else None
        if r is None or r.binario:
            raise self.NoSoportado(f"texto de SVL en FCT {k}+{off:#x}")
        return r.texto()

    def nombre(self, k) -> str:
        pos = self.u32(k, 0x30)  # posición en IDE / 4, más 1; 0 = sin nombre
        return (self.m.ide.get((pos - 1) * 4) or "") if pos else ""

    def color(self, w) -> str:
        if w == TRANSPARENTE:
            return "COLOR transparent"
        if w >> 24:
            raise self.NoSoportado(f"color {w:#x}")
        return f"RGB {w & 0xFF} {(w >> 8) & 0xFF} {(w >> 16) & 0xFF}"

    def fuente(self, k) -> str | None:
        i = self.u32(k, 0x40) >> 16  # 1 + índice en FON; 0 = sin fuente
        if not i:
            return None
        r = self.m.rec("FON", i - 1)
        tam, estilo, juego = struct.unpack_from("<HHH", r, 2)  # estilo: ITALIC 1, BOLD 2
        nombre = r[8:].split(b"\0")[0].decode("cp1252")
        if estilo & 0x30 in (0x10, 0x20):  # 7.4.2 (8.6 no): 0x10 o 0x20 sin nada en el fuente; ¿tipo de fuente?
            estilo &= ~0x30
        if estilo & ~3 or juego != 1 and juego not in JUEGOS:  # juego 1 (DEFAULT_CHARSET): sin CHARSET
            raise self.NoSoportado(f"FONT {nombre!r} con estilo {estilo:#x} y juego {juego}")
        return (f'FONT "{nombre}" {tam}' + (" BOLD" if estilo & 2 else "") + (" ITALIC" if estilo & 1 else "")
                + (f" CHARSET {JUEGOS[juego]}" if juego != 1 else ""))

    def cadena(self, texto: str) -> str:
        if '"' in texto:
            raise self.NoSoportado("texto de formulario con comillas")
        return f'"{texto}"'

    # --- un control
    def guarda(self, k, tipo):
        """Los campos que no se leen tienen que estar a 0; si no, el control usa algo sin descifrar."""
        leidos = LEIDOS | LEIDOS_TIPO.get(tipo, set())
        for o in range(0, 208, 4):
            if o not in leidos and self.u32(k, o):
                raise self.NoSoportado(f"{tipo} FCT {k}: +{o:#04x} = {self.u32(k, o):#x}, sin descifrar")
        r = self.m.u32("FCT", k, 0x88)
        if (r >> 8) & 0xFF != ECL or self.m.ecl[r >> 16] != CLASE_CONTROL or r & 0xFF:
            raise self.NoSoportado(f"{tipo} FCT {k}: clase {r:#x}")
        if (self.u32(k, 0x20) >> 16) and tipo not in (*CON_DATOS, "BAR", "PANEL", "BUTTON", "MENU", "SPIN", *GRUPOS):
            raise self.NoSoportado(f"{tipo} FCT {k}: +0x20 {self.u32(k, 0x20):#x}")
        if (self.u32(k, 0x40) & 0xFFFF) and tipo not in ("BUTTON", "RADIO", "SPIN", "TAB", "MENU", *CON_DATOS, *GRUPOS):
            raise self.NoSoportado(f"{tipo} FCT {k}: +0x40 {self.u32(k, 0x40):#x}")
        for bit, off in ((LABEL, 0x48), (COMMENT, 0x80)):
            if not self.u32(k, 0x00) & bit and self.u32(k, off):
                raise self.NoSoportado(f"{tipo} FCT {k}: +{off:#x} sin su bit")
        if not self.u32(k, 0x00) & TAGS and self.u32(k, 0x58):
            raise self.NoSoportado(f"{tipo} FCT {k}: +0x58 sin TAGS")
        if self.u32(k, 0x60) >> 16 and tipo not in ("DROPLIST", "DROPEDIT", "BOX", "TAB"):
            raise self.NoSoportado(f"{tipo} FCT {k}: +0x60 {self.u32(k, 0x60):#x}")
        if self.u32(k, 0x78) and self.ref(k, 0x78, FOB) is None and self.ref(k, 0x78, 0x14) is None:
            raise self.NoSoportado(f"{tipo} FCT {k}: +0x78 {self.u32(k, 0x78):#x}")

    def icono(self, k, tipo, b0) -> str | None:
        """ICON n FILE "x" [CENTER] [VERTICAL] de BUTTON, BOX y EDIT; ICON n de CHECK."""
        w = self.u32(k, 0x70)
        if tipo == "TAB":
            if not b0 & ICON:
                if w:
                    raise self.NoSoportado(f"ICON {w:#x} sin su bit en el TAB FCT {k}")
                return None
            if w >= self.m.s["ICO"].n:
                raise self.NoSoportado(f"ICON {w:#x} fuera de ICO en FCT {k}")
            return f'ICON FILE "{self.m.rec("ICO", w)[2:].split(b"\0")[0].decode("cp1252")}" CENTER'
        if tipo == "MENU":  # ICON [CENTER] [VERTICAL], sin número ni fichero: +0x70 a 0
            if w:
                raise self.NoSoportado(f"ICON {w:#x} en el control MENU FCT {k}")
            if not b0 & ICON:
                if b0 & (ICONO_IZQ | ICONO_VERTICAL):
                    raise self.NoSoportado(f"bits de icono sin ICON en el control MENU FCT {k}")
                return None
            return "ICON" + ("" if b0 & ICONO_IZQ else " CENTER") + (" VERTICAL" if b0 & ICONO_VERTICAL else "")
        if tipo == "CHECK":  # sin FILE (con FILE no compila); ICON 1 = sin icono
            if w & 0xFFFF:
                raise self.NoSoportado(f"ICON {w:#x} en el CHECK FCT {k}")
            return f"ICON {(w >> 16) + 1}" if w else None
        if tipo in GRUPOS:  # +0x70: el índice en ICO de su ICON FILE (lo comprueba grupo())
            return None
        if tipo not in CON_ICONO:
            if w != SIN_ICONO.get(tipo, 0):
                raise self.NoSoportado(f"ICON {w:#x} en FCT {k}, sin descifrar")
            return None
        if not b0 & ICON:
            if w != SIN_ICONO[tipo]:
                raise self.NoSoportado(f"ICON {w:#x} sin su bit en FCT {k}")
            return None
        n, i = (w >> 16) + 1, w & 0xFFFF
        if i >= self.m.s["ICO"].n:
            raise self.NoSoportado(f"ICON {w:#x} fuera de ICO en FCT {k}")
        fichero = self.m.rec("ICO", i)[2:].split(b"\0")[0].decode("cp1252")
        return (f'ICON {n} FILE "{fichero}"' + ("" if b0 & ICONO_IZQ else " CENTER")
                + (" VERTICAL" if b0 & ICONO_VERTICAL else ""))

    def borde(self, b0) -> str | None:
        partes = [n for bit, n in ((BLACK, "BLACK"), (DOUBLE, "DOUBLE"), (ETCHED, "ETCHED"), (DOWN, "DOWN"), (FRAME, "FRAME"))
                  if b0 & bit]
        if b0 & EXTRA:
            partes.append(f"EXTRA {b0 & EXTRA}")
        # las que compilan (batería controles.py); BLACK, con DOWN, FRAME o EXTRA 1, y no con DOUBLE ni ETCHED
        if partes in (["DOUBLE"], ["DOUBLE", "DOWN"], ["ETCHED"], ["DOWN"], ["FRAME"], ["DOUBLE", "FRAME"], ["DOWN", "FRAME"],
                      ["ETCHED", "EXTRA 1"], ["ETCHED", "EXTRA 3"], ["FRAME", "EXTRA 1"],
                      ["BLACK"], ["BLACK", "DOWN"], ["BLACK", "FRAME"], ["BLACK", "EXTRA 1"]) or not partes \
                or partes[-1].startswith("EXTRA") and partes[:-1] in ([], ["DOUBLE"], ["DOWN"], ["FRAME"], ["ETCHED"]):
            # EXTRA n solo o con DOUBLE, DOWN, FRAME o ETCHED, n de 1 a 3 (batería, y CalcALG calcu3: ETCHED EXTRA 2)
            return "BORDER " + " ".join(partes) if partes else None
        raise self.NoSoportado(f"borde {b0 & (EXTRA | DOUBLE | ETCHED | DOWN | FRAME | BLACK):#x}")

    def atributos(self, k, es_form: bool, focus: int | None) -> list[str]:
        b0, b44 = self.u32(k, 0x00), self.u32(k, 0x44)
        tipo_dato = self.u32(k, 0x20)
        tipo = None if es_form else TIPOS.get(tipo_dato & 0xFFFF)
        if not es_form and tipo is None:
            raise self.NoSoportado(f"control de tipo {tipo_dato & 0xFFFF:#x}")
        sobra = b0 & ~(CONOCIDOS_FORM if es_form else CONOCIDOS | PROPIOS.get(tipo, 0))
        if sobra:
            raise self.NoSoportado(f"bits {sobra:#x} sin descifrar en FCT {k}")
        if not es_form and b44 & ~(CONOCIDOS_44 | PROPIOS_44.get(tipo, 0)):
            raise self.NoSoportado(f"bits {b44 & ~(CONOCIDOS_44 | PROPIOS_44.get(tipo, 0)):#x} de +0x44 sin descifrar en FCT {k}")
        if not es_form:
            self.guarda(k, tipo)
            if tipo == "ACTIVEX":
                self.guarda_activex(k, b0, b44, focus)
        else:
            for o in range(0, 208, 4):
                if o not in LEIDOS_FORM and self.u32(k, o):
                    raise self.NoSoportado(f"formulario FCT {k}: +{o:#04x} = {self.u32(k, o):#x}, sin descifrar")
            if b44 & ~FORM_ALLOWDROP:
                raise self.NoSoportado(f"bits {b44 & ~FORM_ALLOWDROP:#x} de +0x44 del formulario")
        icono = None if es_form or tipo in LISTAS else self.icono(k, tipo, b0)
        x, y, w, h = struct.unpack_from("<4H", self.m.rec("FCT", k), 0x38)
        a = [f"POSITION {x} {y} {w} {h}"]
        if b0 & DISABLED:  # justo tras POSITION: detrás de cualquier otro atributo no compila (batería controles.py)
            a.append("DISABLED")
        if not es_form:
            if b0 & INVISIBLE:
                a.append("INVISIBLE")
        if (c := self.u32(k, 0x54)) != SIN_COLOR:
            a.append(f"FOREGROUND {self.color(c)}")
        if (c := self.u32(k, 0x50)) != SIN_COLOR:
            a.append(f"BACKGROUND {self.color(c)}")
        if b0 & BOLD:  # delante de FONT: detrás, el compilador lo aplica a la fuente
            a.append("BOLD")
        if f := self.fuente(k):
            a.append(f)
        if not es_form and b44 & CURSOR:  # detrás de los colores, BOLD y FONT y delante de STORE, FOCUS, NOTABSTOP y
            a.append("CURSOR")            # ATTACH, en todos los tipos (batería fct.py, cur_; delante no compila)
        if not es_form and b44 & (STORE_STATUS | STORE_DESIGN):
            if not b44 & STORE_DESIGN:
                raise self.NoSoportado(f"STORE {b44 & (STORE_STATUS | STORE_DESIGN):#x} en FCT {k}")
            a.append("STORE STATUS DESIGN" if b44 & STORE_STATUS else "STORE DESIGN")
        if focus is not None and focus == k:
            a.append("FOCUS")
        if not es_form and b44 & NOTABSTOP:
            a.append("NOTABSTOP")
        if not es_form:
            partes = [n for bit, n in ((A_LEFT, "LEFT"), (A_TOP, "TOP"), (A_RIGHT, "RIGHT"), (A_BOTTOM, "BOTTOM")) if b44 & bit]
            if len(partes) == 4:
                a.append("ATTACH ALL")
            elif partes:
                a.append("ATTACH " + " ".join(partes))
            pagina, actual = self.u32(k, 0x60) & 0xFFFF, self.u32(k, 0x60) >> 16
            if pagina:  # PAGE n de un control dentro de un TAB: n − 1 (PAGE 0 = 0xFFFF); tras ATTACH
                a.append(f"PAGE {(pagina + 1) & 0xFFFF}")
            if actual and tipo in ("BOX", "TAB"):
                a.append(f"CURRENT PAGE {actual + 1}")
        if b0 & COMMENT:
            a.append("COMMENT " + self.cadena(self.texto_svl(k, 0x80)))
        if b0 & LABEL and (tipo != "TAB" or self.tab_con_label(k)) and tipo not in (*GRUPOS, "ACTIVEX"):  # en un TAB y en los grupos, las de sus elementos
            a.append("LABEL " + self.cadena(self.texto_svl(k, 0x48)))
        if b0 & NOLABEL:
            a.append("NOLABEL")
        if es_form:
            a += self.borde_form(k, b0)
            for bit, n in ((MAXIMIZE, "MAXIMIZE"), (MINIMIZE, "MINIMIZE"), (THINCAPTION, "THINCAPTION"), (SYSMENU, "SYSMENU")):
                if b0 & bit:
                    a.append(n)
            if b44 & FORM_ALLOWDROP:
                a.append("ALLOWDROP")
            return a
        if tipo in ("CHECK", "RADIO") and b0 & LABELLEFT:
            a.append("LABELLEFT")
        defpush_tras_borde = tipo == "BUTTON" and b0 & DEFPUSH and tipo_dato >> 16
        if tipo == "BUTTON" and b0 & DEFPUSH and not defpush_tras_borde:
            a.append("DEFPUSH")
        if b0 & NOBORDER:
            a.append("NOBORDER")
        if borde := self.borde(b0):
            a.append(borde)
        # BORDER HILIGHT|BLACK: en un BUTTON, delante del icono (detrás no compila); en MENU y SPIN, detrás de BUTTON
        # (sin él no compila; BUTTON solo no deja huella), compatible con un BORDER de los de siempre, y al final
        # de los suyos (en MENU, tras el icono)
        boton = []
        if tipo == "BUTTON" and tipo_dato >> 16 == SIN_BORDE_BOTON:
            if borde:
                raise self.NoSoportado(f"NOBORDER de botón con borde en FCT {k}")
            boton = ["NOBORDER"]
        elif tipo in ("BUTTON", "MENU", "SPIN") and tipo_dato >> 16:
            if tipo_dato >> 16 not in BORDES_BOTON or borde and tipo == "BUTTON":
                raise self.NoSoportado(f"borde de botón {tipo_dato >> 16:#x} en FCT {k}")
            boton = ([] if tipo == "BUTTON" else ["BUTTON"]) + [f"BORDER {BORDES_BOTON[tipo_dato >> 16]}"]
        if tipo == "BUTTON":
            a += boton + (["DEFPUSH"] if defpush_tras_borde else [])
        if tipo == "MENU" and b0 & MENU_VERTICAL:
            a.append("VERTICAL")
        if tipo == "SPLIT" and b0 & VERTICAL:  # detrás del borde (delante no compila: batería controles.py)
            a.append("VERTICAL")
        if icono and tipo != "CHECK":  # detrás del borde (delante no compila); el ICON n de un CHECK, tras VARIABLE
            a.append(icono)
        if tipo == "MENU" and b0 & AUTOSIZE:  # tras el icono y delante de BUTTON BORDER y de `MENU x` (batería menus.py,
            a.append("AUTOSIZE")             # mau_: detrás de `MENU x` o delante de cualquier otro atributo no compila)
        if tipo == "MENU":
            a += boton
        if tipo == "GRID" and b0 & AUTOSIZE:  # tras los bordes, delante de SCROLL, TABLE y PARENTGRID (detrás no compila:
            a.append("AUTOSIZE")             # samples loadCustomFonts, ALMAFAC auxiliar)
        if tipo == "GRID" and b0 & (SCROLL_H | SCROLL_V):
            a.append("SCROLL" + (" VERTICAL" if b0 & SCROLL_V else "") + (" HORIZONTAL" if b0 & SCROLL_H else ""))
        if (tabla := self.ref(k, 0x78, 0x14)) is not None:  # TABLE x: +0x78 → su FTA (en vez de un FOB)
            a.append(f"TABLE {self.m.texto_ide(self.m.u32('FTA', tabla, 0x10))}")
        if tipo == "GRID":
            i = self.ref(k, 0x68, SVL)
            if not b0 & PARENTGRID or i is None or not self.svl.get(i * 4) or not self.svl[i * 4].binario:
                raise self.NoSoportado(f"GRID FCT {k} sin PARENTGRID o sin su binario de SVL")
            a.append("PARENTGRID")
            a += [n for bit, n in ((G_NOROWNUM, "NOROWNUM"), (G_NOARROW, "NOARROW"), (G_NOALLOWADD, "NOALLOWADD")) if b0 & bit]
            if b44 & BUTTON:  # en un GRID, el bit de BUTTON es AUTOSORT
                a.append("AUTOSORT")
        if tipo == "BOX" and b0 & (BOX_SCROLL_H | BOX_SCROLL_V):
            a.append("SCROLL" + (" VERTICAL" if b0 & BOX_SCROLL_V else "") + (" HORIZONTAL" if b0 & BOX_SCROLL_H else ""))
        if tipo == "BITMAP":
            if b0 & AUTOSIZE:  # delante del fichero (detrás no compila: samples almacen)
                a.append("AUTOSIZE")
            if b0 & TAGS:  # el fichero va donde los TAGS; delante de STRETCH
                a.append("BITMAP FILE " + self.cadena(self.texto_svl(k, 0x58)))
            if b0 & PALIND and b0 & GRAYSCALE:
                raise self.NoSoportado(f"PALIND y GRAYSCALE juntos en el BITMAP FCT {k}")
            a += [n for bit, n in ((STRETCH, "STRETCH"), (AUTOFIT, "AUTOFIT"), (PALIND, "PALIND"), (GRAYSCALE, "GRAYSCALE"))
                  if b0 & bit]
        if tipo == "TAB":
            a += self.pestanas(k, b0)
        if tipo in GRUPOS:
            cabeza, elementos = self.grupo(k, tipo, b0, tipo_dato)
            a += cabeza
        if tipo == "MENU":  # control MENU de una barra: +0x68 → la raíz (MOP) del menú que enseña
            a.append(f"MENU {self.nombre_menu(k)}")
        if tipo in ("SLIDER", "PERCENT"):
            if tipo == "SLIDER" and b0 & (TOPLEFT | BOTTOMRIGHT):
                if b0 & TOPLEFT and b0 & BOTTOMRIGHT:
                    raise self.NoSoportado(f"POINT TOPLEFT y BOTTOMRIGHT juntos en FCT {k}")
                a.append("POINT " + ("TOPLEFT" if b0 & TOPLEFT else "BOTTOMRIGHT"))
            if rango := self.u32(k, 0x68):
                a.append(f"RANGE {rango & 0xFFFF} {rango >> 16}")
            if b0 & VERTICAL:
                a.append("VERTICAL")
            if b0 & TICKMARKS:
                a.append("TICKMARKS")
        if tipo == "SPIN":
            if b0 & SPIN_VERTICAL:
                a.append("VERTICAL")
            veces = self.u32(k, 0x40) & 0xFFFF
            if veces not in (2, 4):
                raise self.NoSoportado(f"SPIN FCT {k}: +0x40 {veces:#x}")
            if veces == 4:
                a.append("QUADRUPLE")
            if b0 & SPIN_COMMAND:
                a.append("COMMAND")
            a += boton
        if tipo == "PANEL" and tipo_dato >> 16:
            if tipo_dato >> 16 not in PANELES:
                raise self.NoSoportado(f"PANELTYPE {tipo_dato >> 16} en FCT {k}")
            a.append(f"PANELTYPE {PANELES[tipo_dato >> 16]}")
        if tipo == "BAR" and tipo_dato >> 16:  # sin BARTYPE, 0 (samples Transparent; batería controles.py)
            if (tipo_dato >> 16) not in BARRAS:
                raise self.NoSoportado(f"BARTYPE {tipo_dato >> 16} en FCT {k}")
            a.append(f"BARTYPE {BARRAS[tipo_dato >> 16]}")
        if b0 & AUTOSIZE and tipo not in ("GRID", "BITMAP", "MENU") and not (tipo in GRUPOS and b0 & FRAMEAUTOSIZE):
            a.append("AUTOSIZE")
        if (v := self.ref(k, 0x78, FOB)) is not None:
            a.append(f"VARIABLE {self.m.nombre_fob(v)}")
            if tipo == "TEXT" and b0 & LIKEVAR:  # en un TEXT, LIKEVAR delante de TAGS (detrás no compila)
                a.append("LIKEVAR")
        if icono and tipo == "CHECK":  # ICON n de un CHECK: detrás de AUTOSIZE y de VARIABLE (delante de cualquiera de los
            a.append(icono)           # dos no compila: STOCKMDI TRIPLE; batería menus.py, kic_). Lo demás no compila en un CHECK
        # LIKEVAR sobre una columna de tabla: el tipo, UPSHIFT y ALIGNMENT los copia el compilador del
        # repositorio (no se escriben).
        de_tabla = b0 & LIKEVAR and (v := self.ref(k, 0x78, FOB)) is not None and self.m.refa("FOB", v, 0x50, 0x14) is not None
        # TEXT con LIKEVAR de un Money: el ALIGNMENT RIGHT lo copia el compilador de la variable (batería likevar.py,
        # lk_texto_form; escrito detrás de LIKEVAR, no compila). Otra alineación u otra clase no se han visto.
        fob = self.ref(k, 0x78, FOB)
        texto_likevar_alineado = tipo == "TEXT" and b0 & LIKEVAR and fob is not None and b44 & (CENTER | RIGHT) and not de_tabla
        alinea_la_variable = bool(texto_likevar_alineado and b44 & (CENTER | RIGHT) == RIGHT
                                  and self.m.nombre_clase(self.m.u32("FOB", fob, 0x18)).lower() == "money")
        if texto_likevar_alineado and not alinea_la_variable:
            raise self.NoSoportado(f"TEXT FCT {k} con LIKEVAR y ALIGNMENT {b44 & (CENTER | RIGHT):#x} (no visto)")
        if b44 & (CENTER | RIGHT) and not de_tabla and not alinea_la_variable:
            a.append("ALIGNMENT " + ("CENTER" if b44 & CENTER else "RIGHT"))
        if b44 & SPIN:  # detrás de ALIGNMENT
            if not b44 & BUTTON:
                raise self.NoSoportado(f"SPIN sin BUTTON en FCT {k}")
            a.append("SPIN BUTTON")
        if b0 & MULTILINE and tipo in ("EDIT", "TEXT"):
            a.append("MULTILINE")
        if tipo == "EDIT" and b0 & RICHTEXTEDIT:
            a.append("RICHTEXTEDIT")
        if tipo == "TEXT" and b0 & (ETCHEDIN | ETCHEDOUT):
            if b0 & ETCHEDIN and b0 & ETCHEDOUT:
                raise self.NoSoportado(f"ETCHEDIN y ETCHEDOUT juntos en FCT {k}")
            a.append("ETCHEDIN" if b0 & ETCHEDIN else "ETCHEDOUT")
        if tipo == "BUTTON" and (cmd := self.u32(k, 0x40) & 0xFFFF):
            a.append(f"COMMAND {self.comando(cmd)}")
        if b0 & PASSWORD and tipo != "GRID":  # en un GRID, NOARROW
            a.append("PASSWORD")
        texto_likevar = tipo == "TEXT" and b0 & LIKEVAR and fob is not None  # el tipo, de la variable
        if b0 & UPSHIFT and not de_tabla and not texto_likevar and tipo not in (*GRUPOS, "GRID"):
            a.append("UPSHIFT")  # en un TEXT con LIKEVAR es el de la columna (escrito no compila; batería tablas.py, up_)
        if b44 & WRAP:
            a.append("WRAP")
        if b0 & DOWNSHIFT and tipo not in (*GRUPOS, "GRID"):
            a.append("DOWNSHIFT")
        if b44 & BUTTON and not b44 & SPIN and tipo != "GRID":
            a.append("BUTTON")
        if texto_likevar:
            self.mascara_de_columna(k, fob, tipo_dato, b0)
        if tipo in ("DROPLIST", "DROPEDIT") and self.u32(k, 0xA8) & ICONO:  # delante de DATATYPE (detrás no compila)
            a.append(f'ICON FILE "{self.icono_de_lista(k)}"')
        formato = self.ref(k, 0xA0, SVL)  # DATATYPE CHAR FORMAT "x" (samples drag1); con otro tipo no compila
        if tipo in CON_DATOS and not de_tabla and not texto_likevar:
            d = self.datatype(k, tipo_dato)
            if formato is not None:
                if not d.startswith("DATATYPE CHAR"):
                    raise self.NoSoportado(f"{tipo} FCT {k}: FORMAT con {d}")
                d += " FORMAT " + self.cadena(self.texto_svl(k, 0xA0))
            if d != "DATATYPE CHAR" or tipo != "TEXT":  # TEXT: CHAR a secas = sin DATATYPE
                a.append(d)
        elif formato is not None:
            raise self.NoSoportado(f"{tipo} FCT {k}: FORMAT sin DATATYPE")
        likevar_antes = tipo == "EDIT" and not b0 & ICON and b0 & (SCROLL_H | SCROLL_V) and b0 & LIKEVAR
        if likevar_antes:  # delante de SCROLL (detrás no compila: AGENDA mes)
            a.append("LIKEVAR")
        if tipo == "EDIT" and not b0 & ICON and b0 & (SCROLL_H | SCROLL_V):  # con icono, 0x100/0x200 son del icono
            a.append("SCROLL" + (" VERTICAL" if b0 & SCROLL_V else "") + (" HORIZONTAL" if b0 & SCROLL_H else ""))
        if tipo in ("DROPLIST", "DROPEDIT") and self.u32(k, 0xA8) & ORDENADA:
            if b44 & READONLY or b0 & LIKEVAR:  # SORT con READONLY o LIKEVAR no se ha visto
                raise self.NoSoportado(f"SORT en {tipo} FCT {k} con READONLY o LIKEVAR")
            a.append("SORT")
        if b44 & READONLY:
            a.append("READONLY")
        if b0 & TAGS and tipo == "LIST":  # CURSORTYPE FILE "x": el fichero, donde los TAGS
            if CURSORES.get(self.u32(k, 0xB0) >> 16) != "FILE":
                raise self.NoSoportado(f"TAGS en la lista FCT {k}")
        elif b0 & TAGS and tipo not in ("BITMAP", "ACTIVEX"):
            if tipo in ("RADIO",):
                a.append(f"NUMBER {self.u32(k, 0x40) & 0xFFFF} TAGS " + " ".join(self.cadena(t) for t in self.texto_svl(k, 0x58).split("|")))
            else:
                a.append("TAGS " + " ".join(self.cadena(t) for t in self.texto_svl(k, 0x58).split("|")))
        if b0 & LIKEVAR and not (tipo == "TEXT" and self.ref(k, 0x78, FOB) is not None) and not likevar_antes:
            a.append("LIKEVAR")
        if tipo in LISTAS:
            a += self.lista(k, tipo, b0, b44)
        if b44 & DATETIMEPICKER:
            a.append("DATETIMEPICKER")
        if tipo in ("EDIT", "DROPEDIT") and self.u32(k, 0xB8):
            a.append(self.checkmethod(k, b0, de_tabla))
        if tipo in GRUPOS:  # CLICKTYPE, NUMBER y los elementos, los últimos (VARIABLE o AUTOSIZE detrás no compilan)
            a += elementos
        if tipo == "ACTIVEX":  # el último; detrás, solo PROPERTY (otra cosa no compila)
            a.append("CLSID " + self.cadena(self.texto_svl(k, 0x48)))
            a += [f"PROPERTY {self.cadena(n)} {self.cadena(v)}" for n, v in self.propiedades(k)]
        return a

    def guarda_activex(self, k, b0, b44, focus):
        """Un ACTIVEX solo con lo visto (batería controles.py, ax_): los bits de CLSID (LABEL) y de PROPERTY (TAGS),
        siempre; delante de CLSID, DISABLED, INVISIBLE, FOREGROUND, FONT, ATTACH y los bordes vistos. BACKGROUND no
        compila; CURSOR, BOLD, NOTABSTOP, COMMENT, FOCUS, PAGE, VARIABLE o hijos no se han visto."""
        if b0 & (LABEL | TAGS) != LABEL | TAGS:
            raise self.NoSoportado(f"ACTIVEX FCT {k} sin CLSID o sin el texto de PROPERTY: {b0:#x}")
        if b0 & ~VISTOS_ACTIVEX or b44 & ~VISTOS_ACTIVEX_44:
            raise self.NoSoportado(f"ACTIVEX FCT {k}: bits {b0 & ~VISTOS_ACTIVEX:#x} y {b44 & ~VISTOS_ACTIVEX_44:#x} de +0x44 no vistos")
        if self.u32(k, 0x50) != SIN_COLOR or self.u32(k, 0x60) or self.u32(k, 0x78) or self.u32(k, 0x10) or focus == k:
            raise self.NoSoportado(f"ACTIVEX FCT {k} con BACKGROUND, PAGE, VARIABLE, FOCUS o hijos")

    def propiedades(self, k) -> list[tuple[str, str]]:
        """Las PROPERTY "nombre" "valor" de un ACTIVEX: un solo texto en SVL (+0x58), `nombre=valor|` por cada una, en
        el orden del fuente y con las repetidas (batería controles.py, ax_prop_). Sin escape: `PROPERTY "a=b" "c"` da
        `a=b=c|` y `PROPERTY "Day" "a|b"`, `Day=a|b|`. Se parte por `|` y cada trozo tiene que llevar un solo `=` y un
        nombre: así el fuente vuelve a dar el mismo texto. Lo que no (un `=` de más, un trozo sin `=`), NoSoportado."""
        texto = self.texto_svl(k, 0x58)
        if not texto:
            return []
        if not texto.endswith("|"):
            raise self.NoSoportado(f"PROPERTY de ACTIVEX FCT {k} sin «|» al final: {texto!r}")
        salida = []
        for trozo in texto[:-1].split("|"):
            if trozo.count("=") != 1 or trozo.startswith("="):
                raise self.NoSoportado(f"PROPERTY de ACTIVEX FCT {k} que no se puede partir: {texto!r}")
            salida.append(tuple(trozo.split("=")))
        return salida

    def checkmethod(self, k, b0, de_tabla) -> str:
        """CHECKMETHOD x de EDIT y DROPEDIT: +0xB8 → el nombre, tal cual se escribió, en SVL (sin comillas: con ellas no
        compila; el método no tiene por qué existir). El último de los suyos: detrás de DATATYPE, READONLY, LIKEVAR,
        DATETIMEPICKER y los atributos de lista (delante no compila: batería formularios.py, vw_). Con TAGS no compila
        en ningún orden de los probados. Con LIKEVAR de una columna del repositorio, el compilador podría copiarlo de
        la columna (como UPSHIFT): no se sabe si se escribió."""
        if b0 & TAGS or de_tabla:
            raise self.NoSoportado(f"CHECKMETHOD en FCT {k} con TAGS o con LIKEVAR de una columna")
        nombre = self.texto_svl(k, 0xB8)
        if not nombre or not (nombre[0].isalpha() or nombre[0] == "_") or not all(c.isalnum() or c == "_" for c in nombre):
            raise self.NoSoportado(f"CHECKMETHOD {nombre!r} en FCT {k}")
        return f"CHECKMETHOD {nombre}"

    def borde_form(self, k, b0) -> list[str]:
        """El borde del formulario, en +0x00 de FCT 0: el de serie lleva DOUBLE (0x04); NOBORDER, 0x40 sin DOUBLE;
        RESIZING, 0x200 con DOUBLE; THINFRAME, sin ninguno de los tres. Va detrás de LABEL y NOLABEL y delante de
        MAXIMIZE, MINIMIZE, THINCAPTION, SYSMENU y ALLOWDROP (en otro orden no compila: batería formularios.py, vw_).
        NOBORDER o THINFRAME con RESIZING, y THINFRAME con NOBORDER, no compilan; lo demás no se ha visto."""
        borde = b0 & (DOUBLE | NOBORDER | RESIZING)
        if borde == DOUBLE:
            return []
        if borde in (NOBORDER, RESIZING | DOUBLE, 0):
            return [{NOBORDER: "NOBORDER", RESIZING | DOUBLE: "RESIZING", 0: "THINFRAME"}[borde]]
        raise self.NoSoportado(f"borde del formulario FCT {k}: {borde:#x}")

    def mascara_de_columna(self, k, fob, tipo_dato, b0=0):
        """LIKEVAR copia de la variable su tipo y, si es de una columna, la máscara y el UPSHIFT del repositorio (del
        .crf). Una máscara copiada de una variable que no sale escrita `as tabla.columna` (+0x32 ≠ 0xFFFF: MONEY o
        DECIMAL de columna se leen como el tipo a secas) dice que era de una columna que el .omd no nombra: el escritor
        la busca en el .crf (`tipo_de_columna`); si no la ha sacado así, no se puede escribir igual. Un UPSHIFT con
        LIKEVAR en un TEXT o un VAR de página no se puede escribir (no compila): si la variable no es de columna, no
        hay de dónde copiarlo."""
        if tipo_dato >> 20 and self.m.u32("FOB", fob, 0x30) >> 16 != 0xFFFF and fob not in self.fobs_de_columna:
            raise self.NoSoportado(f"control {k}: LIKEVAR con la máscara {tipo_dato >> 20} de una columna que el .omd no nombra")
        if b0 & UPSHIFT and self.m.u32("FOB", fob, 0x30) >> 16 != 0xFFFF:
            raise self.NoSoportado(f"control {k}: LIKEVAR con UPSHIFT de una variable que no es de columna")

    def datatype(self, k, tipo_dato) -> str:
        """DATATYPE de un control: el tipo en el u16 alto de +0x20 (MASK n en su nibble alto) y el largo en +0x40."""
        dato, mascara = (tipo_dato >> 16) & 0xF, tipo_dato >> 20
        if dato not in DATOS or mascara > 0xF:
            raise self.NoSoportado(f"DATATYPE {tipo_dato >> 16:#x}")
        largo = self.u32(k, 0x40) & 0xFFFF  # CHAR(n): n; DECIMAL(p,s): p | s << 8 (DECIMAL a secas: 0xFF00)
        if DATOS[dato] == "CHAR":
            tipo_txt = f"CHAR({largo})" if largo else "CHAR"
        elif DATOS[dato] == "DECIMAL":
            tipo_txt = "DECIMAL" if largo == 0xFF00 else f"DECIMAL({largo & 0xFF},{struct.unpack('b', bytes([largo >> 8]))[0]})"
        elif largo and DATOS[dato] in ("SMALLINT", "INTEGER"):  # SMALLINT(6): el ancho (DATE(n) no compila)
            tipo_txt = f"{DATOS[dato]}({largo})"
        elif largo:
            raise self.NoSoportado(f"DATATYPE {DATOS[dato]} con +0x40 {largo:#x} en el control {k}")
        else:
            tipo_txt = DATOS[dato]
        return f"DATATYPE {tipo_txt}" + (f" MASK {mascara}" if mascara else "")

    def nombre_menu(self, k) -> str:
        if self.u32(k, 0x24) != 0xFFFF:  # siempre así en el kit [sin descifrar]
            raise self.NoSoportado(f"control MENU FCT {k}: +0x24 {self.u32(k, 0x24):#x}")
        raiz = self.ref(k, 0x68, 0x0A)
        # +0x40: cuántas opciones tiene la raíz (un submenú cuenta como una); lo calcula el compilador
        opciones, o = 0, self.m.refa("MOP", raiz, 0x40, 0x0A) if raiz is not None else None
        while o is not None and opciones < 10000:
            opciones, o = opciones + 1, self.m.refa("MOP", o, 0x08, 0x0A)
        if self.u32(k, 0x40) & 0xFFFF != opciones:
            raise self.NoSoportado(f"control MENU FCT {k}: +0x40 {self.u32(k, 0x40):#x} con {opciones} opciones")
        mnu = next((i for i in range(self.m.s["MNU"].n) if self.m.refa("MNU", i, 0x10, 0x0A) == raiz), None)
        fob = next((f for f in range(self.m.s["FOB"].n) if (c := self.m.refa("FOB", f, 0x18, CLA)) is not None
                    and self.m.refa("CLA", c, 0x40, 0x09) == mnu), None) if mnu is not None else None
        if fob is None:
            raise self.NoSoportado(f"control MENU FCT {k} sin su menú")
        return self.m.texto_ide(self.m.u32("FOB", fob, 0x10))

    def tab_con_label(self, k) -> bool:
        """Un TAB con las páginas en el LABEL (`LABEL "a|b"`, sin NUMBER ni TAB LABEL: ALMAFAC2 FRMTMPL) lleva 0xFFFF
        en el u16 alto del icono de todas sus páginas (0xFFFE, sin icono, con TAB LABEL). Batería `tabs.py`: 6 de 6.
        Con NUMBER además (`LABEL "a|b"` y `NUMBER 2`) también, pero el ancho que calcula el compilador es el de una
        página sin texto; no se distingue, y sale sin NUMBER. Mezcladas, NoSoportado (en pestanas)."""
        i = self.ref(k, 0x68, SVL)
        binario = self.svl.get(i * 4) if i is not None else None
        numero = self.u32(k, 0x40) & 0xFFFF
        if binario is None or not binario.binario or len(binario.datos) < 12 + 12 * numero or not numero:
            return False
        return all(struct.unpack_from("<I", binario.datos, 12 + 12 * n + 4)[0] >> 16 == 0xFFFF for n in range(numero))

    def pestanas(self, k, b0) -> list[str]:
        """Atributos de un TAB: LOWTAB, FIXED WIDTH (su n no se guarda: 1, 2, 3 y 5 dan los mismos
        bytes), VERTICAL, ICON FILE, NUMBER y una línea `TAB LABEL "x" [ICON n]` por página: las
        etiquetas, unidas con |, en el texto de +0x48; el binario de +0x68 lleva por página tres
        u32 (ancho calculado; icono: u16 alto n − 1, 0xFFFE sin él; un valor calculado)."""
        a = [n for bit, n in ((TAB_VERTICAL, "VERTICAL"), (TAB_LOWTAB, "LOWTAB"), (TAB_FIXED, "FIXED WIDTH 1")) if b0 & bit]
        if not b0 & LABEL:
            raise self.NoSoportado(f"TAB FCT {k} sin etiquetas")
        etiquetas = self.texto_svl(k, 0x48).split("|")
        numero = self.u32(k, 0x40) & 0xFFFF
        i = self.ref(k, 0x68, SVL)
        binario = self.svl.get(i * 4) if i is not None else None
        if binario is None or not binario.binario or len(etiquetas) != numero or len(binario.datos) < 12 + 12 * numero:
            raise self.NoSoportado(f"TAB FCT {k}: {numero} páginas y {etiquetas}")
        if self.tab_con_label(k):  # las páginas en el LABEL (lo escribe atributos)
            return a
        a.append(f"NUMBER {numero}")
        for n, texto in enumerate(etiquetas):
            ancho, icono, _ = struct.unpack_from("<3I", binario.datos, 12 + 12 * n)
            if icono >> 16 == 0xFFFF:  # el u16 bajo lo calcula el compilador (2 en un TAB pequeño) [hipótesis]
                raise self.NoSoportado(f"TAB FCT {k}: icono {icono:#x} de la página {n + 1}")
            a.append("\tTAB LABEL " + self.cadena(texto) + (f" ICON {(icono >> 16) + 1}" if icono >> 16 != 0xFFFE else ""))
        return a

    def grupo(self, k, tipo, b0, tipo_dato, borde=None) -> tuple[list[str], list[str]]:
        """BUTTONGROUP y BOXGROUP: [ICON FILE "x" [CENTER] [VERTICAL]], [CLICKTYPE RADIO|MANUAL] (CHECK, el de serie, no
        deja huella), NUMBER n ROWS|COLUMNS m, [BORDER HILIGHT|BLACK / NOBORDER] y una línea por elemento. Las etiquetas, unidas con |, en
        el texto de +0x48 (como en un TAB); NUMBER en +0x40. El binario de +0x68: u16 tamaño, u16 índice en ICO (0xFFFF
        sin icono), u16 ancho y alto del control, u16 ancho y alto de un elemento (los calcula el compilador), u16 m
        (en BOXGROUP, y un u16 a 0); por elemento, u16 icono n − 1 (0xFFFE sin él) y un u16 a 0, y en BOXGROUP un u32
        con su BACKGROUND (0x80000000 sin él). Devuelve el icono y, aparte, de CLICKTYPE a los elementos (van al final).
        En una página, `borde` escribe el de los elementos, y un BOX solo y sin etiqueta no deja ni LABEL ni texto."""
        caja = tipo == "BOXGROUP"
        cabeza, paso = (16, 8) if caja else (14, 4)
        numero = self.u32(k, 0x40) & 0xFFFF
        etiquetas = self.texto_svl(k, 0x48).split("|") if b0 & LABEL else [""] if borde and numero == 1 else []
        i = self.ref(k, 0x68, SVL)
        binario = self.svl.get(i * 4) if i is not None else None
        datos = binario.datos if binario is not None and binario.binario else b""
        _, _, ancho, alto = struct.unpack_from("<4H", self.m.rec(self.SECCION, k), 0x38)
        if (len(etiquetas) != numero or len(datos) < cabeza + paso * numero
                or struct.unpack_from("<3H", datos, 0) != (cabeza + paso * numero, struct.unpack_from("<H", datos, 2)[0], ancho)
                or struct.unpack_from("<H", datos, 6)[0] != alto or caja and struct.unpack_from("<H", datos, 0x0E)[0]):
            raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: {numero} elementos y {etiquetas}")
        fichero, filas = struct.unpack_from("<H", datos, 2)[0], struct.unpack_from("<H", datos, 0x0C)[0]
        b44 = self.u32(k, 0x44)
        if b44 & ALLOWDRAG and b44 & ALLOWDRAG != ALLOWDRAG:
            raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: ALLOWDRAG a medias ({b44 & ALLOWDRAG:#x})")
        arrastre = ["ALLOWDRAG"] if b44 & ALLOWDRAG else []
        # Con FRAMEAUTOSIZE, el orden es AUTOSIZE, ICON FILE, FRAMEAUTOSIZE y ALLOWDRAG (en otro no compila: batería
        # controles.py, vw_); sin él, ALLOWDRAG va delante del icono y AUTOSIZE más tarde (en atributos()).
        marco = b0 & FRAMEAUTOSIZE and self.SECCION == "FCT"
        a = ["AUTOSIZE"] if marco and b0 & AUTOSIZE else [] if marco else arrastre
        if self.u32(k, 0x70) != (fichero if b0 & ICON else 0):
            raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: +0x70 {self.u32(k, 0x70):#x} con el fichero {fichero:#x}")
        if b0 & ICON:
            if fichero >= self.m.s["ICO"].n:
                raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: icono {fichero:#x} fuera de ICO")
            a.append(f'ICON FILE "{self.m.rec("ICO", fichero)[2:].split(b"\0")[0].decode("cp1252")}"'
                     + ("" if b0 & ICONO_IZQ else " CENTER") + (" VERTICAL" if b0 & ICONO_VERTICAL else ""))
        elif fichero != 0xFFFF or b0 & ICONO_VERTICAL or not b0 & ICONO_IZQ:  # sin icono, 0x100 puesto
            raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: bits de icono {b0 & (ICONO_IZQ | ICONO_VERTICAL):#x} sin ICON")
        if marco:
            a += ["FRAMEAUTOSIZE"] + arrastre
        elementos = []
        if b0 & G_RADIO and b0 & G_MANUAL:
            raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: CLICKTYPE RADIO y MANUAL juntos")
        if b0 & (G_RADIO | G_MANUAL):
            elementos.append("CLICKTYPE " + ("RADIO" if b0 & G_RADIO else "MANUAL"))
        elementos.append(f"NUMBER {numero} {'COLUMNS' if b0 & G_COLUMNS else 'ROWS'} {filas}")
        if tipo_dato >> 16 and borde:  # en una página, con los bits del borde de página
            elementos.append(borde(tipo_dato >> 16))
        elif tipo_dato >> 16:  # el borde de los elementos: u16 alto de +0x20, como en un BUTTON
            if tipo_dato >> 16 not in BORDES_GRUPO[tipo]:
                raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: borde {tipo_dato >> 16:#x}")
            elementos.append(BORDES_GRUPO[tipo][tipo_dato >> 16])
        for n, texto in enumerate(etiquetas):
            p = cabeza + paso * n
            icono, cero = struct.unpack_from("<2H", datos, p)
            color = struct.unpack_from("<I", datos, p + 4)[0] if caja else SIN_COLOR
            if cero or icono != 0xFFFE and not b0 & ICON or icono != 0xFFFE and color != SIN_COLOR:
                raise self.NoSoportado(f"{tipo} {self.SECCION} {k}: elemento {n + 1} con {icono:#x}, {cero:#x} y {color:#x}")
            linea = "\tBOX" if caja else "\tBUTTON"
            if texto or not caja and icono == 0xFFFE:  # un botón sin nada: LABEL "" (BOX a secas sí compila)
                linea += " LABEL " + self.cadena(texto)
            if icono != 0xFFFE:
                linea += f" ICON {icono + 1}"
            if color != SIN_COLOR:
                linea += f" BACKGROUND {self.color(color)}"
            elementos.append(linea)
        return a, elementos

    def icono_de_lista(self, k) -> str:
        """El ICON FILE de una lista: el u16 de +0x18 de su binario de SVL (+0x68) es su índice en ICO."""
        i = self.ref(k, 0x68, SVL)
        binario = self.svl.get(i * 4) if i is not None else None
        if binario is None or not binario.binario or len(binario.datos) < 0x1C:
            raise self.NoSoportado(f"lista FCT {k} sin su registro binario de SVL")
        icono, alto = struct.unpack_from("<HH", binario.datos, 0x18)
        if alto != 0xFFFF or icono >= self.m.s["ICO"].n:
            raise self.NoSoportado(f"icono {icono:#x} {alto:#x} de la lista FCT {k}")
        return self.m.rec("ICO", icono)[2:].split(b"\0")[0].decode("cp1252")

    def lista(self, k, tipo, b0, b44) -> list[str]:
        """Atributos propios de LIST, DROPLIST y DROPEDIT. Sus columnas (el registro binario
        de SVL) las calcula el compilador a partir de estos y del tamaño del control."""
        a8 = self.u32(k, 0xA8)
        if self.u32(k, 0x70) != (0 if tipo == "LIST" else 0xFFFFFFFF):
            raise self.NoSoportado(f"+0x70 {self.u32(k, 0x70):#x} en la lista FCT {k}")
        # El icono va en el binario de SVL de la lista (+0x68): u16 en +0x18 = índice en ICO
        # (los recursos de icono), 0xFFFF sin icono; el u16 de +0x1A, siempre 0xFFFF.
        i = self.ref(k, 0x68, SVL)
        binario = self.svl.get(i * 4) if i is not None else None
        if binario is None or not binario.binario or len(binario.datos) < 0x1C:
            raise self.NoSoportado(f"lista FCT {k} sin su registro binario de SVL")
        icono, alto = struct.unpack_from("<HH", binario.datos, 0x18)
        if alto != 0xFFFF or bool(a8 & ICONO) != (icono != 0xFFFF) or icono != 0xFFFF and icono >= self.m.s["ICO"].n:
            raise self.NoSoportado(f"icono {icono:#x} {alto:#x} de la lista FCT {k}")
        columnas, cursor = self.u32(k, 0xB0) & 0xFFFF, self.u32(k, 0xB0) >> 16
        if a8 & ~(LISTCOLS | MULTIPLE | ICONO | SORTONCLICK | ORDENADA) or cursor not in CURSORES:
            raise self.NoSoportado(f"lista FCT {k}: +0xA8 {a8:#x}, CURSORTYPE {cursor}")
        a = []
        if tipo == "LIST":
            if a8 & ICONO:
                a.append(f'ICON FILE "{self.icono_de_lista(k)}"')
            a += [n for bit, n in ((ALLOWDRAG, "ALLOWDRAG"), (ALLOWDROP, "ALLOWDROP")) if b44 & bit == bit]
            if b44 & ALLOWDRAG not in (0, ALLOWDRAG):
                raise self.NoSoportado(f"ALLOWDRAG a medias en la lista FCT {k}")
            if a8 & ORDENADA:
                a.append("SORT")
            if a8 & SORTONCLICK:
                a.append("SORTONCLICK")
            if a8 & LISTCOLS:
                a.append(f"LISTTYPE LISTCOLS {columnas}")
            elif columnas != 1:
                raise self.NoSoportado(f"lista FCT {k} con {columnas} columnas sin LISTCOLS")
            if CURSORES[cursor]:
                fichero = f" {self.cadena(self.texto_svl(k, 0x58))}" if cursor == 1 and b0 & TAGS else ""
                a.append(f"CURSORTYPE {CURSORES[cursor]}{fichero}")
            if a8 & MULTIPLE == MULTIPLE:
                a.append("SELECTTYPE MULTIPLE")
            elif a8 & SIMPLE:
                a.append("SELECTTYPE SIMPLE")
            if b0 & (SCROLL_H | SCROLL_V):
                a.append("SCROLL" + (" VERTICAL" if b0 & SCROLL_V else "") + (" HORIZONTAL" if b0 & SCROLL_H else ""))
        else:  # DROPLIST y DROPEDIT (batería listas.py, segunda tanda), en el orden de los fuentes del kit
            if not a8 & SIMPLE or cursor == 1 and b0 & TAGS:  # el ICON FILE, delante de DATATYPE  # SIMPLE: el de serie; FILE con TAGS: ¿su fichero?
                raise self.NoSoportado(f"{tipo} FCT {k} con atributos de lista sin descifrar")
            if a8 & SORTONCLICK:  # delante de SHOW n LINES (detrás no compila: batería fct.py, so3_)
                a.append("SORTONCLICK")
            if lineas := self.u32(k, 0x60) >> 16:
                a.append(f"SHOW {lineas} LINES")
            if a8 & LISTCOLS:  # con COLUMNS n detrás, los mismos bytes
                a.append(f"LISTTYPE LISTCOLS {columnas}")
            elif columnas != 1:
                a.append(f"COLUMNS {columnas}")
            if CURSORES[cursor]:
                a.append(f"CURSORTYPE {CURSORES[cursor]}")
            if a8 & MULTIPLE == MULTIPLE:
                a.append("SELECTTYPE MULTIPLE")
            if b0 & (SCROLL_H | SCROLL_V):
                a.append("SCROLL" + (" VERTICAL" if b0 & SCROLL_V else "") + (" HORIZONTAL" if b0 & SCROLL_H else ""))
        return a

    def _no(self, que):
        raise self.NoSoportado(que)

    def comando(self, cmd: int) -> str:
        if cmd in COMANDOS:
            return COMANDOS[cmd]
        if 1 <= cmd <= self.m.s["CMD"].n:
            return self.m.rec("CMD", cmd - 1)[2:].split(b"\0")[0].decode("cp1252")
        raise self.NoSoportado(f"comando {cmd:#x}")

    def hijos(self, k):
        salida, h = [], self.ref(k, 0x10, FCT)
        while h is not None:
            salida.append(h)
            h = self.ref(h, 0x08, FCT)
        return salida

    def control(self, k, n: int, focus) -> list[str]:
        s = "\t" * n
        tipo = TIPOS.get(self.u32(k, 0x20) & 0xFFFF)
        nombre = self.nombre(k)
        salida = [s + (f"CONTROL {nombre} AS {tipo}" if nombre else f"CONTROL AS {tipo}")]
        salida += [s + "\t" + x for x in self.atributos(k, False, focus)]
        hijos = self.hijos(k)
        if hijos or tipo == "TAB":  # un TAB lleva siempre su BEGIN … END
            salida.append(s + "BEGIN")
            for h in hijos:
                salida += self.control(h, n + 1, focus)
            salida.append(s + "END")
        return salida

    def formulario(self, raiz: int, n: int) -> list[str]:
        s = "\t" * n
        focus = self.ref(raiz, 0x58, FCT)
        salida = [s + "INTERFACE", *(s + "\t" + x for x in self.atributos(raiz, True, focus)), s + "BEGIN"]
        for h in self.hijos(raiz):
            salida += self.control(h, n + 1, focus)
        return salida + [s + "END"]


# --- páginas (`X is Page`, para imprimir): PAG hace de FOR y PCT de FCT, con sus propios tipos
TIPOS_PAG = {3: "CHECK", 7: "TEXT", 8: "BOX", 9: "SEPARATOR", 0x0E: "BOXGROUP", 0x0F: "BITMAP", 0x11: "VAR", 0x15: "GROUP", 0x19: "BANDGROUP"}
PCT = 0x11
USEPRINTMARGINS = 0x100
BORDE_TODO = 0xF0                 # BORDER ALL: los cuatro lados
# BORDER [UPSHADOW|DOWNSHADOW] [DOUBLE] [ALL | TOP BOTTOM LEFT RIGHT] de los controles de página (byte bajo de +0x00)
P_UPSHADOW, P_DOWNSHADOW, P_DOUBLE = 0x01, 0x02, 0x04
LADOS_PAG = ((0x40, "TOP"), (0x80, "BOTTOM"), (0x10, "LEFT"), (0x20, "RIGHT"))
BORDE_PAG = P_UPSHADOW | P_DOWNSHADOW | P_DOUBLE | BORDE_TODO
SEP_VERTICAL, SEP_GRUESA, SEP_DOBLE, SEP_SOLIDA = 0x1000, 0x04, 0x100, 0x200  # VERTICAL, THICKLINE, DOUBLELINE, SOLID
GRUPO_LINEAS, GRUPO_BYCOLS = 0x200, 0x400  # AS LINES; BYCOLS (ninguno de los dos: REPEAT n a secas)
REJILLA_V, REJILLA_H = 0x4000, 0x2000      # GRID VERTICAL, GRID HORIZONTAL
GRUPO_REJILLA = REJILLA_V | REJILLA_H
BASE_44_PAG, GRUPO_44 = 0x80000000, 0x40000000  # sin GRUPO_44, el GROUP lleva FIXED (detrás de REPEAT; samples BOOLOP)
# Batería paginas.py, sexta tanda: AUTOSIZE de un GROUP (delante de AS LINES y REPEAT), STRETCH de un BITMAP (detrás del
# borde), WRAP de un TEXT (+0x44, entre MULTILINE y TAGS) y CURRENT PAGE n de un BOX (n − 1 en el u16 alto de +0x60;
# tras NOLABEL y delante del borde). FIXED con BYCOLS no compila.
P_STRETCH = 0x100
P_VERTICAL_IZQ, P_VERTICAL_DER = 0x20000, 0x10000  # VERTICALTEXTLEFT y VERTICALTEXTRIGHT de un TEXT, detrás de TAGS
# BOXGROUP de página (batería paginas.py, séptima tanda; samples LISTADOCAJA): como el de formulario (grupo()), pero el
# BORDER de detrás de NUMBER es el de los elementos, con los bits del borde de página en el u16 alto de +0x20; el de
# delante, el del control. NOBORDER, CLICKTYPE y LABEL no compilan.
LEIDOS_PAG = {0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x3C, 0x40, 0x44, 0x48, 0x50, 0x54, 0x58, 0x60, 0x70, 0x78, 0x88}  # +0x08: el hermano siguiente (lo recorre hijos)


class Pagina(Interfaz):
    """Las páginas: como un formulario, pero con PCT y otros tipos de control. Solo lo visto
    en la batería lab/bateria/paginas.py; lo demás, NoSoportado."""
    SECCION = "PCT"

    def u32(self, k, off):
        return self.m.u32("PCT", k, off)

    def hijos(self, k):
        salida, h = [], self.ref(k, 0x10, PCT)
        while h is not None:
            salida.append(h)
            h = self.ref(h, 0x08, PCT)
        return salida

    def raiz(self, k, n: int) -> list[str]:
        s = "\t" * n
        b0 = self.u32(k, 0x00)
        if b0 & ~(BASE | USEPRINTMARGINS) or self.u32(k, 0x44) != BASE_44_PAG or any(
                self.u32(k, o) for o in range(0, 208, 4) if o not in (0x00, 0x10, 0x28, 0x3C, 0x44, 0x50, 0x54, 0x68, 0x80, 0x88)) \
                or self.u32(k, 0x50) != SIN_COLOR or self.u32(k, 0x54) != SIN_COLOR:
            raise self.NoSoportado(f"página PCT {k} con algo sin descifrar")
        ancho, alto = struct.unpack_from("<HH", self.m.rec("PCT", k), 0x3C)
        m = self.u32(k, 0x80)  # MARGIN a b c d: un byte por margen, en unidades de 3, d en el byte 0
        a = [f"SIZE {ancho} {alto}"] + (["USEPRINTMARGINS"] if b0 & USEPRINTMARGINS else [])
        a.append(f"MARGIN {3 * (m >> 24)} {3 * ((m >> 16) & 0xFF)} {3 * ((m >> 8) & 0xFF)} {3 * (m & 0xFF)}")
        salida = [s + "INTERFACE", *(s + "\t" + x for x in a), s + "BEGIN"]
        for h in self.hijos(k):
            salida += self.control_pag(h, n + 1)
        return salida + [s + "END"]

    def borde_pag(self, k, b0) -> str:
        sombra = b0 & (P_UPSHADOW | P_DOWNSHADOW)
        if sombra == P_UPSHADOW | P_DOWNSHADOW or sombra and b0 & P_DOUBLE:  # no compilan
            raise self.NoSoportado(f"PCT {k}: borde {b0 & BORDE_PAG:#x}")
        partes = (["UPSHADOW"] if sombra == P_UPSHADOW else ["DOWNSHADOW"] if sombra else []) + (["DOUBLE"] if b0 & P_DOUBLE else [])
        if b0 & BORDE_TODO == BORDE_TODO:
            partes.append("ALL")
        else:
            partes += [n_ for bit, n_ in LADOS_PAG if b0 & bit]
        return "BORDER " + " ".join(partes)

    def control_pag(self, k, n: int) -> list[str]:
        s = "\t" * n
        tipo_dato = self.u32(k, 0x20)
        tipo = TIPOS_PAG.get(tipo_dato & 0xFFFF)
        if tipo is None:
            raise self.NoSoportado(f"control de página de tipo {tipo_dato & 0xFFFF:#x}")
        b0, b44 = self.u32(k, 0x00), self.u32(k, 0x44)
        propios = {"TEXT": TAGS | BOLD | BORDE_PAG | MULTILINE | P_VERTICAL_IZQ | P_VERTICAL_DER, "VAR": NOLABEL | LABEL | BOLD | LIKEVAR | BORDE_PAG,
                   "CHECK": NOLABEL | LABEL | BORDE_PAG, "BITMAP": NOLABEL | BORDE_PAG | P_STRETCH,
                   "SEPARATOR": SEP_VERTICAL | SEP_GRUESA | SEP_DOBLE | SEP_SOLIDA,
                   "GROUP": GRUPO_LINEAS | GRUPO_BYCOLS | BORDE_PAG | GRUPO_REJILLA | NOLABEL | AUTOSIZE | BOLD,
                   "BOX": BORDE_PAG | NOLABEL | ICON | ICONO_IZQ | ICONO_VERTICAL,
                   "BANDGROUP": BORDE_PAG | NOLABEL | AUTOSIZE,
                   "BOXGROUP": BORDE_PAG | NOLABEL | LABEL | G_COLUMNS | ICONO_IZQ | FRAMEAUTOSIZE | AUTOSIZE | BOLD}[tipo]
        if tipo == "VAR" and b0 & LIKEVAR:
            propios |= UPSHIFT  # copiado de la columna (UPSHIFT escrito no compila en un VAR de página)
        base44 = BASE_44_PAG | (b44 & GRUPO_44 if tipo == "GROUP" else 0)
        wrap = WRAP if tipo == "TEXT" else 0
        if b0 & ~(BASE | propios) or b44 & ~(base44 | wrap | CENTER | RIGHT | A_TOP | A_BOTTOM | A_LEFT | A_RIGHT) or b44 & base44 != base44:
            raise self.NoSoportado(f"{tipo} de página PCT {k}: bits {b0:#x} {b44:#x}")
        leidos = LEIDOS_PAG | ({0x68} if tipo == "BOXGROUP" else set())  # +0x68: el binario de grupo()
        for o in range(0, 208, 4):
            if o not in leidos and self.u32(k, o):
                raise self.NoSoportado(f"{tipo} de página PCT {k}: +{o:#04x} = {self.u32(k, o):#x}")
        if tipo_dato >> 16 and tipo not in ("VAR", "BOXGROUP") or self.u32(k, 0x40) & 0xFFFF and tipo not in ("GROUP", "VAR", "BOXGROUP") \
                or tipo != "BOX" and self.u32(k, 0x70) \
                or self.u32(k, 0x60) >> 16 and tipo != "BOX" \
                or (r := self.ref(k, 0x88, ECL)) is None or self.m.ecl[r] != "SimplePageControl":
            raise self.NoSoportado(f"{tipo} de página PCT {k}: campos sin descifrar")
        icono = self.icono(k, "BOX", b0) if tipo == "BOX" else None  # como el de un BOX de formulario
        elementos = self.grupo(k, tipo, b0, tipo_dato, borde=lambda b: self.borde_pag(k, b))[1] if tipo == "BOXGROUP" else []
        nombre = self.nombre(k)
        x, y, w, h = struct.unpack_from("<4H", self.m.rec("PCT", k), 0x38)
        a = [f"POSITION {x} {y} {w} {h}"]
        if (c := self.u32(k, 0x54)) != SIN_COLOR:
            a.append(f"FOREGROUND {self.color(c)}")
        if (c := self.u32(k, 0x50)) != SIN_COLOR:
            a.append(f"BACKGROUND {self.color(c)}")
        if b0 & BOLD:
            a.append("BOLD")
        if f := self.fuente(k):
            a.append(f)
        # Orden (lo que no, no compila): NOLABEL, ATTACH (delante de NOLABEL, en un BANDGROUP, no), PAGE (delante de
        # ATTACH, no) y LABEL (delante de PAGE, no)
        if b0 & NOLABEL:
            a.append("NOLABEL")
        partes = [n_ for bit, n_ in ((A_LEFT, "LEFT"), (A_TOP, "TOP"), (A_RIGHT, "RIGHT"), (A_BOTTOM, "BOTTOM")) if b44 & bit]
        if partes:
            a.append("ATTACH ALL" if len(partes) == 4 else "ATTACH " + " ".join(partes))
        if self.u32(k, 0x60) & 0xFFFF:  # PAGE n: n − 1 (el u16 alto, CURRENT PAGE de un BOX)
            a.append(f"PAGE {(self.u32(k, 0x60) & 0xFFFF) + 1}")
        if b0 & LABEL and not elementos:  # en un BOXGROUP, el de sus elementos
            a.append("LABEL " + self.cadena(self.texto_svl(k, 0x48)))
        elif self.u32(k, 0x48) and not elementos:
            raise self.NoSoportado(f"PCT {k}: +0x48 sin LABEL")
        if actual := self.u32(k, 0x60) >> 16:  # CURRENT PAGE de un BOX: con ATTACH, PAGE o LABEL no se ha visto
            if partes or self.u32(k, 0x60) & 0xFFFF or b0 & LABEL:
                raise self.NoSoportado(f"BOX PCT {k}: CURRENT PAGE con ATTACH, PAGE o LABEL")
            a.append(f"CURRENT PAGE {actual + 1}")
        if tipo != "SEPARATOR" and b0 & BORDE_PAG:
            a.append(self.borde_pag(k, b0))
        if icono:
            a.append(icono)
        if tipo == "BITMAP" and b0 & P_STRETCH:
            a.append("STRETCH")
        if tipo == "BANDGROUP" and b0 & AUTOSIZE:
            a.append("AUTOSIZE")
        if tipo == "BOXGROUP" and b0 & AUTOSIZE:  # detrás de NOLABEL y delante de FRAMEAUTOSIZE (batería paginas.py, pvw_)
            if partes or self.u32(k, 0x60) & 0xFFFF or b0 & BORDE_PAG:  # con ATTACH, PAGE o el borde no se ha visto
                raise self.NoSoportado(f"BOXGROUP PCT {k}: AUTOSIZE con ATTACH, PAGE o BORDER")
            a.append("AUTOSIZE")
        if tipo == "BOXGROUP" and b0 & FRAMEAUTOSIZE:  # detrás de NOLABEL, ATTACH, PAGE y el borde del control
            a.append("FRAMEAUTOSIZE")
        if tipo == "GROUP":
            fijo = not b44 & GRUPO_44
            if fijo and b0 & GRUPO_BYCOLS or b0 & AUTOSIZE and b0 & GRUPO_REJILLA:
                raise self.NoSoportado(f"GROUP PCT {k}: FIXED con BYCOLS o AUTOSIZE con GRID")
            if b0 & AUTOSIZE:
                a.append("AUTOSIZE")
            if b0 & GRUPO_REJILLA:
                a.append("GRID" + (" VERTICAL" if b0 & REJILLA_V else "") + (" HORIZONTAL" if b0 & REJILLA_H else ""))
            if b0 & GRUPO_LINEAS and b0 & GRUPO_BYCOLS:
                raise self.NoSoportado(f"GROUP PCT {k}: AS LINES y BYCOLS a la vez")
            repetir = f"REPEAT {self.u32(k, 0x40) & 0xFFFF}"
            a += ["AS LINES", repetir] if b0 & GRUPO_LINEAS else [repetir, "BYCOLS"] if b0 & GRUPO_BYCOLS else [repetir]
            if fijo:
                a.append("FIXED")
        if tipo == "SEPARATOR":
            a += [n_ for bit, n_ in ((SEP_VERTICAL, "VERTICAL"), (SEP_GRUESA, "THICKLINE"), (SEP_DOBLE, "DOUBLELINE"),
                                     (SEP_SOLIDA, "SOLID")) if b0 & bit]
        if elementos and self.u32(k, 0x78):
            raise self.NoSoportado(f"BOXGROUP PCT {k} con VARIABLE")
        if (v := self.ref(k, 0x78, FOB)) is not None:
            a.append(f"VARIABLE {self.m.texto_ide(self.m.u32('FOB', v, 0x10))}")
        elif self.u32(k, 0x78):
            raise self.NoSoportado(f"PCT {k}: +0x78")
        likevar = tipo == "VAR" and b0 & LIKEVAR  # en GROUP, 0x4000 es parte de GRID
        if likevar:  # el tipo (+0x20, +0x40) y la alineación los copia el compilador de la variable: no se escriben
            if v is None:
                raise self.NoSoportado(f"VAR PCT {k}: LIKEVAR sin variable")
            self.mascara_de_columna(k, v, tipo_dato, b0)
            a.append("LIKEVAR")
        elif b44 & (CENTER | RIGHT):
            a.append("ALIGNMENT " + ("CENTER" if b44 & CENTER else "RIGHT"))
        if tipo == "TEXT" and b0 & MULTILINE:
            a.append("MULTILINE")
        if tipo == "TEXT" and b44 & WRAP:
            a.append("WRAP")
        if tipo == "VAR" and not likevar:
            a.append(self.datatype(k, tipo_dato))
        if b0 & TAGS:
            a.append("TAGS " + " ".join(self.cadena(t) for t in self.texto_svl(k, 0x58).split("|")))
        elif self.u32(k, 0x58):
            raise self.NoSoportado(f"PCT {k}: +0x58 sin TAGS")
        if tipo == "TEXT" and b0 & (P_VERTICAL_IZQ | P_VERTICAL_DER):
            if b0 & P_VERTICAL_IZQ and b0 & P_VERTICAL_DER:
                raise self.NoSoportado(f"TEXT PCT {k}: VERTICALTEXTLEFT y VERTICALTEXTRIGHT")
            a.append("VERTICALTEXTLEFT" if b0 & P_VERTICAL_IZQ else "VERTICALTEXTRIGHT")
        a += elementos
        salida = [s + (f"CONTROL {nombre} AS {tipo}" if nombre else f"CONTROL AS {tipo}"), *(s + "\t" + x for x in a)]
        hijos = self.hijos(k)
        if hijos:
            salida.append(s + "BEGIN")
            for h in hijos:
                salida += self.control_pag(h, n + 1)
            salida.append(s + "END")
        return salida

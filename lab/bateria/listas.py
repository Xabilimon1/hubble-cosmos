"""Batería de listas (LIST, DROPLIST, DROPEDIT): como formularios.py, un atributo por
programa sobre una lista base. Uso: python3 -I listas.py <dir salida> <huecos.txt> [desde]
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control

P = {}
P["l_base"] = form(controles=control("LIST", "", nombre="l", posicion="10 10 100 50"))
LISTA = [  # en el orden de los fuentes del kit
    'ICON FILE "a.ico"', "LISTTYPE LISTCOLS 1", "LISTTYPE LISTCOLS 2", "LISTTYPE LISTCOLS 3", "CURSORTYPE SQL",
    "CURSORTYPE TREEVIEW", "CURSORTYPE FILE", "SELECTTYPE SIMPLE", "SELECTTYPE MULTIPLE", "SCROLL VERTICAL",
    "SCROLL VERTICAL HORIZONTAL", "SORTONCLICK", "BORDER DOUBLE DOWN", 'LABEL "Lista"', "ATTACH ALL",
]
for a in LISTA:
    clave = "l_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_")
    P[clave] = form(controles=control("LIST", a, nombre="l", posicion="10 10 100 50"))
P["l_listcols2_sql_simple"] = form(controles=control("LIST", "LISTTYPE LISTCOLS 2\nCURSORTYPE SQL\nSELECTTYPE SIMPLE", nombre="l", posicion="10 10 100 50"))
for t in ("DROPLIST", "DROPEDIT"):
    dt = "DATATYPE CHAR\n" if t == "DROPEDIT" else ""
    base = f"d_{t.lower()}"
    P[base] = form(controles=control(t, dt.strip(), nombre="d"))
    for a in ["SHOW 8 LINES", "SHOW 3 LINES", "COLUMNS 1", "COLUMNS 2", "SELECTTYPE SIMPLE", 'TAGS "a" "b"', "AUTOSIZE"]:
        clave = base + "_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_")
        antes = "AUTOSIZE\n" if a == "AUTOSIZE" else ""
        despues = "" if a == "AUTOSIZE" else a
        P[clave] = form(controles=control(t, (antes + dt + despues).strip(), nombre="d"))
# --- segunda tanda (al final, para no mover los huecos): los atributos de lista en DROPLIST y DROPEDIT (STOCKMDI
# customers/items/suppliers, prjbmapsdll EjBmapsdll), uno a uno y como en los fuentes del kit
for t in ("DROPLIST", "DROPEDIT"):
    dt = "DATATYPE CHAR\n" if t == "DROPEDIT" else ""
    base = f"d_{t.lower()}"
    for a in ["LISTTYPE LISTCOLS 1", "LISTTYPE LISTCOLS 2", "CURSORTYPE SQL", "CURSORTYPE FILE", "CURSORTYPE TREEVIEW",
              "SELECTTYPE MULTIPLE", "SCROLL VERTICAL", "SCROLL HORIZONTAL", "SCROLL VERTICAL HORIZONTAL", "SORTONCLICK",
              "SHOW 8 LINES\nLISTTYPE LISTCOLS 2\nCURSORTYPE SQL\nSELECTTYPE SIMPLE\nSCROLL VERTICAL",
              'TAGS "a" "b"\nSHOW 10 LINES\nCOLUMNS 1\nSELECTTYPE SIMPLE\nSCROLL VERTICAL',
              "COLUMNS 2\nSCROLL VERTICAL", "LISTTYPE LISTCOLS 2\nCOLUMNS 2"]:
        clave = base + "2_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_")
        P[clave] = form(controles=control(t, (dt + a).strip(), nombre="d"))

# --- tercera tanda (al final): ICON FILE en DROPLIST y DROPEDIT (samples SetBoxIcoFile)
IC = 'ICON FILE "_MBSTDBMP_"'
for t in ("DROPLIST", "DROPEDIT"):
    dt = "DATATYPE CHAR\n" if t == "DROPEDIT" else ""
    for a in [IC, IC + "\nSHOW 8 LINES", "AUTOSIZE\n" + IC,
              "BORDER DOUBLE DOWN\nAUTOSIZE\n" + IC + "\n" + dt + "SHOW 8 LINES\nCOLUMNS 1\nSELECTTYPE SIMPLE\nSCROLL VERTICAL",
              IC + "\n" + dt + "LISTTYPE LISTCOLS 2\nCURSORTYPE SQL", IC + "\n" + dt + "SORTONCLICK"]:
        cuerpo = a if dt and dt.strip() in a else (dt + a if "AUTOSIZE" not in a else a.replace(IC, IC + "\n" + dt.strip()).strip())
        P[f"d3_{t.lower()}_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_")[:60]] = form(
            controles=control(t, cuerpo.replace("\n\n", "\n"), nombre="d"))
    if dt:  # DATATYPE delante del ICON FILE (en el sample, detrás)
        P[f"d3_{t.lower()}_datatype_antes"] = form(controles=control(t, (dt + IC).strip(), nombre="d"))


def principal(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    principal()

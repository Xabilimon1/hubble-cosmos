"""Batería de bits de FCT (+0x00) por tipo de control: las palabras del compilador que cambian un bit
según el control (ETCHEDIN/ETCHEDOUT de TEXT, TICKMARKS/TICKS/POINT/VERTICAL de PERCENT y SLIDER,
GRAYSCALE/PALIND/FRAMEAUTOSIZE de BITMAP, ICON [CENTER] [VERTICAL] y VERTICAL del control MENU). Un
cambio por programa sobre la base de su tipo. Uso: python3 -I fct.py <dir salida> <huecos.txt> [desde]
"""
import importlib.util
from pathlib import Path


def _cargar(nombre):
    spec = importlib.util.spec_from_file_location(nombre, Path(__file__).with_name(nombre + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_f, _m = _cargar("formularios"), _cargar("menus")
form, control = _f.form, _f.control


def clave(prefijo, a):
    return prefijo + "_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_").replace("__", "_")


P = {}
# --- TEXT
P["t_base"] = form(controles=control("TEXT"))
for a in ["ETCHEDIN", "ETCHEDOUT", "MULTILINE\nETCHEDOUT", "BORDER FRAME\nETCHEDOUT", "NOBORDER\nETCHEDIN"]:
    P[clave("t", a)] = form(controles=control("TEXT", a))
# --- PERCENT y SLIDER
for p, tipo in (("p", "PERCENT"), ("s", "SLIDER")):
    P[f"{p}_base"] = form(controles=control(tipo))
    for a in ["TICKMARKS", "VERTICAL", "TICKS 5", "POINT TOPLEFT", "POINT BOTTOMRIGHT", "POINT TOPLEFT BOTTOMRIGHT",
              "RANGE 0 5", "RANGE 0 5\nVERTICAL\nTICKMARKS", "TICKS 5\nTICKMARKS"]:
        P[clave(p, a)] = form(controles=control(tipo, a))
# --- BITMAP y BOX
P["bm_base"] = form(controles=control("BITMAP"))
for a in ["GRAYSCALE", "PALIND", "FRAMEAUTOSIZE", "STRETCH\nGRAYSCALE"]:
    P[clave("bm", a)] = form(controles=control("BITMAP", a))
P["x_frameautosize"] = form(controles=control("BOX", "FRAMEAUTOSIZE"))
# --- control MENU de una barra
A = ['OPTION', '\t"a"']


def barra(atributos=""):
    c = "".join(f"\t\t\t\t\t{x}\n" for x in atributos.split("\n") if x)
    return _m.con_menu([_m.menu("m", A)], controles="\t\t\tCONTROL AS BAR\n\t\t\t\tPOSITION 0 0 100 30\n\t\t\t\tBARTYPE MENU\n"
                       "\t\t\tBEGIN\n\t\t\t\tCONTROL AS MENU\n\t\t\t\t\tPOSITION 0 0 90 24\n" + c + "\t\t\t\t\tMENU m\n\t\t\tEND\n")


P["m_base"] = barra()
for a in ["ICON", "ICON CENTER", "ICON VERTICAL", "ICON CENTER VERTICAL", "VERTICAL", "BUTTON", "BORDER HILIGHT",
          "NOBORDER", "BORDER ETCHED", "VERTICAL\nICON", "BUTTON\nBORDER HILIGHT",
          "NOBORDER\nVERTICAL\nICON\nBUTTON\nBORDER HILIGHT", "NOBORDER\nICON CENTER VERTICAL\nBUTTON\nBORDER HILIGHT"]:
    P[clave("m", a)] = barra(a)
# Combinaciones (al final, para no mover los huecos de las anteriores)
P["t_etchedin_etchedout"] = form(controles=control("TEXT", "ETCHEDIN\nETCHEDOUT"))
P["t_alignment_multiline_etchedout"] = form(controles=control("TEXT", "ALIGNMENT CENTER\nMULTILINE\nETCHEDOUT\nDATATYPE CHAR"))
P["s_vertical_point_bottomright"] = form(controles=control("SLIDER", "POINT BOTTOMRIGHT\nVERTICAL"))
P["p_store_range_vertical_tickmarks"] = form(controles=control("PERCENT", "STORE DESIGN\nBORDER DOUBLE DOWN\nRANGE 0 5\nVERTICAL\nTICKMARKS"))
P["bm_palind_grayscale"] = form(controles=control("BITMAP", "PALIND\nGRAYSCALE"))
P["m_button_border_black"] = barra("BUTTON\nBORDER BLACK")
P["m_icon_button_border_hilight"] = barra("ICON\nBUTTON\nBORDER HILIGHT")
P["m_border_etched_vertical_icon_button"] = barra("BORDER ETCHED\nVERTICAL\nICON\nBUTTON\nBORDER HILIGHT")
# El TEXT con DATATYPE (como EDIT), y el control MENU con menús de varias opciones (+0x40)
for a in ["DATATYPE CHAR", "DATATYPE CHAR(50)", "DATATYPE INTEGER MASK 2", "DATATYPE DECIMAL(8,2)", "DATATYPE DATE",
          "ALIGNMENT RIGHT\nDATATYPE INTEGER MASK 2\nTAGS \"1\""]:
    P[clave("t", a)] = form(controles=control("TEXT", a))


def barra_con(items):
    return barra().replace("\t\t\t\tOPTION\n\t\t\t\t\t\"a\"\n", "".join("\t\t\t\t" + l + "\n" for l in items), 1)


P["m_dos_opciones"] = barra_con(A + ['OPTION', '\t"b"'])
P["m_siete_opciones"] = barra_con(sum((['OPTION', f'\t"{c}"'] for c in "abcdefg"), []))
P["m_submenu_y_opcion"] = barra_con(['MENU', '\t"s"', '\tBEGIN', '\t\tOPTION', '\t\t\t"a"', '\t\tOPTION', '\t\t\t"c"', '\tEND',
                                     'OPTION', '\t"b"'])
P["m_separator"] = barra_con(['OPTION', '\t"a"', '\tSEPARATOR', 'OPTION', '\t"b"'])
# BUTTON + BORDER HILIGHT|BLACK también en el SPIN
P["sp_base"] = form(controles=control("SPIN"))
for a in ["BUTTON", "BUTTON\nBORDER HILIGHT", "BUTTON\nBORDER BLACK", "BORDER ETCHED\nBUTTON\nBORDER HILIGHT",
          "CURSOR\nBORDER ETCHED\nVERTICAL\nQUADRUPLE\nCOMMAND\nBUTTON\nBORDER HILIGHT"]:
    P[clave("sp", a)] = form(controles=control("SPIN", a))


# --- SORT de LIST, DROPLIST y DROPEDIT (no sale como atributo en ningún fuente del kit; en el compilador, la cadena
# va delante de SORTONCLICK), al final
LB = dict(nombre="l", posicion="10 10 100 50")
for a in ["SORT", "SORT\nSORTONCLICK", "SORTONCLICK\nSORT", 'ICON FILE "a.ico"\nSORT', 'SORT\nICON FILE "a.ico"',
          "ALLOWDRAG\nSORT", "SORT\nALLOWDRAG", "ALLOWDROP\nSORT", "SORT\nALLOWDROP", "SORT\nLISTTYPE LISTCOLS 2",
          "SORT\nCURSORTYPE SQL", "SORT\nCURSORTYPE TREEVIEW", "SORT\nSELECTTYPE SIMPLE", "SORT\nSELECTTYPE MULTIPLE",
          "SORT\nSCROLL VERTICAL", "LISTTYPE LISTCOLS 2\nSORT", 'BORDER DOUBLE DOWN\nLABEL "Lista"\nSORT',
          'ICON FILE "a.ico"\nALLOWDRAG\nALLOWDROP\nSORT\nSORTONCLICK\nLISTTYPE LISTCOLS 2\nCURSORTYPE SQL\nSELECTTYPE MULTIPLE\nSCROLL VERTICAL']:
    P[clave("so_list", a)[:70]] = form(controles=control("LIST", a, **LB))
for t in ("DROPLIST", "DROPEDIT"):
    dt = "DATATYPE CHAR\n" if t == "DROPEDIT" else ""
    for a in ["SORT", "SORT\nSORTONCLICK", "SORTONCLICK\nSORT", "SHOW 8 LINES\nSORT", "SORT\nSHOW 8 LINES",
              "SORT\nLISTTYPE LISTCOLS 2", "SORT\nSCROLL VERTICAL"]:
        P[clave(f"so_{t.lower()}", a)] = form(controles=control(t, dt + a, nombre="d"))
    if dt:
        P["so_dropedit_sort_antes_datatype"] = form(controles=control(t, "SORT\n" + dt, nombre="d"))
# segunda tanda: con un icono que existe (a.ico no está en el proyecto) y en el orden de Hubble
IC = 'ICON FILE "_MBSTDBMP_"'
for a in [IC + "\nSORT", "SORT\n" + IC, 'LABEL "Lista"\nBORDER DOUBLE DOWN\nSORT',
          IC + "\nALLOWDRAG\nALLOWDROP\nSORT\nSORTONCLICK\nLISTTYPE LISTCOLS 2\nCURSORTYPE SQL\nSELECTTYPE MULTIPLE\nSCROLL VERTICAL"]:
    P[clave("so2_list", a)[:70]] = form(controles=control("LIST", a, **LB))
for t in ("DROPLIST", "DROPEDIT"):
    dt = "DATATYPE CHAR\n" if t == "DROPEDIT" else ""
    for a in [IC + "\n" + dt + "SORT", 'TAGS "a" "b"\nSORT', 'SORT\nTAGS "a" "b"',
              "SORT\nSHOW 8 LINES\nSORTONCLICK\nLISTTYPE LISTCOLS 2\nCURSORTYPE SQL\nSELECTTYPE MULTIPLE\nSCROLL VERTICAL"]:
        cuerpo = a if a.startswith(IC) else dt + a
        P[clave(f"so2_{t.lower()}", a)[:70]] = form(controles=control(t, cuerpo, nombre="d"))
# tercera tanda: SHOW n LINES con SORTONCLICK (detrás de SHOW, SORTONCLICK no compiló en so2_)
for t in ("DROPLIST", "DROPEDIT"):
    dt = "DATATYPE CHAR\n" if t == "DROPEDIT" else ""
    for a in ["SHOW 8 LINES\nSORTONCLICK", "SORTONCLICK\nSHOW 8 LINES", "SORT\nSORTONCLICK\nSHOW 8 LINES",
              "SORT\nSORTONCLICK\nSHOW 8 LINES\nLISTTYPE LISTCOLS 2\nCURSORTYPE SQL\nSCROLL VERTICAL"]:
        P[clave(f"so3_{t.lower()}", a)[:70]] = form(controles=control(t, dt + a, nombre="d"))


# --- familia «codigo» del vocabulario (2026-10-31), al final: TICKS n detrás de TICKMARKS (orden de cosmakecon:
# 'TICKMARKS' 'TICKS %d'); delante y solo ya no compilaron
for p, tipo in (("tks", "SLIDER"), ("tkp", "PERCENT")):
    for a in ["TICKMARKS\nTICKS 5", "TICKMARKS\nTICKS 1", "TICKMARKS\nTICKS 0", "RANGE 0 10\nTICKMARKS\nTICKS 5",
              "VERTICAL\nTICKMARKS\nTICKS 5", "TICKMARKS\nTICKS"]:
        P[clave(p, a)] = form(controles=control(tipo, a))
    P[f"{p}_tickmarks_ticks_5_linea"] = form(controles=control(tipo, "TICKMARKS TICKS 5"))
P[clave("tks", "POINT TOPLEFT\nTICKMARKS\nTICKS 5")] = form(controles=control("SLIDER", "POINT TOPLEFT\nTICKMARKS\nTICKS 5"))

# --- geometría que parece una declaración (samples EjDisableAceleradores, que en 32 bits no salía), al final: un
# u32 de POSITION con el u16 bajo 0x0100 (x o ancho 256) se parece a una referencia a IDE con el código 0x01 de las
# declaraciones; si y (o el alto) por 4 cae en el registro de IDE de un nombre que solo se usa por puntero (Text,
# PutEnv, Run), ese nombre se tomaba por declarado. Como el primer registro de IDE es el nombre del módulo, y sale del
# hueco que le toca a cada variante (está en su nombre: el registro al que apunta y en qué arquitectura). Con x = 255
# no se parece.
EV = 'On Open\nbegin\n    b.Text = "x";\nend\n\nOn event Click control b(e as event)\nbegin\n    PutEnv("A", "TRUE");\nend\n\n'


def _geometria(posicion, forma="POSITION 0 0 200 100"):
    return form(controles=control("BUTTON", 'LABEL "b"', nombre="b")
                + control("TEXT", 'DATATYPE CHAR\nTAGS "t"', nombre="t", posicion=posicion),
                eventos=EV).replace("POSITION 0 0 200 100", forma)


for nombre, pos in [("x_text32", "256 13 225 22"), ("x_putenv32", "256 19 225 22"), ("x_run32", "256 24 225 22"),
                    ("x_text64", "256 14 225 22"), ("x_putenv64", "256 18 225 22"), ("x_run64", "256 26 225 22"),
                    ("255_text", "255 14 225 22"), ("255_putenv32", "255 18 225 22"),
                    ("ancho_putenv32", "10 10 256 20"), ("ancho_putenv64", "10 10 256 20")]:
    P["geo_" + nombre] = _geometria(pos)
P["geo_form_ancho_putenv32"] = _geometria("255 1 225 22", "POSITION 0 0 256 19")


# --- CURSOR frente a FOREGROUND, BACKGROUND + BOLD y FONT, en los dos órdenes y en cada tipo de control (los proyectos
# ALMAFAC3/almafac4 AUXILIAR e INICIO, STOCKMDI menu y TryThisOneFirst menu_examples llevan en un BUTTON `FONT … CURSOR`
# y `BACKGROUND … BOLD CURSOR`; Hubble lo escribía justo tras POSITION y no compilaba: «Expecting control, end»), al final
CUR_TIPOS = [("b", "BUTTON", "", {}), ("x", "BOX", "", {}), ("e", "EDIT", "DATATYPE CHAR", {}), ("k", "CHECK", "", {}),
             ("r", "RADIO", 'NUMBER 2 TAGS "a" "b"', {}), ("t", "TEXT", "", {}), ("bm", "BITMAP", "", {}),
             ("s", "SLIDER", "", {}), ("p", "PERCENT", "", {}), ("sp", "SPIN", "", {}),
             ("l", "LIST", "", LB), ("dl", "DROPLIST", "", {}), ("de", "DROPEDIT", "DATATYPE CHAR", {}),
             ("u", "USER", "", {}), ("bar", "BAR", "BARTYPE STATUS", {}), ("spl", "SPLIT", "", dict(posicion="10 10 7 80")),
             ("g", "GRID", "", {}), ("tab", "TAB", 'NUMBER 2\n\tTAB LABEL "a"\n\tTAB LABEL "b"', {}), ("pn", "PANEL", "", {})]
for c, tipo, resto, extra in CUR_TIPOS:
    for nombre, a in [("fg_cursor", "FOREGROUND RGB 0 0 255\nCURSOR"), ("cursor_fg", "CURSOR\nFOREGROUND RGB 0 0 255"),
                      ("bg_bold_cursor", "BACKGROUND RGB 0 0 255\nBOLD\nCURSOR"), ("cursor_bg_bold", "CURSOR\nBACKGROUND RGB 0 0 255\nBOLD"),
                      ("font_cursor", 'FONT "Arial" 10\nCURSOR'), ("cursor_font", 'CURSOR\nFONT "Arial" 10')]:
        cuerpo = control(tipo, a + ("\n" + resto if resto else ""), **extra)
        P[f"cur_{c}_{nombre}"] = form(controles=cuerpo + ("\t\t\tBEGIN\n\t\t\tEND\n" if tipo == "TAB" else ""))
# y su sitio frente a lo que Hubble escribe detrás de FONT: STORE (EDIT), FOCUS, NOTABSTOP, ATTACH, INVISIBLE
for nombre, a in [("cursor_store", "CURSOR\nSTORE DESIGN\nDATATYPE CHAR"), ("store_cursor", "STORE DESIGN\nCURSOR\nDATATYPE CHAR")]:
    P[f"cur_e_{nombre}"] = form(controles=control("EDIT", a))
for nombre, a in [("cursor_focus", "CURSOR\nFOCUS"), ("focus_cursor", "FOCUS\nCURSOR"),
                  ("cursor_notabstop", "CURSOR\nNOTABSTOP"), ("notabstop_cursor", "NOTABSTOP\nCURSOR"),
                  ("cursor_attach", "CURSOR\nATTACH ALL"), ("attach_cursor", "ATTACH ALL\nCURSOR"),
                  ("invisible_cursor", "INVISIBLE\nCURSOR"), ("cursor_invisible", "CURSOR\nINVISIBLE"),
                  ("todo", 'INVISIBLE\nFOREGROUND RGB 0 0 255\nBACKGROUND RGB 0 255 0\nBOLD\nFONT "Arial" 10\nCURSOR\nFOCUS\nNOTABSTOP\nATTACH ALL\nLABEL "x"')]:
    P[f"cur_b_{nombre}"] = form(controles=control("BUTTON", a))


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

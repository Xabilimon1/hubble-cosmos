"""Batería de BUTTONGROUP (control de tipo 0xC) y BOXGROUP (0xE): una variante por palabra, con las formas que
usan los fuentes del kit (CLICKTYPE CHECK/RADIO/MANUAL, NUMBER n ROWS/COLUMNS m, ICON FILE "x" [CENTER] [VERTICAL],
BORDER HILIGHT, `BUTTON LABEL "x" ICON n`, `BOX LABEL "x"`, `BOX ICON n`, `BOX BACKGROUND COLOR c`).
Uso: python3 -I grupos.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control


def grupo(tipo, atributos, nombre="g", posicion="10 10 120 60"):
    return form(controles=control(tipo, atributos, nombre=nombre, posicion=posicion))


BG = '\tBUTTON LABEL "1"\n\tBUTTON LABEL "2"'
BX = '\tBOX LABEL "1"\n\tBOX LABEL "2"'
ICONOS = 'ICON FILE "_MBSTDBMP_" CENTER'
P = {}
# --- BUTTONGROUP
P["g_base"] = grupo("BUTTONGROUP", "CLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
for nombre, a in [("radio", "CLICKTYPE RADIO"), ("manual", "CLICKTYPE MANUAL")]:
    P[f"g_{nombre}"] = grupo("BUTTONGROUP", f"{a}\nNUMBER 2 ROWS 1\n" + BG)
P["g_sin_clicktype"] = grupo("BUTTONGROUP", "NUMBER 2 ROWS 1\n" + BG)
P["g_rows2"] = grupo("BUTTONGROUP", 'CLICKTYPE CHECK\nNUMBER 4 ROWS 2\n' + BG + '\n\tBUTTON LABEL "3"\n\tBUTTON LABEL "4"')
P["g_columns1"] = grupo("BUTTONGROUP", "CLICKTYPE CHECK\nNUMBER 2 COLUMNS 1\n" + BG)
P["g_columns2"] = grupo("BUTTONGROUP", 'CLICKTYPE CHECK\nNUMBER 4 COLUMNS 2\n' + BG + '\n\tBUTTON LABEL "3"\n\tBUTTON LABEL "4"')
P["g_uno"] = grupo("BUTTONGROUP", 'CLICKTYPE CHECK\nNUMBER 1 ROWS 1\n\tBUTTON LABEL "1"')
P["g_hilight"] = grupo("BUTTONGROUP", "CLICKTYPE CHECK\nNUMBER 2 ROWS 1\nBORDER HILIGHT\n" + BG)
P["g_iconos"] = grupo("BUTTONGROUP", f"{ICONOS}\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON ICON 1\n\tBUTTON ICON 2")
P["g_iconos_vertical"] = grupo("BUTTONGROUP", f"{ICONOS} VERTICAL\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON ICON 1\n\tBUTTON ICON 2")
P["g_iconos_sin_center"] = grupo("BUTTONGROUP", 'ICON FILE "_MBSTDBMP_"\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON ICON 1\n\tBUTTON ICON 2')
P["g_label_icono"] = grupo("BUTTONGROUP", f'{ICONOS}\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON LABEL "a" ICON 3\n\tBUTTON LABEL "b" ICON 5')
P["g_un_icono"] = grupo("BUTTONGROUP", f'{ICONOS}\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON LABEL "a" ICON 3\n\tBUTTON LABEL "b"')
P["g_label_vacio"] = grupo("BUTTONGROUP", 'CLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON LABEL ""\n\tBUTTON LABEL "2"')
P["g_noborder"] = grupo("BUTTONGROUP", "NOBORDER\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
P["g_nolabel"] = grupo("BUTTONGROUP", "NOLABEL\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
P["g_cursor"] = grupo("BUTTONGROUP", "CURSOR\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
P["g_bold"] = grupo("BUTTONGROUP", "BOLD\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
P["g_foreground"] = grupo("BUTTONGROUP", "FOREGROUND RGB 64 0 64\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
P["g_attach"] = grupo("BUTTONGROUP", "ATTACH LEFT RIGHT\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n" + BG)
P["g_variable"] = form(objetos="v as Smallint", controles=control("BUTTONGROUP", "VARIABLE v\nCLICKTYPE RADIO\nNUMBER 2 ROWS 1\n" + BG,
                                                                     nombre="g", posicion="10 10 120 60"))
P["g_label"] = grupo("BUTTONGROUP", 'LABEL "Grupo"\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n' + BG)
# --- BOXGROUP
P["x_base"] = grupo("BOXGROUP", "NUMBER 2 COLUMNS 1\n" + BX)
P["x_rows"] = grupo("BOXGROUP", "NUMBER 2 ROWS 1\n" + BX)
P["x_columns2"] = grupo("BOXGROUP", 'NUMBER 4 COLUMNS 2\n' + BX + '\n\tBOX LABEL "3"\n\tBOX LABEL "4"')
for nombre, a in [("check", "CLICKTYPE CHECK"), ("radio", "CLICKTYPE RADIO"), ("manual", "CLICKTYPE MANUAL")]:
    P[f"x_{nombre}"] = grupo("BOXGROUP", f"{a}\nNUMBER 2 COLUMNS 1\n" + BX)
P["x_color"] = grupo("BOXGROUP", 'NUMBER 2 COLUMNS 1\n\tBOX BACKGROUND COLOR red\n\tBOX LABEL "2"')
P["x_color_label"] = grupo("BOXGROUP", 'NUMBER 2 COLUMNS 1\n\tBOX LABEL "1" BACKGROUND COLOR red\n\tBOX LABEL "2"')
P["x_color_rgb"] = grupo("BOXGROUP", 'NUMBER 2 COLUMNS 1\n\tBOX LABEL "1" BACKGROUND RGB 1 2 3\n\tBOX LABEL "2"')
P["x_border_all"] = grupo("BOXGROUP", "NOLABEL\nNUMBER 1 COLUMNS 1\nBORDER ALL\n\tBOX")
P["x_box_vacio"] = grupo("BOXGROUP", "NUMBER 2 COLUMNS 1\n\tBOX\n\tBOX")
P["x_iconos"] = grupo("BOXGROUP", 'ICON FILE "_MBSTDBMP_"\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBOX ICON 2\n\tBOX ICON 3')
P["x_label_icono"] = grupo("BOXGROUP", 'ICON FILE "_MBSTDBMP_"\nNUMBER 2 ROWS 1\n\tBOX LABEL "a" ICON 2\n\tBOX LABEL "b"')
P["x_noborder"] = grupo("BOXGROUP", "NOBORDER\nNUMBER 2 COLUMNS 1\n" + BX)
P["x_nolabel"] = grupo("BOXGROUP", "NOLABEL\nNUMBER 2 COLUMNS 1\n" + BX)
P["x_cursor"] = grupo("BOXGROUP", "CURSOR\nNUMBER 2 COLUMNS 1\n" + BX)
P["x_foreground"] = grupo("BOXGROUP", "FOREGROUND COLOR blue\nNUMBER 2 COLUMNS 1\n" + BX)
P["x_allowdrag"] = grupo("BOXGROUP", "ALLOWDRAG\nNUMBER 2 COLUMNS 1\n" + BX)
P["x_hilight"] = grupo("BOXGROUP", "NUMBER 2 COLUMNS 1\nBORDER HILIGHT\n" + BX)
# --- segunda tanda: CLICKTYPE con iconos (ALMAFAC3 inicio y ActiveX demo: +0x20 alto = 0x40 con MANUAL e ICON FILE)
ICONOS2 = "\n\tBUTTON LABEL \"a\" ICON 1\n\tBUTTON LABEL \"b\" ICON 2"
P["g_manual_iconos"] = grupo("BUTTONGROUP", f"{ICONOS} VERTICAL\nCLICKTYPE MANUAL\nNUMBER 2 ROWS 1" + ICONOS2)
P["g_manual_iconos_sin_center"] = grupo("BUTTONGROUP", 'ICON FILE "_MBSTDBMP_"\nCLICKTYPE MANUAL\nNUMBER 2 COLUMNS 1' + ICONOS2)
P["g_radio_iconos"] = grupo("BUTTONGROUP", f"{ICONOS}\nCLICKTYPE RADIO\nNUMBER 2 ROWS 1" + ICONOS2)
P["g_check_iconos_hilight"] = grupo("BUTTONGROUP", f"{ICONOS} VERTICAL\nCLICKTYPE CHECK\nNUMBER 2 COLUMNS 1\nBORDER HILIGHT" + ICONOS2)
P["g_manual_hilight"] = grupo("BUTTONGROUP", "CLICKTYPE MANUAL\nNUMBER 2 ROWS 1\nBORDER HILIGHT\n" + BG)
P["x_manual_iconos"] = grupo("BOXGROUP", 'ICON FILE "_MBSTDBMP_"\nCLICKTYPE MANUAL\nNUMBER 2 ROWS 1\n\tBOX ICON 2\n\tBOX ICON 3')
P["g_page"] = form(controles=control("TAB", 'NUMBER 2\n\tTAB LABEL "a"\n\tTAB LABEL "b"', nombre="t", posicion="0 0 200 100")
                   + "\t\t\tBEGIN\n" + control("BUTTONGROUP", "PAGE 1\nCLICKTYPE MANUAL\nNUMBER 2 ROWS 1\n" + BG,
                                                nombre="g", posicion="10 10 120 60").replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")
# --- tercera tanda: VARIABLE delante de CLICKTYPE (detrás de NUMBER no compila: samples SELEC), con ICON FILE
P["g_variable_iconos"] = form(objetos="v as Smallint", controles=control(
    "BUTTONGROUP", f"NOBORDER\n{ICONOS}\nVARIABLE v\nCLICKTYPE RADIO\nNUMBER 2 ROWS 1" + ICONOS2, nombre="g", posicion="10 10 120 60"))
P["x_variable"] = form(objetos="v as Smallint", controles=control("BOXGROUP", "NOBORDER\nVARIABLE v\nCLICKTYPE RADIO\nNUMBER 2 COLUMNS 1\n" + BX,
                                                                   nombre="g", posicion="10 10 120 60"))
# --- cuarta tanda: borde de los botones tras NUMBER (u16 alto de +0x20): NOBORDER (0x40, ALMAFAC3 inicio, ActiveX demo)
# y los demás bordes, a ver cuáles compilan
for nombre, b in [("noborder", "NOBORDER"), ("double", "BORDER DOUBLE"), ("etched", "BORDER ETCHED"),
                  ("down", "BORDER DOWN"), ("frame", "BORDER FRAME"), ("black", "BORDER BLACK"),
                  ("double_down", "BORDER DOUBLE DOWN"), ("hilight_black", "BORDER HILIGHT BLACK")]:
    P[f"g_b_{nombre}"] = grupo("BUTTONGROUP", f"CLICKTYPE CHECK\nNUMBER 2 ROWS 1\n{b}\n" + BG)
P["g_b_noborder_iconos"] = grupo("BUTTONGROUP", f"NOBORDER\n{ICONOS} VERTICAL\nCLICKTYPE MANUAL\nNUMBER 2 ROWS 1\nNOBORDER" + ICONOS2)
P["x_b_noborder"] = grupo("BOXGROUP", "NUMBER 2 COLUMNS 1\nNOBORDER\n" + BX)
# --- quinta tanda: CURSOR con FOREGROUND y BOLD, en los dos órdenes (samples URLText: `FOREGROUND … CURSOR` en un
# BOXGROUP; al revés, «Actual foreground»)
for tipo, c, cuerpo in [("BOXGROUP", "x", "NUMBER 2 COLUMNS 1\n" + BX), ("BUTTONGROUP", "g", "CLICKTYPE MANUAL\nNUMBER 2 ROWS 1\n" + BG)]:
    for nombre, a in [("fg_cursor", "FOREGROUND COLOR blue\nCURSOR"), ("cursor_fg", "CURSOR\nFOREGROUND COLOR blue"),
                      ("bold_cursor", "BOLD\nCURSOR"), ("cursor_bold", "CURSOR\nBOLD"),
                      ("bg_cursor", "BACKGROUND COLOR blue\nCURSOR"), ("cursor_bg", "CURSOR\nBACKGROUND COLOR blue")]:
        P[f"{c}_{nombre}"] = grupo(tipo, f"{a}\n{cuerpo}")


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

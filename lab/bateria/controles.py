"""Batería de controles: iconos, bordes, atributos que faltan en formularios.py y los tipos
de control nuevos (TAB, USER, BAR, BUTTONGROUP, BOXGROUP, MDICLIENT). Un cambio por programa
sobre la base de su tipo (`<x>_base`). Cuando no se sabe en qué orden admite el compilador un
atributo, va en dos variantes (`_antes` y `_despues` de DATATYPE): la que no compila lo dice.

Uso: python3 -I controles.py <dir salida> <huecos.txt> [desde]
Va en su propia carpeta del laboratorio, así que puede usar los huecos desde el primero.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control


def clave(prefijo, a):
    return prefijo + "_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_").replace("__", "_")


P = {}
ICONO = 'ICON 2 FILE "_MBSTDBMP_"'
# --- BUTTON
P["b_base"] = form(controles=control("BUTTON"))
for a in ['ICON 1 FILE "_MBSTDBMP_"', ICONO, 'ICON 3 FILE "_MBSTDBMP_"', 'ICON 2 FILE "Small Buttons"',
          ICONO + " CENTER", ICONO + " VERTICAL", ICONO + " CENTER VERTICAL", "ICON 2", "CURSOR"]:
    P[clave("b", a)] = form(controles=control("BUTTON", a))
P["b_label_icono"] = form(controles=control("BUTTON", 'LABEL "x"\n' + ICONO))
P["b_dos_iconos"] = form(controles=control("BUTTON", ICONO) + control("BUTTON", 'ICON 3 FILE "Small Buttons"', nombre="d", posicion="10 40 50 20"))
# --- BOX
P["x_base"] = form(controles=control("BOX"))
for a in [ICONO, ICONO + " CENTER", "SCROLL VERTICAL", "SCROLL VERTICAL HORIZONTAL", "BORDER FRAME", "BORDER DOUBLE FRAME",
          "BORDER DOWN FRAME", "BORDER ETCHED EXTRA 1", "BORDER ETCHED EXTRA 3", "BORDER FRAME EXTRA 1", "BORDER DOWNSHADOW ALL",
          "BORDER ALL", "CURSOR"]:
    P[clave("x", a)] = form(controles=control("BOX", a))
# --- EDIT (base: DATATYPE CHAR)
P["e_base"] = form(controles=control("EDIT", "DATATYPE CHAR"))
for a in ["READONLY", "SCROLL VERTICAL", "SCROLL HORIZONTAL", "SCROLL VERTICAL HORIZONTAL", "SPIN BUTTON",
          "STORE STATUS DESIGN", "STORE DESIGN", ICONO + " CENTER", ICONO, "ALLOWDRAG", "ALLOWDROP", "INVISIBLE", "CURSOR"]:
    P[clave("e", a) + "_antes"] = form(controles=control("EDIT", a + "\nDATATYPE CHAR"))
    P[clave("e", a) + "_despues"] = form(controles=control("EDIT", "DATATYPE CHAR\n" + a))
P["e_multiline_scroll"] = form(controles=control("EDIT", "MULTILINE\nDATATYPE CHAR\nSCROLL VERTICAL"))
P["e_multiline_scroll_readonly"] = form(controles=control("EDIT", "MULTILINE\nDATATYPE CHAR\nSCROLL VERTICAL\nREADONLY"))
# --- CHECK, RADIO, TEXT
P["k_base"] = form(controles=control("CHECK"))
for a in ["ICON 2", "ICON 3", "LABELLEFT", "CURSOR", ICONO]:
    P[clave("k", a)] = form(controles=control("CHECK", a))
RADIO = 'NUMBER 2 TAGS "a" "b"'
P["r_base"] = form(controles=control("RADIO", RADIO))
for a in ["LABELLEFT", "CURSOR"]:
    P[clave("r", a) + "_antes"] = form(controles=control("RADIO", a + "\n" + RADIO))
    P[clave("r", a) + "_despues"] = form(controles=control("RADIO", RADIO + "\n" + a))
P["t_base"] = form(controles=control("TEXT"))
P["t_invisible"] = form(controles=control("TEXT", "INVISIBLE"))
# --- BITMAP, SLIDER, SPIN
P["bm_base"] = form(controles=control("BITMAP"))
for a in ["STRETCH", "AUTOFIT", 'BITMAP FILE "x.bmp"', "BORDER FRAME EXTRA 1"]:
    P[clave("bm", a)] = form(controles=control("BITMAP", a))
P["s_base"] = form(controles=control("SLIDER"))
for a in ["POINT TOPLEFT", "RANGE 0 30", "TICKMARKS", "POINT TOPLEFT\nRANGE 0 30\nTICKMARKS"]:
    P[clave("s", a)] = form(controles=control("SLIDER", a))
P["sp_base"] = form(controles=control("SPIN"))
for a in ["VERTICAL", "QUADRUPLE", "COMMAND", "VERTICAL\nQUADRUPLE\nCOMMAND"]:
    P[clave("sp", a)] = form(controles=control("SPIN", a))
# --- tipos nuevos
TAB = 'NUMBER 2\n\tTAB LABEL "a"\n\tTAB LABEL "b"'
P["tab_base"] = form(controles=control("TAB", TAB) + "\t\t\tBEGIN\n\t\t\tEND\n")
for nombre, a in [("tres", 'NUMBER 3\n\tTAB LABEL "a"\n\tTAB LABEL "b"\n\tTAB LABEL "c"'),
                  ("otra_etiqueta", 'NUMBER 2\n\tTAB LABEL "x"\n\tTAB LABEL "b"'),
                  ("icono", 'ICON FILE "_MBSTDBMP_" CENTER\nNUMBER 2\n\tTAB LABEL "a" ICON 2\n\tTAB LABEL "b" ICON 3'),
                  ("fixed", "FIXED WIDTH 2\n" + TAB), ("border_double", "BORDER DOUBLE\n" + TAB)]:
    P[f"tab_{nombre}"] = form(controles=control("TAB", a) + "\t\t\tBEGIN\n\t\t\tEND\n")
P["tab_con_edit"] = form(controles=control("TAB", TAB) + "\t\t\tBEGIN\n" + control("EDIT", "DATATYPE CHAR", nombre="d").replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")
P["u_base"] = form(controles=control("USER"))
P["u_border_frame"] = form(controles=control("USER", "BORDER FRAME"))
P["md_base"] = form(controles=control("MDICLIENT"))
P["bar_base"] = form(controles=control("BAR", "BARTYPE STATUS"))
P["bar_menu"] = form(controles=control("BAR", "BARTYPE MENU"))
P["bar_panel"] = form(controles=control("BAR", "BARTYPE STATUS") + "\t\t\tBEGIN\n" + control("PANEL", "", nombre="").replace("CONTROL  AS", "CONTROL AS").replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")
BG = 'CLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON LABEL "1"\n\tBUTTON LABEL "2"'
P["bg_base"] = form(controles=control("BUTTONGROUP", BG))
P["bg_radio"] = form(controles=control("BUTTONGROUP", BG.replace("CHECK", "RADIO")))
P["bg_tres"] = form(controles=control("BUTTONGROUP", 'CLICKTYPE CHECK\nNUMBER 3 ROWS 1\n\tBUTTON LABEL "1"\n\tBUTTON LABEL "2"\n\tBUTTON LABEL "3"'))
P["bg_iconos"] = form(controles=control("BUTTONGROUP", 'ICON FILE "_MBSTDBMP_" CENTER\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON ICON 1\n\tBUTTON ICON 2'))
BX = 'NUMBER 2 COLUMNS 1\n\tBOX LABEL "1"\n\tBOX LABEL "2"'
P["bx_base"] = form(controles=control("BOXGROUP", BX))
P["bx_rows"] = form(controles=control("BOXGROUP", BX.replace("COLUMNS", "ROWS")))
P["bx_check"] = form(controles=control("BOXGROUP", "CLICKTYPE CHECK\n" + BX))
P["bx_color"] = form(controles=control("BOXGROUP", 'NUMBER 2 COLUMNS 1\n\tBOX BACKGROUND COLOR red\n\tBOX LABEL "2"'))
P["bx_border_all"] = form(controles=control("BOXGROUP", "BORDER ALL\n" + BX))
# --- LIST: arrastrar y soltar
P["l_base"] = form(controles=control("LIST", "", nombre="l", posicion="10 10 100 50"))
for a in ["ALLOWDRAG", "ALLOWDROP", "ALLOWDRAG\nALLOWDROP"]:
    P[clave("l", a)] = form(controles=control("LIST", a, nombre="l", posicion="10 10 100 50"))
# --- BORDER BLACK (bit 0x10 de +0x00: STOCKMDI menu y TryThisOneFirst `BORDER BLACK DOWN`, CalcRPN `BORDER BLACK`),
# solo y con los demás bordes, y en qué orden se escribe (al final, para no mover los huecos)
for a in ["BORDER BLACK", "BORDER BLACK DOWN", "BORDER DOWN BLACK", "BORDER BLACK DOUBLE", "BORDER BLACK ETCHED",
          "BORDER BLACK FRAME", "BORDER BLACK DOUBLE DOWN", "BORDER BLACK EXTRA 1", "BORDER BLACK ETCHED EXTRA 1",
          "BORDER BLACK DOUBLE FRAME", "NOLABEL\nBORDER BLACK DOWN"]:
    P[clave("xk", a)] = form(controles=control("BOX", a))
for tipo, c in [("BITMAP", "bmk"), ("TEXT", "tk"), ("BUTTON", "bk")]:
    P[f"{c}_black"] = form(controles=control(tipo, "BORDER BLACK"))
P["ek_black"] = form(controles=control("EDIT", "DATATYPE CHAR\nBORDER BLACK"))
# EXTRA 2 (CalcALG calcu3: BORDER ETCHED EXTRA 2), al final
for a in ["BORDER ETCHED EXTRA 2", "BORDER FRAME EXTRA 2", "BORDER FRAME EXTRA 3", "BORDER EXTRA 1", "BORDER EXTRA 2",
          "BORDER EXTRA 3", "BORDER DOUBLE EXTRA 2", "BORDER DOWN EXTRA 2"]:
    P[clave("xe", a)] = form(controles=control("BOX", a))
# --- SPLIT (tipo 0x16; OutlookActiveX, samples GetChildList, dbmanager ABOUT), al final
P["spl_base"] = form(controles=control("SPLIT", posicion="10 10 7 80"))
for a in ["VERTICAL", "BORDER DOUBLE", "BORDER DOUBLE\nVERTICAL", "BORDER DOWN", "ATTACH TOP BOTTOM\nVERTICAL",
          "ATTACH LEFT RIGHT\nBORDER DOWN", "ATTACH TOP BOTTOM\nBORDER DOUBLE\nVERTICAL", "NOLABEL", 'LABEL "x"', "INVISIBLE",
          "VERTICAL\nBORDER DOUBLE", "DISABLED"]:
    P[clave("spl", a)] = form(controles=control("SPLIT", a, posicion="10 10 7 80"))
P["spl_entre_dos"] = form(controles=control("BOX", nombre="a", posicion="0 0 10 80")
                         + control("SPLIT", "ATTACH TOP BOTTOM\nBORDER DOUBLE\nVERTICAL", nombre="s", posicion="10 0 7 80")
                         + control("BOX", nombre="b", posicion="17 0 10 80"))
P["spl_sin_nombre"] = form(controles=control("SPLIT", "VERTICAL", posicion="10 10 7 80").replace("CONTROL c AS", "CONTROL AS"))
# --- DISABLED con otros atributos (samples CosHttpDllPostCommand: DISABLED delante de FOREGROUND), al final
for a in ["FOREGROUND RGB 0 0 255", "BACKGROUND RGB 0 0 255", "INVISIBLE", "CURSOR", "BOLD", 'FONT "Arial" 10',
          "NOTABSTOP", "ATTACH ALL"]:
    P[clave("dis_antes", a)] = form(controles=control("EDIT", "DISABLED\n" + a + "\nDATATYPE CHAR"))
    P[clave("dis_despues", a)] = form(controles=control("EDIT", a + "\nDISABLED\nDATATYPE CHAR"))
# --- NOBORDER en un BUTTON (samples NewLook, EJUPDATESTRING), al final
for a in ["NOBORDER", "NOBORDER\n" + ICONO, ICONO + "\nNOBORDER", 'LABEL "x"\nNOBORDER', "NOBORDER\nBORDER HILIGHT",
          "DEFPUSH\nNOBORDER"]:
    P[clave("bnb", a)] = form(controles=control("BUTTON", a))
# --- BAR sin BARTYPE (samples Transparent, IgnoreCustomColors, CosmosVisualModeV2), al final
P["bt0_base"] = form(controles=control("BAR"))
P["bt0_borde"] = form(controles=control("BAR", "ATTACH LEFT RIGHT BOTTOM\nBORDER ETCHED"))
# --- NOLABEL del formulario (samples RichText: LABEL "x" NOLABEL NOBORDER), al final
for a in ["NOLABEL", 'LABEL "x"\nNOLABEL', 'NOLABEL\nLABEL "x"', 'LABEL "x"\nNOLABEL\nNOBORDER', "NOLABEL\nSYSMENU",
          "SYSMENU\nNOLABEL"]:
    P[clave("fnl", a)] = form(interfaz_form=a)
# --- RICHTEXTEDIT en un EDIT (samples RichTextPrintEx: BORDER ETCHED RICHTEXTEDIT WRAP DATATYPE CHAR), al final
for a in ["RICHTEXTEDIT\nDATATYPE CHAR", "DATATYPE CHAR\nRICHTEXTEDIT", "BORDER ETCHED\nRICHTEXTEDIT\nDATATYPE CHAR",
          "RICHTEXTEDIT\nBORDER ETCHED\nDATATYPE CHAR", "RICHTEXTEDIT\nWRAP\nDATATYPE CHAR", "WRAP\nRICHTEXTEDIT\nDATATYPE CHAR",
          "MULTILINE\nRICHTEXTEDIT\nDATATYPE CHAR", "RICHTEXTEDIT\nMULTILINE\nDATATYPE CHAR",
          "RICHTEXTEDIT\nDATATYPE CHAR\nSCROLL VERTICAL", 'LABEL "x"\nRICHTEXTEDIT\nDATATYPE CHAR',
          'RICHTEXTEDIT\nLABEL "x"\nDATATYPE CHAR', "ATTACH ALL\nRICHTEXTEDIT\nDATATYPE CHAR",
          "RICHTEXTEDIT\nPASSWORD\nDATATYPE CHAR", "PASSWORD\nRICHTEXTEDIT\nDATATYPE CHAR"]:
    P[clave("rte", a)] = form(controles=control("EDIT", a))
# --- DEFPUSH con el borde de botón (samples NewLook: BORDER HILIGHT DEFPUSH), al final
for a in ["BORDER HILIGHT\nDEFPUSH", "DEFPUSH\nBORDER HILIGHT", "NOBORDER\nDEFPUSH", "BORDER BLACK\nDEFPUSH",
          'BORDER HILIGHT\nDEFPUSH\nICON 2 FILE "_MBSTDBMP_"', 'NOBORDER\nDEFPUSH\nICON 2 FILE "_MBSTDBMP_"']:
    P[clave("bdp", a)] = form(controles=control("BUTTON", a))

# --- DATATYPE … FORMAT "x" (samples drag1: TEXT con NOBORDER DATATYPE CHAR FORMAT "AAAAAAAAAAA"), al final
for t, a in [("TEXT", 'NOBORDER\nDATATYPE CHAR FORMAT "AAAAAAAAAAA"\nTAGS "x"'), ("TEXT", 'DATATYPE CHAR FORMAT "AAA"\nTAGS "x"'),
             ("TEXT", 'DATATYPE CHAR FORMAT "AAA"'), ("EDIT", 'DATATYPE CHAR FORMAT "AAA"'), ("EDIT", 'DATATYPE CHAR(10) FORMAT "AA"'),
             ("EDIT", 'DATATYPE SMALLINT FORMAT "999"'), ("EDIT", 'DATATYPE DATE FORMAT "dd/mm/yyyy"'),
             ("EDIT", 'DATATYPE DECIMAL(9,2) FORMAT "###.##"'), ("EDIT", 'DATATYPE SMALLINT MASK 2 FORMAT "99"'),
             ("EDIT", 'DATATYPE CHAR FORMAT ""'), ("TEXT", 'DATATYPE CHAR FORMAT "B"\nTAGS "x"')]:
    P[clave("fmt_" + t.lower(), a)] = form(controles=control(t, a))

# --- FRAMEAUTOSIZE de los grupos (familia «ventana», 2026-10-31), al final (prefijo vw_)
ICONOS_BX = 'NUMBER 2 COLUMNS 1\n\tBOX ICON 1\n\tBOX ICON 2'
for nombre, tipo, a in [
        ("bg_frameautosize", "BUTTONGROUP", "FRAMEAUTOSIZE\n" + BG),
        ("bx_frameautosize", "BOXGROUP", "FRAMEAUTOSIZE\n" + BX),
        ("bx_check_frameautosize", "BOXGROUP", "CLICKTYPE CHECK\nFRAMEAUTOSIZE\n" + BX),
        ("bx_icon_frameautosize", "BOXGROUP", 'ICON FILE "_MBSTDBMP_" CENTER\nFRAMEAUTOSIZE\n' + ICONOS_BX),
        ("bx_frameautosize_icon", "BOXGROUP", 'FRAMEAUTOSIZE\nICON FILE "_MBSTDBMP_" CENTER\n' + ICONOS_BX),
        ("bx_autosize_frameautosize", "BOXGROUP", "AUTOSIZE\nFRAMEAUTOSIZE\n" + BX),
        ("bx_frameautosize_autosize", "BOXGROUP", "FRAMEAUTOSIZE\nAUTOSIZE\n" + BX),
        ("bx_frameautosize_allowdrag", "BOXGROUP", "FRAMEAUTOSIZE\nALLOWDRAG\n" + BX),
        ("bx_allowdrag_frameautosize", "BOXGROUP", "ALLOWDRAG\nFRAMEAUTOSIZE\n" + BX),
        ("bg_radio_frameautosize", "BUTTONGROUP", "FRAMEAUTOSIZE\n" + BG.replace("CHECK", "RADIO")),
        ("bg_frameautosize_tras_clicktype", "BUTTONGROUP", BG.replace("CLICKTYPE CHECK", "CLICKTYPE RADIO\nFRAMEAUTOSIZE")),
        ("bx_nolabel_frameautosize", "BOXGROUP", "NOLABEL\nFRAMEAUTOSIZE\n" + BX),
        ("bx_frameautosize_nolabel", "BOXGROUP", "FRAMEAUTOSIZE\nNOLABEL\n" + BX),
        ("bx_comment_frameautosize", "BOXGROUP", 'COMMENT "c"\nFRAMEAUTOSIZE\n' + BX),
        ("bg_icon_frameautosize", "BUTTONGROUP", 'ICON FILE "_MBSTDBMP_" CENTER\nFRAMEAUTOSIZE\nCLICKTYPE CHECK\nNUMBER 2 ROWS 1\n\tBUTTON ICON 1\n\tBUTTON ICON 2'),
        ("bx_frameautosize_noborder", "BOXGROUP", "FRAMEAUTOSIZE\nNUMBER 2 COLUMNS 1\nNOBORDER\n\tBOX LABEL \"1\"\n\tBOX LABEL \"2\""),
        ("bx_frameautosize_cursor", "BOXGROUP", "CURSOR\nFRAMEAUTOSIZE\n" + BX),
        ("box_frameautosize", "BOX", "FRAMEAUTOSIZE"),
        ("edit_frameautosize", "EDIT", "DATATYPE CHAR\nFRAMEAUTOSIZE")]:
    P["vw_" + nombre] = form(controles=control(tipo, a))

# segunda tanda: FRAMEAUTOSIZE con dos de los suyos a la vez, y con VARIABLE
ICONO_BX = 'ICON FILE "_MBSTDBMP_" CENTER\n'
for nombre, tipo, a, o in [
        ("bx_autosize_icon_frameautosize", "BOXGROUP", "AUTOSIZE\n" + ICONO_BX + "FRAMEAUTOSIZE\n" + ICONOS_BX, ""),
        ("bx_icon_autosize_frameautosize", "BOXGROUP", ICONO_BX + "AUTOSIZE\nFRAMEAUTOSIZE\n" + ICONOS_BX, ""),
        ("bx_icon_frameautosize_allowdrag", "BOXGROUP", ICONO_BX + "FRAMEAUTOSIZE\nALLOWDRAG\n" + ICONOS_BX, ""),
        ("bx_autosize_frameautosize_allowdrag", "BOXGROUP", "AUTOSIZE\nFRAMEAUTOSIZE\nALLOWDRAG\n" + BX, ""),
        ("bx_frameautosize_variable", "BOXGROUP", "FRAMEAUTOSIZE\nVARIABLE v\n" + BX, "v as integer"),
        ("bx_variable_frameautosize", "BOXGROUP", "VARIABLE v\nFRAMEAUTOSIZE\n" + BX, "v as integer"),
        ("bg_autosize_frameautosize", "BUTTONGROUP", "AUTOSIZE\nFRAMEAUTOSIZE\n" + BG, ""),
        ("bx_bold_frameautosize", "BOXGROUP", "BOLD\nFRAMEAUTOSIZE\n" + BX, ""),
        ("bx_attach_frameautosize", "BOXGROUP", "ATTACH ALL\nFRAMEAUTOSIZE\n" + BX, "")]:
    P["vw2_" + nombre] = form(controles=control(tipo, a), objetos=o)


# --- ACTIVEX: CLSID y PROPERTY (familia «activex», 2026-10-31), al final (prefijo ax_). Base: el CLSID del Calendar
# Control de Events.smd (kit 86x86, projects/ActiveX)
CLSID = 'CLSID "{8E27C92B-1264-101C-8A2F-040224009C02}"'
for nombre, a in [
        ("base", CLSID), ("sin_clsid", ""), ("progid", 'CLSID "Word.Application"'),
        ("minusculas", 'CLSID "{8e27c92b-1264-101c-8a2f-040224009c02}"'),
        ("label_antes", 'LABEL "x"\n' + CLSID), ("label_despues", CLSID + '\nLABEL "x"'),
        ("nolabel_antes", "NOLABEL\n" + CLSID), ("cursor_background_bold_notabstop", "CURSOR\nBACKGROUND RGB 0 255 0\nBOLD\nNOTABSTOP\n" + CLSID),
        ("tags_despues", CLSID + '\nTAGS "x"'),
        ("border_double_down_antes", "BORDER DOUBLE DOWN\n" + CLSID), ("border_double_down_despues", CLSID + "\nBORDER DOUBLE DOWN"),
        ("noborder_antes", "NOBORDER\n" + CLSID),
        ("varios_antes", 'DISABLED\nINVISIBLE\nFOREGROUND RGB 0 0 255\nFONT "Arial" 10\nATTACH ALL\nBORDER DOUBLE DOWN\n' + CLSID + '\nPROPERTY "Day" "2"'),
        ("border_etched_extra_antes", "BORDER ETCHED EXTRA 2\n" + CLSID),
        ("attach_antes", "ATTACH ALL\n" + CLSID), ("attach_despues", CLSID + "\nATTACH ALL"),
        ("disabled", "DISABLED\n" + CLSID), ("invisible_antes", "INVISIBLE\n" + CLSID),
        ("font_antes", 'FONT "Arial" 10\n' + CLSID), ("foreground_antes", "FOREGROUND RGB 0 0 255\n" + CLSID),
        ("prop1", CLSID + '\nPROPERTY "Day" "2"'), ("prop2", CLSID + '\nPROPERTY "Day" "2"\nPROPERTY "Month" "6"'),
        ("prop_orden", CLSID + '\nPROPERTY "Month" "6"\nPROPERTY "Day" "2"'),
        ("prop_antes_clsid", 'PROPERTY "Day" "2"\n' + CLSID), ("prop_vacia", CLSID + '\nPROPERTY "Day" ""'),
        ("prop_igual_nombre", CLSID + '\nPROPERTY "a=b" "c"'), ("prop_barra_valor", CLSID + '\nPROPERTY "Day" "a|b"'),
        ("prop_repetida", CLSID + '\nPROPERTY "Day" "1"\nPROPERTY "Day" "2"'),
        ("prop_tags", CLSID + '\nPROPERTY "Day" "2"\nTAGS "x"'), ("prop_sin_clsid", 'PROPERTY "Day" "2"'),
        ("prop_label", CLSID + '\nPROPERTY "Day" "2"\nLABEL "x"')]:
    P["ax_" + nombre] = form(controles=control("ACTIVEX", a))
P["ax_sin_nombre"] = form(controles=control("ACTIVEX", CLSID).replace("CONTROL c AS", "CONTROL AS"))
P["ax_dos"] = form(controles=control("ACTIVEX", CLSID) + control("ACTIVEX", 'CLSID "{00000000-0000-0000-0000-000000000001}"', nombre="d", posicion="10 40 50 20"))
P["ax_en_box"] = form(controles=control("BOX", "NOLABEL", nombre="").replace("CONTROL  AS", "CONTROL AS") + "\t\t\tBEGIN\n" + control("ACTIVEX", CLSID + '\nPROPERTY "Day" "2"').replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")
# `On Control x (e as Event)` (Events.smd), prefijo onc_
EVC = "On Control c (e as Event)\nbegin\nend\n"
P["onc_activex"] = form(controles=control("ACTIVEX", CLSID), eventos=EVC)
P["onc_button"] = form(controles=control("BUTTON"), eventos=EVC)
P["onc_literal"] = form(controles=control("BUTTON"), eventos='On Control "c" (e as Event)\nbegin\nend\n')
P["onc_sin_param"] = form(controles=control("BUTTON"), eventos="On Control c\nbegin\nend\n")


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

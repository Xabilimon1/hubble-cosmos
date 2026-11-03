"""Batería de páginas (`X is Page`, para imprimir): INTERFACE con SIZE y MARGIN y los controles de
página (TEXT, VAR, SEPARATOR, GROUP…). Un cambio por programa sobre `p_base`.
Uso: python3 -I paginas.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
control = _f.control


def pagina(interfaz="SIZE 595 842\nMARGIN 12 24 15 48", controles=None, objetos="", extra=""):
    if controles is None:
        controles = control("TEXT", 'TAGS "x"', nombre="")
    controles = controles.replace("CONTROL  AS", "CONTROL AS")
    return (
        "CONSTANTS  begin\nend\nCLASSES BEGIN\n\tpg is Page begin\n\t\tobjects begin\n"
        + "".join(f"\t\t\t{o}\n" for o in objetos.split("\n") if o)
        + "\t\tend\n\t\tINTERFACE\n" + "".join(f"\t\t\t{a}\n" for a in interfaz.split("\n") if a)
        + "\t\tBEGIN\n" + controles + "\t\tEND\n\tend\n" + extra + "END\n"
        + "CODE CLASS pg BEGIN\n//{{CODEBEGIN\n//{{CODEEND\nEND\n"
        + "CODE BEGIN\n//{{CODEBEGIN\nmain\nobjects begin\n    p as pg\nend\nbegin\nend\n//{{CODEEND\nEND\n"
    )


def texto(atributos, nombre=""):
    return control("TEXT", atributos, nombre=nombre)


P = {}
P["p_base"] = pagina()
for nombre, i in [("size", "SIZE 842 595\nMARGIN 12 24 15 48"), ("margin_0", "SIZE 595 842\nMARGIN 0 0 0 0"),
                  ("margin_24", "SIZE 595 842\nMARGIN 24 24 24 24"), ("margin_13", "SIZE 595 842\nMARGIN 13 24 15 48"),
                  ("margin_orden", "SIZE 595 842\nMARGIN 3 6 9 12"), ("useprintmargins", "SIZE 595 842\nUSEPRINTMARGINS\nMARGIN 12 24 15 48")]:
    P[f"p_{nombre}"] = pagina(i)
for nombre, a in [("tags", 'TAGS "otro"'), ("font", 'FONT "Arial" 12\nTAGS "x"'), ("font_bold", 'FONT "Arial" 12 BOLD\nTAGS "x"'),
                  ("bold", 'BOLD\nTAGS "x"'), ("alignment", 'ALIGNMENT RIGHT\nTAGS "x"'), ("noborder", 'NOBORDER\nTAGS "x"'),
                  ("border_all", 'BORDER ALL\nTAGS "x"'), ("transparent", 'BACKGROUND COLOR transparent\nTAGS "x"'),
                  ("datatype", 'DATATYPE CHAR\nTAGS "x"'), ("nombre", None)]:
    P[f"t_{nombre}"] = pagina(controles=texto(a) if a else texto('TAGS "x"', nombre="t"))
P["v_base"] = pagina(controles=control("VAR", "NOLABEL\nDATATYPE SMALLINT", nombre="v"))
P["v_alignment"] = pagina(controles=control("VAR", "NOLABEL\nALIGNMENT RIGHT\nDATATYPE SMALLINT", nombre="v"))
P["v_char"] = pagina(controles=control("VAR", "NOLABEL\nDATATYPE CHAR", nombre="v"))
P["v_label"] = pagina(controles=control("VAR", 'LABEL "l"\nDATATYPE SMALLINT', nombre="v"))
P["v_variable"] = pagina(objetos="n as Smallint", controles=control("VAR", "NOLABEL\nVARIABLE n\nDATATYPE SMALLINT", nombre="v"))
P["s_horizontal"] = pagina(controles=control("SEPARATOR", "", nombre="", posicion="10 10 100 2"))
P["s_vertical"] = pagina(controles=control("SEPARATOR", "VERTICAL", nombre="", posicion="10 10 2 100"))
P["s_thickline"] = pagina(controles=control("SEPARATOR", "THICKLINE", nombre="", posicion="10 10 100 2"))
GRUPO = "\t\t\tCONTROL AS GROUP\n\t\t\t\tPOSITION 10 10 200 100\n{}\t\t\tBEGIN\n" + texto('TAGS "x"').replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n"
P["g_base"] = pagina(controles=GRUPO.format("\t\t\t\tAS LINES\n\t\t\t\tREPEAT 0\n"))
P["g_border"] = pagina(controles=GRUPO.format("\t\t\t\tBORDER ALL\n\t\t\t\tAS LINES\n\t\t\t\tREPEAT 0\n"))
P["g_grid"] = pagina(controles=GRUPO.format("\t\t\t\tBORDER ALL\n\t\t\t\tGRID VERTICAL HORIZONTAL\n\t\t\t\tAS LINES\n\t\t\t\tREPEAT 0\n"))
P["g_repeat"] = pagina(controles=GRUPO.format("\t\t\t\tAS LINES\n\t\t\t\tREPEAT 3\n"))
P["b_box"] = pagina(controles=control("BOX", "", nombre=""))
P["dos_paginas"] = pagina(extra="\tpg2 is Page begin\n\t\tobjects begin\n\t\tend\n\t\tINTERFACE\n\t\t\tSIZE 595 842\n\t\t\tMARGIN 0 0 0 0\n"
                          "\t\tBEGIN\n" + texto('TAGS "y"') + "\t\tEND\n\tend\n")
# --- ampliación (familia de páginas): bordes de página «BORDER [DOWNSHADOW|UPSHADOW] [DOUBLE] [ALL|lados]»,
# hermanos, BOX con hijos, GROUP BYCOLS, SEPARATOR DOUBLELINE/SOLID y VAR con LIKEVAR y DATATYPE
for b in ["DOWNSHADOW", "UPSHADOW", "DOWNSHADOW ALL", "UPSHADOW ALL", "DOUBLE", "DOUBLE ALL", "DOWNSHADOW DOUBLE ALL",
          "TOP", "BOTTOM", "LEFT", "RIGHT", "TOP BOTTOM", "LEFT RIGHT", "DOWNSHADOW TOP"]:
    P["t_border_" + b.lower().replace(" ", "_")] = pagina(controles=texto(f'BORDER {b}\nTAGS "x"'))
for nombre, a in [("multiline", 'MULTILINE\nTAGS "x" "y"'), ("italic", 'FONT "Arial" 12 ITALIC\nTAGS "x"'),
                  ("bold_italic", 'FONT "Arial" 22 BOLD ITALIC\nTAGS "x"'), ("attach", 'ATTACH LEFT RIGHT\nTAGS "x"'),
                  ("default", 'BACKGROUND COLOR default\nTAGS "x"'), ("foreground", 'FOREGROUND RGB 1 2 3\nTAGS "x"')]:
    P[f"t_{nombre}"] = pagina(controles=texto(a))
P["t_dos"] = pagina(controles=texto('TAGS "x"') + texto('TAGS "y"').replace("10 10 50 20", "10 40 50 20"))
P["t_tres"] = pagina(controles=texto('TAGS "x"') + texto('TAGS "y"').replace("10 10 50 20", "10 40 50 20")
                     + texto('TAGS "z"').replace("10 10 50 20", "10 70 50 20"))


def caja(atributos, hijos=None, tipo="BOX", nombre=""):
    if hijos is None:
        hijos = texto('TAGS "x"')
    return (control(tipo, atributos, nombre=nombre, posicion="10 10 200 100").replace("CONTROL  AS", "CONTROL AS")
            + "\t\t\tBEGIN\n" + hijos.replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")


for nombre, a in [("con_hijo", ""), ("nolabel", "NOLABEL"), ("border_all", "BORDER ALL"),
                  ("border_downshadow_all", "BORDER DOWNSHADOW ALL"), ("transparent", "BACKGROUND COLOR transparent"),
                  ("attach", "ATTACH LEFT RIGHT"), ("almafac", "BACKGROUND COLOR transparent\nNOLABEL\nBORDER DOWNSHADOW ALL")]:
    P[f"b_{nombre}"] = pagina(controles=caja(a))
P["b_dos_hijos"] = pagina(controles=caja("NOLABEL", texto('TAGS "x"') + texto('TAGS "y"').replace("10 10 50 20", "10 40 50 20")))
P["b_nombre"] = pagina(controles=caja("NOLABEL", nombre="cb"))
P["b_y_texto"] = pagina(controles=caja("NOLABEL") + texto('TAGS "z"').replace("10 10 50 20", "10 120 50 20"))
P["b_dentro_de_b"] = pagina(controles=caja("NOLABEL", caja("BORDER ALL")))
LINEAS = "AS LINES\nREPEAT 0"
for nombre, a in [("bycols", "REPEAT 0\nBYCOLS"), ("nolabel", "NOLABEL\n" + LINEAS), ("downshadow", "BORDER DOWNSHADOW\n" + LINEAS),
                  ("transparent", "BACKGROUND COLOR transparent\n" + LINEAS),
                  ("almafac", "BACKGROUND COLOR transparent\nNOLABEL\nBORDER DOWNSHADOW\nREPEAT 0\nBYCOLS")]:
    P[f"g_{nombre}"] = pagina(controles=caja(a, tipo="GROUP"))
P["g_con_box"] = pagina(controles=caja("NOLABEL\nREPEAT 0\nBYCOLS", caja("NOLABEL\nBORDER DOWNSHADOW ALL"), tipo="GROUP"))
for a in ["DOUBLELINE", "SOLID", "THICKLINE\nSOLID", "ATTACH LEFT RIGHT"]:
    P["s_" + a.lower().replace("\n", "_").replace(" ", "_")] = pagina(controles=control("SEPARATOR", a, nombre="", posicion="10 10 100 2"))
for nombre, a in [("char_35", "NOLABEL\nDATATYPE CHAR(35)"), ("decimal", "NOLABEL\nDATATYPE DECIMAL(8,2)"),
                  ("date", "NOLABEL\nDATATYPE DATE"), ("mask", "NOLABEL\nDATATYPE INTEGER MASK 2"),
                  ("nolabel_label", 'NOLABEL\nLABEL "Nombre"\nDATATYPE CHAR(35)')]:
    P[f"v_{nombre}"] = pagina(controles=control("VAR", a, nombre="v"))
P["v_likevar"] = pagina(objetos="n as Smallint", controles=control("VAR", 'LABEL "l"\nVARIABLE n\nLIKEVAR', nombre="v"))
P["v_variable_char"] = pagina(objetos="n as Char(10)", controles=control("VAR", "NOLABEL\nVARIABLE n\nALIGNMENT RIGHT\nDATATYPE CHAR", nombre="v"))
# --- segunda tanda (lo que paró a los proyectos): icono en un BOX, GROUP sin AS LINES ni BYCOLS, GRID de un
# solo sentido, PAGE y UPSHIFT en VAR, y BANDGROUP
P["b_icon"] = pagina(controles=caja('NOLABEL\nICON 3 FILE "_MBSTDBMP_" CENTER', hijos=""))
P["b_icon_sin_center"] = pagina(controles=caja('NOLABEL\nICON 3 FILE "_MBSTDBMP_"', hijos=""))
P["b_icon_vertical"] = pagina(controles=caja('NOLABEL\nICON 2 FILE "_MBSTDBMP_" CENTER VERTICAL', hijos=""))
P["g_solo_repeat"] = pagina(controles=caja("REPEAT 0", tipo="GROUP"))
P["g_solo_repeat_3"] = pagina(controles=caja("NOLABEL\nBORDER DOWNSHADOW ALL\nREPEAT 3", tipo="GROUP"))
P["g_grid_vertical"] = pagina(controles=caja("BORDER ALL\nGRID VERTICAL\n" + LINEAS, tipo="GROUP"))
P["g_grid_horizontal"] = pagina(controles=caja("BORDER ALL\nGRID HORIZONTAL\n" + LINEAS, tipo="GROUP"))
P["v_page"] = pagina(controles=control("VAR", 'PAGE 2\nLABEL "l"\nDATATYPE SMALLINT', nombre="v"))
P["v_upshift"] = pagina(controles=control("VAR", "NOLABEL\nUPSHIFT\nDATATYPE CHAR", nombre="v"))
for nombre, a in [("base", ""), ("nolabel", "NOLABEL"), ("border_all", "BORDER ALL"), ("autosize", "AUTOSIZE"),
                  ("transparent", "BACKGROUND COLOR transparent"),
                  ("stockmdi", "BACKGROUND COLOR transparent\nNOLABEL\nATTACH ALL\nBORDER ALL\nAUTOSIZE")]:
    P[f"bg_{nombre}"] = pagina(controles=caja(a, caja("BACKGROUND COLOR transparent\nNOLABEL"), tipo="BANDGROUP"))
# --- tercera tanda: PAGE en TEXT y en un hijo de GROUP; MASK de un número sobre una variable (+0x40)
P["t_page"] = pagina(controles=texto('PAGE 2\nTAGS "x"'))
P["g_hijo_page"] = pagina(controles=caja(LINEAS, texto('PAGE 2\nBOLD\nTAGS "x"'), tipo="GROUP"))
P["v_smallint_mask"] = pagina(controles=control("VAR", "NOLABEL\nDATATYPE SMALLINT MASK 2", nombre="v"))
P["v_variable_mask"] = pagina(objetos="n as Smallint", controles=control("VAR", "NOLABEL\nVARIABLE n\nALIGNMENT RIGHT\nDATATYPE SMALLINT MASK 2", nombre="v"))
P["v_variable_smallint"] = pagina(objetos="n as Smallint", controles=control("VAR", "NOLABEL\nVARIABLE n\nALIGNMENT RIGHT\nDATATYPE SMALLINT", nombre="v"))
P["v_variable_integer_mask"] = pagina(objetos="n as Integer", controles=control("VAR", "NOLABEL\nVARIABLE n\nDATATYPE INTEGER MASK 2", nombre="v"))
P["v_variable_date_mask"] = pagina(objetos="n as Date", controles=control("VAR", "NOLABEL\nVARIABLE n\nDATATYPE DATE MASK 5", nombre="v"))
for nombre, dt in [("smallint_6", "SMALLINT(6) MASK 2"), ("smallint_3", "SMALLINT(3)"), ("integer_10", "INTEGER(10)"),
                   ("date_8", "DATE(8)")]:
    P[f"v_{nombre}"] = pagina(controles=control("VAR", f"NOLABEL\nDATATYPE {dt}", nombre="v"))
P["e_edit_smallint_6"] = _f.form(controles=control("EDIT", "DATATYPE SMALLINT(6)"))
P["v_variable_otro_tipo"] =pagina(objetos="n as Integer", controles=control("VAR", "NOLABEL\nVARIABLE n\nDATATYPE SMALLINT MASK 2", nombre="v"))

# --- cuarta tanda: orden de NOLABEL/LABEL, ATTACH y PAGE (ALMAFAC LPROART: SEPARATOR con ATTACH y PAGE)
P["v_label_page"] = pagina(controles=control("VAR", 'LABEL "l"\nPAGE 2\nDATATYPE SMALLINT', nombre="v"))
P["s_attach_page"] = pagina(controles=control("SEPARATOR", "ATTACH LEFT RIGHT\nPAGE 2\nTHICKLINE", nombre="", posicion="10 10 100 2"))
P["t_attach_page"] = pagina(controles=texto('ATTACH LEFT RIGHT\nPAGE 2\nTAGS "x"'))
P["b_nolabel_attach_page"] = pagina(controles=caja("NOLABEL\nATTACH ALL\nPAGE 2"))
# VAR con borde de página (STOCKMDI item_rep1: BORDER DOUBLE TOP BOTTOM, BORDER TOP BOTTOM), al final
for b in ["DOUBLE TOP BOTTOM", "TOP BOTTOM", "ALL", "DOWNSHADOW", "DOUBLE"]:
    P["v_border_" + b.lower().replace(" ", "_")] = pagina(controles=control("VAR", f'LABEL "l"\nBORDER {b}\nDATATYPE CHAR', nombre="v"))
P["v_border_likevar"] = pagina(objetos="n as Smallint", controles=control("VAR", 'LABEL "l"\nBORDER TOP BOTTOM\nVARIABLE n\nLIKEVAR', nombre="v"))
# --- GROUP con AUTOSIZE y FIXED (samples BOOLOP, PAG), al final
for a in ["NOLABEL\nBORDER ALL\nAUTOSIZE\nREPEAT 9\nFIXED", "NOLABEL\nBORDER DOWNSHADOW ALL\nAUTOSIZE\nREPEAT 0", "AUTOSIZE\nREPEAT 0",
          "REPEAT 0\nAUTOSIZE", "REPEAT 3\nFIXED", "FIXED\nREPEAT 3", "AS LINES\nREPEAT 0\nFIXED", "AUTOSIZE\nAS LINES\nREPEAT 0",
          "AS LINES\nAUTOSIZE\nREPEAT 0", "AUTOSIZE\nREPEAT 3\nBYCOLS", "REPEAT 3\nBYCOLS\nFIXED"]:
    P["pga_" + a.lower().replace("\n", "_").replace(" ", "_")] = pagina(controles=GRUPO.format("".join(f"\t\t\t\t{x}\n" for x in a.split("\n"))))
# --- TEXT con WRAP y CHARSET (samples Impresionpdfmulticharset), al final
for a in ['MULTILINE\nWRAP\nTAGS "x"', 'WRAP\nTAGS "x"', 'WRAP\nMULTILINE\nTAGS "x"', 'TAGS "x"\nWRAP',
          'FONT "Arial" 12 CHARSET Russian\nTAGS "x"', 'ALIGNMENT CENTER\nMULTILINE\nWRAP\nTAGS "x"']:
    P["ptw_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = pagina(controles=texto(a))
# --- CHECK y BITMAP de página (samples EjReportProv, LISTADOCAJA, EjPrintChart), al final
for a in ["", "BORDER ALL", 'LABEL "x"', "NOLABEL", "NOLABEL\nBORDER ALL", "BORDER ALL\nNOLABEL", "ATTACH ALL"]:
    P["pck_" + ("".join(ch if ch.isalnum() else "_" for ch in a.lower()) or "base")] = pagina(controles=control("CHECK", a, nombre="c"))
P["pck_variable"] = pagina(objetos="n as Boolean", controles=control("CHECK", "VARIABLE n", nombre="c"))
for a in ["", "NOLABEL", "STRETCH", "NOLABEL\nBORDER DOWNSHADOW ALL\nSTRETCH", "NOLABEL\nSTRETCH\nBORDER DOWNSHADOW ALL",
          "BORDER ALL"]:
    P["pbm_" + ("".join(ch if ch.isalnum() else "_" for ch in a.lower()) or "base")] = pagina(controles=control("BITMAP", a, nombre="b"))
P["pbm_begin_end"] = pagina(controles=caja("NOLABEL\nBORDER DOWNSHADOW ALL\nSTRETCH", hijos="", tipo="BITMAP", nombre="b"))
# --- BOX con CURRENT PAGE (samples OpenPrinterPdf, EJSETGROUPEXPORTDATAREPORT), al final
HIJO_P2 = texto('PAGE 2\nTAGS "x"')
for a in ["NOLABEL\nCURRENT PAGE 2", "CURRENT PAGE 2\nNOLABEL", "NOLABEL\nBORDER ALL\nCURRENT PAGE 2",
          "NOLABEL\nCURRENT PAGE 2\nBORDER ALL", "NOLABEL\nCURRENT PAGE 3", "BACKGROUND COLOR transparent\nNOLABEL\nCURRENT PAGE 2"]:
    P["pbx_" + a.lower().replace("\n", "_").replace(" ", "_")] = pagina(controles=caja(a, hijos=HIJO_P2))
# --- VERTICALTEXT de un TEXT (samples EjReportProv), CHARSET Gb (Impresionpdfmulticharset) y GROUP con BOLD
# (EjPrintChart), al final
for a in ['TAGS "x"\nVERTICALTEXTLEFT', 'TAGS "x"\nVERTICALTEXTRIGHT', 'VERTICALTEXTLEFT\nTAGS "x"', 'MULTILINE\nTAGS "x"\nVERTICALTEXTLEFT',
          'WRAP\nTAGS "x"\nVERTICALTEXTRIGHT', 'FONT "FangSong" 12 CHARSET Gb\nTAGS "x"']:
    P["pvt_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = pagina(controles=texto(a))
for a in ["BOLD\nBORDER ALL\nGRID VERTICAL HORIZONTAL\nAS LINES\nREPEAT 0", "BOLD\nAS LINES\nREPEAT 0",
          "BACKGROUND COLOR transparent\nBOLD\nBORDER ALL\nAS LINES\nREPEAT 0"]:
    P["pgb_" + a.lower().replace("\n", "_").replace(" ", "_")] = pagina(controles=GRUPO.format("".join(f"\t\t\t\t{x}\n" for x in a.split("\n"))))

# --- BOXGROUP de página (samples LISTADOCAJA), al final
for a in ["NOLABEL\nNUMBER 1 COLUMNS 1\nBORDER ALL\n\tBOX", "NUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nNUMBER 1 COLUMNS 1\n\tBOX",
          "NOLABEL\nNUMBER 2 COLUMNS 1\n\tBOX\n\tBOX", 'NUMBER 2 COLUMNS 1\n\tBOX LABEL "1"\n\tBOX LABEL "2"',
          'NUMBER 2 ROWS 1\n\tBOX LABEL "1"\n\tBOX LABEL "2"', "NOLABEL\nNUMBER 1 COLUMNS 1\nBORDER DOWNSHADOW ALL\n\tBOX",
          "NOLABEL\nNUMBER 1 COLUMNS 1\nBORDER TOP BOTTOM\n\tBOX", "NOLABEL\nBORDER ALL\nNUMBER 1 COLUMNS 1\n\tBOX",
          'NUMBER 2 COLUMNS 1\n\tBOX BACKGROUND COLOR red\n\tBOX LABEL "2"', "NOBORDER\nNUMBER 1 COLUMNS 1\n\tBOX",
          "ATTACH ALL\nNUMBER 1 COLUMNS 1\n\tBOX", 'NUMBER 1 COLUMNS 1\nBORDER ALL\n\tBOX LABEL "a"',
          "CLICKTYPE RADIO\nNUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nNUMBER 4 COLUMNS 2\n\tBOX\n\tBOX\n\tBOX\n\tBOX",
          "BACKGROUND COLOR transparent\nNOLABEL\nNUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nPAGE 2\nNUMBER 1 COLUMNS 1\n\tBOX",
          'LABEL "t"\nNUMBER 1 COLUMNS 1\n\tBOX', 'NUMBER 2 COLUMNS 1\n\tBOX LABEL ""\n\tBOX LABEL "2"']:
    P["pxg_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = pagina(controles=control("BOXGROUP", a, nombre="x", posicion="10 10 200 100"))

# --- FRAMEAUTOSIZE del BOXGROUP de página (familia «ventana», 2026-10-31), al final (prefijo pvw_)
for a in ["NOLABEL\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\nBORDER ALL\n\tBOX",
          "FRAMEAUTOSIZE\nNOLABEL\nNUMBER 1 COLUMNS 1\n\tBOX", 'FRAMEAUTOSIZE\nNUMBER 2 COLUMNS 1\n\tBOX LABEL "1"\n\tBOX LABEL "2"',
          "AUTOSIZE\nFRAMEAUTOSIZE\nNOLABEL\nNUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nAUTOSIZE\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX",
          "NOLABEL\nFRAMEAUTOSIZE\nAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX"]:
    P["pvw_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = pagina(controles=control("BOXGROUP", a, nombre="x", posicion="10 10 200 100"))

# segunda tanda: con ATTACH, PAGE y el borde del control
for a in ["NOLABEL\nATTACH ALL\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nPAGE 2\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX",
          "NOLABEL\nBORDER ALL\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX", "NOLABEL\nFRAMEAUTOSIZE\nBORDER ALL\nNUMBER 1 COLUMNS 1\n\tBOX",
          "NOLABEL\nAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX", "BOLD\nNOLABEL\nFRAMEAUTOSIZE\nNUMBER 1 COLUMNS 1\n\tBOX"]:
    P["pvw2_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = pagina(controles=control("BOXGROUP", a, nombre="x", posicion="10 10 200 100"))


# --- geometría que parece una declaración (como en fct.py, geo_), al final: x o ancho 256 con y (o alto) por 4 en el
# registro de IDE de Trace, que no se declara (y sale del hueco de cada variante, como en fct.py)
def _geometria(posicion):
    return pagina(controles=control("TEXT", 'TAGS "x"', nombre="t", posicion=posicion)).replace(
        "begin\nend\n//{{CODEEND", 'begin\n    "x".Trace();\nend\n//{{CODEEND')


for nombre, pos in [("x_trace32", "256 14 225 22"), ("x_trace64", "256 16 225 22"), ("255_trace32", "255 11 225 22"),
                    ("ancho_trace32", "10 10 256 13"), ("ancho_trace64", "10 10 256 12")]:
    P["pgeo_" + nombre] = _geometria(pos)


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

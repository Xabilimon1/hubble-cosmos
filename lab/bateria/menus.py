"""Batería de menús: `menu x PULLDOWN BEGIN … END` dentro de un formulario (entre su objects y su
INTERFACE), `default menu`, el control MENU de una barra y las clases `X is Menu`. Un cambio por
programa sobre `m_base`. Uso: python3 -I menus.py <dir salida> <huecos.txt> [desde]
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control


def arbol(items, n=3):
    """items: líneas ya formadas (con sus propios BEGIN/END); se sangran a partir de n."""
    return "".join("\t" * n + l + "\n" for l in items)


def con_menu(menus, default=None, controles="", eventos=""):
    texto = form(controles=controles, eventos=eventos)
    if default:
        texto = texto.replace("\tf is Form begin\n", f"\tf is Form begin\n\t\tdefault menu {default}\n")
    return texto.replace("\t\tINTERFACE\n", "".join(menus) + "\t\tINTERFACE\n")


def menu(nombre, items, tipo="PULLDOWN", cabecera=()):
    """cabecera: atributos del menú entre `menu x` y el PULLDOWN (ICONFILE, ALLOWICON…). tipo "": sin PULLDOWN."""
    return (f"\t\tmenu {nombre}\n" + "".join(f"\t\t\t{c}\n" for c in cabecera) + (f"\t\t{tipo}\n" if tipo else "") + "\t\t\tBEGIN\n"
            + arbol(items, 4) + "\t\t\tEND\n")


A = ['OPTION', '\t"a"']
P = {}
P["m_base"] = con_menu([menu("m", A)])
P["m_dos_opciones"] = con_menu([menu("m", A + ['OPTION', '\t"b"'])])
P["m_opcion_nombre"] = con_menu([menu("m", ['OPTION x', '\t"a"'])])
P["m_otro_texto"] = con_menu([menu("m", ['OPTION', '\t"otro"'])])
P["m_command"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tCOMMAND Close'])])
P["m_command_usuario"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tCOMMAND MiComando'])])
P["m_separator"] = con_menu([menu("m", A + ['SEPARATOR', 'OPTION', '\t"b"'])])
P["m_checked"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tCHECKED'])])
P["m_submenu"] = con_menu([menu("m", ['MENU', '\t"s"', '\tBEGIN', '\t\tOPTION', '\t\t\t"a"', '\tEND'])])
P["m_submenu_nombre"] = con_menu([menu("m", ['MENU s', '\t"s"', '\tBEGIN', '\t\tOPTION', '\t\t\t"a"', '\tEND'])])
P["m_submenu_y_opcion"] = con_menu([menu("m", ['MENU', '\t"s"', '\tBEGIN', '\t\tOPTION', '\t\t\t"a"', '\tEND', 'OPTION', '\t"b"'])])
P["m_popup"] = con_menu([menu("m", A, "POPUP")])
P["m_dos_menus"] = con_menu([menu("m", A), menu("n", ['OPTION', '\t"b"'])])
P["m_default"] = con_menu([menu("m", A)], default="m")
P["m_control"] = con_menu([menu("m", A)], controles="\t\t\tCONTROL AS BAR\n\t\t\t\tPOSITION 0 0 100 30\n\t\t\t\tBARTYPE MENU\n\t\t\tBEGIN\n"
                          "\t\t\t\tCONTROL AS MENU\n\t\t\t\t\tPOSITION 0 0 90 24\n\t\t\t\t\tMENU m\n\t\t\tEND\n")
P["m_uso"] = con_menu([menu("m", A)], eventos="On Open\nbegin\n    self.SetMenu(m);\nend\n")
# Cabecera del menú y atributos de opción: todas las palabras de menú que escribe el compilador
# («"%s" SEPARATOR DISABLED CHECKED ICON %d HELP "%s" COMMAND %s ICONFILE "%s" DEFAULT ICON %d ALLOWICON
# ALLOWCHECK PULLDOWN NOLABEL NOWAIT»), cada una sola y algunas juntas.
IF = 'ICONFILE "_MBSTDBMP_"'
P["h_iconfile"] = con_menu([menu("m", A, cabecera=[IF])])
P["h_iconfile_otro"] = con_menu([menu("m", A, cabecera=['ICONFILE "_MBSTDLIS_"'])])
P["h_allowicon"] = con_menu([menu("m", A, cabecera=[IF, "ALLOWICON"])])
P["h_allowicon_solo"] = con_menu([menu("m", A, cabecera=["ALLOWICON"])])
P["h_allowcheck"] = con_menu([menu("m", A, cabecera=["ALLOWCHECK"])])
P["h_allowicon_allowcheck"] = con_menu([menu("m", A, cabecera=[IF, "ALLOWICON", "ALLOWCHECK"])])
P["h_default_icon"] = con_menu([menu("m", A, cabecera=[IF, "DEFAULT ICON 5"])])
# NOLABEL y NOWAIT van en la línea del PULLDOWN (en la cabecera o en una opción: error de sintaxis).
P["h_nolabel"] = con_menu([menu("m", A, "PULLDOWN NOLABEL")])
P["h_nowait"] = con_menu([menu("m", A, "PULLDOWN NOWAIT")])
P["h_nolabel_nowait"] = con_menu([menu("m", A, "PULLDOWN NOLABEL NOWAIT")])
P["o_icon"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tICON 6'], cabecera=[IF, "ALLOWICON"])])
P["o_icon_otro"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tICON 157'], cabecera=[IF, "ALLOWICON"])])
P["o_icon_sin_cabecera"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tICON 6'])])
P["o_disabled"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tDISABLED'])])
P["o_help"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tHELP "ayuda"'])])
P["o_separator_dentro"] = con_menu([menu("m", ['OPTION', '\t"a"', 'OPTION', '\t"b"', '\tSEPARATOR'])])
P["o_todo"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tSEPARATOR', '\tDISABLED', '\tCHECKED', '\tICON 3',
                                   '\tHELP "h"', '\tCOMMAND Close'], cabecera=[IF, "ALLOWICON", "ALLOWCHECK"])])
P["o_submenu_icon"] = con_menu([menu("m", ['MENU', '\t"s"', '\tICON 7', '\tBEGIN', '\t\tOPTION', '\t\t\t"a"',
                                           '\t\t\tICON 8', '\tEND'], cabecera=[IF, "ALLOWICON"])])


def sub(*atributos):
    """Un submenú con atributos de cabecera detrás de su texto (como el MENU pepe de ALMAFAC)."""
    return ['MENU', '\t"s"', *(f"\t{a}" for a in atributos), '\tBEGIN', '\t\tOPTION', '\t\t\t"a"', '\tEND']


P["s_iconfile"] = con_menu([menu("m", sub(IF))])
P["s_allowicon"] = con_menu([menu("m", sub("ALLOWICON"))])
P["s_allowcheck"] = con_menu([menu("m", sub("ALLOWCHECK"))])
P["s_default_icon"] = con_menu([menu("m", sub(IF, "DEFAULT ICON 4"))])
P["s_todo"] = con_menu([menu("m", sub(IF, "DEFAULT ICON 2", "ALLOWICON", "ALLOWCHECK"))])
P["s_icon_e_iconfile"] = con_menu([menu("m", sub("ICON 9", IF, "ALLOWICON"))])
CLASE = ("CONSTANTS  begin\nend\nCLASSES BEGIN\n\tmc is Menu\n\tPULLDOWN\n\t\tBEGIN\nITEMS\t\tEND\nEND\n"
         "CODE CLASS mc BEGIN\n//{{CODEBEGIN\n//{{CODEEND\nEND\nCODE BEGIN\n//{{CODEBEGIN\nmain\nbegin\nend\n//{{CODEEND\nEND\n")
P["c_base"] = CLASE.replace("ITEMS", arbol(A, 3))
P["c_dos"] = CLASE.replace("ITEMS", arbol(A + ['OPTION', '\t"b"'], 3))
# --- sin PULLDOWN (raíz 0x89084002: sin el 0x40; STOCKMDI frmtmpl, ALMAFAC3 albaran) y con título («"Open"» detrás
# de `menu x`: raíz +0x18 → STR; TryThisOneFirst Menu_examples)
BARRA = ("\t\t\tCONTROL AS BAR\n\t\t\t\tPOSITION 0 0 100 30\n\t\t\t\tBARTYPE MENU\n\t\t\tBEGIN\n"
         "\t\t\t\tCONTROL AS MENU\n\t\t\t\t\tPOSITION 0 0 90 24\n\t\t\t\t\tMENU m\n\t\t\tEND\n")
P["t_sin_pulldown"] = con_menu([menu("m", A, "")])
P["t_sin_pulldown_cabecera"] = con_menu([menu("m", ['OPTION', '\t"a"', '\tICON 6'], "", cabecera=[IF, "ALLOWICON"])])
P["t_sin_pulldown_default"] = con_menu([menu("m", A, "")], default="m", controles=BARRA)
P["t_sin_pulldown_submenu"] = con_menu([menu("m", sub("ALLOWICON") + ['OPTION', '\t"b"'], "")])
P["t_sin_pulldown_allowcheck"] = con_menu([menu("m", A, "", cabecera=["ALLOWCHECK"])])
P["t_titulo"] = con_menu([menu("m", A, cabecera=['"Open"'])])
P["t_titulo_cabecera"] = con_menu([menu("m", A, cabecera=['"Open"', IF, "ALLOWICON"])])
P["t_titulo_sin_pulldown"] = con_menu([menu("m", A, "", cabecera=['"Open"'])])
P["t_titulo_detras"] = con_menu([menu("m", A, cabecera=[IF, '"Open"'])])
P["t_nolabel_sin_pulldown"] = con_menu([menu("m", A, "NOLABEL")])


# --- AUTOSIZE del control MENU de una barra (ALMAFAC2 FRMTMPL: `ICON CENTER VERTICAL` / `AUTOSIZE` / `MENU menuForm`;
# Hubble lo escribía detrás de `MENU x` y no compilaba: «Actual autosize(AUTOSIZE). Expecting control, end»), al final.
# Su sitio frente a cada atributo que el control MENU puede llevar, en los dos órdenes.
def barra_mau(antes="", despues=""):
    """Control MENU de una BAR BARTYPE MENU con atributos delante y detrás de `MENU m`."""
    def lineas(a):
        return "".join(f"\t\t\t\t\t{x}\n" for x in a.split("\n") if x)
    return con_menu([menu("m", A)], controles="\t\t\tCONTROL AS BAR\n\t\t\t\tPOSITION 0 0 100 30\n\t\t\t\tBARTYPE MENU\n"
                    "\t\t\tBEGIN\n\t\t\t\tCONTROL AS MENU\n\t\t\t\t\tPOSITION 0 0 90 24\n" + lineas(antes)
                    + "\t\t\t\t\tMENU m\n" + lineas(despues) + "\t\t\tEND\n")


P["mau_autosize"] = barra_mau("AUTOSIZE")
P["mau_menu_autosize"] = barra_mau("", "AUTOSIZE")  # lo que escribía Hubble
for nombre, otro in [("icon", "ICON CENTER VERTICAL"), ("button_border", "BUTTON\nBORDER HILIGHT"), ("vertical", "VERTICAL"),
                     ("noborder", "NOBORDER"), ("border_etched", "BORDER ETCHED"), ("attach", "ATTACH ALL"),
                     ("fg", "FOREGROUND RGB 0 0 0"), ("invisible", "INVISIBLE"), ("cursor", "CURSOR")]:
    P[f"mau_{nombre}_autosize"] = barra_mau(otro + "\nAUTOSIZE")
    P[f"mau_autosize_{nombre}"] = barra_mau("AUTOSIZE\n" + otro)
P["mau_icon_button_border_autosize"] = barra_mau("ICON VERTICAL\nBUTTON\nBORDER HILIGHT\nAUTOSIZE")
P["mau_icon_autosize_button_border"] = barra_mau("ICON VERTICAL\nAUTOSIZE\nBUTTON\nBORDER HILIGHT")
P["mau_todo"] = barra_mau("FOREGROUND RGB 0 0 0\nATTACH ALL\nNOBORDER\nICON CENTER VERTICAL\nAUTOSIZE")  # ALMAFAC2 FRMTMPL
P["mau_todo_boton"] = barra_mau("FOREGROUND RGB 0 0 0\nATTACH ALL\nNOBORDER\nVERTICAL\nICON VERTICAL\nBUTTON\nBORDER HILIGHT\nAUTOSIZE")
P["mau_todo_autosize_boton"] = barra_mau("FOREGROUND RGB 0 0 0\nATTACH ALL\nNOBORDER\nVERTICAL\nICON VERTICAL\nAUTOSIZE\nBUTTON\nBORDER HILIGHT")


# --- ICON n de un CHECK con VARIABLE (STOCKMDI TRIPLE: `NOBORDER` / `VARIABLE orders.order_status` / `ICON 6` en un CHECK
# de una rejilla; Hubble escribía el icono delante de VARIABLE y no compilaba: «Actual variable(VARIABLE). Expecting
# control, end»), al final (fct.py no tiene huecos libres). Un CHECK de formulario con una variable Char, y el icono
# frente a lo que Hubble escribe alrededor de VARIABLE (AUTOSIZE y LABELLEFT delante; TAGS y LIKEVAR detrás); y el
# mismo par de órdenes en EDIT, BUTTON y BOX con `ICON n FILE "x"`.
def con_variable(atributos, tipo="CHECK"):
    return form(objetos="v as Char (1)", controles=control(tipo, atributos))


P["kic_var_icon"] = con_variable("VARIABLE v\nICON 6")
P["kic_icon_var"] = con_variable("ICON 6\nVARIABLE v")  # lo que escribía Hubble
P["kic_triple"] = con_variable('LABEL "Invoiced"\nNOBORDER\nVARIABLE v\nICON 6')  # el CHECK de STOCKMDI TRIPLE
P["kic_triple_hubble"] = con_variable('LABEL "Invoiced"\nNOBORDER\nICON 6\nVARIABLE v')
for nombre, a in [("autosize_var_icon", "AUTOSIZE\nVARIABLE v\nICON 6"), ("var_icon_autosize", "VARIABLE v\nICON 6\nAUTOSIZE"),
                  ("var_autosize_icon", "VARIABLE v\nAUTOSIZE\nICON 6"),
                  ("labelleft_var_icon", "LABELLEFT\nVARIABLE v\nICON 6"), ("var_icon_labelleft", "VARIABLE v\nICON 6\nLABELLEFT"),
                  ("var_icon_tags", 'VARIABLE v\nICON 6\nTAGS "a"'), ("var_tags_icon", 'VARIABLE v\nTAGS "a"\nICON 6'),
                  ("icon_tags", 'ICON 6\nTAGS "a"'), ("tags_icon", 'TAGS "a"\nICON 6'),
                  ("var_icon_likevar", "VARIABLE v\nICON 6\nLIKEVAR"), ("var_likevar_icon", "VARIABLE v\nLIKEVAR\nICON 6"),
                  ("todo", 'INVISIBLE\nFOREGROUND RGB 0 0 255\nCURSOR\nATTACH ALL\nLABEL "x"\nLABELLEFT\nNOBORDER\nAUTOSIZE\nVARIABLE v\nICON 6\nTAGS "a"')]:
    P[f"kic_{nombre}"] = con_variable(a)
# EDIT, BUTTON y BOX: `ICON n FILE "x"` con VARIABLE, en los dos órdenes (y VARIABLE solo, por si no compila en ese tipo)
ICONO_F = 'ICON 2 FILE "_MBSTDBMP_"'
for c, tipo, resto in [("e", "EDIT", "\nDATATYPE CHAR"), ("b", "BUTTON", ""), ("x", "BOX", "")]:
    P[f"kic_{c}_var"] = con_variable("VARIABLE v" + resto, tipo)
    P[f"kic_{c}_var_icon"] = con_variable(f"VARIABLE v\n{ICONO_F}" + resto, tipo)
    P[f"kic_{c}_icon_var"] = con_variable(f"{ICONO_F}\nVARIABLE v" + resto, tipo)
# segunda tanda: TAGS y LIKEVAR no compilan en un CHECK (en ningún orden), y VARIABLE no compila en BUTTON ni BOX. El
# icono frente a AUTOSIZE sin VARIABLE, y frente a lo que Hubble escribe detrás de VARIABLE (ALIGNMENT, READONLY)
for nombre, a in [("autosize_icon", "AUTOSIZE\nICON 6"), ("icon_autosize", "ICON 6\nAUTOSIZE"),
                  ("var_icon_readonly", "VARIABLE v\nICON 6\nREADONLY"), ("var_readonly_icon", "VARIABLE v\nREADONLY\nICON 6"),
                  ("var_icon_alignment", "VARIABLE v\nICON 6\nALIGNMENT RIGHT"), ("var_alignment_icon", "VARIABLE v\nALIGNMENT RIGHT\nICON 6")]:
    P[f"kic2_{nombre}"] = con_variable(a)


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

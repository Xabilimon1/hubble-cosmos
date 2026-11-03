"""Batería de tipos de dato y de lo que quedó suelto tras controles.py: DATATYPE con precisión
y MASK, bordes de BUTTON, PANELTYPE, eventos sin control y `default null`. Un cambio por
programa sobre la base de su prefijo (`<x>_base`).

Uso: python3 -I datos.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
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
P["dt_base"] = form(controles=control("EDIT", "DATATYPE CHAR"))
for a in ["DECIMAL", "DECIMAL(9,2)", "DECIMAL(16,2)", "DECIMAL(5,0)", "DECIMAL(12,-1)", "DECIMAL MASK 4", "DECIMAL(9,2) MASK 4",
          "INTEGER MASK 1", "INTEGER MASK 3", "DATE MASK 4", "SMALLINT MASK 2", "CHAR MASK 1", "CHAR(10) MASK 1"]:
    P[clave("dt", a)] = form(controles=control("EDIT", "DATATYPE " + a))
P["dd_base"] = form(controles=control("DROPEDIT", "DATATYPE CHAR"))
P["dd_decimal_9_2"] = form(controles=control("DROPEDIT", "DATATYPE DECIMAL(9,2)"))
P["b_base"] = form(controles=control("BUTTON"))
for a in ["BORDER HILIGHT", "BORDER BLACK", "BORDER HILIGHT\nNOLABEL"]:
    P[clave("b", a)] = form(controles=control("BUTTON", a))
P["p_base"] = form(controles=control("PANEL"))
for a in ["PANELTYPE COMMENT", "PANELTYPE EDITMODE", "PANELTYPE DATE", "PANELTYPE TIME"]:
    P[clave("p", a)] = form(controles=control("PANEL", a))
BOTON = control("BUTTON")
P["e_base"] = form(controles=BOTON, eventos="On Click c\nbegin\nend\n")
P["e_click_sin_control"] = form(controles=BOTON, eventos="On Click (sender as char)\nbegin\nend\n")
P["e_click_sin_control_ni_param"] = form(controles=BOTON, eventos="On Click\nbegin\nend\n")
P["e_exit_sin_control"] = form(controles=control("EDIT", "DATATYPE CHAR"), eventos="On Exit (sender as char)\nbegin\nend\n")
MAIN = "CONSTANTS  begin\nend\nCODE BEGIN\n//{{CODEBEGIN\nmain\nobjects begin\n    a as TIPO\nend\nbegin\nend\n//{{CODEEND\nEND\n"
P["o_base"] = MAIN.replace("TIPO", "Char")
# o_char_default_null es `default "NULL"` (la versión con null daba la misma clave); el null de
# un Char va en f_char_default_null.
for a in ["Char default \"NULL\"", "Integer default null", "Char default \"x\"", "Decimal(9,2) default 1.5"]:
    P[clave("o", a)] = MAIN.replace("TIPO", a)
P["f_base"] = form(objetos="v as Char")
P["f_char_default_null"] = form(objetos="v as Char default null")
# --- paréntesis vacíos cuando el resultado lleva conversión implícita (la llamada se crea tarde)
SLIDER = control("SLIDER", "", nombre="s")
for nombre, tipo, expr in [("par_slider_smallint", "Smallint", "s.Min()"), ("sin_slider_smallint", "Smallint", "s.Min"),
                           ("par_slider_integer", "Integer", "s.Min()"), ("sin_slider_integer", "Integer", "s.Min")]:
    P[nombre] = form(objetos=f"a as {tipo}", controles=SLIDER, eventos=f"On Open\nbegin\n    a = {expr};\nend\n")
for nombre, tipo, expr in [("par_len_smallint", "Smallint", "b.Length()"), ("sin_len_smallint", "Smallint", "b.Length"),
                           ("par_len_integer", "Integer", "b.Length()"), ("sin_len_integer", "Integer", "b.Length")]:
    P[nombre] = MAIN.replace("    a as TIPO\n", f"    a as {tipo}\n    b as Char\n").replace("begin\nend\n//", f"begin\n    a = {expr};\nend\n//")
P["asig_doble"] = MAIN.replace("    a as TIPO\n", "    a b as Integer\n").replace("begin\nend\n//", "begin\n    a = b = 1;\nend\n//")
# --- segunda tanda (al final, para no mover los huecos): DATATYPE TIME (dato 4: AGENDA mes `TIME MASK 3`,
# OutlookActiveX `TIME`), y de paso los demás tipos que el compilador pueda tener tras DATE
for a in ["TIME", "TIME MASK 1", "TIME MASK 3", "TIME(8)", "DATETIME", "MONEY", "BOOLEAN", "FLOAT"]:
    P[clave("dt2", a)] = form(controles=control("EDIT", "DATATYPE " + a))
P["dd_time"] = form(controles=control("DROPEDIT", "DATATYPE TIME"))
P["tx_time"] = form(controles=control("TEXT", "DATATYPE TIME"))


# --- familia «codigo» del vocabulario (2026-10-31), al final: PANELTYPE OPERATION (editor visual Victrpro.drw:
# «General|Comment|Message|EditMode|Operation»)
P["pop_operation"] = form(controles=control("PANEL", "PANELTYPE OPERATION"))
P["pop_message"] = form(controles=control("PANEL", "PANELTYPE MESSAGE"))
P["pop_operation_bar"] = form(controles=control("BAR", "BARTYPE STATUS") + "\t\t\tBEGIN\n"
                              + control("PANEL", "PANELTYPE OPERATION", nombre="").replace("CONTROL  AS", "CONTROL AS")
                              .replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")
P["pop_operation_label"] = form(controles=control("PANEL", 'LABEL "x"\nPANELTYPE OPERATION'))


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

"""Batería del control TAB (pestañas). Un cambio por programa sobre `t_base` (dos páginas, «a» y
«b»). Uso: python3 -I tabs.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control


def tab(atributos="", paginas=('TAB LABEL "a"', 'TAB LABEL "b"'), hijos=""):
    cuerpo = "".join(f"{a}\n" for a in atributos.split("\n") if a) + f"NUMBER {len(paginas)}\n" + "".join(f"\t{p}\n" for p in paginas)
    return form(controles=control("TAB", cuerpo, posicion="10 10 150 80") + "\t\t\tBEGIN\n" + hijos + "\t\t\tEND\n")


P = {}
P["t_base"] = tab()
for a in ["FIXED WIDTH 1", "FIXED WIDTH 2", "FIXED WIDTH 3", "FIXED WIDTH 5", "FIXED", "VERTICAL", "LOWTAB",
          "CURRENT PAGE 2", "BORDER DOUBLE", 'ICON FILE "_MBSTDBMP_" CENTER', 'ICON FILE "_MBSTDBMP_"', 'ICON FILE "Small Buttons" CENTER',
          'COMMENT "c"', 'FONT "Arial" 10']:
    P["t_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_")] = tab(a)
for nombre, paginas in [("una", ('TAB LABEL "a"',)), ("tres", ('TAB LABEL "a"', 'TAB LABEL "b"', 'TAB LABEL "c"')),
                        ("larga", ('TAB LABEL "abcdefghij"', 'TAB LABEL "b"')), ("acelerador", ('TAB LABEL "&a"', 'TAB LABEL "b"')),
                        ("ancha", ('TAB LABEL "WWWW"', 'TAB LABEL "b"'))]:
    P[f"t_paginas_{nombre}"] = tab(paginas=paginas)
ICONOS = 'ICON FILE "_MBSTDBMP_" CENTER'
for nombre, paginas in [("icono_2", ('TAB LABEL "a" ICON 2', 'TAB LABEL "b"')), ("icono_5", ('TAB LABEL "a" ICON 5', 'TAB LABEL "b"')),
                        ("icono_1_4", ('TAB LABEL "a" ICON 1', 'TAB LABEL "b" ICON 4'))]:
    P[f"t_{nombre}"] = tab(ICONOS, paginas)
EDIT = _f.control("EDIT", "DATATYPE CHAR", nombre="d", posicion="5 30 50 20").replace("\t\t\t", "\t\t\t\t")
P["t_hijo"] = tab(hijos=EDIT)
P["t_hijo_page_2"] = tab(hijos=EDIT.replace("POSITION 5 30 50 20\n", "POSITION 5 30 50 20\n\t\t\t\t\tPAGE 2\n"))
P["t_hijo_page_0"] = tab(hijos=EDIT.replace("POSITION 5 30 50 20\n", "POSITION 5 30 50 20\n\t\t\t\t\tPAGE 0\n"))
# Las páginas con LABEL "a|b" (sin NUMBER ni TAB LABEL: ALMAFAC2 FRMTMPL), al final
def tab_label(atributos="", label="a|b"):
    cuerpo = f'LABEL "{label}"\n' + "".join(f"{a}\n" for a in atributos.split("\n") if a)
    return form(controles=control("TAB", cuerpo, posicion="10 10 150 80") + "\t\t\tBEGIN\n\t\t\tEND\n")


P["t_label_ab"] = tab_label()
P["t_label_abc"] = tab_label(label="a|b|c")
P["t_label_lowtab"] = tab_label("LOWTAB")
P["t_label_doble"] = tab_label("BORDER DOUBLE FRAME\nLOWTAB", "Datos 1|Datos 2|....")
# `LABEL "a|b"` con `NUMBER 2` también compila, pero el compilador calcula el ancho de cada página sin su texto; el
# .omd no dice que hubiera NUMBER y sale sin él (otros anchos): fuera de la batería.
P["t_label_icono"] = tab_label('ICON FILE "_MBSTDBMP_" CENTER')
P["t_label_y_paginas"] = tab_label('NUMBER 2\n\tTAB LABEL "c"\n\tTAB LABEL "d"')


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

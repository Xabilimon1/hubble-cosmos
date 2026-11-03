"""Batería de comandos: un botón con `COMMAND x` por programa, para saber qué número da el
compilador a cada comando predefinido (los del usuario van a CMD).
Uso: python3 -I comandos.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control

COMANDOS = ["QueryByForm", "Query", "EditQuery", "EditQueryLike", "EditNew", "EditUpdate", "AcceptEdit", "CancelEdit",
            "Update", "Delete", "Close", "AscendingSort", "DescendingSort", "HideColumn", "ShowAllColumns", "ResetFilters",
            "FilterByColumn", "Next", "Previous", "First", "Last", "Print", "Export", "Find", "Help", "Ok", "Cancel",
            "New", "Add", "Insert", "Remove", "Save"]
P = {f"c_{c.lower()}": form(controles=control("BUTTON", f"COMMAND {c}")) for c in COMANDOS}
# `On Command (cmd as Char)`: el de cualquier comando (PRO de tipo 7 con +0x28 = 0; ALMAFAC auxiliar)
BOTON = control("BUTTON", "COMMAND Close")
CUERPO = 'begin\n    MessageBox(cmd, "t");\nend\n'
P["o_cualquiera"] = form(controles=BOTON, eventos="On Command (cmd as Char)\n" + CUERPO)
P["o_cualquiera_otro_nombre"] = form(controles=BOTON, eventos='On Command (c as Char)\nbegin\n    MessageBox(c, "t");\nend\n')
P["o_cualquiera_y_uno"] = form(controles=BOTON, eventos='On Command Close\nbegin\n    MessageBox("a", "t");\nend\n\n'
                                                       "On Command (cmd as Char)\n" + CUERPO)
P["o_cualquiera_locales"] = form(controles=BOTON, eventos="On Command (cmd as Char)\nobjects begin\n    x as Char\nend\n"
                                                         'begin\n    x = cmd;\n    MessageBox(x, "t");\nend\n')
P["o_sin_parametro"] = form(controles=BOTON, eventos='On Command\nbegin\n    MessageBox("a", "t");\nend\n')


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

"""Batería de comentarios de documentación {* … *} en módulos con clases: delante del primer procedimiento de un
CODE CLASS, delante de `main`, `@global` y entre procedimientos (STOCKMDI, almafac4).
Uso: python3 -I comentarios.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form = _f.form

ABRIR = "On Open\nbegin\n    SetEditMode(TRUE);\nend\n"
CERRAR = "On Close\nbegin\n    SetEditMode(FALSE);\nend\n"
MAIN = "main\nobjects begin\n    o as f\nend\n"


def con_main(texto, antes):
    """El comentario `antes` delante de `main`."""
    return texto.replace("//{{CODEBEGIN\n" + MAIN, "//{{CODEBEGIN\n" + antes + "\n" + MAIN, 1)


P = {}
P["k_base"] = form(eventos=ABRIR)
P["k_antes_del_primero"] = form(eventos="{*\n * Abre el formulario.\n *}\n" + ABRIR)
P["k_entre"] = form(eventos=ABRIR + "\n{*\n * Cierra.\n *}\n" + CERRAR)
P["k_antes_y_entre"] = form(eventos="{*\n * Uno.\n *}\n" + ABRIR + "\n{*\n * Dos.\n *}\n" + CERRAR)
P["k_antes_de_main"] = con_main(form(eventos=ABRIR), "{*\n * El programa.\n *}")
P["k_global"] = con_main(form(eventos=ABRIR), "{*\n * @global El módulo.\n *}")
P["k_antes_de_main_sin_eventos"] = con_main(form(), "{*\n * Sin eventos.\n *}")
# dos formularios, el primero sin procedimientos: el comentario delante del primero del segundo
_dos = form(eventos="").replace("\tend\nEND\nCODE CLASS f BEGIN", "\tend\n\tg is Form begin\n\t\tobjects begin\n\t\tend\n"
                                 "\t\tINTERFACE\n\t\t\tPOSITION 0 0 200 100\n\t\tBEGIN\n\t\tEND\n\tend\nEND\nCODE CLASS f BEGIN", 1)
P["k_seccion_vacia"] = _dos.replace("//{{CODEEND\nEND\nCODE BEGIN", "//{{CODEEND\nEND\nCODE CLASS g BEGIN\n//{{CODEBEGIN\n"
                                    "{*\n * De g.\n *}\n" + ABRIR + "//{{CODEEND\nEND\nCODE BEGIN", 1)


# con cadenas en los procedimientos, que fijan el sitio: entre dos del mismo CODE CLASS (exacto) y en la frontera
# entre el CODE CLASS y el CODE (cabe al final del uno o al principio del otro: aviso)
CON_A = 'On Open\nbegin\n    MessageBox("a", "b");\nend\n'
CON_C = 'On Close\nbegin\n    MessageBox("c", "d");\nend\n'
P["k_exacto"] = form(eventos=CON_A + "\n{*\n * Entre dos con cadenas.\n *}\n" + CON_C)
P["k_frontera"] = form(eventos=CON_A).replace('    o.Run;\n', '    o.Run;\n    MessageBox("e", "f");\n', 1).replace(
    "//{{CODEBEGIN\n" + MAIN, "//{{CODEBEGIN\n{*\n * En la frontera.\n *}\n" + MAIN, 1)


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

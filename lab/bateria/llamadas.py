"""Batería de llamadas: argumentos por defecto que pone el compilador (`f` frente a `f()` y `f(5)`, en
sentencia, en asignación y en condición; también los de métodos predefinidos como `o.Run`), y formas de
escribir lo mismo (`!=` / `<>`, `Ok` / `Module.Ok`, `public f` / `public f()`). Un cambio por programa sobre
`d_base`. Uso: python3 -I llamadas.py <dir salida> <huecos.txt>
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("genera", Path(__file__).with_name("genera.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
prog = _g.prog

F = "public f(x as integer default 5)\nbegin\nend\n\n"
G = "public g(x as integer default 0) return boolean\nbegin\n    return true;\nend\n\n"
H = "public h(x as integer default 0) return integer\nbegin\n    return x;\nend\n\n"
P = {}
P["d_base"] = prog(cuerpo="f(1);", funciones=F)
P["d_sin_arg"] = prog(cuerpo="f;", funciones=F)
P["d_parentesis"] = prog(cuerpo="f();", funciones=F)
P["d_explicito"] = prog(cuerpo="f(5);", funciones=F)
P["d_null"] = prog(cuerpo="f;", funciones=F.replace("default 5", "default null"))
P["d_null_explicito"] = prog(cuerpo="f(null);", funciones=F.replace("default 5", "default null"))
P["d_dos_uno"] = prog(cuerpo="f(1);", funciones="public f(x as integer, y as integer default 2)\nbegin\nend\n\n")
P["d_dos_dos"] = prog(cuerpo="f(1, 2);", funciones="public f(x as integer, y as integer default 2)\nbegin\nend\n\n")
P["d_if_sin_arg"] = prog(cuerpo="if g then\n    a = 2;", funciones=G)
P["d_if_explicito"] = prog(cuerpo="if g(0) then\n    a = 2;", funciones=G)
P["d_asigna_sin_arg"] = prog(cuerpo="a = h;", funciones=H)
P["d_asigna_explicito"] = prog(cuerpo="a = h(0);", funciones=H)
P["d_suma_sin_arg"] = prog(cuerpo="a = h + 1;", funciones=H)
# Métodos predefinidos con argumento por defecto: Run de un formulario
FORM = ("CONSTANTS  begin\nend\nCLASSES BEGIN\n\tfo is Form begin\n\t\tobjects begin\n\t\tend\n\t\tINTERFACE\n"
        "\t\t\tPOSITION 0 0 200 100\n\t\tBEGIN\n\t\tEND\n\tend\nEND\nCODE CLASS fo BEGIN\n//{{CODEBEGIN\n//{{CODEEND\nEND\n")


def con_form(cuerpo):
    return FORM + prog(objetos="a as integer\no as fo", cuerpo=cuerpo).replace("CONSTANTS  begin\nend\n", "")


P["r_run"] = con_form("o.Run;")
P["r_run_null"] = con_form("o.Run(null);")
P["r_if_run"] = con_form("if o.Run then\n    a = 2;")
P["r_if_run_null"] = con_form("if o.Run(null) then\n    a = 2;")
# Lo mismo escrito de dos maneras
P["e_distinto"] = prog(cuerpo="if a != 1 then\n    a = 2;")
P["e_distinto_menor_mayor"] = prog(cuerpo="if a <> 1 then\n    a = 2;")
P["e_ok"] = prog(cuerpo='Ok("a", "b");')
P["e_module_ok"] = prog(cuerpo='Module.Ok("a", "b");')
P["e_sin_parentesis"] = prog(cuerpo="f;", funciones="public f\nbegin\nend\n\n")
P["e_con_parentesis"] = prog(cuerpo="f;", funciones="public f()\nbegin\nend\n\n")
P["e_projectdir"] = prog(objetos="s as char", cuerpo="s = ProjectDir();")
P["e_module_projectdir"] = prog(objetos="s as char", cuerpo="s = Module.ProjectDir();")
P["e_projectdir_sin"] = prog(objetos="s as char", cuerpo="s = ProjectDir;")
# Declaraciones de varios nombres: un decimal con default comparte su DEC (una línea por nombre crea uno cada una)
P["v_tres_decimal"] = prog(objetos="a as integer\nx y z as decimal default 0", cuerpo="a = 1;")
P["v_tres_decimal_lineas"] = prog(objetos="a as integer\nx as decimal default 0\ny as decimal default 0\nz as decimal default 0")
P["v_dos_decimal_y_otro"] = prog(objetos="a as integer\nx y as decimal default 1.5\nz as decimal default 1.5")
P["v_tres_integer"] = prog(objetos="a as integer\nx y z as integer default 0")
P["v_dos_decimal_local"] = prog(cuerpo="f;", funciones="public f\nobjects begin\n    x y as decimal default 2\nend\nbegin\nend\n\n")
# --- main con parámetros (samples Auxiliar: `main(doRun as boolean default TRUE)`); su OBJ lleva el 0x40 (VAR)
P["m_main_param"] = prog().replace("main\n", "main(x as boolean default TRUE)\n", 1)
P["m_main_param_var"] = prog().replace("main\n", "main(VAR x as boolean default TRUE)\n", 1)
P["m_main_param_integer"] = prog().replace("main\n", "main(x as integer)\n", 1)
P["m_main_dos"] = prog().replace("main\n", "main(x as integer, y as char)\n", 1)


def main(argv=None):
    _g.P.clear()
    _g.P.update(P)
    _g.main(argv)


if __name__ == "__main__":
    main()

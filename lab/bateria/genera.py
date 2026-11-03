"""Genera la batería de programas COOL mínimos para la compilación diferencial.

Cada programa difiere del base (`b_base`) en una sola cosa, para que la diferencia
entre sus `.omd` señale qué codifica ese cambio. Uso:

    python3 -I genera.py <dir salida> <huecos.txt>

`huecos.txt` lista nombres de módulo registrados en el `.prj` (uno por línea); cada
programa ocupa un hueco. Escribe `<dir>/<HUECO>.SMD` (cp1252, CRLF) y `<dir>/manifiesto.tsv`.
"""
import sys
from pathlib import Path


def prog(objetos="a as integer", cuerpo="a = 1;", funciones=""):
    obj = "".join(f"    {o}\n" for o in objetos.split("\n") if o) if objetos else ""
    bloque_obj = f"objects begin\n{obj}end\n" if objetos else ""
    lineas = "".join(f"    {l}\n" for l in cuerpo.split("\n"))
    return (
        "CONSTANTS  begin\nend\nCODE BEGIN\n//{{CODEBEGIN\n"
        f"{funciones}main\n{bloque_obj}begin\n{lineas}end\n//{{{{CODEEND\nEND\n"
    ).replace("{{{{", "{{")


P = {}
# --- base y vacíos
P["b_base"] = prog()
P["b_vacio"] = prog(objetos="", cuerpo="")
P["b_solo_decl"] = prog(cuerpo="")
P["b_dos_decl"] = prog(objetos="a as integer\nb as integer")
P["b_nombre_largo"] = prog(objetos="variablelarga as integer", cuerpo="variablelarga = 1;")
# --- literales enteros
for v in ["0", "2", "255", "256", "65535", "65536", "2147483647", "-1", "-2"]:
    P[f"lit_int_{v.replace('-', 'm')}"] = prog(cuerpo=f"a = {v};")
# --- otros literales y tipos
P["lit_null"] = prog(cuerpo="a = null;")
P["tipo_smallint"] = prog(objetos="a as smallint")
P["tipo_decimal"] = prog(objetos="a as decimal (12,2)", cuerpo="a = 1.5;")
P["tipo_char_lit"] = prog(objetos="a as char", cuerpo='a = "x";')
P["tipo_char_lit2"] = prog(objetos="a as char", cuerpo='a = "hola";')
P["tipo_char_vacio"] = prog(objetos="a as char", cuerpo='a = "";')
P["tipo_bool_true"] = prog(objetos="a as boolean", cuerpo="a = true;")
P["tipo_bool_false"] = prog(objetos="a as boolean", cuerpo="a = false;")
P["tipo_date"] = prog(objetos="a as date", cuerpo="a = today;")
P["tipo_default"] = prog(objetos="a as integer default 7", cuerpo="")
# --- secuencias
P["sec_dos"] = prog(cuerpo="a = 1;\na = 2;")
P["sec_tres"] = prog(cuerpo="a = 1;\na = 2;\na = 3;")
P["sec_dos_vars"] = prog(objetos="a as integer\nb as integer", cuerpo="a = 1;\nb = 2;")
P["asig_var"] = prog(objetos="a as integer\nb as integer", cuerpo="a = b;")
# --- operadores binarios
for nombre, op in [("suma", "+"), ("resta", "-"), ("mult", "*"), ("div", "/"), ("mod", "%")]:
    P[f"op_{nombre}"] = prog(cuerpo=f"a = a {op} 2;")
P["op_suma_vars"] = prog(objetos="a as integer\nb as integer", cuerpo="a = a + b;")
P["op_prec1"] = prog(cuerpo="a = 1 + 2 * 3;")
P["op_prec2"] = prog(cuerpo="a = (1 + 2) * 3;")
P["op_neg"] = prog(cuerpo="a = -a;")
P["op_concat"] = prog(objetos="a as char", cuerpo='a = a + "x";')
P["op_masigual"] = prog(cuerpo="a += 2;")
P["op_menosigual"] = prog(cuerpo="a -= 2;")
P["op_inc"] = prog(cuerpo="++a;")
P["op_dec"] = prog(cuerpo="--a;")
# --- comparaciones y lógicos (dentro de if)
for nombre, op in [("eq", "=="), ("ne", "<>"), ("lt", "<"), ("le", "<="), ("gt", ">"), ("ge", ">=")]:
    P[f"cmp_{nombre}"] = prog(cuerpo=f"if a {op} 1 then\n    a = 2;")
P["log_and"] = prog(cuerpo="if a > 1 and a < 5 then\n    a = 2;")
P["log_or"] = prog(cuerpo="if a > 1 or a < 5 then\n    a = 2;")
P["log_not"] = prog(cuerpo="if not (a > 1) then\n    a = 2;")
P["cmp_is_null"] = prog(cuerpo="if a is null then\n    a = 2;")
P["cmp_in"] = prog(cuerpo="if a in (1, 3, 5) then\n    a = 2;")
P["cmp_between"] = prog(cuerpo="if a between 1 and 5 then\n    a = 2;")
# --- control de flujo
P["if_simple"] = prog(cuerpo="if a == 1 then\n    a = 2;")
P["if_bloque"] = prog(cuerpo="if a == 1 then\nbegin\n    a = 2;\n    a = 3;\nend")
P["if_else"] = prog(cuerpo="if a == 1 then\n    a = 2;\nelse\n    a = 3;")
P["if_elseif"] = prog(cuerpo="if a == 1 then\n    a = 2;\nelse if a == 2 then\n    a = 3;\nelse\n    a = 4;")
P["if_anidado"] = prog(cuerpo="if a == 1 then\n    if a == 2 then\n        a = 3;")
P["while"] = prog(cuerpo="while a < 10 do\n    ++a;")
P["while_bloque"] = prog(cuerpo="while a < 10 do\nbegin\n    ++a;\n    a = a;\nend")
P["repeat"] = prog(cuerpo="repeat ++a;\nuntil a > 10;")
P["for_to"] = prog(cuerpo="for a = 1 to 5 do\n    a = a;")
P["for_down"] = prog(cuerpo="for a = 5 down to 1 do\n    a = a;")
P["for_step"] = prog(cuerpo="for a = 0 to 10 step 2 do\n    a = a;")
P["for_lista"] = prog(cuerpo="for a as 1, 2, 3 do\n    a = a;")
P["forever_break"] = prog(cuerpo="forever begin\n    ++a;\n    if a > 10 then\n        break;\nend")
P["switch_valor"] = prog(cuerpo="switch a begin\n    case 1:\n        a = 2;\n    case 2:\n        a = 3;\nend")
P["switch_default"] = prog(cuerpo="switch a begin\n    case 1:\n        a = 2;\n    default:\n        a = 3;\nend")
P["switch_cond"] = prog(cuerpo="switch begin\n    case a == 1:\n        a = 2;\n    case a == 2:\n        a = 3;\nend")
P["exit"] = prog(cuerpo="Exit(1);")
# --- llamadas y métodos
P["met_trace"] = prog(cuerpo="a.Trace;")
P["met_trace_par"] = prog(cuerpo="a.Trace();")
P["met_lit"] = prog(objetos="", cuerpo='"hola".Trace;')
P["met_prop"] = prog(objetos="a as char\nb as integer", cuerpo="b = a.Length;")
P["met_cadena"] = prog(objetos="a as char", cuerpo="a.Length.Trace;")
P["call_stm"] = prog(cuerpo="call a.Trace;")
P["fun_builtin"] = prog(objetos="", cuerpo='MessageBox("hola");')
FUN = "public f()\nbegin\nend\n\n"
P["fun_vacia"] = prog(objetos="", cuerpo="", funciones=FUN)
P["fun_llamada"] = prog(objetos="", cuerpo="f();", funciones=FUN)
P["fun_privada"] = prog(objetos="", cuerpo="f();", funciones="private f()\nbegin\nend\n\n")
P["fun_param"] = prog(cuerpo="f(a);", funciones="public f(x as integer)\nbegin\nend\n\n")
P["fun_dos_param"] = prog(cuerpo="f(a, 2);", funciones="public f(x as integer, y as integer)\nbegin\nend\n\n")
P["fun_return"] = prog(cuerpo="a = f();", funciones="public f() return integer\nbegin\n    return 5;\nend\n\n")
P["fun_return_param"] = prog(cuerpo="a = f(a);", funciones="public f(x as integer) return integer\nbegin\n    return x + 1;\nend\n\n")
P["fun_local"] = prog(objetos="", cuerpo="f();", funciones="public f()\nobjects begin\n    x as integer\nend\nbegin\n    x = 1;\nend\n\n")
P["fun_dos"] = prog(objetos="", cuerpo="f();\ng();", funciones=FUN + "public g()\nbegin\nend\n\n")
# --- constantes de módulo
P["const_uso"] = prog(cuerpo="a = K;").replace("CONSTANTS  begin\nend", "CONSTANTS  begin\nK = 9\nend")
P["const_sin_uso"] = prog().replace("CONSTANTS  begin\nend", "CONSTANTS  begin\nK = 9\nend")
# --- comentarios (no deberían cambiar el código)
P["coment_linea"] = prog(cuerpo="// comentario\na = 1;")
P["espacios"] = prog(cuerpo="a  =  1 ;")
# --- case in (lista): operador 27 en el case de valor (al final, para no mover los huecos)
P["switch_in"] = prog(cuerpo="switch a begin\n    case in (1, 2):\n        a = 2;\n    case 3:\n        a = 3;\nend")
P["switch_in_uno"] = prog(cuerpo="switch a begin\n    case in (1):\n        a = 2;\nend")
P["switch_in_char"] = prog(objetos="c as char", cuerpo='switch c begin\n    case in ("x", "y", "z"):\n        c = "w";\nend')
P["switch_in_var"] = prog(objetos="a as integer\nb as integer", cuerpo="switch a begin\n    case in (b, b + 1):\n        a = 2;\nend")
P["switch_in_default"] = prog(cuerpo="switch a begin\n    case in (1, 2):\n        a = 2;\n    default:\n        a = 3;\nend")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    salida, huecos = Path(argv[0]), Path(argv[1]).read_text().split()
    if len(huecos) < len(P):
        sys.exit(f"faltan huecos: {len(huecos)} < {len(P)}")
    salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for (nombre, fuente), hueco in zip(P.items(), huecos):
        (salida / f"{hueco}.SMD").write_bytes(fuente.replace("\n", "\r\n").encode("cp1252"))
        filas.append(f"{hueco}\t{nombre}")
    (salida / "manifiesto.tsv").write_text("\n".join(filas) + "\n")
    print(len(filas), "programas")


if __name__ == "__main__":
    main()

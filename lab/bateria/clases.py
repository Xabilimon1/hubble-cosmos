"""Batería de clases del usuario que no son formulario: herencia de una clase con miembros (`B is A begin … end`,
`B is A`), visibilidad (PUBLIC, PROTECTED, PRIVATE) de clases, miembros, objetos del módulo y métodos, clases de
un tipo con parámetros (`X is Decimal (32,2)`), constantes que no son números y métodos `operator` y `conversor`.
Las formas sin ejemplo en el kit van en varias: la que no compila lo dice. Un cambio por programa sobre `c_base`.
Uso: python3 -I clases.py <dir salida> <huecos.txt>
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("genera", Path(__file__).with_name("genera.py"))
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)

A = "\tA is Struct begin\n\t\tx as Integer\n\tend\n"


def modulo(clases=A, constantes="", objetos="", codigo_clases=None, codigo=""):
    """Un módulo con su CLASSES, un CODE CLASS por clase (`codigo_clases`: nombre → métodos) y un main vacío."""
    nombres = [l.split()[-3] if " is " not in l else l.split(" is ")[0].split()[-1]
               for l in clases.split("\n") if l.startswith("\t") and not l.startswith("\t\t") and " is " in l]
    codigo_clases = codigo_clases or {}
    texto = f"CONSTANTS  begin\n{constantes}end\nCLASSES BEGIN\n{clases}END\n"
    if objetos:
        texto += f"OBJECTS BEGIN\n{objetos}END\n"
    for n in nombres:
        texto += f"CODE CLASS {n} BEGIN\n//{{{{CODEBEGIN\n{codigo_clases.get(n, '')}//{{{{CODEEND\nEND\n"
    return (texto + f"CODE BEGIN\n//{{{{CODEBEGIN\n{codigo}main\nbegin\nend\n//{{{{CODEEND\nEND\n").replace("{{{{", "{{")


P = {}
P["c_base"] = modulo()
# --- herencia de una clase con miembros
P["c_vacio_begin"] = modulo("\tA is Struct begin\n\tend\n")
P["c_vacio"] = modulo("\tA is Struct\n")
P["c_hereda"] = modulo(A + "\tB is A begin\n\t\ty as Char\n\tend\n")
P["c_hereda_sin"] = modulo(A + "\tB is A\n")
P["c_hereda_vacio_begin"] = modulo(A + "\tB is A begin\n\tend\n")
P["c_hereda_dos"] = modulo(A + "\tB is A begin\n\t\ty as Char\n\tend\n\tC is B\n")
P["c_hereda_abstracta"] = modulo("\tA is abstract Struct\n\tB is A begin\n\t\ty as Char\n\tend\n")
P["c_abstracta_miembros"] = modulo("\tA is abstract Struct begin\n\t\tx as Integer\n\tend\n")
P["c_hereda_default"] = modulo(A + '\tB is A begin\n\t\ty as Char default "z"\n\t\tn as Decimal (16,0)\n\tend\n')
# --- visibilidad de la clase
P["v_public"] = modulo("\tPUBLIC A is Struct begin\n\t\tx as Integer\n\tend\n")
P["v_protected"] = modulo("\tPROTECTED A is Struct begin\n\t\tx as Integer\n\tend\n")
P["v_private"] = modulo("\tPRIVATE A is Struct begin\n\t\tx as Integer\n\tend\n")
P["v_protected_hereda"] = modulo(A + "\tPROTECTED B is A begin\n\t\ty as Char\n\tend\n")
P["v_protected_hereda_sin"] = modulo(A + "\tPROTECTED B is A\n")
P["v_private_smallint"] = modulo("\tPRIVATE A is Smallint\n")
P["v_protected_smallint"] = modulo("\tPROTECTED A is Smallint\n")
P["v_private_form"] = modulo("\tPRIVATE A is Form begin\n\t\tobjects begin\n\t\tend\n\t\tINTERFACE\n"
                             "\t\t\tPOSITION 0 0 200 100\n\t\tBEGIN\n\t\tEND\n\tend\n")
# --- visibilidad de un miembro
P["m_public"] = modulo("\tA is Struct begin\n\t\tPUBLIC x as Integer\n\tend\n")
P["m_protected"] = modulo("\tA is Struct begin\n\t\tPROTECTED x as Integer\n\tend\n")
P["m_private"] = modulo("\tA is Struct begin\n\t\tPRIVATE x as Integer\n\tend\n")
P["m_private_y_otro"] = modulo("\tA is Struct begin\n\t\tPRIVATE x as Char (50)\n\t\ty as Integer\n\tend\n")
# --- visibilidad de un objeto del módulo
P["o_normal"] = modulo(objetos="\tg as Integer\n")
P["o_public"] = modulo(objetos="\tPUBLIC g as Integer\n")
P["o_protected"] = modulo(objetos="\tPROTECTED g as Integer\n")
P["o_private"] = modulo(objetos="\tPRIVATE g as Integer\n")
P["o_protected_default"] = modulo(objetos='\tPROTECTED g as Char default " "\n')
# --- visibilidad de un método de la clase y del módulo
F = "{} f\nbegin\nend\n"
for vis in ("public", "protected", "private"):
    P[f"p_{vis}"] = modulo(codigo_clases={"A": F.format(vis)})
    P[f"p_{vis}_modulo"] = modulo(codigo=F.format(vis) + "\n")
P["p_protected_return"] = modulo(codigo_clases={"A": "protected f(c as Char) return Char\nbegin\n    return c;\nend\n"})
# --- clases de un tipo con parámetros
for nombre, tipo in (("decimal", "Decimal (32,2)"), ("decimal_sin", "Decimal"), ("decimal_10", "Decimal (10)"),
                     ("money", "Money (10,2)"), ("money_sin", "Money"), ("char", "Char (10)"), ("char_sin", "Char")):
    P[f"t_{nombre}"] = modulo(f"\tA is {tipo}\n")
# --- constantes
for nombre, valor in (("char", '"ABC"'), ("char_vacio", '""'), ("char_simples", "'a\"b'"), ("decimal", "1.5"),
                      ("negativo", "-1"), ("grande", "100000"), ("bool", "TRUE"), ("null", "null")):
    P[f"k_{nombre}"] = modulo(constantes=f"\tK = {valor}\n")
P["k_char_y_entero"] = modulo(constantes='\tK = "ABC"\n\tN = 9\n')
# --- operator y conversor (sobre una clase con un Char)
C = "\tA is Struct begin\n\t\tx as Char\n\tend\n"
for nombre, firma in (("igual", "operator = (c as Char)"), ("igual_integer", "operator = (c as Integer)"),
                      ("suma", "operator + (c as Integer) return Integer"),
                      ("igualigual", "operator == (c as Char) return Boolean"),
                      ("menor", "operator < (c as Char) return Boolean"),
                      ("masigual", "operator += (c as Char)"),
                      ("distinto", "operator <> (c as Char) return Boolean"),
                      ("mult", "operator * (c as Integer) return Integer")):
    cuerpo = "    return 0;\n" if "Integer" in firma.split("return")[-1] and "return" in firma else (
        "    return true;\n" if "Boolean" in firma else "    x = c;\n" if "Char)" in firma and "return" not in firma else "")
    P[f"op_{nombre}"] = modulo(C, codigo_clases={"A": f"public {firma}\nbegin\n{cuerpo}end\n"})
for nombre, clase, valor in (("char", "Char", "x"), ("integer", "Integer", "0"), ("boolean", "Boolean", "true")):
    P[f"cv_{nombre}"] = modulo(C, codigo_clases={"A": f"public conversor {clase}\nbegin\n    return {valor};\nend\n"})
P["cv_dos"] = modulo(C, codigo_clases={"A": "public conversor Char\nbegin\n    return x;\nend\n\n"
                                            "public conversor Integer\nbegin\n    return 0;\nend\n"})
P["op_y_cv"] = modulo(C, codigo_clases={"A": "public operator = (c as Char)\nbegin\n    x = c;\nend\n\n"
                                             "public conversor Char\nbegin\n    return x;\nend\n"})
# --- segunda tanda: objetos de una clase con parámetros (el OBJ lleva los de la clase), herencia de una abstracta
AD = "\tA is Decimal (32,2)\n"
P["t_objeto_decimal"] = modulo(AD, objetos="\tg as A\n")
P["t_objeto_decimal_param"] = modulo(AD, objetos="\tg as A (10,2)\n")
P["t_objeto_char"] = modulo("\tA is Char (10)\n", objetos="\tg as A\n")
P["t_objeto_money"] = modulo("\tA is Money (10,2)\n", objetos="\tg as A\n")
P["t_local_decimal"] = modulo(AD, codigo="public f\nobjects begin\n    d as A\nend\nbegin\nend\n\n")
P["t_return_decimal"] = modulo(AD, codigo="public f return A\nbegin\n    return 1;\nend\n\n")
P["t_hereda_decimal"] = modulo(AD + "\tB is A\n", objetos="\tg as B\n")
AB = "\tA is abstract Struct\n"
P["c_abstracta_hereda_dos"] = modulo(AB + "\tB is A begin\n\t\ty as Char\n\tend\n\tC is B\n")
P["c_abstracta_hereda_default"] = modulo(AB + '\tB is A begin\n\t\ty as Char default "z"\n\t\tn as Decimal (16,0)\n\tend\n')
P["c_abstracta_protected"] = modulo(AB + "\tPROTECTED B is A begin\n\t\ty as Char\n\tend\n")
P["c_abstracta_private_miembro"] = modulo(AB + "\tB is A begin\n\t\tPRIVATE y as Char\n\t\tz as Integer\n\tend\n")
P["c_abstracta_vacia"] = modulo(AB + "\tB is A begin\n\tend\n")
P["c_abstracta_sin"] = modulo(AB + "\tB is A\n")
P["c_abstracta_abstracta"] = modulo(AB + "\tB is abstract A\n")
P["c_hereda_sin_objeto"] = modulo(A + "\tB is A\n", objetos="\tg as B\n")
P["k_bool_false"] = modulo(constantes="\tK = FALSE\n")
P["k_char_uso"] = modulo(constantes='\tK = "ABC"\n', objetos="\tg as Char\n", codigo="public f\nbegin\n    g = K;\nend\n\n")
P["v_private_modulo_dos"] = modulo(objetos="\tPRIVATE g h as Integer\n")
# --- tercera tanda: PI (CalcALG calcu3 `PI.Char()`), un case de varios valores, un decimal entero y defaults compartidos
G = "\tg as Decimal\n"
P["k_pi"] = modulo(objetos=G, codigo="public f\nbegin\n    g = PI;\nend\n\n")
P["k_pi_literal"] = modulo(objetos=G, codigo="public f\nbegin\n    g = 3.141592653589793238462643383;\nend\n\n")
P["k_pi_metodo"] = modulo(objetos=G, codigo="public f\nbegin\n    g = Module.Pi;\nend\n\n")
P["k_pi_char"] = modulo(objetos="\tg as Char\n", codigo="public f\nbegin\n    g = PI.Char();\nend\n\n")
P["k_e"] = modulo(objetos=G, codigo="public f\nbegin\n    g = E;\nend\n\n")
P["s_case_dos"] = modulo(objetos="\tg as Char\n", codigo='public f\nbegin\n    switch g begin\n        case "a", "b":\n'
                                                     '            g = "c";\n    end\nend\n\n')
P["s_case_tres"] = modulo(objetos="\tg as Integer\n", codigo="public f\nbegin\n    switch g begin\n        case 1, 2, 3:\n"
                                                          "            g = 0;\n        case 4:\n            g = 1;\n    end\nend\n\n")
P["d_decimal_entero"] = modulo(objetos=G, codigo="public f\nbegin\n    if g > 0.0 then\n        g = 1.0;\nend\n\n")
P["d_decimal_entero_sin"] = modulo(objetos=G, codigo="public f\nbegin\n    if g > 0 then\n        g = 1;\nend\n\n")
P["d_char_compartido"] = modulo(codigo='public f\nobjects begin\n    a b c as Char default ""\nend\nbegin\nend\n\n')
P["d_char_lineas"] = modulo(codigo='public f\nobjects begin\n    a as Char default ""\n    b as Char default ""\nend\nbegin\nend\n\n')
# --- cuarta tanda: Array de un tipo con parámetros (mail IncEncoders `Array [256] of Char (8)`) y defaults de Time
# (mail IncViews `vTmCrono as Time default 0`)
for nombre, tipo in (("char8", "Char (8)"), ("decimal", "Decimal (10,2)"), ("char", "Char"), ("money", "Money (12,2)")):
    P[f"a_{nombre}"] = modulo(f"\tA is Array [256] of {tipo}\n")
for nombre, valor in (("0", "0"), ("1", "1"), ("3600", "3600"), ("hora", '"10:30:00"'), ("now", "NOW"), ("null", "null")):
    P[f"h_{nombre}"] = modulo(objetos=f"\tt as Time default {valor}\n")
    P[f"h_local_{nombre}"] = modulo(codigo=f"public f\nobjects begin\n    t as Time default {valor}\nend\nbegin\nend\n\n")
# --- Enum y EnumSet (samples ENUM), al final
E = "\tcolor is Enum of [red yellow green]\n"
S = "\thas is EnumSet of [head foot hands]\n"
for nombre, clases in (("uno", "\tcolor is Enum of [red]\n"), ("tres", E), ("set", S), ("set_uno", "\thas is EnumSet of [head]\n"),
                       ("dos", E + S), ("mayus", "\tdia is Enum of [Lunes MARTES miercoles]\n")):
    P[f"en_{nombre}"] = modulo(clases)


def _usa(clases, objetos, cuerpo):
    return modulo(clases, codigo=f"public f\nobjects begin\n{objetos}end\nbegin\n{cuerpo}end\n\n")


P["en_asigna"] = _usa(E, "    c as color\n", "    c = green;\n")
P["en_compara"] = _usa(E, "    c as color\n", "    if c == yellow then\n        c.Trace;\n")
P["en_traza"] = _usa(E, "", "    red.Trace;\n")
P["en_set_suma"] = _usa(S, "    t as has\n", "    t = head + hands;\n")
P["en_set_resta"] = _usa(S, "    t as has\n", "    t = t - foot;\n")
P["en_set_tres"] = _usa(S, "    t as has\n", "    t = head + foot + hands;\n")
P["en_argumento"] = _usa(E, "", "    g(green);\n") .replace("public f\n", "public g(c as color)\nbegin\nend\n\npublic f\n")
P["en_default"] = modulo(E, objetos="\tc as color default green\n")
# --- ArgList (samples ARG), al final
for nombre, tipo in (("char", "Char"), ("integer", "Integer"), ("decimal", "Decimal")):
    P[f"al_{nombre}"] = modulo(f"\tl is ArgList of {tipo}\n")
P["al_uso"] = modulo("\tl is ArgList of Char\n", codigo="public f(a as l)\nbegin\n    a[1].Trace;\n    a.Size.Trace;\nend\n\n")
P["al_var"] = modulo("\tl is ArgList of Char\n", codigo="public f(VAR a as l)\nbegin\n    a[1].Trace;\nend\n\n")
P["al_llamada"] = modulo("\tl is ArgList of Integer\n",
                         codigo='public f(a as l)\nbegin\n    a.Size.Trace;\nend\n\npublic g\nbegin\n    f(1, 2, 3);\nend\n\n')

# --- `X is Struct as tabla` (samples EjInitializeWithDefault), con el repositorio stock, al final
for tabla in ("states", "customers", "items", "payforms"):
    P[f"sa_{tabla}"] = "REPOSITORY stock\n" + modulo(f"\tS is Struct as {tabla}\n")
P["sa_uso"] = "REPOSITORY stock\n" + modulo("\tS is Struct as states\n", codigo="public f\nobjects begin\n    o as S\nend\nbegin\n    o.state.Trace;\nend\n\n")
P["sa_a_mano"] = "REPOSITORY stock\n" + modulo("\tS is Struct begin\n\t\tstate as states.state\n\t\tsname as states.sname\n\tend\n")


# --- familia «codigo» del vocabulario (2026-10-31), al final: SELF de un método dll/javaclass (manual refer
# ref00030: «dll_identifier ::= [SELF] DLL dll_path identifier»), selfclass, FUNCTION opcional y grafías en mayúsculas
SM = "\tsm is Smallint\n"
P["sd_base"] = modulo(codigo='public dll "user32.dll" GetTickCount() return Integer\n')
P["sd_self"] = modulo(codigo='public self dll "user32.dll" GetTickCount() return Integer\n')
P["sd_self_mayus"] = modulo(codigo='public SELF DLL "user32.dll" GetTickCount() return Integer\n')
P["sd_self_sin_return"] = modulo(codigo='public self dll "user32.dll" MessageBeep(t as Integer)\n')
P["sd_sin_return"] = modulo(codigo='public dll "user32.dll" MessageBeep(t as Integer)\n')
P["sd_self_private"] = modulo(codigo='private self dll "user32.dll" GetTickCount() return Integer\n')
P["sd_self_delante"] = modulo(codigo='self public dll "user32.dll" GetTickCount() return Integer\n')
P["sd_self_sin_acceso"] = modulo(codigo='self dll "user32.dll" GetTickCount() return Integer\n')
P["sd_clase_base"] = modulo(SM, codigo_clases={"sm": 'public dll "user32.dll" GetTickCount() return Integer\n'})
P["sd_clase_self"] = modulo(SM, codigo_clases={"sm": 'public self dll "user32.dll" GetTickCount() return Integer\n'})
P["sd_clase_self_param"] = modulo(SM, codigo_clases={"sm": 'public self dll "user32.dll" MessageBeep(t as Integer)\n'})
P["sd_struct_self"] = modulo(codigo_clases={"A": 'public self dll "user32.dll" GetTickCount() return Integer\n'})
P["sd_struct_base"] = modulo(codigo_clases={"A": 'public dll "user32.dll" GetTickCount() return Integer\n'})
P["sj_base"] = modulo(codigo='public javaclass "Test1" FuncionJava1()\n')
P["sj_self"] = modulo(codigo='public self javaclass "Test1" FuncionJava1()\n')
P["sj_clase_self"] = modulo(SM, codigo_clases={"sm": 'public self javaclass "Test1" FuncionJava1()\n'})
F = "begin\n    return self;\nend\n"
P["sc_return_clase"] = modulo(SM, codigo_clases={"sm": "public f() return sm\n" + F})
P["sc_return_selfclass"] = modulo(SM, codigo_clases={"sm": "public f() return selfclass\n" + F})
P["sc_return_selfclass_mayus"] = modulo(SM, codigo_clases={"sm": "public f() RETURN SELFCLASS\n" + F})
P["sc_param_clase"] = modulo(SM, codigo_clases={"sm": "public f(o as sm)\nbegin\nend\n"})
P["sc_param_selfclass"] = modulo(SM, codigo_clases={"sm": "public f(o as selfclass)\nbegin\nend\n"})
P["sc_param_var_clase"] = modulo(SM, codigo_clases={"sm": "public f(VAR o as sm)\nbegin\nend\n"})
P["sc_param_struct"] = modulo(codigo_clases={"A": "public f(o as A)\nbegin\nend\n"})
P["sc_param_var_struct"] = modulo(codigo_clases={"A": "public f(VAR o as A)\nbegin\nend\n"})
P["sc_dll_return_selfclass"] = modulo(SM, codigo_clases={"sm": 'public dll "user32.dll" GetTickCount() return selfclass\n'})
P["fn_sin"] = modulo(codigo="public f(c as Char) return Char\nbegin\n    return c;\nend\n\n")
P["fn_function"] = modulo(codigo="public function f(c as Char) return Char\nbegin\n    return c;\nend\n\n")
P["fn_function_mayus"] = modulo(codigo="public FUNCTION f(c as Char) return Char\nbegin\n    return c;\nend\n\n")
P["fn_function_private"] = modulo(codigo="private function f\nbegin\nend\n\n")
P["fn_private"] = modulo(codigo="private f\nbegin\nend\n\n")
P["fn_function_clase"] = modulo(codigo_clases={"A": "public function f(c as Char) return Char\nbegin\n    return c;\nend\n"})
P["fn_function_sin_acceso"] = modulo(codigo="function f\nbegin\nend\n\n")
P["gr_return_mayus"] = modulo(codigo="public f(c as Char) RETURN Char\nbegin\n    return c;\nend\n\n")
P["gr_of_mayus"] = modulo("\tA is Array [256] OF Char\n")
P["gr_enum_of_mayus"] = modulo("\tcolor is Enum OF [red yellow green]\n")
P["gr_dll_mayus"] = modulo(codigo='PUBLIC DLL "user32.dll" GetTickCount() RETURN Integer\n')


# --- parámetro `a as ArgList of X` (samples ChartRadar, que en 32 bits no salía), al final: X va en el +0x40 del OBJ
# del parámetro en 64 bits y en el +0x24 en 32
def _arglist(param, cuerpo="    a.Size.Trace;\n"):
    return modulo(codigo=f"public f({param})\nbegin\n{cuerpo}end\n\n")


P["alp_integer"] = _arglist("a as ArgList of Integer")
P["alp_char"] = _arglist("a as ArgList of Char(10)")
P["alp_char_esp"] = _arglist("a as ArgList of Char (10)")
P["alp_decimal"] = _arglist("a as ArgList of Decimal(10,2)")
P["alp_decimal_sin"] = _arglist("a as ArgList of Decimal")
P["alp_clase"] = _arglist("a as ArgList of A")
P["alp_sin_of"] = _arglist("a as ArgList")
P["alp_dos"] = _arglist("n as Integer, a as ArgList of Decimal")
P["alp_minusculas"] = _arglist("a as arglist of decimal")
P["alp_local"] = modulo(codigo="public f\nobjects begin\n    x as ArgList of Integer\nend\nbegin\n    x.Size.Trace;\nend\n\n")
P["alp_llamada"] = modulo(codigo="public f(a as ArgList of Decimal)\nbegin\n    a.Size.Trace;\nend\n\n"
                          "public g\nbegin\n    f(1.5, 2.5);\nend\n\n")


def main(argv=None):
    _g.P.clear()
    _g.P.update(P)
    _g.main(argv)


if __name__ == "__main__":
    main()

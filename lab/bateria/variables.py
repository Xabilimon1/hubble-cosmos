"""Batería de variables y tablas de formulario (familia 3): atributos de una variable (`boolean values`,
`enumerated n values`), de una columna (`required`, `noentry`, `noupdate`, default que no es cadena) y de
una tabla (`depend on … join`, `order by`, `references`, `joining`, `Vartable`). Las palabras sin ejemplo en
el kit van en varias formas: la que no compila lo dice. Repositorio `stock` del kit.
Uso: python3 -I variables.py <dir salida> <huecos.txt>
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("tablas", Path(__file__).with_name("tablas.py"))
_t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t)
_f = _t._f
form, control, con_tabla = _f.form, _f.control, _t.con_tabla

P = {}
# --- variables de formulario
E = control("EDIT", "DATATYPE CHAR", nombre="e")
for nombre, objetos in [("base", "b as Boolean"), ("boolean", 'b as Boolean\n\tboolean values "0|1"'),
                        ("boolean_otros", 'b as Boolean\n\tboolean values "TRUE|FALSE"'),
                        ("boolean_smallint", 'b as Smallint default 1\n\tboolean values "0|1"'),
                        ("boolean_char", 'b as Char (1)\n\tboolean values "S|N"'),
                        ("enumerated", 'b as Char (5)\n\tenumerated 4 values "d1|d2|d3|d4"'),
                        ("enumerated_3", 'b as Char (2)\n\tenumerated 3 values "a|b|c"'),
                        ("enumerated_integer", 'b as Integer\n\tenumerated 3 values "1|2|3"'),
                        ("dos", 'b as Boolean\n\tboolean values "0|1"\nc as Char (2)\n\tenumerated 3 values "x|y|z"')]:
    P[f"o_{nombre}"] = form(objetos=objetos, controles=E)
# --- columnas
for nombre, col in [("required", "state as column required"), ("noentry", "state as column noentry"),
                    ("noupdate", "state as column noupdate"), ("required_noentry", "state as column required noentry"),
                    ("noentry_noupdate", "state as column noentry noupdate"),
                    ("todo", "state as column required noentry noupdate")]:
    P[f"c_{nombre}"] = con_tabla((col,))
P["c_enumerated"] = con_tabla(("state as column", 'sname as column\n\t\t\t\tenumerated 3 values "a|b|c"'))
# --- default de una columna que no es cadena (tabla orders del repositorio stock)
ORD = control("EDIT", "VARIABLE orders.order_nbr\nLIKEVAR", nombre="e")
for nombre, col in [("today", "order_date as column default TODAY"), ("fecha", 'order_date as column default "01/01/2026"'),
                    ("char", 'order_status as column default "A"')]:
    P[f"d_{nombre}"] = con_tabla(("order_nbr as column", col), cabecera="Table orders is orders", controles=ORD)
LIN_E = control("EDIT", "VARIABLE orderlines.line_nbr\nLIKEVAR", nombre="e")
for nombre, col in [("numero", "quantity as column default 0"), ("numero_5", "quantity as column default 5"),
                    ("decimal", "price as column default 1.5"), ("negativo", "discount as column default -1")]:
    P[f"d_{nombre}"] = con_tabla(("line_nbr as column", col), cabecera="Table orderlines is orderlines", controles=LIN_E)
# --- tablas: depend on, order by, references, joining, Vartable
CAB = "Table orders is orders"
DOS = ["order_nbr as column", "customer as column"]
LIN = "\t\tTable orderlines is orderlines\n{}\t\tbegin\n\t\t\tline_nbr as column\n\t\tend\n"


def dos_tablas(extra_lineas="", columnas=DOS):
    texto = con_tabla(columnas, cabecera=CAB, controles=ORD)
    return texto.replace("\t\tINTERFACE\n", LIN.format("".join(f"\t\t\t{x}\n" for x in extra_lineas.split("\n") if x)) + "\t\tINTERFACE\n")


P["t_base"] = dos_tablas()
P["t_depend_on"] = dos_tablas("depend on orders join fk2_lines")
P["t_order_by"] = con_tabla(DOS, cabecera=CAB, controles=ORD, extra_tabla="order by (customer)")
P["t_order_by_dos"] = con_tabla(DOS, cabecera=CAB, controles=ORD, extra_tabla="order by (customer, order_nbr)")
# un join definido en la tabla del formulario (manual: «lookup for2_alb references "formpagos" joining (formpago) (formpago)»)
P["t_lookup_references"] = con_tabla(DOS + ["company as customers.company", '\tjoin mio lookup "company"'], cabecera=CAB, controles=ORD,
                                     extra_tabla='lookup mio references "customers" joining (customer) (customer)')
P["t_join_references"] = con_tabla(DOS + ["company as customers.company", '\tjoin mio lookup "company"'], cabecera=CAB, controles=ORD,
                                   extra_tabla="join mio references customers joining (customer) (customer)")
P["t_join_references_comillas"] = con_tabla(DOS + ["company as customers.company", '\tjoin mio lookup "company"'], cabecera=CAB,
                                            controles=ORD, extra_tabla='join mio references "customers" joining (customer) (customer)')
P["t_depend_on_join_propio"] = dos_tablas("join mio references orders joining (order_nbr) (order_nbr)\ndepend on orders join mio")
P["t_order_by_y_depend"] = dos_tablas("depend on orders join fk2_lines\norder by (line_nbr)")
P["t_vartable"] = con_tabla(DOS, cabecera="Vartable orders is orders", controles=ORD)
P["t_vartable_sin_is"] = con_tabla(DOS, cabecera="Vartable orders", controles=ORD)
# --- segunda tanda: bases de una tabla, required sobre una columna que admite nulos, otra fecha y NOW
P["t_una"] = con_tabla(DOS, cabecera=CAB, controles=ORD)
P["c_sname"] = con_tabla(("state as column", "sname as column"))
P["c_sname_required"] = con_tabla(("state as column", "sname as column required"))
P["c_sname_noentry"] = con_tabla(("state as column", "sname as column noentry"))
P["d_fecha_2"] = con_tabla(("order_nbr as column", 'order_date as column default "15/03/2026"'), cabecera=CAB, controles=ORD)
P["d_fecha_3"] = con_tabla(("order_nbr as column", 'order_date as column default "31/12/1999"'), cabecera=CAB, controles=ORD)
P["d_now"] = con_tabla(("order_nbr as column", "order_date as column default NOW"), cabecera=CAB, controles=ORD)
P["d_null"] = con_tabla(("order_nbr as column", "order_date as column default null"), cabecera=CAB, controles=ORD)
P["d_entero"] = con_tabla(("order_nbr as column", "customer as column default 7"), cabecera=CAB, controles=ORD)
P["d_money_0"] = con_tabla(("line_nbr as column", "price as column default 0"), cabecera="Table orderlines is orderlines", controles=LIN_E)
P["o_fecha_today"] = form(objetos="f as Date default TODAY", controles=E)
# --- tercera tanda: orden de default y required/noentry; fechas mm/dd/aaaa; defaults de variables
P["d_todo"] = con_tabla(("line_nbr as column", "quantity as column default 5 required noentry noupdate"),
                        cabecera="Table orderlines is orderlines", controles=LIN_E)
P["d_fecha_mdy"] = con_tabla(("order_nbr as column", 'order_date as column default "03/15/2026"'), cabecera=CAB, controles=ORD)
P["d_fecha_1900"] = con_tabla(("order_nbr as column", 'order_date as column default "01/01/1900"'), cabecera=CAB, controles=ORD)
P["o_fecha"] = form(objetos='f as Date default "03/15/2026"', controles=E)
P["o_decimal"] = form(objetos="f as Decimal (8,2) default 1.5", controles=E)
P["o_money"] = form(objetos="f as Money (16,2) default 0", controles=E)
P["c_sname_noupdate_required"] = con_tabla(("state as column", "sname as column required noupdate"))


# --- cuarta tanda: depend on (FTA +0x30 → padre, +0x38 → FRC de la unión; +0x68 = casilla de la tabla)
def tablas(*bloques, controles=ORD):
    """Formulario con varias tablas: cada bloque, (cabecera, líneas de la tabla, columnas)."""
    texto = "".join(f"\t\t{c}\n" + "".join(f"\t\t\t{x}\n" for x in extra if x) + "\t\tbegin\n"
                    + "".join(f"\t\t\t{x}\n" for x in cols) + "\t\tend\n" for c, extra, cols in bloques)
    return "REPOSITORY stock\n" + form(controles=controles).replace("\t\tINTERFACE\n", texto + "\t\tINTERFACE\n")


CLI = ("Table customers is customers", (), ("customer as column", "company as column"))
P["t_tres"] = tablas(CLI, ("Table orders is orders", ("depend on customers join fk1_orders",), ("order_nbr as column",)),
                     ("Table orderlines is orderlines", ("depend on orders join fk2_lines",), ("line_nbr as column",)))
P["t_depend_customers"] = tablas(CLI, ("Table orders is orders", ("depend on customers join fk1_orders",), DOS[:1]))
P["t_depend_alias"] = tablas(("Table cab is orders", (), DOS), ("Table lin is orderlines", ("depend on cab join fk2_lines",),
                             ("line_nbr as column",)), controles=control("EDIT", "VARIABLE cab.order_nbr\nLIKEVAR", nombre="e"))
P["t_depend_con_clave"] = dos_tablas("depend on orders join fk2_lines", DOS).replace(
    "\t\t\tline_nbr as column\n", "\t\t\torder_nbr as column\n\t\t\tline_nbr as column\n", 1)
P["t_depend_mas_columnas"] = tablas(("Table orders is orders", (), DOS), ("Table orderlines is orderlines",
                                    ("depend on orders join fk2_lines",), ("line_nbr as column", "quantity as column", "price as column")))
P["t_order_by_antes"] = dos_tablas("order by (line_nbr)\ndepend on orders join fk2_lines")
P["t_variables_y_depend"] = tablas(("Table orders is orders", (), DOS), ("Table orderlines is orderlines",
                                   ("depend on orders join fk2_lines",), ("line_nbr as column",))).replace(
    "\t\tobjects begin\n", "\t\tobjects begin\n\t\t\tx as Integer\n\t\t\ty as Char (5)\n", 1)


# --- familia «codigo» del vocabulario (2026-10-31), al final: references y joining en otras formas (cosmakecon:
# 'join ' ' references ' ' joining ' 'depend on ')
J = DOS + ["company as customers.company", '\tjoin mio lookup "company"']
for nombre, extra in [("cols_antes", "join mio (customer) references customers joining (customer)"),
                      ("cols_antes_comillas", 'join mio (customer) references "customers" joining (customer)'),
                      ("una_lista", "join mio references customers joining (customer)"),
                      ("sin_parentesis", "join mio references customers joining customer"),
                      ("cols_tras_tabla", "join mio references customers (customer) joining (customer)"),
                      ("lookup_una", 'lookup mio references "customers" joining (customer)'),
                      ("viejo", "join mio references customers joining (customer) (customer)")]:
    P[f"rf_{nombre}"] = con_tabla(J, cabecera=CAB, controles=ORD, extra_tabla=extra)
P["rf_vartable"] = con_tabla(J, cabecera="Vartable orders is orders", controles=ORD,
                             extra_tabla="join mio references customers joining (customer) (customer)")
P["rf_depend"] = dos_tablas("join mio (order_nbr) references orders joining (order_nbr)\ndepend on orders join mio")
P["rf_depend_vieja"] = dos_tablas("join mio references orders joining (order_nbr) (order_nbr)\ndepend on orders join mio")

# segunda tanda: detrás de la cabecera de la tabla no compila ninguna («Actual join(join). Expecting  begin»): dentro
# del begin … end, en la misma línea de la cabecera o en una columna
V = "join mio references customers joining (customer) (customer)"
P["rf_dentro"] = con_tabla(J + [V], cabecera=CAB, controles=ORD)
P["rf_dentro_cols_antes"] = con_tabla(J + ["join mio (customer) references customers joining (customer)"], cabecera=CAB, controles=ORD)
P["rf_dentro_sin_lookup"] = con_tabla(DOS + [V], cabecera=CAB, controles=ORD)
P["rf_cabecera"] = con_tabla(J, cabecera=CAB + " " + V, controles=ORD)
P["rf_columna"] = con_tabla(["order_nbr as column", "customer as column references customers joining (customer)"], cabecera=CAB, controles=ORD)
P["rf_depend_references"] = dos_tablas("depend on orders join mio references orders joining (order_nbr) (order_nbr)")


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

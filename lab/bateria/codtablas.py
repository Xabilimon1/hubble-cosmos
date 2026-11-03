"""Batería de tablas de formulario en el código (repositorio `stock`): la tabla como objeto (`orders.Metodo(…)`),
`tabla.columna` y la columna a secas, en expresiones y como argumento.
Uso: python3 -I codtablas.py <dir salida> <huecos.txt> [desde]   (en la carpeta samples del laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("tablas", Path(__file__).with_name("tablas.py"))
_t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t)
_f = _t._f
control, con_tabla = _f.control, _t.con_tabla

ORD = control("EDIT", "VARIABLE orders.order_nbr\nLIKEVAR", nombre="e")
VACIO = "CODE CLASS f BEGIN\n//{{CODEBEGIN\n//{{CODEEND\n"


def con_codigo(cuerpo, objetos=""):
    """Formulario con la tabla orders y un `On Open` con ese cuerpo (y esas variables locales)."""
    texto = con_tabla(("order_nbr as column", "customer as column"), cabecera="Table orders is orders", controles=ORD)
    locales = "objects begin\n" + "".join(f"    {o}\n" for o in objetos.split("\n") if o) + "end\n" if objetos else ""
    evento = "On Open\n" + locales + "begin\n" + "".join(f"    {s}\n" for s in cuerpo.split("\n") if s) + "end\n"
    return texto.replace(VACIO, "CODE CLASS f BEGIN\n//{{CODEBEGIN\n" + evento + "//{{CODEEND\n")


P = {}
P["k_base"] = con_codigo("SetEditMode(TRUE);")
P["k_disable"] = con_codigo('orders.DisableCommand("Query", TRUE);')
P["k_disable_variable"] = con_codigo('orders.DisableCommand("Query", b);', "b as Boolean")
P["k_columna_tabla"] = con_codigo("x = orders.order_nbr;", "x as Integer")
P["k_columna_sola"] = con_codigo("x = order_nbr;", "x as Integer")
P["k_asigna_columna"] = con_codigo("orders.customer = 5;")
P["k_asigna_columna_sola"] = con_codigo("customer = 5;")
P["k_select_columna"] = con_codigo('Sql.SelectWindow(Self, "select customer from customers", NULL, "t", 1, orders.customer);')
P["k_select_variable"] = con_codigo('Sql.SelectWindow(Self, "select customer from customers", NULL, "t", 1, x);', "x as Integer")
P["k_select_dos"] = con_codigo('Sql.SelectWindow(Self, "select customer from customers", NULL, "t", 2, orders.customer);')
P["k_columna_suma"] = con_codigo("x = orders.order_nbr + orders.customer;", "x as Integer")
# --- segunda tanda: la tabla como argumento (ALMAFAC2 albaran: `EditingTable.IsMe(albaranes)`; su nodo lleva 0x05 en
# el byte 2, como cualquier argumento), al final para no mover los huecos
P["k_isme"] = con_codigo("b = EditingTable.IsMe(orders);", "b as Boolean")
P["k_isme_not"] = con_codigo("b = not EditingTable.IsMe(orders);", "b as Boolean")
P["k_isme_if"] = con_codigo("if orders.IsMe(EditingTable) then\n    b = TRUE;", "b as Boolean")
P["k_disable_isme"] = con_codigo('DisableCommand("Query", not EditingTable.IsMe(orders));')


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

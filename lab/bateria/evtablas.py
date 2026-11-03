"""Batería de eventos de tabla (`On Fetch Table orders`…; PRO de tipo 6), uno por programa, para saber el código que
da el compilador a cada uno (PRO +0x28). Los nombres, los de la lista de eventos de cosmakecon (de Fetch a Locked).
Uso: python3 -I evtablas.py <dir salida> <huecos.txt> [desde]   (en la carpeta samples del laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("codtablas", Path(__file__).with_name("codtablas.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)
_f, con_tabla, ORD, VACIO = _c._f, _c.con_tabla, _c.ORD, _c.VACIO

EVENTOS = ["Fetch", "Add", "Update", "Delete", "RowChanged", "Edit", "AcceptEdit", "CancelEdit", "QueryBegin", "QueryEnd",
           "ReFetch", "ChangingRow", "Error", "BeginGroup", "EndGroup", "Eof", "Locked"]


def con_evento(cabecera, cuerpo="SetEditMode(TRUE);", objetos=""):
    texto = con_tabla(("order_nbr as column", "customer as column"), cabecera="Table orders is orders", controles=ORD)
    locales = "objects begin\n" + "".join(f"    {o}\n" for o in objetos.split("\n") if o) + "end\n" if objetos else ""
    evento = cabecera + "\n" + locales + "begin\n" + "".join(f"    {s}\n" for s in cuerpo.split("\n") if s) + "end\n"
    return texto.replace(VACIO, "CODE CLASS f BEGIN\n//{{CODEBEGIN\n" + evento + "//{{CODEEND\n")


P = {f"e_{e.lower()}": con_evento(f"On {e} Table orders") for e in EVENTOS}
P["e_fetch_locales"] = con_evento("On Fetch Table orders", "x = orders.order_nbr;", "x as Integer")
P["e_dos"] = con_evento("On Fetch Table orders").replace("//{{CODEEND\n", "On Edit Table orders\nbegin\n    SetEditMode(FALSE);\nend\n//{{CODEEND\n", 1)
P["e_fetch_minusculas"] = con_evento("on fetch table orders")
# de cualquier tabla: +0x20 = 0 y el nombre de la tabla como parámetro (ALMAFAC2 albaran)
P["e_edit_cualquiera"] = con_evento("On Edit Table (tab as Char)")
P["e_fetch_cualquiera"] = con_evento("On Fetch Table (tab as Char)")
P["e_edit_sin_parametro"] = con_evento("On Edit Table")
P["e_table_minusculas"] = con_evento("On Fetch table orders")


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

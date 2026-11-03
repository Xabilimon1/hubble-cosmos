"""Batería de tablas en formularios (`Table x is tabla begin … end`, repositorio `stock` del kit):
columnas, required, default, calculadas, alias y los controles con VARIABLE tabla.columna. Un
cambio por programa sobre `tb_base`. El fuente lleva `REPOSITORY stock`, que el .omd no guarda.
Uso: python3 -I tablas.py <dir salida> <huecos.txt> [desde]   (carpeta propia en el laboratorio)
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("formularios", Path(__file__).with_name("formularios.py"))
_f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f)
form, control = _f.form, _f.control


def con_tabla(columnas=("state as column",), cabecera="Table states is states", controles=None, extra_tabla=""):
    if controles is None:
        controles = control("EDIT", "VARIABLE states.state\nLIKEVAR", nombre="e")
    tabla = (f"\t\t{cabecera}\n" + "".join(f"\t\t\t{x}\n" for x in extra_tabla.split("\n") if x)
             + "\t\tbegin\n" + "".join(f"\t\t\t{c}\n" for c in columnas) + "\t\tend\n")
    texto = form(controles=controles)
    return "REPOSITORY stock\n" + texto.replace("\t\tINTERFACE\n", tabla + "\t\tINTERFACE\n")


P = {}
P["tb_base"] = con_tabla()
P["tb_required"] = con_tabla(("state as column required",))
P["tb_dos"] = con_tabla(("state as column", "sname as column"))
P["tb_dos_orden"] = con_tabla(("sname as column", "state as column"))
P["tb_default"] = con_tabla(("state as column default \"MA\"",))
P["tb_calculada"] = con_tabla(("state as column", "x as Char (10)"))
P["tb_calculada_default"] = con_tabla(("state as column", "x as Decimal (9,2) default 0"))
P["tb_alias"] = con_tabla(cabecera="Table st is states", controles=control("EDIT", "VARIABLE st.state\nLIKEVAR", nombre="e"))
P["tb_sin_likevar"] = con_tabla(controles=control("EDIT", "VARIABLE states.state\nDATATYPE CHAR(2)", nombre="e"))
P["tb_dos_controles"] = con_tabla(("state as column", "sname as column"),
                                  controles=control("EDIT", "VARIABLE states.state\nLIKEVAR", nombre="e")
                                  + control("EDIT", "VARIABLE states.sname\nLIKEVAR", nombre="f", posicion="10 40 50 20"))
P["tb_otra_tabla"] = con_tabla(("payform as column",), cabecera="Table payforms is payforms",
                               controles=control("EDIT", "VARIABLE payforms.payform\nLIKEVAR", nombre="e"))
P["tb_lookup"] = con_tabla(("customer as column", "company as column", "state as column", "sname as states.sname",
                            "\tjoin fk1_customers lookup \"sname\""), cabecera="Table customers is customers",
                           controles=control("EDIT", "VARIABLE customers.customer\nLIKEVAR", nombre="e"))


P["tb_box_table"] = con_tabla(controles="\t\t\tCONTROL AS BOX\n\t\t\t\tPOSITION 0 0 190 90\n\t\t\t\tTABLE states\n\t\t\tBEGIN\n"
                              + control("EDIT", "VARIABLE states.state\nLIKEVAR", nombre="e").replace("\t\t\t", "\t\t\t\t")
                              + "\t\t\tEND\n")


# --- join … lookup (claves de customers en el repositorio stock: for1_cli → states, for2_cli → payforms)
CLI = control("EDIT", "VARIABLE customers.customer\nLIKEVAR", nombre="e")
UNION = ("sname as states.sname", '\tjoin for1_cli lookup "sname"')
P["j_base"] = con_tabla(("customer as column", "state as column", *UNION), cabecera="Table customers is customers", controles=CLI)
P["j_dos"] = con_tabla(("customer as column", "state as column", *UNION, "payform as column", "description as payforms.description",
                        '\tjoin for2_cli lookup "description"'), cabecera="Table customers is customers", controles=CLI)
P["j_otro_nombre"] = con_tabla(("customer as column", "state as column", "nombre as states.sname", '\tjoin for1_cli lookup "sname"'),
                               cabecera="Table customers is customers", controles=CLI)
P["j_antes"] = con_tabla(("customer as column", *UNION, "state as column"), cabecera="Table customers is customers", controles=CLI)

# --- `x as tabla.columna` sin join (samples EjLookupColumns: state as states.state, statename as states.sname), al final
for nombre, cols in [("misma", ("customer as column", "state as states.state")),
                     ("otro_nombre", ("customer as column", "statename as states.sname")),
                     ("dos", ("customer as column", "state as states.state", "statename as states.sname")),
                     ("con_join", ("customer as column", "state as column", *UNION, "x as payforms.description")),
                     ("delante", ("x as states.sname", "customer as column"))]:
    P[f"jx_{nombre}"] = con_tabla(cols, cabecera="Table customers is customers", controles=CLI)


# --- GRID: NOROWNUM, NOARROW y NOALLOWADD (no salen en ningún fuente del kit; el orden de las cadenas del compilador
# es PARENTGRID, COLUMNS n, NOROWNUM, NOARROW, NOALLOWADD, AUTOSORT), al final
HIJO = "\t\t\t\tCONTROL e AS EDIT\n\t\t\t\t\tPOSITION 0 0 75 22\n\t\t\t\t\tNOBORDER\n\t\t\t\t\tVARIABLE states.state\n\t\t\t\t\tLIKEVAR\n"


def rejilla(atributos="TABLE states\nPARENTGRID"):
    cab = "\t\t\tCONTROL g AS GRID\n\t\t\t\tPOSITION 0 0 190 90\n" + "".join(f"\t\t\t\t{x}\n" for x in atributos.split("\n") if x)
    return con_tabla(controles=cab + "\t\t\tBEGIN\n" + HIJO + "\t\t\tEND\n")


TP = "TABLE states\nPARENTGRID\n"
for nombre, a in [("base", ""), ("autosort", "AUTOSORT"), ("norownum", "NOROWNUM"), ("noarrow", "NOARROW"),
                  ("noallowadd", "NOALLOWADD"), ("norownum_noarrow", "NOROWNUM\nNOARROW"),
                  ("noarrow_noallowadd", "NOARROW\nNOALLOWADD"), ("norownum_noallowadd", "NOROWNUM\nNOALLOWADD"),
                  ("tres", "NOROWNUM\nNOARROW\nNOALLOWADD"), ("cuatro", "NOROWNUM\nNOARROW\nNOALLOWADD\nAUTOSORT"),
                  ("noarrow_norownum", "NOARROW\nNOROWNUM"), ("noallowadd_noarrow", "NOALLOWADD\nNOARROW"),
                  ("noallowadd_norownum", "NOALLOWADD\nNOROWNUM"), ("autosort_noallowadd", "AUTOSORT\nNOALLOWADD"),
                  ("autosort_norownum", "AUTOSORT\nNOROWNUM"), ("columns", "COLUMNS 1"), ("columns_norownum", "COLUMNS 1\nNOROWNUM"),
                  ("norownum_columns", "NOROWNUM\nCOLUMNS 1")]:
    P[f"rj_{nombre}"] = rejilla(TP + a)
P["rj_norownum_antes_parentgrid"] = rejilla("TABLE states\nNOROWNUM\nPARENTGRID")
P["rj_norownum_antes_table"] = rejilla("NOROWNUM\nTABLE states\nPARENTGRID")
P["rj_scroll_norownum"] = rejilla("SCROLL VERTICAL\nTABLE states\nPARENTGRID\nNOROWNUM")
P["rj_norownum_sin_parentgrid"] = rejilla("TABLE states\nNOROWNUM")
P["rj_noarrow_antes_parentgrid"] = rejilla("TABLE states\nNOARROW\nPARENTGRID")
P["rj_noallowadd_antes_parentgrid"] = rejilla("TABLE states\nNOALLOWADD\nPARENTGRID")
P["rj_tres_scroll_autosize"] = rejilla("AUTOSIZE\nSCROLL VERTICAL HORIZONTAL\nTABLE states\nPARENTGRID\nNOROWNUM\nNOARROW\nNOALLOWADD\nAUTOSORT")
# segunda tanda: en un GRID, los bits de NOARROW, NOROWNUM y NOALLOWADD son los de PASSWORD, UPSHIFT y DOWNSHIFT
for a in ("PASSWORD", "UPSHIFT", "DOWNSHIFT"):
    P[f"rj2_{a.lower()}"] = rejilla(TP + a)
    P[f"rj2_{a.lower()}_antes"] = rejilla("TABLE states\n" + a + "\nPARENTGRID")


# --- un CHECK con VARIABLE e ICON n dentro de la rejilla, como el de STOCKMDI TRIPLE (`LABEL "Invoiced"` / `NOBORDER` /
# `VARIABLE orders.order_status` / `ICON 6`; Hubble escribía el icono delante de VARIABLE y no compilaba), al final
def rejilla_check(atributos):
    hijo = ('\t\t\t\tCONTROL AS CHECK\n\t\t\t\t\tPOSITION 0 0 65 22\n\t\t\t\t\tLABEL "Invoiced"\n\t\t\t\t\tNOBORDER\n'
            + "".join(f"\t\t\t\t\t{x}\n" for x in atributos.split("\n") if x))
    cab = "\t\t\tCONTROL g AS GRID\n\t\t\t\tPOSITION 0 0 190 90\n\t\t\t\tSCROLL VERTICAL\n\t\t\t\tTABLE states\n\t\t\t\tPARENTGRID\n"
    return con_tabla(("state as column", "sname as column"), controles=cab + "\t\t\tBEGIN\n" + HIJO + hijo + "\t\t\tEND\n")


P["rk_var_icon"] = rejilla_check("VARIABLE states.sname\nICON 6")
P["rk_icon_var"] = rejilla_check("ICON 6\nVARIABLE states.sname")  # lo que escribía Hubble


# --- UPSHIFT que LIKEVAR copia de la columna (STOCKMDI cust_rep: `surname1 as customers.surname` salía
# `customers.company`, las dos Char(25) con máscara 0, y el VAR de página con LIKEVAR llevaba 0x40000 de +0x00 de más).
# En stock.crf, `customers.company`, `states.state`… llevan 0x2 en el u16 de +0x24 del registro de columna
# (syscolattr 'B' = 'U'); `surname` y `fname`, 0. Variables `p as tabla.columna` sin join (escala -1), al final.
def pagina_stock(objetos, controles):
    return ("REPOSITORY stock\nCONSTANTS  begin\nend\nCLASSES BEGIN\n\tpg is Page begin\n\t\tobjects begin\n"
            + "".join(f"\t\t\t{o}\n" for o in objetos.split("\n") if o)
            + "\t\tend\n\t\tINTERFACE\n\t\t\tSIZE 595 842\n\t\t\tMARGIN 12 24 15 48\n\t\tBEGIN\n" + controles
            + "\t\tEND\n\tend\nEND\nCODE CLASS pg BEGIN\n//{{CODEBEGIN\n//{{CODEEND\nEND\n"
            "CODE BEGIN\n//{{CODEBEGIN\nmain\nobjects begin\n    q as pg\nend\nbegin\nend\n//{{CODEEND\nEND\n")


def var_pag(atributos, variable="p", posicion="10 10 100 20"):
    return (f"\t\t\tCONTROL AS VAR\n\t\t\t\tPOSITION {posicion}\n\t\t\t\tLABEL \"l\"\n\t\t\t\tVARIABLE {variable}\n"
            + "".join(f"\t\t\t\t{a}\n" for a in atributos.split("\n") if a))


def form_stock(objetos, tipo, atributos):
    return "REPOSITORY stock\n" + form(objetos=objetos, controles=control(tipo, atributos, nombre="e"))


P["up_var_surname"] = pagina_stock("p as customers.surname", var_pag("LIKEVAR"))  # sin 0x2 en el .crf
P["up_var_company"] = pagina_stock("p as customers.company", var_pag("LIKEVAR"))  # con 0x2: ¿UPSHIFT en el control?
P["up_var_state"] = pagina_stock("p as states.state", var_pag("LIKEVAR"))  # Char(2) con 0x2
P["up_var_fname"] = pagina_stock("p as customers.fname", var_pag("LIKEVAR"))  # Char(15) sin 0x2
P["up_var_company_datatype"] = pagina_stock("p as customers.company", var_pag("DATATYPE CHAR(25)"))  # sin LIKEVAR
P["up_var_company_upshift"] = pagina_stock("p as customers.company", var_pag("LIKEVAR\nUPSHIFT"))  # escrito
P["up_var_surname_upshift"] = pagina_stock("p as customers.surname", var_pag("LIKEVAR\nUPSHIFT"))
P["up_text_company"] = form_stock("p as customers.company", "TEXT", "VARIABLE p\nLIKEVAR\nTAGS \"x\"")
P["up_text_surname"] = form_stock("p as customers.surname", "TEXT", "VARIABLE p\nLIKEVAR\nTAGS \"x\"")
P["up_text_company_upshift"] = form_stock("p as customers.company", "TEXT", "VARIABLE p\nLIKEVAR\nUPSHIFT\nTAGS \"x\"")
P["up_text_surname_upshift"] = form_stock("p as customers.surname", "TEXT", "VARIABLE p\nLIKEVAR\nUPSHIFT\nTAGS \"x\"")
P["up_edit_company"] = form_stock("p as customers.company", "EDIT", "VARIABLE p\nLIKEVAR")
P["up_edit_surname"] = form_stock("p as customers.surname", "EDIT", "VARIABLE p\nLIKEVAR")
P["up_edit_company_upshift"] = form_stock("p as customers.company", "EDIT", "VARIABLE p\nUPSHIFT\nLIKEVAR")  # como lo escribe Hubble
P["up_edit_surname_upshift"] = form_stock("p as customers.surname", "EDIT", "VARIABLE p\nUPSHIFT\nLIKEVAR")
P["up_edit_company_datatype"] = form_stock("p as customers.company", "EDIT", "VARIABLE p\nDATATYPE CHAR(25)")  # sin LIKEVAR
P["up_edit_company_datatype_upshift"] = form_stock("p as customers.company", "EDIT", "VARIABLE p\nDATATYPE CHAR(25)\nUPSHIFT")
P["up_edit_surname_datatype_upshift"] = form_stock("p as customers.surname", "EDIT", "VARIABLE p\nDATATYPE CHAR(25)\nUPSHIFT")


def main(argv=None):
    _f.P.clear()
    _f.P.update(P)
    _f.main(argv)


if __name__ == "__main__":
    main()

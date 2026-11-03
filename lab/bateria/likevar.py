"""Batería de LIKEVAR con la máscara de una columna (REPOSITORY almafac, el proyecto ALMAFAC del kit).

`LIKEVAR` copia en el control (nibble alto del u16 alto de +0x20) la máscara de la columna, y la columna la saca
del repositorio: del `.crf` de junto al `.dbs` (sin él, «Can not load repository almafac»). Una variable Money de
columna da en el FOB los mismos bytes que escrita a mano: solo la máscara del control dice que era una columna.

Se compila en una copia del proyecto ALMAFAC (`~/hubble-lab/trabajo/ALMAFAC`, con su ALMAFAC.PRJ): los módulos
tienen que estar registrados en el .prj («Unregistered module»), así que los programas llevan los nombres de los
módulos de ALMAFAC en vez de huecos. Uso:

    python3 -I likevar.py <dir salida>

En la exploración (2026-10-31) se compiló además con copias del repositorio con un byte cambiado:
- máscara de `precio_tipo` (registro 63 del .crf, +0x32) de 4 a 3: el control de `p as articulos.pr_cost` da 3;
- máscara propia de `pr_cost` (registro 11, que hereda de `precio_tipo`) de 0 a 3: sigue en 4 (no cuenta);
- máscara de `articulos.existencias` a 3: da 3; la de `articulos.articulo` a 6: `lineas.articulo` (que hereda de
  ella) da 6;
- sin el .crf: no compila;
- el .crf v2 de almafac4 (y el mismo cambio de 4 a 3 en su `precio_tipo`): igual.
"""
import sys
from pathlib import Path

# los módulos de ALMAFAC.PRJ (sin COMUN, que lo incluyen los demás)
NOMBRES = ["ALBARAN", "ARTICULO", "AUXILIAR", "CLIENTES", "ETICLI", "FACTURAR", "FRMTMPL", "INICIO", "LISALBA1",
           "LISTACLI", "LISTALBA", "LPROART", "PROVCLI", "PROVEE", "PROVPROV", "TRIPLE"]


def var(atributos, variable="p", posicion="10 10 100 20"):
    return (f"\t\t\tCONTROL AS VAR\n\t\t\t\tPOSITION {posicion}\n\t\t\t\tLABEL \"l\"\n\t\t\t\tVARIABLE {variable}\n"
            + "".join(f"\t\t\t\t{a}\n" for a in atributos.split("\n") if a))


def pagina(objetos, controles):
    return ("REPOSITORY almafac\nCONSTANTS  begin\nend\nCLASSES BEGIN\n\tpg is Page begin\n\t\tobjects begin\n"
            + "".join(f"\t\t\t{o}\n" for o in objetos.split("\n") if o)
            + "\t\tend\n\t\tINTERFACE\n\t\t\tSIZE 595 842\n\t\t\tMARGIN 12 24 15 48\n\t\tBEGIN\n" + controles
            + "\t\tEND\n\tend\nEND\nCODE CLASS pg BEGIN\n//{{CODEBEGIN\n//{{CODEEND\nEND\n"
            "CODE BEGIN\n//{{CODEBEGIN\nmain\nobjects begin\n    q as pg\nend\nbegin\nend\n//{{CODEEND\nEND\n")


def form(objetos, controles):
    return ("REPOSITORY almafac\nCONSTANTS  begin\nend\nCLASSES BEGIN\n\tf is Form begin\n\t\tobjects begin\n"
            + "".join(f"\t\t\t{o}\n" for o in objetos.split("\n") if o)
            + "\t\tend\n\t\tINTERFACE\n\t\t\tPOSITION 0 0 200 100\n\t\tBEGIN\n" + controles
            + "\t\tEND\n\tend\nEND\nCODE CLASS f BEGIN\n//{{CODEBEGIN\n//{{CODEEND\nEND\n"
            "CODE BEGIN\n//{{CODEBEGIN\nmain\nobjects begin\n    o as f\nend\nbegin\n    o.Run;\nend\n//{{CODEEND\nEND\n")


P = {}
P["lk_money_columna"] = pagina("p as articulos.pr_cost", var("LIKEVAR"))  # LPROART: máscara 4 (DECIMAL MASK 4)
P["lk_money_a_mano"] = pagina("p as Money(12,2)", var("LIKEVAR"))  # máscara 0: no es de la clase ni de (12,2)
P["lk_money_total_factura"] = pagina("p as clientes.total_factura", var("LIKEVAR"))  # las cuatro heredan de
P["lk_money_pr_vent"] = pagina("p as articulos.pr_vent", var("LIKEVAR"))  # precio_tipo: el mismo .omd
P["lk_money_precio"] = pagina("p as lineas.precio", var("LIKEVAR"))
P["lk_columna_datatype"] = pagina("p as articulos.pr_cost", var("DATATYPE DECIMAL(12,2)"))  # sin LIKEVAR: igual
P["lk_money_datatype"] = pagina("p as Money(12,2)", var("DATATYPE DECIMAL(12,2)"))  # que el de a mano
P["lk_decimal_a_mano"] = pagina("p as Decimal(12,2)", var("LIKEVAR"))
P["lk_date_columna"] = pagina("p as albaranes.fecha_albaran", var("LIKEVAR"))  # fecha_tipo: máscara 5
P["lk_date_a_mano"] = pagina("p as Date", var("LIKEVAR"))
P["lk_smallint_columna"] = pagina("p as articulos.existencias", var("LIKEVAR"))
P["lk_texto_form"] = form("p as articulos.pr_cost", "\t\t\tCONTROL AS TEXT\n\t\t\t\tPOSITION 10 10 100 20\n"
                          "\t\t\t\tVARIABLE p\n\t\t\t\tLIKEVAR\n\t\t\t\tTAGS \"x\"\n")
P["lk_dos_controles"] = pagina("p as articulos.pr_cost", var("LIKEVAR") + var("LIKEVAR", posicion="10 40 100 20"))
P["lk_dos_variables"] = pagina("p as articulos.pr_cost\nm as Money(12,2)",
                               var("LIKEVAR") + var("LIKEVAR", variable="m", posicion="10 40 100 20"))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    salida = Path(argv[0])
    if len(NOMBRES) < len(P):
        sys.exit(f"faltan nombres: {len(NOMBRES)} < {len(P)}")
    salida.mkdir(parents=True, exist_ok=True)
    filas = []
    for (nombre, fuente), modulo in zip(P.items(), NOMBRES):
        (salida / f"{modulo}.SMD").write_bytes(fuente.replace("\n", "\r\n").encode("cp1252"))
        filas.append(f"{modulo}\t{nombre}")
    (salida / "manifiesto.tsv").write_text("\n".join(filas) + "\n")
    print(len(filas), "programas")


if __name__ == "__main__":
    main()

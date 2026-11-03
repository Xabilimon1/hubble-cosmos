"""Batería de formularios para la compilación diferencial.

Como genera.py, pero cada programa es un módulo con un formulario `f` y un `main` que lo
abre. El base (`f_base`) es un formulario vacío; cada variante cambia una sola cosa: un
atributo del formulario, un control, un atributo de un EDIT o un evento. Uso:

    python3 -I formularios.py <dir salida> <huecos.txt> [desde]

`desde` = cuántos huecos saltarse (los que ya usa la batería de código).
"""
import sys
from pathlib import Path


def form(interfaz_form="", controles="", objetos="", eventos=""):
    return (
        "CONSTANTS  begin\nend\nCLASSES BEGIN\n\tf is Form begin\n\t\tobjects begin\n"
        + "".join(f"\t\t\t{o}\n" for o in objetos.split("\n") if o)
        + "\t\tend\n\t\tINTERFACE\n\t\t\tPOSITION 0 0 200 100\n"
        + "".join(f"\t\t\t{a}\n" for a in interfaz_form.split("\n") if a)
        + "\t\tBEGIN\n" + controles + "\t\tEND\n\tend\nEND\n"
        + "CODE CLASS f BEGIN\n//{{CODEBEGIN\n" + eventos + "//{{CODEEND\nEND\n"
        + "CODE BEGIN\n//{{CODEBEGIN\nmain\nobjects begin\n    o as f\nend\nbegin\n    o.Run;\nend\n//{{CODEEND\nEND\n"
    )


def control(tipo, atributos="", nombre="c", posicion="10 10 50 20"):
    return (f"\t\t\tCONTROL {nombre} AS {tipo}\n\t\t\t\tPOSITION {posicion}\n"
            + "".join(f"\t\t\t\t{a}\n" for a in atributos.split("\n") if a))


EDIT = "DATATYPE CHAR"
P = {}
P["f_base"] = form()
# --- el formulario
for nombre, a in [("label", 'LABEL "Hola"'), ("sysmenu", "SYSMENU"), ("minimize", "MINIMIZE"), ("maximize", "MAXIMIZE"),
                  ("resizing", "RESIZING"), ("label_sysmenu", 'LABEL "Hola"\nSYSMENU'), ("font", 'FONT "Arial" 10'),
                  ("foreground", "FOREGROUND RGB 1 2 3"), ("background", "BACKGROUND COLOR white"), ("noborder", "NOBORDER")]:
    P[f"f_{nombre}"] = form(interfaz_form=a)
P["f_pos_ancho"] = form().replace("POSITION 0 0 200 100", "POSITION 0 0 300 100")
P["f_pos_xy"] = form().replace("POSITION 0 0 200 100", "POSITION 10 20 200 100")
# --- un control de cada tipo
for t in ["TEXT", "BOX", "BUTTON", "EDIT", "LIST", "CHECK", "RADIO", "SPIN", "DROPLIST", "DROPEDIT",
          "PERCENT", "SLIDER", "PANEL", "BITMAP", "GRID", "BUTTONGROUP", "BOXGROUP"]:
    atributos = {"EDIT": EDIT, "DROPEDIT": EDIT, "RADIO": 'NUMBER 2 TAGS "a" "b"',
                 "BUTTONGROUP": 'NUMBER 2 TAGS "a" "b"', "BOXGROUP": 'NUMBER 2 TAGS "a" "b"'}.get(t, "")
    P[f"c_{t.lower()}"] = form(controles=control(t, atributos))
P["c_edit_sin_nombre"] = form(controles=control("EDIT", EDIT, nombre="").replace("CONTROL  AS", "CONTROL AS"))
P["c_edit_otro_nombre"] = form(controles=control("EDIT", EDIT, nombre="campo"))
P["c_dos_edits"] = form(controles=control("EDIT", EDIT) + control("EDIT", EDIT, nombre="d", posicion="10 40 50 20"))
for nombre, pos in [("pos_x", "11 10 50 20"), ("pos_y", "10 11 50 20"), ("pos_w", "10 10 51 20"), ("pos_h", "10 10 50 21"),
                    ("pos_grande", "300 400 500 600")]:
    P[f"c_edit_{nombre}"] = form(controles=control("EDIT", EDIT, posicion=pos))
P["c_box_con_edit"] = form(controles="\t\t\tCONTROL AS BOX\n\t\t\t\tPOSITION 0 0 190 90\n\t\t\tBEGIN\n"
                           + control("EDIT", EDIT).replace("\t\t\t", "\t\t\t\t") + "\t\t\tEND\n")
# --- atributos de un EDIT
ATRIBUTOS = [
    "NOBORDER", "BORDER DOUBLE DOWN", "BORDER ETCHED", "BORDER DOWN", "BORDER HILIGHT", "NOLABEL", 'LABEL "x"', 'LABEL "otro"',
    'TAGS "a"', 'TAGS "a" "b"', "FOREGROUND RGB 1 2 3", "FOREGROUND RGB 0 0 0", "FOREGROUND COLOR blue", "BACKGROUND COLOR white",
    "BACKGROUND RGB 4 5 6", "ATTACH ALL", "ATTACH TOP RIGHT", "ATTACH LEFT", "ALIGNMENT RIGHT", "ALIGNMENT CENTER",
    'FONT "Arial" 10', 'FONT "Arial" 12', 'FONT "Arial" 10 CHARSET Ansi', "BOLD", "MULTILINE", "PASSWORD", "READONLY",
    "DISABLED", "UPSHIFT", "DOWNSHIFT", "NOTABSTOP", 'COMMENT "c"', "SCROLL VERTICAL", "SCROLL VERTICAL HORIZONTAL",
    "BUTTON", "AUTOSIZE", "WRAP", "FOCUS", "LABELLEFT",
]
for a in ATRIBUTOS:
    clave = "a_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower()).strip("_")
    P[clave] = form(controles=control("EDIT", a + "\n" + EDIT))  # DATATYPE va después
for nombre, dt in [("integer", "DATATYPE INTEGER"), ("smallint", "DATATYPE SMALLINT"), ("date", "DATATYPE DATE"),
                   ("char30", "DATATYPE CHAR(30)"), ("integer_mask", "DATATYPE INTEGER MASK 2"), ("decimal", "DATATYPE DECIMAL"),
                   ("sin", "")]:
    P[f"dt_{nombre}"] = form(controles=control("EDIT", dt))
P["dt_date_picker"] = form(controles=control("EDIT", "DATATYPE DATE\nDATETIMEPICKER"))
P["v_variable"] = form(objetos="v as char", controles=control("EDIT", "VARIABLE v\n" + EDIT))
P["v_likevar"] = form(objetos="v as char", controles=control("EDIT", "VARIABLE v\nLIKEVAR"))
P["b_command"] = form(controles=control("BUTTON", "COMMAND Close"))
P["b_command_ok"] = form(controles=control("BUTTON", "COMMAND Ok"))
P["b_defpush"] = form(controles=control("BUTTON", "DEFPUSH"))
P["b_label"] = form(controles=control("BUTTON", 'LABEL "Aceptar"'))
P["t_tags"] = form(controles=control("TEXT", 'TAGS "Nombre"'))
P["t_tags_noborder"] = form(controles=control("TEXT", 'NOBORDER\nTAGS "Nombre"'))
# --- eventos
P["e_open"] = form(eventos="On Open\nbegin\nend\n")
P["e_open_codigo"] = form(eventos='On Open\nbegin\n    "x".Trace;\nend\n')
P["e_close"] = form(eventos="On Close\nbegin\nend\n")
P["e_command_ok"] = form(controles=control("BUTTON", "COMMAND Ok"), eventos="On Command Ok\nbegin\nend\n")
P["e_click"] = form(controles=control("BUTTON", ""), eventos="On Click c\nbegin\nend\n")
P["e_exit"] = form(controles=control("EDIT", EDIT), eventos="On Exit c\nbegin\nend\n")
P["e_enter"] = form(controles=control("EDIT", EDIT), eventos="On Enter c\nbegin\nend\n")
P["e_open_close"] = form(eventos="On Open\nbegin\nend\n\nOn Close\nbegin\nend\n")
P["m_metodo"] = form(eventos="public m()\nbegin\nend\n")
P["m_metodo_uso"] = form(eventos='public m()\nbegin\n    "x".Trace;\nend\n\nOn Open\nbegin\n    m();\nend\n')
P["o_objeto_form"] = form(objetos="v as integer")
P["o_objeto_form_uso"] = form(objetos="v as integer", eventos="On Open\nbegin\n    v = 1;\nend\n")

# --- familia «ventana» (2026-10-31): THINFRAME, THINCAPTION y CHECKMETHOD, al final (prefijo vw_)
for a in ["THINFRAME", "THINFRAME\nSYSMENU", "SYSMENU\nTHINFRAME", "THINFRAME\nMAXIMIZE", "MAXIMIZE\nTHINFRAME",
          "RESIZING\nTHINFRAME", "THINFRAME\nRESIZING", "THINFRAME\nNOBORDER", "NOBORDER\nTHINFRAME", 'LABEL "Hola"\nTHINFRAME',
          "THINFRAME\nMINIMIZE", "THINFRAME\nALLOWDROP", "NOBORDER\nSYSMENU", "NOBORDER\nRESIZING", "RESIZING\nNOBORDER",
          "THINCAPTION", "THINCAPTION\nSYSMENU", "SYSMENU\nTHINCAPTION", "FOREGROUND RGB 0 0 0\nTHINCAPTION\nSYSMENU",
          'LABEL "Hola"\nTHINCAPTION', "THINFRAME\nTHINCAPTION", "THINCAPTION\nTHINFRAME", "THINCAPTION\nMINIMIZE",
          "MINIMIZE\nTHINCAPTION", "THINCAPTION\nNOBORDER", "NOBORDER\nTHINCAPTION", "RESIZING\nTHINCAPTION",
          "MAXIMIZE\nMINIMIZE\nTHINCAPTION\nSYSMENU"]:
    P["vw_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = form(interfaz_form=a)
P["vw_thinframe_control"] = form(controles=control("EDIT", "DATATYPE CHAR\nTHINFRAME"))
P["vw_thincaption_control"] = form(controles=control("EDIT", "DATATYPE CHAR\nTHINCAPTION"))
CHEQUEAR = "public Chequear() return Boolean\nbegin\n    return TRUE;\nend\n"
for nombre, tipo, a, ev in [
        ("checkmethod", "EDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_antes", "EDIT", "CHECKMETHOD Chequear\nDATATYPE CHAR", CHEQUEAR),
        ("checkmethod_otro", "EDIT", "DATATYPE CHAR\nCHECKMETHOD Otro", CHEQUEAR.replace("Chequear", "Otro")),
        ("checkmethod_cadena", "EDIT", 'DATATYPE CHAR\nCHECKMETHOD "Chequear"', CHEQUEAR),
        ("checkmethod_sin_metodo", "EDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear", ""),
        ("checkmethod_readonly", "EDIT", "DATATYPE CHAR\nREADONLY\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_readonly_tras", "EDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear\nREADONLY", CHEQUEAR),
        ("checkmethod_dropedit", "DROPEDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_dropedit_readonly", "DROPEDIT", "DATATYPE CHAR\nREADONLY\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_text", "TEXT", "CHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_integer", "EDIT", "DATATYPE INTEGER\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_picker", "EDIT", "DATATYPE DATE\nDATETIMEPICKER\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_picker_antes", "EDIT", "DATATYPE DATE\nCHECKMETHOD Chequear\nDATETIMEPICKER", CHEQUEAR),
        ("checkmethod_scroll", "EDIT", "DATATYPE CHAR\nSCROLL VERTICAL\nCHECKMETHOD Chequear", CHEQUEAR),
        ("checkmethod_tags", "EDIT", 'DATATYPE CHAR\nTAGS "a"\nCHECKMETHOD Chequear', CHEQUEAR),
        ("checkmethod_largo", "EDIT", "DATATYPE CHAR\nCHECKMETHOD ChequearElValorQueSeHaEscrito",
         CHEQUEAR.replace("Chequear", "ChequearElValorQueSeHaEscrito")),
        ("checkmethod_privado", "EDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear", CHEQUEAR.replace("public", "private")),
        ("checkmethod_dos", "EDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear", CHEQUEAR + "\npublic Otro() return Boolean\nbegin\n    return TRUE;\nend\n")]:
    P["vw_" + nombre] = form(controles=control(tipo, a), eventos=ev)
P["vw_checkmethod_edit_variable"] = form(objetos="v as char", controles=control("EDIT", "VARIABLE v\nLIKEVAR\nCHECKMETHOD Chequear"), eventos=CHEQUEAR)
P["vw_checkmethod_dos_edits"] = form(controles=control("EDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear")
                                     + control("EDIT", "DATATYPE CHAR\nCHECKMETHOD Otro", nombre="d", posicion="10 40 50 20"),
                                     eventos=CHEQUEAR + "\npublic Otro() return Boolean\nbegin\n    return TRUE;\nend\n")

# segunda tanda: dónde va NOBORDER respecto a los demás del formulario, y CHECKMETHOD con los atributos de lista
for a in ["SYSMENU\nNOBORDER", "NOBORDER\nMAXIMIZE", "MAXIMIZE\nNOBORDER", "NOBORDER\nMINIMIZE", "MINIMIZE\nNOBORDER",
          "NOBORDER\nALLOWDROP", "ALLOWDROP\nNOBORDER", "ALLOWDROP\nTHINFRAME", "THINCAPTION\nALLOWDROP", "ALLOWDROP\nTHINCAPTION",
          "THINCAPTION\nSYSMENU\nNOBORDER", "NOBORDER\nTHINCAPTION\nSYSMENU", 'THINFRAME\nLABEL "Hola"', 'THINCAPTION\nLABEL "Hola"',
          "NOLABEL\nTHINFRAME", "THINFRAME\nNOLABEL", "RESIZING\nMAXIMIZE\nMINIMIZE\nTHINCAPTION\nSYSMENU\nALLOWDROP"]:
    P["vw2_" + "".join(ch if ch.isalnum() else "_" for ch in a.lower())] = form(interfaz_form=a)
for nombre, tipo, a in [("dropedit_show", "DROPEDIT", "DATATYPE CHAR\nSHOW 3 LINES\nCHECKMETHOD Chequear"),
                        ("dropedit_show_antes", "DROPEDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear\nSHOW 3 LINES"),
                        ("dropedit_sort", "DROPEDIT", "DATATYPE CHAR\nSORTONCLICK\nCHECKMETHOD Chequear"),
                        ("dropedit_sort_antes", "DROPEDIT", "DATATYPE CHAR\nCHECKMETHOD Chequear\nSORTONCLICK"),
                        ("edit_tags", "EDIT", 'TAGS "a"\nDATATYPE CHAR\nCHECKMETHOD Chequear'),
                        ("edit_mayusculas", "EDIT", "DATATYPE CHAR\nCHECKMETHOD CHEQUEAR"),
                        ("edit_password", "EDIT", "PASSWORD\nDATATYPE CHAR\nCHECKMETHOD Chequear"),
                        ("edit_likevar_tras", "EDIT", "DATATYPE CHAR\nLIKEVAR\nCHECKMETHOD Chequear")]:
    P["vw2_cm_" + nombre] = form(controles=control(tipo, a), eventos=CHEQUEAR)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    salida, huecos = Path(argv[0]), Path(argv[1]).read_text().split()
    huecos = huecos[int(argv[2]) if len(argv) > 2 else 0:]
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

"""Descompilador: el .omd de cada programa de la batería vuelve a dar su fuente.

Los .omd los genera el compilador de Base 100 en el laboratorio (lab/bateria) y no están
en el repo: se buscan en $HUBBLE_KITS/compilados/bateria-86x64; si no están, se salta.
"""
import os
import re
import struct
from pathlib import Path

import pytest

from hubble import descompilador
from hubble.interfaz import Interfaz

KITS = Path(os.environ.get("HUBBLE_KITS", Path(__file__).resolve().parents[1] / "kits"))
BATERIA = KITS / "compilados" / "bateria-86x64"
pytestmark = pytest.mark.skipif(not (BATERIA / "manifiesto.tsv").exists(), reason=f"sin batería en {BATERIA}")


def omd(programa: str) -> bytes:
    huecos = dict(reversed(l.split("\t")) for l in (BATERIA / "manifiesto.tsv").read_text().splitlines())
    hueco = huecos[programa].lower()
    return next(p for p in BATERIA.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == hueco).read_bytes()


def smd(constantes: str, codigo: str) -> str:
    return f"CONSTANTS  begin\n{constantes}end\nCODE BEGIN\n//{{{{CODEBEGIN\n{codigo}//{{{{CODEEND\nEND\n"


MAIN_A = "main\nobjects begin\n    a as Integer\nend\nbegin\n{}end\n"

ESPERADO = {
    "b_base": smd("", MAIN_A.format("    a = 1;\n")),
    "b_vacio": smd("", "main\nbegin\nend\n"),
    "lit_int_m1": smd("", MAIN_A.format("    a = -1;\n")),
    "lit_null": smd("", MAIN_A.format("    a = null;\n")),
    "tipo_bool_true": smd("", "main\nobjects begin\n    a as Boolean\nend\nbegin\n    a = true;\nend\n"),
    "tipo_char_lit2": smd("", 'main\nobjects begin\n    a as Char\nend\nbegin\n    a = "hola";\nend\n'),
    "tipo_decimal": smd("", "main\nobjects begin\n    a as Decimal(12,2)\nend\nbegin\n    a = 1.5;\nend\n"),
    "met_trace": smd("", MAIN_A.format("    a.Trace;\n")),
    "met_trace_par": smd("", MAIN_A.format("    a.Trace();\n")),
    "tipo_default": smd("", "main\nobjects begin\n    a as Integer default 7\nend\nbegin\nend\n"),
    "tipo_date": smd("", "main\nobjects begin\n    a as Date\nend\nbegin\n    a = today;\nend\n"),
    "const_uso": smd("    K = 9\n", MAIN_A.format("    a = K;\n")),
    "op_prec2": smd("", MAIN_A.format("    a = (1 + 2) * 3;\n")),
    "log_not": smd("", MAIN_A.format("    if not (a > 1) then\n        a = 2;\n")),
    "cmp_in": smd("", MAIN_A.format("    if a in (1, 3, 5) then\n        a = 2;\n")),
    "if_elseif": smd("", MAIN_A.format(
        "    if a == 1 then\n        a = 2;\n    else if a == 2 then\n        a = 3;\n    else\n        a = 4;\n")),
    "for_lista": smd("", MAIN_A.format("    for a as 1, 2, 3 do\n        a = a;\n")),
    "switch_default": smd("", MAIN_A.format(
        "    switch a begin\n        case 1:\n            a = 2;\n        default:\n            a = 3;\n    end\n")),
    "switch_in": smd("", MAIN_A.format(
        "    switch a begin\n        case in (1, 2):\n            a = 2;\n        case 3:\n            a = 3;\n    end\n")),
    "switch_in_uno": smd("", MAIN_A.format("    switch a begin\n        case in (1):\n            a = 2;\n    end\n")),
    "switch_in_char": smd("", 'main\nobjects begin\n    c as Char\nend\nbegin\n    switch c begin\n'
                              '        case in ("x", "y", "z"):\n            c = "w";\n    end\nend\n'),
    "switch_in_var": smd("", "main\nobjects begin\n    a as Integer\n    b as Integer\nend\nbegin\n    switch a begin\n"
                             "        case in (b, b + 1):\n            a = 2;\n    end\nend\n"),
    "switch_in_default": smd("", MAIN_A.format(
        "    switch a begin\n        case in (1, 2):\n            a = 2;\n        default:\n            a = 3;\n    end\n")),
    "met_cadena": smd("", "main\nobjects begin\n    a as Char\nend\nbegin\n    a.Length.Trace;\nend\n"),
    "fun_builtin": smd("", 'main\nbegin\n    MessageBox("hola");\nend\n'),
    "exit": smd("", MAIN_A.format("    Exit(1);\n")),
    "fun_privada": smd("", "private f()\nbegin\nend\n\nmain\nbegin\n    f();\nend\n"),
    "fun_return_param": smd("", (
        "public f(x as Integer) return Integer\nbegin\n    return x + 1;\nend\n\n"
        + MAIN_A.format("    a = f(a);\n"))),
    "fun_local": smd("", "public f()\nobjects begin\n    x as Integer\nend\nbegin\n    x = 1;\nend\n\nmain\nbegin\n    f();\nend\n"),
}


@pytest.mark.parametrize("programa", sorted(ESPERADO))
def test_descompila_la_bateria(programa):
    assert descompilador.descompilar(omd(programa)) == ESPERADO[programa]


def test_32_bits_da_lo_mismo_que_64():
    """Los módulos que los kits traen compilados en las dos arquitecturas dan el mismo fuente, si su .smd es el mismo
    (sin contar los espacios): ActiveX demo de 8.6 tiene dos botones en 32 bits y uno en 64."""
    import zipfile

    def omds(z):
        with zipfile.ZipFile(z) as zf:
            return {"/".join(n.lower().split("/")[1:]): zf.read(n) for n in zf.namelist() if n.lower().endswith(".omd")}

    def fuentes(z):  # x.omd → su .smd sin espacios
        with zipfile.ZipFile(z) as zf:
            return {"/".join(n.lower().split("/")[1:])[:-4] + ".omd": re.sub(rb"\s+", b"", zf.read(n))
                    for n in zf.namelist() if n.lower().endswith(".smd")}

    zips = [(KITS / f"cosmos{v}x64eval.zip", KITS / f"cosmos{v}x86eval.zip") for v in ("82", "84", "86")]
    if not all(a.exists() and b.exists() for a, b in zips):
        pytest.skip("sin los kits")
    # Con el compilador de 32 bits del laboratorio (2026-10-29) se descifró lo que faltaba: el valor implícito
    # (VALORES_IMPLICITOS_32), el smallint escrito (variante normal), los tramos de punteros dudosos y los mapas de
    # FTA, PAG, FJO, FRC, PCT y FOB. Ya no queda ninguno que solo salga en 64 bits.
    comparados, otro_fuente = 0, set()
    for za, zb in zips:
        a, b = omds(za), omds(zb)
        fa, fb = fuentes(za), fuentes(zb)
        for n in sorted(set(a) & set(b)):
            try:
                fuente = descompilador.descompilar(a[n])
            except descompilador.NoSoportado:
                continue
            # samples demorestcosmos customers: en los tres kits, el .omd de 64 bits se compiló de otra versión del
            # fuente (lleva " supplier = " en STR donde el .smd y el .omd de 32 bits dicen " customer = ")
            if fa.get(n) != fb.get(n) or n == "samples/demorestcosmos/customers.omd":
                otro_fuente.add(f"{za.name[6:8]} {n}")
                continue
            assert descompilador.descompilar(b[n]) == fuente, n
            comparados += 1
    assert comparados == 231  # antes 29, y 15 ambiguos; después el nombre por entrada, TAB con LABEL…; las clases (144 → 195),
    # OutlookActiveX y mail (195 → 231)
    assert "86 projects/activex/demo.omd" in otro_fuente



def test_orden_descompila(tmp_path, capsys):
    from hubble import cli

    f = tmp_path / "x.omd"
    f.write_bytes(omd("b_base"))
    cli.main(["descompila", str(f)])
    assert capsys.readouterr().out == ESPERADO["b_base"]


def test_orden_descompila_a_smd(tmp_path):
    from hubble import cli

    f = tmp_path / "x.omd"
    f.write_bytes(omd("tipo_char_lit2"))
    cli.main(["descompila", str(f), "-o", str(tmp_path / "s")])
    assert (tmp_path / "s" / "x.SMD").read_bytes() == ESPERADO["tipo_char_lit2"].replace("\n", "\r\n").encode("cp1252")


def test_orden_descompila_no_soportado(tmp_path, capsys):
    from hubble import cli

    f = tmp_path / "x.omd"
    f.write_bytes(b"COMD" + bytes(200))
    with pytest.raises(SystemExit) as e:
        cli.main(["descompila", str(f)])
    assert e.value.code == 1
    assert "x.omd" in capsys.readouterr().err


SAMPLES = KITS / "compilados" / "samples-86x64"


def _sample(nombre: str) -> str:
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    f = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == nombre)
    return descompilador.descompilar(f.read_bytes())


@pytest.mark.parametrize(("modulo", "linea"), [
    ("par", "public f2(VAR i as Smallint)"),                      # parámetro por referencia
    ("getdrivetype", "{*\n#define DRIVE_UNKNOWN     0\n"),          # comentario de documentación
    ("cone10", "OBJECTS BEGIN\n    nombre as Char(40)\n    codigo as Smallint\nEND\n"),  # globales
    ("cone", '    st.SqlExec("delete from customers where customers.customer = ?", i);'),  # variables
    ("selectwindow", '        Sql.SelectWindow(null, "select customer, surname from customers where customers.customer > 3", str);'),
    ("selectwindow", "    Sql.AttachConnection;\n"),                   # sin paréntesis y sin el por defecto
    ("sw", '        default:\n            "i=2 is not digit".Trace;\n    end\nend\n//{{CODEEND'),  # default del switch de condiciones
    ("ejgetsysenvvar", "Module."),                                  # llamada con la clase delante
    ("call", "    c.Trace();\n"),
    ("call", "    c.Trace;\n"),
])
def test_construcciones_de_samples(modulo, linea):
    assert linea in _sample(modulo)


FORMULARIOS = KITS / "compilados" / "formularios-86x64"
# Los que vuelven a dar exactamente su fuente (los demás de la batería dan uno equivalente,
# con los mismos bytes: COLOR blue → RGB, DATATYPE CHAR implícito, tamaño de AUTOSIZE…).
EXACTOS = (
    "f_base f_label f_sysmenu f_minimize f_maximize f_resizing f_label_sysmenu f_font f_foreground f_noborder "
    "f_pos_ancho f_pos_xy c_text c_box c_button c_edit c_check c_radio c_spin c_percent c_slider c_panel c_bitmap "
    "c_edit_sin_nombre c_edit_otro_nombre c_dos_edits c_edit_pos_x c_edit_pos_y c_edit_pos_w c_edit_pos_h "
    "c_edit_pos_grande c_box_con_edit a_noborder a_border_double_down a_border_etched a_border_down a_nolabel "
    "a_label__x a_label__otro a_foreground_rgb_1_2_3 a_foreground_rgb_0_0_0 a_background_rgb_4_5_6 a_attach_all "
    "a_attach_top_right a_attach_left a_alignment_right a_alignment_center a_font__arial__10 a_font__arial__12 "
    "a_font__arial__10_charset_ansi a_bold a_multiline a_password a_disabled a_upshift a_downshift a_notabstop "
    "a_comment__c a_button a_wrap a_focus dt_integer dt_smallint dt_date dt_char30 dt_decimal dt_date_picker "
    "v_variable b_command b_command_ok b_defpush b_label t_tags t_tags_noborder e_open e_open_codigo e_close "
    "e_command_ok e_click e_exit e_enter e_open_close m_metodo m_metodo_uso o_objeto_form o_objeto_form_uso"
).split()


@pytest.fixture(scope="module")
def fuentes_formularios():
    import importlib.util

    spec = importlib.util.spec_from_file_location("formularios", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "formularios.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.P


def _formulario(nombre: str) -> bytes:
    if not (FORMULARIOS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {FORMULARIOS}")
    huecos = dict(reversed(l.split("\t")) for l in (FORMULARIOS / "manifiesto.tsv").read_text().splitlines())
    return next(p for p in FORMULARIOS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[nombre].lower()).read_bytes()


@pytest.mark.parametrize("programa", EXACTOS)
def test_formularios_vuelven_a_su_fuente(programa, fuentes_formularios):
    assert descompilador.descompilar(_formulario(programa)).lower() == fuentes_formularios[programa].lower()


def test_grid_de_la_bateria():
    # c_grid (un GRID sin nada) no lleva PARENTGRID: sigue sin poder escribirse.
    with pytest.raises(descompilador.NoSoportado, match="GRID"):
        descompilador.descompilar(_formulario("c_grid"))


LISTAS = KITS / "compilados" / "listas-86x64"
# Los demás de la batería de listas dan un fuente equivalente (COLUMNS 1 y SELECTTYPE SIMPLE
# son los de serie de los desplegables; AUTOSIZE cambia el tamaño guardado).
LISTAS_EXACTAS = (
    "l_base l_listtype_listcols_1 l_listtype_listcols_2 l_listtype_listcols_3 l_cursortype_sql l_cursortype_treeview "
    "l_cursortype_file l_selecttype_simple l_selecttype_multiple l_scroll_vertical l_scroll_vertical_horizontal "
    "l_sortonclick l_border_double_down l_label__lista l_attach_all l_listcols2_sql_simple d_droplist "
    "d_droplist_show_8_lines d_droplist_show_3_lines d_droplist_columns_2 d_droplist_tags__a___b d_dropedit "
    "d_dropedit_show_8_lines d_dropedit_show_3_lines d_dropedit_columns_2 d_dropedit_tags__a___b "
    # segunda tanda: atributos de lista en los desplegables
    "d_droplist2_listtype_listcols_1 d_droplist2_listtype_listcols_2 d_droplist2_cursortype_sql "
    "d_droplist2_cursortype_file d_droplist2_cursortype_treeview d_droplist2_selecttype_multiple "
    "d_droplist2_scroll_vertical d_droplist2_scroll_horizontal d_droplist2_scroll_vertical_horizontal "
    "d_droplist2_sortonclick d_droplist2_columns_2_scroll_vertical d_dropedit2_listtype_listcols_1 "
    "d_dropedit2_listtype_listcols_2 d_dropedit2_cursortype_sql d_dropedit2_cursortype_file "
    "d_dropedit2_cursortype_treeview d_dropedit2_selecttype_multiple d_dropedit2_scroll_vertical "
    "d_dropedit2_scroll_horizontal d_dropedit2_scroll_vertical_horizontal d_dropedit2_sortonclick "
    "d_dropedit2_columns_2_scroll_vertical "
    # tercera tanda: ICON FILE en los desplegables (en un DROPEDIT, delante de DATATYPE)
    "d3_droplist_icon_file___mbstdbmp d3_droplist_icon_file___mbstdbmp___show_8_lines "
    "d3_droplist_icon_file___mbstdbmp___listtype_listcols_2_cursortype_sql d3_droplist_icon_file___mbstdbmp___sortonclick "
    "d3_dropedit_icon_file___mbstdbmp___datatype_char_listtype_listcols_2_cur d3_dropedit_icon_file___mbstdbmp___datatype_char_sortonclick"
).split()


@pytest.fixture(scope="module")
def fuentes_listas():
    import importlib.util

    spec = importlib.util.spec_from_file_location("listas", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "listas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.P


@pytest.mark.parametrize("programa", LISTAS_EXACTAS)
def test_listas_vuelven_a_su_fuente(programa, fuentes_listas):
    if not (LISTAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {LISTAS}")
    huecos = dict(reversed(l.split("\t")) for l in (LISTAS / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in LISTAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()
    assert descompilador.descompilar(datos).lower() == fuentes_listas[programa].lower()


@pytest.mark.parametrize(("programa", "sobra"), [
    # equivalentes: SELECTTYPE SIMPLE y COLUMNS 1 son los de serie, y COLUMNS n tras LISTTYPE LISTCOLS n no deja huella
    ("d_droplist2_show_8_lines_listtype_listcols_2_cursortype_sql_selecttype_simple_scroll_vertical", ["SELECTTYPE SIMPLE"]),
    ("d_dropedit2_show_8_lines_listtype_listcols_2_cursortype_sql_selecttype_simple_scroll_vertical", ["SELECTTYPE SIMPLE"]),
    ("d_droplist2_tags__a___b__show_10_lines_columns_1_selecttype_simple_scroll_vertical", ["COLUMNS 1", "SELECTTYPE SIMPLE"]),
    ("d_dropedit2_tags__a___b__show_10_lines_columns_1_selecttype_simple_scroll_vertical", ["COLUMNS 1", "SELECTTYPE SIMPLE"]),
    ("d_droplist2_listtype_listcols_2_columns_2", ["COLUMNS 2"]),
    ("d_dropedit2_listtype_listcols_2_columns_2", ["COLUMNS 2"]),
])
def test_desplegables_equivalentes(programa, sobra, fuentes_listas):
    if not (LISTAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {LISTAS}")
    huecos = dict(reversed(l.split("\t")) for l in (LISTAS / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in LISTAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()
    esperado = fuentes_listas[programa]
    for linea in sobra:
        esperado = esperado.replace(f"\t\t\t\t{linea}\n", "")
    assert descompilador.descompilar(datos) == esperado


def _lista_omd(programa):
    if not (LISTAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {LISTAS}")
    huecos = dict(reversed(l.split("\t")) for l in (LISTAS / "manifiesto.tsv").read_text().splitlines())
    return next(p for p in LISTAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()


@pytest.mark.parametrize(("programa", "desp", "valor", "motivo"), [
    ("d_dropedit", 0xA8, 0x00, "atributos de lista sin descifrar"),       # sin SIMPLE (el de serie)
    ("d_droplist", 0xA9, 0x01, "icono 0xffff 0xffff de la lista"),        # ICON FILE sin icono en su binario
    ("d_dropedit_tags__a___b", 0xB2, 0x01, "atributos de lista sin descifrar"),  # CURSORTYPE FILE con TAGS: ¿fichero o lista?
])
def test_desplegables_imposibles(programa, desp, valor, motivo):
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia(_lista_omd(programa), "FCT", 1, desp, valor))


@pytest.mark.parametrize(("modulo", "trozo"), [
    ("STOCKMDI/customers.OMD", "\t\t\t\t\t\tSHOW 8 LINES\n\t\t\t\t\t\tLISTTYPE LISTCOLS 2\n\t\t\t\t\t\tCURSORTYPE SQL\n"
                               "\t\t\t\t\t\tSCROLL VERTICAL\n"),
    ("STOCKMDI/items.OMD", "\tLISTTYPE LISTCOLS 2\n"),
    ("STOCKMDI/suppliers.OMD", "\tCURSORTYPE SQL\n"),
])
def test_desplegables_del_kit(modulo, trozo):
    test_fct_bits_de_los_proyectos(modulo, trozo)


@pytest.mark.parametrize(("modulo", "linea"), [
    ("open", '    i = mlistbox.AddString("a1");\n'),     # por defecto creado antes de la llamada, con basura
    ("date", "    s = date1.Using(2);\n"),                # escrito, con el 0x11 tras el valor: se queda
    ("listbox", '\t\t\t\tICON FILE "_MBSTDBMP_"\n'),     # icono de lista: índice en ICO
    # el índice va en el binario de SVL de la lista, no en +0x70 (aquí ICO tiene 3 y es el 2º)
    ("ttxmlapplyxsltandsave", '\t\t\t\t\tICON FILE "_MBSTDBMP_"\n'),
    ("alternatebackcolorignoreempty", '\t\t\t\tICON FILE "_MBSTDBMP_"\n'),  # su SVL, en el 2º bloque
    ("customcolorsbycontrol", "\t\t\t\tBACKGROUND COLOR transparent\n"),        # 0xC0000000
])
def test_argumentos_y_listas_de_samples(modulo, linea):
    assert linea in _sample(modulo)


@pytest.mark.parametrize(("modulo", "linea"), [
    ("headerparameter", "LIBRARIES BEGIN\n    LIBCOSHTTPDLL\nEND\nCONSTANTS"),          # una librería
    ("ttxmlupdatenode", "LIBRARIES BEGIN\n    LIBLEERXML\nEND\n"),     # la que incluye otra: solo la escrita
    ("libcosqrdll", 'public dll "cosqrdll.dll" CosQRNewCode() return Integer\n'),
    ("libcosqrdll", 'public dll "cosqrdll.dll" CosQRFreeCode(qrcodeId as Integer) return Integer\n'),
    ("libchart", 'public dll "ttchartdll.dll" NewXYChart(hWindow as Integer)\n'),      # sin return
    ("libcossmtpdll", "MESSAGES cossmtpdll\nCONSTANTS"),                   # fichero de mensajes (cabecera +0x30)
    ("dis", "    Mdrop.Disabled = true;\n"),                                 # propiedad (nodo 0x11), escrita
    ("putenv", "    server = mserv.Text;\n"),                                  # y leída
])
def test_librerias_y_dll_de_samples(modulo, linea):
    assert linea in _sample(modulo)


def _modulo(nombre: str):
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    f = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == nombre)
    return descompilador._Modulo(f.read_bytes())


def test_icono_de_un_check():
    # ismaximized: CHECK con ICON 2 (+0x70 = 0x10000, sin FILE). Antes de PR #17 se perdía en silencio.
    assert "\t\t\t\t\tLABEL \"Is Minimized\"\n\t\t\t\t\tNOBORDER\n\t\t\t\t\tICON 2\n" in _sample("ismaximized")  # detrás del borde


CONTROLES = KITS / "compilados" / "controles-86x64"


@pytest.fixture(scope="module")
def fuentes_controles():
    import importlib.util

    spec = importlib.util.spec_from_file_location("controles", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "controles.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.P


def test_controles_vuelven_a_su_fuente(fuentes_controles):
    """Cada programa compilado de la batería de controles da exactamente su fuente. BUTTONGROUP y BOXGROUP (bg_, bx_),
    equivalentes: `CLICKTYPE CHECK` es el de serie (no deja huella) y los colores salen en RGB."""
    if not (CONTROLES / "manifiesto.tsv").exists():
        pytest.skip(f"sin {CONTROLES}")
    huecos = dict(reversed(l.split("\t")) for l in (CONTROLES / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in CONTROLES.iterdir() if p.suffix.lower() == ".omd"}
    exactos = ventana = 0
    for programa, fuente in fuentes_controles.items():
        if huecos[programa].lower() not in omds:
            continue  # no compila (variante de orden que el compilador rechaza)
        datos = omds[huecos[programa].lower()].read_bytes()
        if programa.split("_")[0] == "tab":  # equivalentes (los de la batería de TAB, exactos)
            assert "AS TAB" in descompilador.descompilar(datos)
            continue
        if programa.split("_")[0] in ("bg", "bx"):
            esperado = fuente.replace("\t\t\t\tCLICKTYPE CHECK\n", "").replace("COLOR red", "RGB 255 0 0")
            assert descompilador.descompilar(datos).lower() == esperado.lower(), programa
            continue
        if programa in ("ax_prop_igual_nombre", "ax_prop_barra_valor"):  # sin escape: «a=b=c|» y «Day=a|b|»
            with pytest.raises(descompilador.NoSoportado, match="no se puede partir"):
                descompilador.descompilar(datos)
            continue
        if programa == "onc_literal":  # `On Control "c"`: los mismos bytes que sin comillas
            assert descompilador.descompilar(datos).lower() == fuente.replace('"c"', "c").lower()
            continue
        if programa.startswith(("vw_", "vw2_")):  # FRAMEAUTOSIZE de los grupos: con AUTOSIZE, el tamaño es otro
            texto = descompilador.descompilar(datos)
            esperado = fuente.replace("\t\t\t\tCLICKTYPE CHECK\n", "")
            if "AUTOSIZE\n\t" in fuente.replace("FRAMEAUTOSIZE", ""):
                texto, esperado = (re.sub(r"\t\t\t\tPOSITION 10 10 \d+ \d+\n", "", x, count=1) for x in (texto, esperado))
            assert texto.lower() == esperado.lower(), programa
            ventana += fuente == esperado
            continue
        assert descompilador.descompilar(datos).lower() == fuente.lower(), programa
        exactos += 1
    assert ventana == 12  # FRAMEAUTOSIZE (de 18 que compilan, exactos sin CLICKTYPE CHECK ni AUTOSIZE)
    assert exactos == 160  # + 8 de BORDER BLACK, 8 de EXTRA n, 12 de SPLIT, 13 de DISABLED, NOBORDER y BAR, 17 de NOLABEL, RICHTEXTEDIT y DEFPUSH, 7 de FORMAT
    # y 23 de ACTIVEX y `On Control` (ax_, onc_)


def _omd_control(programa):
    if not (CONTROLES / "manifiesto.tsv").exists():
        pytest.skip(f"sin {CONTROLES}")
    huecos = dict(reversed(l.split("\t")) for l in (CONTROLES / "manifiesto.tsv").read_text().splitlines())
    return next(p for p in CONTROLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()


@pytest.mark.parametrize(("programa", "trozo"), [
    # BORDER BLACK: bit 0x10 de +0x00, delante de los demás (STOCKMDI menu y TryThisOneFirst: BLACK DOWN; CalcRPN: BITMAP)
    ("xk_border_black_down", "\t\t\t\tBORDER BLACK DOWN\n"),
    ("xk_border_black_extra_1", "\t\t\t\tBORDER BLACK EXTRA 1\n"),
    ("bmk_black", "\t\t\t\tBORDER BLACK\n"),
    ("tk_black", "\t\t\t\tBORDER BLACK\n"),
])
def test_border_black(programa, trozo):
    assert trozo in descompilador.descompilar(_omd_control(programa))


@pytest.mark.parametrize(("programa", "byte", "valor", "motivo"), [
    ("xk_border_black", 0x00, 0x14, "borde 0x14"),        # BLACK DOUBLE no compila
    ("xk_border_black", 0x00, 0x18, "borde 0x18"),        # BLACK ETCHED tampoco
    ("e_base", 0x00, 0x10, "bits 0x10 sin descifrar"),    # en un EDIT no compila
    ("b_base", 0x00, 0x10, "bits 0x10 sin descifrar"),    # en un BUTTON, BLACK va en +0x20
])
def test_border_black_imposible(programa, byte, valor, motivo):
    datos = _omd_control(programa)
    viejo = datos[contenedor_fct(datos, 1) + byte]
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia(datos, "FCT", 1, byte, viejo | valor))


def contenedor_fct(datos, k):
    from hubble import contenedor

    s = contenedor.leer(datos).seccion("FCT")
    return s.datos + k * s.tam_registro


@pytest.mark.parametrize(("modulo", "linea"), [
    ("chartbarrasagrupadas", "\t\t\tvalueT1 as Decimal(16,1) default 0\n"),     # FOB con tipo y default
    ("ejcallwebserviceex", '\t\t\t\t\t\tICON 2 FILE "_MBSTDBMP_" CENTER\n'),     # icono de botón
])
def test_controles_de_samples(modulo, linea):
    assert linea in _sample(modulo)


def test_text_sobre_una_columna():
    # LIKEVAR delante de TAGS en un TEXT (detrás no compila: lo cazó la vuelta de samples)
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    f = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "items")
    assert ('\t\t\t\t\t\tVARIABLE items.fk1_items_company\n\t\t\t\t\t\tLIKEVAR\n\t\t\t\t\t\tTAGS "Company"\n'
            in descompilador.descompilar(f.read_bytes(), "stock"))


def test_text_con_likevar_sobre_una_variable():
    # LIKEVAR sobre una variable (aquí del tipo de una columna): el TEXT copia su tipo; DATATYPE detrás no compila
    from hubble import repositorio

    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    f = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "ejhideexportexcelbutton")
    texto = descompilador.descompilar(f.read_bytes(), "stock", repositorio.Catalogo(KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "samples" / "stock.dbs"))
    assert '\t\t\t\t\tVARIABLE vChSname\n\t\t\t\t\tLIKEVAR\n\t\t\t\t\tTAGS "Control"\n' in texto


def test_guarda_de_campos_sin_leer():
    datos = _sample_datos("drag1")  # su +0xA0 es el FORMAT; +0xA4, un campo que no se lee
    with pytest.raises(descompilador.NoSoportado, match=r"TEXT FCT 3: \+0xa4 = 0x1"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 3, 0xA4, 1))


@pytest.mark.parametrize(("desp", "valor", "mensaje"), [
    (0x22, 7, r"DATATYPE 0x7"),                        # DATATYPE de un TEXT que no se conoce (4 es TIME)
    (0x40, 1, r"DATATYPE DATE con \+0x40 0x1"),        # largo en un TEXT de tipo DATE
    (0x24, 1, r"TEXT FCT 1: \+0x24 = 0x1"),            # un campo que no se lee
    (0x68, 1, r"TEXT FCT 1: \+0x68 = 0x1"),            # un campo que solo leen las listas, el SLIDER y el PERCENT
])
def test_guarda_con_un_byte_cambiado(desp, valor, mensaje):
    from hubble import contenedor

    datos = bytearray(_formulario("c_text"))
    fct = contenedor.leer(bytes(datos)).seccion("FCT")
    if desp == 0x40:
        datos[fct.datos + fct.tam_registro + 0x22] = 5  # DATATYPE DATE
    datos[fct.datos + fct.tam_registro + desp] = valor
    with pytest.raises(descompilador.NoSoportado, match=mensaje):
        descompilador.descompilar(bytes(datos))


def test_guarda_del_formulario():
    from hubble import contenedor

    datos = bytearray(_formulario("f_base"))
    fct = contenedor.leer(bytes(datos)).seccion("FCT")
    datos[fct.datos + 0x60] = 1  # un campo del formulario que no se lee
    with pytest.raises(descompilador.NoSoportado, match=r"formulario FCT 0: \+0x60"):
        descompilador.descompilar(bytes(datos))


DATOS = KITS / "compilados" / "datos-86x64"
EXACTOS_DATOS = 47  # + 6 de DATATYPE TIME y DATETIME y 4 de PANELTYPE OPERATION


@pytest.mark.parametrize(("valor", "motivo"), [(0x07, "DATATYPE 0x7"), (0x08, "DATATYPE 0x8")])
def test_datatype_desconocido(valor, motivo):
    """DATATYPE: 4 TIME, 6 DATETIME (AGENDA mes, OutlookActiveX); 7 y siguientes, sin descifrar (MONEY, BOOLEAN y FLOAT
    no compilan en un control: «Expecting char, date, datetime, decimal, integer, smallint, time»)."""
    huecos = dict(reversed(l.split("\t")) for l in (DATOS / "manifiesto.tsv").read_text().splitlines()) if (DATOS / "manifiesto.tsv").exists() else {}
    if "dt2_time" not in huecos:
        pytest.skip(f"sin {DATOS}")
    datos = next(p for p in DATOS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["dt2_time"].lower()).read_bytes()
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia(datos, "FCT", 1, 0x22, valor))


def test_datos_vuelven_a_su_fuente():
    """Batería de tipos de dato (DECIMAL(p,s), MASK), bordes de BUTTON, PANELTYPE, eventos
    sin control y default de Char: los que se descompilan dan exactamente su fuente."""
    import importlib.util

    if not (DATOS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {DATOS}")
    spec = importlib.util.spec_from_file_location("datos", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "datos.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (DATOS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in DATOS.iterdir() if p.suffix.lower() == ".omd"}
    exactos = 0
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() not in omds:
            continue
        datos = omds[huecos[programa].lower()].read_bytes()
        if programa in ("f_char_default_null",):  # el null de un Char solo deja «NULL» suelto en STR
            with pytest.raises(descompilador.NoSoportado, match="NULL"):
                descompilador.descompilar(datos)
            continue
        if programa == "asig_doble":  # `a b as Integer` sale en dos líneas; a = b = 1, sin paréntesis
            assert "    a = b = 1;\n" in descompilador.descompilar(datos)
            continue
        if programa == "o_integer_default_null":  # da los mismos bytes que sin default
            assert "    a as Integer\n" in descompilador.descompilar(datos)
            continue
        assert descompilador.descompilar(datos).lower() == fuente.lower(), programa
        exactos += 1
    assert exactos == EXACTOS_DATOS


@pytest.mark.parametrize(("modulo", "linea"), [
    ("api_chartexportimagen", "On event Click control btn_exportImagen (e as Event)\n"),  # control en STR; VAR, implícito en un objeto
    ("bit", "On Click (sender as Char)\n"),                     # evento de cualquier control
    ("cl", "\t\t\t\t\tPANELTYPE COMMENT\n"),
    ("chartlineasconmarcadores", '    legendStr as Char default ""\n'),
])
def test_eventos_y_datos_de_samples(modulo, linea):
    assert linea in _sample(modulo)


@pytest.mark.parametrize(("modulo", "linea"), [
    ("xor", "    b = b xor b1;\n"),                        # operador 17
    ("like", "    if s like s1 then\n"),                    # 25
    ("matc", "    if s matches s1 then\n"),                 # 24
    ("ejttxmlgetencodednodetext", " is not null then\n"),   # 29
    ("exp", "    n = n ** n1;\n"),                          # 2
    ("pe", "    n *= 2;\n"),                                # 6
    ("de", "    n /= 2;\n"),                                # 7
    ("mod1", "    i %= 5;\n"),                              # 8
    ("if", "    if today.Char[1, 5] between \"03-21\" and \"06-20\" then\n"),  # 30: índice y subcadena
    ("switch", '        case between "03-21" and "06-20":\n'),  # case de valor con between
    ("chartandlegendxshift", "    micolorfrom = micolorto = Module.Rgb(252, 231, 230);\n"),  # asignación encadenada
    ("chartandlegendxshift", "    min = ctrSlideXShiftChart.Min();\n"),  # paréntesis con la llamada creada tarde
    ("tree5", " + mlist.GetListIcon(i)).Trace;\n"),           # booleano por defecto (basura tras el valor)
    ("clientecosmoswebserver", "oJSonRespuesta.GetString(true).UTF8ToAnsi(1252);\n"),  # booleano escrito (ceros)
    ("etch", '\t\t\t\t\tBOLD\n\t\t\t\t\tFONT "MS Serif" 18 ITALIC\n'),   # estilo de la fuente; BOLD del control, delante
    ("getclipboardtextutf8", '\t\t\t\t\tFONT "Times New Roman" 12 CHARSET Greek\n'),
    ("getclipboardtextutf8", '\t\t\t\t\tFONT "Arial" 12 CHARSET Turkish\n'),
    ("getdragcolumngetdropcolumn", "\t\t\tSYSMENU\n\t\t\tALLOWDROP\n"),     # +0x44 del formulario
    ("getdragcolumngetdropcolumn", "On Dragover (ctr as Char, fromCtr as SimpleFormControl, fromItem as Integer, VAR result as Integer)\n"),
    ("chartradar", "valores as ArgList of Decimal)\n"),
])
def test_operadores_fuentes_y_mas_de_samples(modulo, linea):
    assert linea in _sample(modulo)


@pytest.mark.parametrize(("modulo", "linea"), [
    ("pare", "CLASSES BEGIN\n\tA is Smallint\n\tB is A\nEND\n"),          # clases derivadas simples
    ("mm", "\tmiinteger is Integer\n"),
    ("clasejson", "\tcJson is JSON\n"),
    ("incl5", "\tfrmAbs is abstract Form\n"),                           # 0x80 del byte 0
    ("array", "\taArray is Array [6] of Integer\n"),                    # +0x34 y +0x40
    ("fnsqltrunc_fecha", "\tcFormats is Struct begin\n\t\tformatCode as Char\n\t\tformatDescription as Char(256)\n\tend\n"),
    ("mm", "    self = 8;\n"),                                          # literal 0x60 con variante 0x31
    ("pare", "    parent.value;\n"),                                     # método con variante 0x40
    ("self", "public abs() return sm\n"),                               # devuelve una clase del módulo
])
def test_clases_de_samples(modulo, linea):
    assert linea in _sample(modulo)


def _cambia(datos: bytes, etiqueta: str, k: int, desp: int, valor: int) -> bytes:
    from hubble import contenedor

    s = contenedor.leer(datos).seccion(etiqueta)
    nuevo = bytearray(datos)
    nuevo[s.datos + k * s.tam_registro + desp] = valor
    return bytes(nuevo)


def test_literal_de_variante_desconocida():
    m = descompilador._Modulo(omd("b_base"))
    k = next(k for k in range(m.s["REF"].n) if m.rec("REF", k)[0] == 0x60)  # el 1 de `a = 1`
    with pytest.raises(descompilador.NoSoportado, match="variante 0x77"):
        descompilador.descompilar(_cambia(omd("b_base"), "REF", k, 1, 0x77))


def test_case_in_sin_lista():
    """`case in (…)`: el argumento del operador 27 es la lista; si no lo es, no se sabe escribir."""
    m = descompilador._Modulo(omd("switch_in"))
    k = next(k for k in range(m.s["REF"].n) if m.rec("REF", k)[0] == descompilador.LISTA)
    datos = _cambia(omd("switch_in"), "REF", k, 0, 0x60)  # un literal suelto en vez de la lista…
    for desp in range(0x08, 0x10):  # …sin el enlace +0x08, que haría de los elementos varios argumentos
        datos = _cambia(datos, "REF", k, desp, 0)
    with pytest.raises(descompilador.NoSoportado, match="case de valor con el operador 27"):
        descompilador.descompilar(datos)


def test_clase_no_escrita():
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "pare").read_bytes()
    # byte 3 sin la visibilidad (0x83): una clase que pone el compilador
    with pytest.raises(descompilador.NoSoportado, match="clase CLA 1 sin visibilidad"):
        descompilador.descompilar(_cambia(datos, "CLA", 1, 3, 0x83))


@pytest.mark.parametrize(("modulo", "mensaje"), [
    ("cone15", "hace falta el repositorio"),       # `Struct as customers`: sin catálogo no se sabe la columna
    ("ejinitializewithdefault", "fecha es del tipo de una columna"),  # (con catálogo se para en un Time)
])
def test_tipos_de_columna_sin_repositorio(modulo, mensaje):
    with pytest.raises(descompilador.NoSoportado, match=mensaje):
        _sample(modulo)


@pytest.mark.parametrize(("modulo", "texto"), [
    ("addcustomcolors_setcustomcolors", "INCLUDES BEGIN\n    INC_VISULAMODE\nEND\nCONSTANTS"),
    ("setcomputedcolumnredonde", "INCLUDES BEGIN\n    INCL5\nEND\n"),
])
def test_includes(modulo, texto):
    assert texto in _sample(modulo)


def test_include_que_lleva_una_libreria():
    # ejcajasredondasenpag incluye LIBCON, que va en EMO detrás de LIBPRNPAG (su LIBRARIES)
    m = _modulo("ejcajasredondasenpag")
    assert (m.librerias(), m.librerias("INC")) == (["LIBPRNPAG"], ["LIBCON"])


def _stock():
    from hubble import repositorio

    dbs = KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "samples" / "stock.dbs"
    if not dbs.is_dir():
        pytest.skip(f"sin {dbs}")
    return repositorio.Catalogo(dbs)


def test_grid_de_samples():
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    f = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "setgridcurrentrowbackcolor")
    texto = descompilador.descompilar(f.read_bytes(), "stock", _stock())
    assert ("\t\t\t\t\tCONTROL id_grid AS GRID\n\t\t\t\t\t\tPOSITION 20 8 291 197\n\t\t\t\t\t\tBORDER DOUBLE DOWN\n"
            "\t\t\t\t\t\tSCROLL VERTICAL\n\t\t\t\t\t\tTABLE states\n\t\t\t\t\t\tPARENTGRID\n") in texto
    assert "\t\tTable states is states\n\t\tbegin\n\t\t\tstate as column\n\t\t\tsname as column\n\t\tend\n" in texto
    f = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "ejsetgridcolumninvisibledata")
    assert "\tPARENTGRID\n\t\t\t\t\tAUTOSORT\n" in descompilador.descompilar(f.read_bytes(), "stock")  # el bit de BUTTON


ALMAFAC = KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "projects" / "ALMAFAC"


def test_fuentes_de_742_como_las_de_86():
    # El mismo fuente compilado con 7.4.2 (el kit) y con 8.6 (el laboratorio): 7.4.2 añade 0x10/0x20 al estilo.
    otro = KITS / "compilados" / "almafac-86x64" / "comun.OMD"
    if not otro.is_file():
        pytest.skip(f"sin {otro}")
    fuentes = []
    for f in (ALMAFAC / "comun.OMD", otro):
        m = descompilador._Modulo(f.read_bytes())
        i = Interfaz(m, descompilador.NoSoportado)
        fuentes.append([i.fuente(k) for k in range(m.s["FCT"].n)])
    assert fuentes[0] == fuentes[1]
    assert 'FONT "Verdana" 10' in fuentes[0] and 'FONT "Verdana" 20 CHARSET Ansi' in fuentes[0]
    r = bytearray((ALMAFAC / "comun.OMD").read_bytes())  # con los dos bits a la vez: no
    s = descompilador._Modulo(bytes(r)).s["FON"]
    r[s.datos + 2 * s.tam_registro + 4] |= 0x30  # FON 2, Verdana 10, el de los controles
    m = descompilador._Modulo(bytes(r))
    i = Interfaz(m, descompilador.NoSoportado)
    with pytest.raises(descompilador.NoSoportado, match="estilo 0x3"):
        [i.fuente(k) for k in range(m.s["FCT"].n)]


def test_comandos_predefinidos():
    """Batería de comandos: cada COMMAND vuelve con su nombre (los predefinidos, por su número). Y `On Command (cmd as
    Char)`, el de cualquier comando (PRO de tipo 7 con +0x28 = 0); `On Command` a secas no compila."""
    import importlib.util

    d = KITS / "compilados" / "comandos-86x64"
    if not (d / "manifiesto.tsv").exists():
        pytest.skip(f"sin {d}")
    spec = importlib.util.spec_from_file_location("comandos", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "comandos.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (d / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in d.iterdir() if p.suffix.lower() == ".omd"}
    assert [p for p in modulo.P if huecos[p].lower() not in omds] == ["o_sin_parametro"]
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() in omds:
            assert descompilador.descompilar(omds[huecos[programa].lower()].read_bytes()).lower() == fuente.lower(), programa
    datos = omds[huecos["o_cualquiera"].lower()].read_bytes()
    assert "On Command (cmd as Char)\n" in descompilador.descompilar(datos)
    m = descompilador._Modulo(datos)
    k = next(k for k in range(m.s["PRO"].n) if m.rec("PRO", k)[0] == 7)
    with pytest.raises(descompilador.NoSoportado, match="sin comando ni parámetro"):  # sin el parámetro
        descompilador.descompilar(_cambia(datos, "PRO", k, 0x11, 0))


TABLAS = KITS / "compilados" / "tablas-86x64"


def _tablas():
    import importlib.util

    if not (TABLAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {TABLAS}")
    spec = importlib.util.spec_from_file_location("tablas", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "tablas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (TABLAS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in TABLAS.iterdir() if p.suffix.lower() == ".omd"}
    return {n: (f, omds[huecos[n].lower()].read_bytes()) for n, f in modulo.P.items() if huecos[n].lower() in omds}


def test_tablas_vuelven_a_su_fuente():
    """Tablas de formulario (repositorio stock). Equivalentes, no exactos: `required` en la clave
    (no deja rastro) y `Char (10)` con espacio."""
    exactos = 0
    for programa, (fuente, datos) in _tablas().items():
        if programa.startswith("up_"):  # el UPSHIFT que LIKEVAR copia de la columna: test_likevar_copia_el_upshift_de_la_columna
            continue
        if programa == "rj_norownum_sin_parentgrid":  # un GRID sin PARENTGRID no se ha descifrado
            with pytest.raises(descompilador.NoSoportado, match="sin PARENTGRID"):
                descompilador.descompilar(datos, "stock", _stock())
            continue
        texto = descompilador.descompilar(datos, "stock", _stock())  # con él, el required de una NOT NULL no se escribe
        if programa == "rj_tres_scroll_autosize":  # con AUTOSIZE, el alto guardado es otro que el escrito
            fuente = fuente.replace("POSITION 0 0 190 90", "POSITION 0 0 190 84")
        if programa.startswith("rk_"):  # el segundo control de la rejilla: el compilador lo coloca tras el primero (75 + 1)
            fuente = fuente.replace("POSITION 0 0 65 22", "POSITION 76 0 65 22")
        esperado = fuente.replace("state as column required", "state as column").replace("Char (10)", "Char(10)")
        esperado = esperado.replace("Decimal (9,2)", "Decimal(9,2)")
        if programa.startswith(("j_", "jx_")):  # customers.state tiene default «CA» en el repositorio: sale escrito
            esperado = esperado.replace("state as column\n", 'state as column default "CA"\n')
        if programa.startswith("jx_"):  # `x as tabla.columna` sin join: una columna del mismo tipo (el .omd no dice cuál)
            esperado = (esperado.replace("state as states.state", "state as customers.state")
                        .replace("statename as states.sname", "statename as payforms.description")
                        .replace("x as states.sname", "x as payforms.description"))
        assert texto.lower() == esperado.lower(), programa
        exactos += fuente == esperado
    assert exactos == 22  # 9 + 12 de GRID (rj_) + 1 del ICON n de un CHECK de la rejilla tras VARIABLE (rk_)


@pytest.mark.parametrize(("programa", "columna", "upshift"), [
    ("up_var_surname", "customers.surname", False),  # Char(25) sin 0x2 en +0x24 del .crf: el VAR sale sin 0x40000
    ("up_var_company", "customers.company", True),  # Char(25) con 0x2: con 0x40000 (antes salía surname → company)
    ("up_var_state", "customers.state", True),  # Char(2) con 0x2 (states.state también; el módulo no nombra tablas)
    ("up_var_fname", "customers.fname", False),
    ("up_var_company_datatype", "customers.company", False),  # sin LIKEVAR, la columna no deja huella: por el nombre
    ("up_text_company", "customers.company", True),  # TEXT: el bit viene de la columna; escrito no compila
    ("up_text_surname", "customers.surname", False),
    ("up_edit_company", "customers.company", True),  # EDIT: escrito compila y no cuenta (la columna decide)
    ("up_edit_surname", "customers.surname", False),
    ("up_edit_surname_upshift", "customers.surname", False),  # el UPSHIFT escrito sobre surname no deja el bit
])
def test_likevar_copia_el_upshift_de_la_columna(programa, columna, upshift):
    """El UPSHIFT de un control con LIKEVAR (0x40000 de +0x00) lo copia el compilador de la columna (+0x24 del
    registro del .crf con 0x2; batería tablas.py, up_, compilada además con copias de stock.crf con ese u16
    cambiado). STOCKMDI cust_rep: surname y company son Char(25) con la misma máscara y solo company es UPSHIFT."""
    fuente, datos = _tablas()[programa]
    avisos = []
    texto = descompilador.descompilar(datos, "stock", _stock(), avisos)
    assert f"\t\t\tp as {columna}\n" in texto
    if programa == "up_var_company":
        assert avisos == ["p as customers.company: una de 2 columnas del mismo tipo y UPSHIFT (el .omd no guarda cuál era; "
                          "todas compilan igual)"]
    assert ("\t\t\t\tUPSHIFT\n" in texto) == (upshift and programa.startswith("up_edit"))  # en TEXT y VAR no se escribe


def test_upshift_del_crf():
    # +0x24 del registro de columna del .crf: 0x2 en company, payform y state; 0 en surname; en otros tipos no se mira
    catalogo = _stock()
    de = {c.nombre: catalogo.upshift(c) for c in catalogo.columnas if c.tabla == "customers"}
    assert de == {"customer": None, "company": True, "surname": False, "fname": False, "address1": False, "address2": False,
                  "city": False, "zip": None, "phone": False, "payform": True, "total_invoice": None, "state": True}
    assert catalogo.buscar("Char", 25, -1, "surname", upshift=True)[0].nombre == "company"
    assert catalogo.buscar("Char", 25, -1, "company", upshift=False)[0].nombre == "surname"
    assert catalogo.buscar("Char", 25, -1, "company")[0].nombre == "company"


def test_likevar_con_upshift_imposible(tmp_path):
    import shutil

    from hubble import repositorio

    datos = _tablas()["up_var_fname"][1]
    con_bit = _cambia(datos, "PCT", 1, 2, 0x04)  # 0x40000 de +0x00 en el VAR con LIKEVAR
    with pytest.raises(descompilador.NoSoportado, match=r"ninguna columna del repositorio es Char\(15\) con la máscara 0 y UPSHIFT en el .crf"):
        descompilador.descompilar(con_bit, "stock", _stock())
    shutil.copytree(KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "samples" / "stock.dbs", tmp_path / "stock.dbs")
    with pytest.raises(descompilador.NoSoportado, match=r"LIKEVAR con UPSHIFT de una columna Char\(25\) y sin el .crf"):
        descompilador.descompilar(_tablas()["up_var_company"][1], "stock", repositorio.Catalogo(tmp_path / "stock.dbs"))
    avisos = []
    assert "\t\t\tp as customers.company\n" in descompilador.descompilar(  # sin el bit, sin .crf se elige como antes
        _tablas()["up_var_surname"][1], "stock", repositorio.Catalogo(tmp_path / "stock.dbs"), avisos)  # (la primera)
    assert avisos[-1].startswith("p as customers.company: el LIKEVAR no lleva UPSHIFT y sin el .crf no se sabe qué "
                                 "columnas lo son; candidatas: customers.company, customers.surname")  # y se avisa


def test_upshift_heredado_del_crf(tmp_path):
    # proveedores.apellidos hereda de tipos_fijos.apellidos (registro 55) y las dos llevan 0x2: vale. Con el suyo
    # cambiado (registro 41, +0x24 → 0), el suyo y el del padre no coinciden y no se ha medido cuál manda: None
    import shutil
    import struct

    from hubble import repositorio

    origen = PROYECTOS_KIT / "ALMAFAC"
    if not (origen / "ALMAFAC.CRF").is_file():
        pytest.skip(f"sin {origen}")
    shutil.copytree(origen / "almafac.dbs", tmp_path / "almafac.dbs")
    datos = bytearray((origen / "ALMAFAC.CRF").read_bytes())
    o = 0x40
    for tam in repositorio._CRF_TAMANOS[struct.unpack_from("<H", datos, 8)[0]][:3]:
        o = repositorio._tabla_crf(bytes(datos), o, tam)[1]
    (tmp_path / "almafac.crf").write_bytes(datos)
    apellidos = next(c for c in repositorio.Catalogo(tmp_path / "almafac.dbs").columnas if (c.tabla, c.nombre) == ("proveedores", "apellidos"))
    assert repositorio.Catalogo(tmp_path / "almafac.dbs").upshift(apellidos) is True
    assert struct.unpack_from("<H", datos, o + 0x18 + 41 * 94 + 0x24)[0] == 2
    struct.pack_into("<H", datos, o + 0x18 + 41 * 94 + 0x24, 0)
    (tmp_path / "almafac.crf").write_bytes(datos)
    catalogo = repositorio.Catalogo(tmp_path / "almafac.dbs")
    assert catalogo.upshift(apellidos) is None
    # con el bit, una columna con el UPSHIFT sin saber no se elige (sería a ciegas); sin él, vale como antes (y se avisa)
    clase, largo, escala = apellidos.en_omd()
    assert catalogo.buscar(clase, largo, escala, "apellidos", ("proveedores",), upshift=True)[0] != apellidos
    assert catalogo.buscar(clase, largo, escala, "apellidos", ("proveedores",), upshift=False)[0] == apellidos


def test_base_de_datos_del_crf(tmp_path):
    # +0x14 de la cabecera del .crf: el registro de la tabla de nombres con la base de datos (la carpeta .dbs)
    import shutil
    import struct

    from hubble import repositorio

    origen = PROYECTOS_KIT / "INDODIC"
    if not (origen / "INDODIC.CRF").is_file():
        pytest.skip(f"sin {origen}")
    assert repositorio.base_del_crf(origen / "INDODIC.CRF") == "indonesi"
    assert repositorio.base_del_crf(PROYECTOS_KIT / "STOCKMDI" / "stock.crf") == "STOCK"
    assert repositorio.base_del_crf(PROYECTOS_KIT / "AGENDA" / "agenda.crf") == "AGENDA"  # registro 6, no 3
    modulo = origen / "UpkeepDict.OMD"
    assert repositorio.encontrar("indodic", modulo) == origen / "INDONESI.DBS"
    assert repositorio.crf_de(origen / "INDONESI.DBS") == origen / "INDODIC.CRF"
    catalogo = repositorio.Catalogo(origen / "INDONESI.DBS")
    assert catalogo.mascaras is not None and catalogo.upshifts is not None  # con el .crf de otro nombre
    assert "REPOSITORY indodic\n" in descompilador.descompilar(modulo.read_bytes(), "indodic", catalogo)
    # con +0x14 apuntando a otro registro (el 4, «indodic»), ni la carpeta ni el .crf se encuentran
    copia = tmp_path / "INDODIC"
    shutil.copytree(origen, copia)
    datos = bytearray((copia / "INDODIC.CRF").read_bytes())
    struct.pack_into("<I", datos, 0x14, 4)
    (copia / "INDODIC.CRF").write_bytes(datos)
    assert repositorio.encontrar("indodic", copia / "UpkeepDict.OMD") is None
    assert repositorio.crf_de(copia / "INDONESI.DBS") is None
    assert repositorio.Catalogo(copia / "INDONESI.DBS").mascaras is None
    # dos .crf de la misma base y ninguno con su nombre: no se elige
    struct.pack_into("<I", datos, 0x14, 3)
    (copia / "INDODIC.CRF").write_bytes(datos)
    (copia / "OTRO.CRF").write_bytes(datos)
    assert repositorio.crf_de(copia / "INDONESI.DBS") is None
    assert repositorio.encontrar("otro", copia / "UpkeepDict.OMD") == copia / "INDONESI.DBS"


def test_likevar_con_upshift_de_una_variable_a_mano():
    # VAR de página con LIKEVAR de `n as Smallint` y el bit: no es de columna y escrito no compila
    datos = _bateria("paginas", "v_likevar")
    with pytest.raises(descompilador.NoSoportado, match="LIKEVAR con UPSHIFT de una variable que no es de columna"):
        descompilador.descompilar(_cambia(datos, "PCT", 1, 2, 0x04))


def test_required_sin_catalogo():
    # el bit de required (0x400) lo pone también una columna NOT NULL del repositorio; sin catálogo no se sabe si lo
    # era, y se escribe (mismos bytes)
    fuente, datos = _tablas()["tb_base"]
    assert "\t\t\tstate as column required\n" in descompilador.descompilar(datos, "stock")


def test_tablas_sin_repositorio():
    fuente, datos = _tablas()["tb_base"]
    with pytest.raises(descompilador.NoSoportado, match="REPOSITORY"):
        descompilador.descompilar(datos)


def test_orden_descompila_con_repositorio(tmp_path, capsys):
    from hubble import cli

    fuente, datos = _tablas()["tb_alias"]
    f = tmp_path / "t.omd"
    f.write_bytes(datos)
    cli.main(["descompila", "--repositorio", "stock", str(f)])
    salida = capsys.readouterr().out
    assert salida.startswith("REPOSITORY stock\n") and "\t\tTable st is states\n" in salida and "VARIABLE st.state\n" in salida


PAGINAS = KITS / "compilados" / "paginas-86x64"


def test_paginas_vuelven_a_su_fuente():
    """Batería de páginas. Equivalentes (mismos bytes) y no exactos: MARGIN 13 (sale 12: se guarda
    en unidades de 3), los hijos de un GROUP (la posición guardada es otra que la escrita) y
    dos_paginas (CODE CLASS de la segunda), `BACKGROUND COLOR default`, que no deja huella, el BEGIN END vacío
    de un BOX y los hijos de un BANDGROUP (como los de un GROUP)."""
    import importlib.util

    if not (PAGINAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {PAGINAS}")
    spec = importlib.util.spec_from_file_location("paginas", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "paginas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (PAGINAS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in PAGINAS.iterdir() if p.suffix.lower() == ".omd"}
    exactos = 0
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() not in omds:
            continue  # NOBORDER y DATATYPE no compilan en una TEXT de página
        texto = descompilador.descompilar(omds[huecos[programa].lower()].read_bytes())
        if programa == "p_margin_13":
            assert "\t\t\tMARGIN 12 24 15 48\n" in texto
        elif programa.startswith(("g_", "bg_", "pga_", "pgb_")):  # la línea de atributos del GROUP o del BANDGROUP, tal cual
            lineas = [l.strip() for l in fuente.splitlines()]
            i = next(j for j, l in enumerate(lineas) if l in ("CONTROL AS GROUP", "CONTROL AS BANDGROUP")) + 2
            esperado = "\n".join(lineas[i:lineas.index("BEGIN", i)])
            assert esperado in "\n".join(l.strip() for l in texto.splitlines()), programa
        elif programa == "dos_paginas":
            assert "\tpg2 is Page begin\n" in texto
        elif programa.startswith("b_icon") or programa == "pbm_begin_end":  # BEGIN END vacío: los mismos bytes
            assert texto.lower() == fuente.replace("\t\t\tBEGIN\n\t\t\tEND\n", "").lower(), programa
        elif programa == "pvt_font__fangsong__12_charset_gb_tags__x_":  # `CHARSET Gb` no deja huella (es Gb2312)
            assert texto.lower() == fuente.replace(" CHARSET Gb\n", "\n").lower()
        elif programa == "t_default":
            assert texto.lower() == fuente.replace("\t\t\t\tBACKGROUND COLOR default\n", "").lower()
        elif programa.startswith("pxg_") and ("COLOR red" in fuente or 'LABEL ""' in fuente):  # BOX de un BOXGROUP
            assert texto.lower() == fuente.replace("COLOR red", "RGB 255 0 0").replace(' LABEL ""', "").lower(), programa
        else:
            assert texto.lower() == fuente.lower(), programa
            exactos += 1
    assert exactos == 138  # + los 6 VAR con borde de página, 24 de WRAP, CHECK, BITMAP, CURRENT PAGE y VERTICALTEXT, 14 BOXGROUP y 9 FRAMEAUTOSIZE
    # y 5 de geometría que parecía una declaración (pgeo_: antes, 4 de ellas salían con `"x".t()` en vez de Trace)


def test_guarda_de_las_paginas():
    if not (PAGINAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {PAGINAS}")
    huecos = dict(reversed(l.split("\t")) for l in (PAGINAS / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in PAGINAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["p_base"].lower()).read_bytes()
    assert "\t\t\t\tPAGE 2\n" in descompilador.descompilar(_cambia(datos, "PCT", 1, 0x60, 1))  # PAGE n: n − 1
    with pytest.raises(descompilador.NoSoportado, match=r"TEXT de página PCT 1: campos sin descifrar"):
        descompilador.descompilar(_cambia(datos, "PCT", 1, 0x62, 1))  # u16 alto de +0x60
    with pytest.raises(descompilador.NoSoportado, match=r"TEXT de página PCT 1: \+0x24 = 0x1"):
        descompilador.descompilar(_cambia(datos, "PCT", 1, 0x24, 1))
    with pytest.raises(descompilador.NoSoportado, match=r"borde 0x3"):  # UPSHADOW y DOWNSHADOW a la vez
        descompilador.descompilar(_cambia(datos, "PCT", 1, 0, 0x03))
    with pytest.raises(descompilador.NoSoportado, match=r"borde 0x6"):  # sombra y DOUBLE: no compila
        descompilador.descompilar(_cambia(datos, "PCT", 1, 0, 0x06))


def test_paginas_de_samples():
    assert "\t\tINTERFACE\n\t\t\tSIZE 595 842\n\t\t\tMARGIN 12 24 15 48\n" in _sample("prn1")


MENUS = KITS / "compilados" / "menus-86x64"


def test_menus_vuelven_a_su_fuente():
    """Batería de menús: exactos salvo `self.SetMenu(m)`, que sale `SetMenu(m)`, y el SEPARATOR escrito suelto
    detrás de una opción, que sale dentro de ella (la misma marca en esa opción: mismos bytes; suelto detrás de la
    última no compila)."""
    import importlib.util

    if not (MENUS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {MENUS}")
    spec = importlib.util.spec_from_file_location("menus", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "menus.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (MENUS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in MENUS.iterdir() if p.suffix.lower() == ".omd"}
    exactos, separador = 0, 0
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() not in omds:
            continue  # POPUP, y el título detrás de ICONFILE, no compilan
        esperado = fuente.replace("    self.SetMenu(m);\n", "    SetMenu(m);\n")
        if programa.startswith("kic"):  # `Char (1)` con espacio; con AUTOSIZE, el tamaño guardado es el calculado
            esperado = esperado.replace("v as Char (1)", "v as Char(1)")
            if "AUTOSIZE" in esperado:
                esperado = esperado.replace("POSITION 10 10 50 20", "POSITION 10 10 38 22")
        texto = descompilador.descompilar(omds[huecos[programa].lower()].read_bytes())
        if programa == "m_separator":
            assert esperado.count("SEPARATOR") == texto.count("SEPARATOR") == 1
            sin = [l.strip() for l in esperado.lower().splitlines() if l.strip() != "separator"]
            assert sin == [l.strip() for l in texto.lower().splitlines() if l.strip() != "separator"], programa
            separador += 1
            continue
        assert texto.lower() == esperado.lower(), programa
        exactos += 1
    assert (exactos, separador) == (69, 1)  # 49 + 13 de AUTOSIZE del control MENU (mau_) + 7 del ICON n de un CHECK (kic_)
    # Los mau_ que no compilan: AUTOSIZE detrás de `MENU x` o delante de cualquier otro atributo que no sea BUTTON BORDER.
    # Los kic_: el ICON n de un CHECK delante de VARIABLE o de AUTOSIZE, LABELLEFT detrás de VARIABLE, TAGS, LIKEVAR,
    # READONLY y ALIGNMENT en un CHECK (en cualquier orden), VARIABLE en BUTTON o BOX, y en un EDIT el icono detrás de VARIABLE
    assert sorted(p for p in modulo.P if huecos[p].lower() not in omds) == [
        "kic2_icon_autosize", "kic2_var_alignment_icon", "kic2_var_icon_alignment", "kic2_var_icon_readonly",
        "kic2_var_readonly_icon", "kic_b_icon_var", "kic_b_var", "kic_b_var_icon", "kic_e_var_icon", "kic_icon_tags",
        "kic_icon_var", "kic_tags_icon", "kic_todo", "kic_triple_hubble", "kic_var_autosize_icon", "kic_var_icon_autosize",
        "kic_var_icon_labelleft", "kic_var_icon_likevar", "kic_var_icon_tags", "kic_var_likevar_icon", "kic_var_tags_icon",
        "kic_x_icon_var", "kic_x_var", "kic_x_var_icon",
        "m_popup", "mau_autosize_attach", "mau_autosize_border_etched", "mau_autosize_cursor", "mau_autosize_fg",
        "mau_autosize_icon", "mau_autosize_invisible", "mau_autosize_noborder", "mau_autosize_vertical",
        "mau_button_border_autosize", "mau_icon_button_border_autosize", "mau_menu_autosize", "mau_todo_boton",
        "t_titulo_detras"]


@pytest.mark.parametrize(("programa", "trozo"), [
    # AUTOSIZE del control MENU: tras el icono y delante de BUTTON BORDER y de `MENU x` (batería menus.py, mau_: en
    # cualquier otro sitio no compila)
    ("mau_autosize", "\t\t\t\t\tPOSITION 0 0 90 24\n\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tMENU m\n"),
    ("mau_icon_autosize_button_border", "\t\t\t\t\tICON VERTICAL\n\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tBUTTON\n\t\t\t\t\tBORDER HILIGHT\n\t\t\t\t\tMENU m\n"),
    ("mau_todo", "\t\t\t\t\tFOREGROUND RGB 0 0 0\n\t\t\t\t\tATTACH ALL\n\t\t\t\t\tNOBORDER\n\t\t\t\t\tICON CENTER VERTICAL\n"
                 "\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tMENU m\n"),
    ("mau_cursor_autosize", "\t\t\t\t\tCURSOR\n\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tMENU m\n"),
])
def test_autosize_del_control_menu(programa, trozo):
    assert trozo in descompilador.descompilar(_bateria("menus", programa))


@pytest.mark.parametrize(("programa", "trozo"), [
    # ICON n de un CHECK: detrás de VARIABLE y de AUTOSIZE (batería menus.py, kic_: delante de cualquiera de los dos no
    # compila; STOCKMDI TRIPLE lleva `NOBORDER` / `VARIABLE orders.order_status` / `ICON 6` en el CHECK de su rejilla)
    ("kic_var_icon", "\t\t\t\tPOSITION 10 10 50 20\n\t\t\t\tVARIABLE v\n\t\t\t\tICON 6\n\t\tEND\n"),
    ("kic_triple", '\t\t\t\tLABEL "Invoiced"\n\t\t\t\tNOBORDER\n\t\t\t\tVARIABLE v\n\t\t\t\tICON 6\n\t\tEND\n'),
    ("kic_autosize_var_icon", "\t\t\t\tAUTOSIZE\n\t\t\t\tVARIABLE v\n\t\t\t\tICON 6\n\t\tEND\n"),
    ("kic_labelleft_var_icon", "\t\t\t\tLABELLEFT\n\t\t\t\tVARIABLE v\n\t\t\t\tICON 6\n\t\tEND\n"),
    ("kic2_autosize_icon", "\t\t\t\tAUTOSIZE\n\t\t\t\tICON 6\n\t\tEND\n"),
    # en un EDIT, `ICON n FILE "x"` sigue delante de VARIABLE (detrás no compila)
    ("kic_e_icon_var", '\t\t\t\tICON 2 FILE "_MBSTDBMP_"\n\t\t\t\tVARIABLE v\n\t\t\t\tDATATYPE CHAR\n'),
])
def test_icono_del_check_tras_variable(programa, trozo):
    assert trozo in descompilador.descompilar(_bateria("menus", programa))


@pytest.mark.parametrize(("programa", "trozo"), [
    ("t_sin_pulldown", "\t\tmenu m\n\t\t\tBEGIN\n"),  # raíz sin el 0x40: sin línea de tipo
    ("t_sin_pulldown_cabecera", '\t\tmenu m\n\t\t\tICONFILE "_MBSTDBMP_"\n\t\t\tALLOWICON\n\t\t\tBEGIN\n'),
    ("t_nolabel_sin_pulldown", "\t\tmenu m\n\t\tNOLABEL\n\t\t\tBEGIN\n"),
    ("t_titulo", '\t\tmenu m\n\t\t\t"Open"\n\t\tPULLDOWN\n'),  # el título: +0x18 de la raíz → STR
    ("t_titulo_cabecera", '\t\tmenu m\n\t\t\t"Open"\n\t\t\tICONFILE "_MBSTDBMP_"\n\t\t\tALLOWICON\n\t\tPULLDOWN\n'),
])
def test_menu_sin_pulldown_y_con_titulo(programa, trozo):
    huecos = dict(reversed(l.split("\t")) for l in (MENUS / "manifiesto.tsv").read_text().splitlines()) if MENUS.is_dir() else {}
    if programa not in huecos:
        pytest.skip(f"sin {MENUS}")
    datos = next(p for p in MENUS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()
    assert trozo in descompilador.descompilar(datos)


def test_raiz_de_menu_imposible():
    huecos = dict(reversed(l.split("\t")) for l in (MENUS / "manifiesto.tsv").read_text().splitlines()) if MENUS.is_dir() else {}
    if "t_titulo" not in huecos:
        pytest.skip(f"sin {MENUS}")
    datos = next(p for p in MENUS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["t_titulo"].lower()).read_bytes()
    for desp, valor in [(0, 0x48),  # un bit sin descifrar (0x08) en la raíz
                        (0x19, 0x01),  # el título: +0x18 a otra sección (IDE)
                        (0x1A, 0xFF)]:  # el título: una cadena que no está en STR
        with pytest.raises(descompilador.NoSoportado, match="raíz"):
            descompilador.descompilar(_cambia(datos, "MOP", 0, desp, valor))


def test_opcion_de_menu_con_bits_desconocidos():
    if not (MENUS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {MENUS}")
    huecos = dict(reversed(l.split("\t")) for l in (MENUS / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in MENUS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["m_base"].lower()).read_bytes()
    with pytest.raises(descompilador.NoSoportado, match="opción de menú MOP 1"):
        descompilador.descompilar(_cambia(datos, "MOP", 1, 1, 0x80))  # byte 1 de la opción «a»


PROYECTOS_KIT = KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "projects"


def test_menu_con_iconos_de_almafac():
    # ALMAFAC (7.4.2): un submenú con ICONFILE.
    f = PROYECTOS_KIT / "ALMAFAC" / "inicio.OMD"
    if not f.is_file():
        pytest.skip(f"sin {f}")
    texto = descompilador.descompilar(f.read_bytes())
    assert ('\t\tmenu menu1\n\t\tPULLDOWN\n\t\t\tBEGIN\n\t\t\t\tMENU pepe\n\t\t\t\t\t"Fichero          "\n'
            '\t\t\t\t\tICONFILE "_MBSTDBMP_"\n\t\t\t\t\tBEGIN\n') in texto  # cabecera de un submenú


def test_menu_default_icon_de_16_bits():
    # DEFAULT ICON n va en los 16 bits bajos de +0x54 de la raíz (los altos, 0): un n que no cabe en un byte.
    if not (MENUS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {MENUS}")
    huecos = dict(reversed(l.split("\t")) for l in (MENUS / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in MENUS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["h_default_icon"].lower()).read_bytes()
    assert "\t\t\tDEFAULT ICON 5\n" in descompilador.descompilar(datos)
    s = descompilador._Modulo(datos).s["MOP"]
    r = bytearray(datos)
    r[s.datos + 0x54: s.datos + 0x56] = (300).to_bytes(2, "little")
    assert "\t\t\tDEFAULT ICON 300\n" in descompilador.descompilar(bytes(r))


def test_menu_de_32_bits_estricto():
    # MNU y MOP de 32 bits: un u32 que el mapa no lleva tiene que ser 0 (si no, se perdería al expandir).
    import zipfile

    z = KITS / "cosmos82x86eval.zip"
    if not z.exists():
        pytest.skip(f"sin {z}")
    # ALMAFAC3 FRMTMPL (52 opciones); ALMAFAC inicio, el de antes, de 32 bits se para en un argumento ambiguo
    with zipfile.ZipFile(z) as zf:
        datos = zf.read(next(n for n in zf.namelist() if n.lower().endswith("projects/almafac3/frmtmpl.omd")))
    assert "\t\tmenu menuForm\n" in descompilador.descompilar(datos)
    m = descompilador._Modulo(datos)
    s = m.s["MOP"]
    r = bytearray(datos)
    r[s.datos + 1 * s.tam_registro + 0x20] = 1  # MOP 1, +0x20 de 32 bits: sin pareja en 64
    with pytest.raises(descompilador.NoSoportado, match=r"MOP 1 de 32 bits con datos sin mapa en \['0x20'\]"):
        descompilador.descompilar(bytes(r))


def test_menus_de_samples():
    assert "\t\tdefault menu MiMenu\n" in _sample("multiidoma")


TABS = KITS / "compilados" / "tabs-86x64"


def test_tabs_vuelven_a_su_fuente():
    """Batería de TAB: exactos salvo FIXED WIDTH n (n no se guarda: sale 1) e ICON FILE sin CENTER
    (CENTER no se guarda: sale con él), que dan los mismos bytes. Con las páginas en el LABEL (`LABEL "a|b"`), el
    icono de cada página lleva 0xFFFF (tab_con_label)."""
    import importlib.util

    if not (TABS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {TABS}")
    spec = importlib.util.spec_from_file_location("tabs", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "tabs.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (TABS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in TABS.iterdir() if p.suffix.lower() == ".omd"}
    exactos = 0
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() not in omds:
            continue
        esperado = fuente.replace('ICON FILE "_MBSTDBMP_"\n', 'ICON FILE "_MBSTDBMP_" CENTER\n')
        if programa == "t_label_icono":  # con las páginas en el LABEL, el ICON FILE no se guarda (ni el bit ni ICO)
            esperado = re.sub(r'\t*ICON FILE "_MBSTDBMP_" CENTER\n', "", esperado)
        if programa == "t_label_y_paginas":  # con TAB LABEL, el LABEL del TAB no se guarda: mandan las páginas
            esperado = re.sub(r'\t*LABEL "a\|b"\n', "", esperado)
        for n in (2, 3, 5):
            esperado = esperado.replace(f"FIXED WIDTH {n}\n", "FIXED WIDTH 1\n")
        assert descompilador.descompilar(omds[huecos[programa].lower()].read_bytes()).lower() == esperado.lower(), programa
        exactos += 1
    assert exactos == 31  # 6 con las páginas en el LABEL


@pytest.mark.parametrize(("modulo", "texto"), [
    ("exporttopdfex", '\t\t\t\t\t\tTAB LABEL "SQL" ICON 42\n'),                  # icono de una página
    ("refreshcosmosvisualmode", '\t\t\t\t\tNUMBER 4 TAGS "Blue" "Gray" "Brown" "Black"\n'),  # RADIO con fuente (u16 alto)
    ("color_flap_tab", "\t\t\t\t\tBORDER DOUBLE\n\t\t\t\t\tVERTICAL\n\t\t\t\t\tLOWTAB\n\t\t\t\t\tNUMBER 3\n"),  # orden
])
def test_tabs_de_samples(modulo, texto):
    assert texto in _sample(modulo)


def test_continue_y_do_while():
    assert "            continue;\n" in _sample("clasearray")
    assert "    do\n        SqlC.FetchTupleJson().Trace();\n    while SqlC.Found();\n" in _sample("fetchtuplejson")


def test_sentencia_vacia_y_valor_implicito():
    t = _sample("nullstm")
    assert "    while now.Hour <> 12 do\n        ;\n    ;\n    ;\n    ;\n    repeat\n        ;\n    until" in t
    assert '    medit = "HELLO WORLD";\n' in _sample("edit")   # propiedad implícita de un control


def test_dos_librerias_en_su_orden():
    # ttxmlopenhtmldoc aún no se descompila entero (bits de un control), pero sus LIBRARIES sí.
    assert _modulo("ttxmlopenhtmldoc").librerias() == ["LIBXML", "UTILSHTML"]


@pytest.mark.parametrize(("modulo", "pro", "cabecera"), [
    ("charthidelineonnulllabel", "LoadLibraryA", 'private dll "kernel32.dll" LoadLibraryA(aDllName as Char) return Integer'),
    ("loadjvm", "ReturnJavaVersion", 'public javaclass "Test1" ReturnJavaVersion() return Char'),
])
def test_declaraciones_externas(modulo, pro, cabecera):
    m = _modulo(modulo)
    k = next(k for k in range(m.s["PRO"].n) if m.nombre_pro(k) == pro)
    assert descompilador._Escritor(m).procedimiento(k) == [cabecera]


FCT_BITS = KITS / "compilados" / "fct-86x64"


def _fct(programa: str) -> bytes:
    if not (FCT_BITS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {FCT_BITS}")
    huecos = dict(reversed(l.split("\t")) for l in (FCT_BITS / "manifiesto.tsv").read_text().splitlines())
    return next(p for p in FCT_BITS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()


def test_fct_bits_vuelven_a_su_fuente():
    """Batería de bits de FCT: exactos salvo lo que el compilador no guarda (mismos bytes): `DATATYPE CHAR` a
    secas en un TEXT y `BUTTON` solo en MENU o SPIN (sin BORDER HILIGHT|BLACK detrás)."""
    import importlib.util

    if not (FCT_BITS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {FCT_BITS}")
    spec = importlib.util.spec_from_file_location("fct", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "fct.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (FCT_BITS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in FCT_BITS.iterdir() if p.suffix.lower() == ".omd"}
    sin_huella = {"t_datatype_char": "\t\t\t\tDATATYPE CHAR\n", "t_alignment_multiline_etchedout": "\t\t\t\tDATATYPE CHAR\n",
                  "m_button": "\t\t\t\t\tBUTTON\n", "sp_button": "\t\t\t\tBUTTON\n"}
    exactos = 0
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() not in omds:
            continue  # TICKS, FRAMEAUTOSIZE, POINT en PERCENT, ETCHEDIN con ETCHEDOUT…: no compilan
        if programa.startswith("cur_g_"):  # un GRID sin PARENTGRID (sin su binario de SVL) no se descompila
            with pytest.raises(descompilador.NoSoportado, match="sin PARENTGRID"):
                descompilador.descompilar(omds[huecos[programa].lower()].read_bytes())
            continue
        texto = descompilador.descompilar(omds[huecos[programa].lower()].read_bytes())
        if programa in sin_huella:
            assert texto.lower() == fuente.replace(sin_huella[programa], "", 1).lower(), programa
            continue
        if programa.startswith("geo_"):  # geometría que parecía una declaración: lo que no deja huella, de una forma
            fuente = fuente.replace('\t\t\t\tDATATYPE CHAR\n\t\t\t\tTAGS "t"', '\t\t\t\tTAGS "t"').replace(
                "b(e as event)", "b (e as Event)").replace("    PutEnv(", "    Module.PutEnv(").replace("end\n\n//{{CODEEND", "end\n//{{CODEEND")
        assert texto.lower() == fuente.lower(), programa
        exactos += 1
    # 53 + 33 de SORT (so_, so2_, so3_) + 11 de geometría que parecía una declaración (geo_) + 59 de CURSOR detrás de los
    # colores, BOLD y FONT (cur_: 19 tipos por 3 órdenes que compilan, menos los 3 de GRID, y cur_e_cursor_store,
    # cur_b_cursor_focus, cur_b_cursor_notabstop, cur_b_cursor_attach y cur_b_invisible_cursor)
    assert exactos == 156


@pytest.mark.parametrize(("programa", "k", "byte", "valor", "motivo"), [
    ("t_etchedout", 1, 1, 0x03, "ETCHEDIN y ETCHEDOUT juntos"),
    ("bm_palind", 1, 1, 0x06, "PALIND y GRAYSCALE juntos"),
    ("s_point_topleft", 1, 1, 0x03, "POINT TOPLEFT y BOTTOMRIGHT juntos"),
    ("m_base", 2, 1, 0x01, "bits de icono sin ICON"),
    ("m_base", 2, 0x40, 2, r"\+0x40 0x2 con 1 opciones"),
    ("m_base", 2, 0x70, 1, "ICON 0x1 en el control MENU"),
    ("m_button_border_hilight", 2, 0x22, 0x0D, "borde de botón 0xd"),
])
def test_fct_bits_imposibles(programa, k, byte, valor, motivo):
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia(_fct(programa), "FCT", k, byte, valor))


@pytest.mark.parametrize(("modulo", "trozo"), [
    ("ALMAFAC/comun.OMD", '\t\t\t\t\tMULTILINE\n\t\t\t\t\tETCHEDOUT\n\t\t\t\t\tTAGS "Control de Acceso"\n'),
    ("ALMAFAC/facturar.OMD", "\t\t\t\t\t\tBORDER DOUBLE DOWN\n\t\t\t\t\t\tTICKMARKS\n"),
    ("ALMAFAC/facturar.OMD", '\t\t\t\t\t\t\tDATATYPE INTEGER MASK 2\n\t\t\t\t\t\t\tTAGS "1"\n'),
    ("INDODIC/Mymenu2.OMD", "\t\t\t\t\tALIGNMENT RIGHT\n\t\t\t\t\tETCHEDOUT\n"),
    # VAR de página con LIKEVAR sobre una columna en mayúsculas: el UPSHIFT lo copia el compilador
    ("ALMAFAC/LISTACLI.OMD", '\t\t\t\t\tNOLABEL\n\t\t\t\t\tLABEL "Empresa"\n\t\t\t\t\tVARIABLE empresa\n\t\t\t\t\tLIKEVAR\n'),
    # parámetro por referencia de tipo Simple: VAR escrito (sin él, el compilador no pone el 0x40)
    ("ALMAFAC/eticli.OMD", "private GetCliente(VAR envar as Simple)\n"),
    # Char(25) con LIKEVAR: clientes.direccion (de un tipo compuesto) no tiene máscara en el .crf y sigue valiendo
    ("ALMAFAC/eticli.OMD", "\t\t\tdireccion as clientes.direccion\n"),
    ("ALMAFAC/eticli.OMD", '\t\t\tpreview as Smallint default 1\n\t\t\t\tboolean values "0|1"\n'),
    # CURSOR detrás de FONT, de BACKGROUND y BOLD, y de BOLD solo (batería fct.py, cur_): delante no compila
    ("ALMAFAC3/auxiliar.OMD", '\t\t\t\t\t\tFONT "Verdana" 10 CHARSET Ansi\n\t\t\t\t\t\tCURSOR\n\t\t\t\t\t\tLABEL "Provincias"\n'),
    ("ALMAFAC3/inicio.OMD", "\t\t\t\t\t\tBACKGROUND COLOR transparent\n\t\t\t\t\t\tBOLD\n\t\t\t\t\t\tCURSOR\n\t\t\t\t\t\tATTACH ALL\n"),
    ("ALMAFAC3/inicio.OMD", "\t\t\t\t\t\tBOLD\n\t\t\t\t\t\tCURSOR\n\t\t\t\t\t\tATTACH LEFT TOP RIGHT\n"),
    ("almafac4/auxiliar.OMD", '\t\t\t\t\t\tFONT "Verdana" 10 CHARSET Ansi\n\t\t\t\t\t\tCURSOR\n\t\t\t\t\t\tLABEL "Provincias"\n'),
    ("almafac4/inicio.OMD", '\t\t\t\t\t\tBACKGROUND COLOR transparent\n\t\t\t\t\t\tBOLD\n\t\t\t\t\t\tCURSOR\n\t\t\t\t\t\tATTACH BOTTOM\n\t\t\t\t\t\tLABEL "Salir"\n'),
    ("STOCKMDI/menu.OMD", '\t\t\t\t\t\tBACKGROUND COLOR transparent\n\t\t\t\t\t\tBOLD\n\t\t\t\t\t\tCURSOR\n\t\t\t\t\t\tATTACH LEFT BOTTOM\n\t\t\t\t\t\tLABEL "Exit"\n'),
    ("TryThisOneFirst/Menu_examples.OMD", '\t\t\t\t\tBACKGROUND COLOR transparent\n\t\t\t\t\tBOLD\n\t\t\t\t\tCURSOR\n\t\t\t\t\tLABEL "Exit"\n'),
    # AUTOSIZE del control MENU delante de `MENU x` (batería menus.py, mau_): detrás no compila
    ("ALMAFAC2/FRMTMPL.OMD", "\t\t\t\t\tICON CENTER VERTICAL\n\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tMENU menuForm\n"),
    # ICON n de un CHECK detrás de VARIABLE (batería menus.py, kic_, y tablas.py, rk_: delante no compila)
    ("STOCKMDI/triple.OMD", '\t\t\t\t\t\tLABEL "Invoiced"\n\t\t\t\t\t\tNOBORDER\n\t\t\t\t\t\tVARIABLE orders.order_status\n'
                            "\t\t\t\t\t\tICON 6\n\t\t\t\t\tCONTROL AS EDIT\n"),
    # el UPSHIFT que LIKEVAR copia de la columna elige entre surname y company (Char(25) con la misma máscara)
    ("STOCKMDI/cust_rep.OMD", "\t\t\tcompany1 as customers.company\n"),
    ("STOCKMDI/cust_rep.OMD", "\t\t\tsurname1 as customers.surname\n"),
])
def test_fct_bits_de_los_proyectos(modulo, trozo):
    from hubble import repositorio

    f = PROYECTOS_KIT / modulo
    if not f.is_file():
        pytest.skip(f"sin {f}")
    dbs = next((p for p in sorted(f.parent.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs"), None)
    catalogo = repositorio.Catalogo(dbs) if dbs else None
    assert trozo in descompilador.descompilar(f.read_bytes(), dbs.stem if dbs else "repositorio", catalogo)


def test_likevar_sin_upshift_de_columna_que_el_crf_no_aclara():
    # ALMAFAC eticli: `direccion as clientes.direccion` con LIKEVAR sin el bit; el .crf no dice si clientes.direccion
    # es UPSHIFT: se elige como antes (por el nombre) y se avisa
    from hubble import repositorio

    f = PROYECTOS_KIT / "ALMAFAC/eticli.OMD"
    if not f.is_file():
        pytest.skip(f"sin {f}")
    dbs = next(p for p in sorted(f.parent.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs")
    avisos = []
    texto = descompilador.descompilar(f.read_bytes(), dbs.stem, repositorio.Catalogo(dbs), avisos)
    assert "\t\t\tdireccion as clientes.direccion\n" in texto
    assert ("direccion as clientes.direccion: el LIKEVAR no lleva UPSHIFT y el .crf no dice si esa columna lo es "
            "(si lo fuera, compilaría distinto)") in avisos


@pytest.mark.parametrize(("modulo", "trozo"), [
    # valor implícito de un control en la dirección de los .omd del kit (0x14019d1f8)
    ("NIF/sample01.OMD", "On Enter ctrNif\nbegin\n    ctrNif = null;\nend\n"),
    ("ALMAFAC/albaran.OMD", '            barra = "Linea añadida";\n'),
    ("ALMAFAC/albaran.OMD", "    barra.Text = null;\n"),  # la propiedad escrita, con su nombre
    ("STOCKMDI/orders.OMD", '            barra = "Deleted Order line";\n'),
    ("ALMAFAC/albaran.OMD", '        case in ("cCantidad", "cDescuento", "cPrecio"):\n'),  # PR #45
])
def test_valor_implicito_del_kit(modulo, trozo):
    test_fct_bits_de_los_proyectos(modulo, trozo)


@pytest.mark.parametrize(("modulo", "trozo"), [
    # NOBORDER de los botones de un BUTTONGROUP, tras NUMBER (u16 alto de +0x20 = 0x40)
    ("ALMAFAC3/inicio.OMD", "\t\t\t\t\t\tNUMBER 2 COLUMNS 1\n\t\t\t\t\t\tNOBORDER\n\t\t\t\t\t\t\tBUTTON LABEL \"Facturar\" ICON 96\n"),
    ("ActiveX/demo.OMD", '\t\t\t\t\tNUMBER 1 ROWS 1\n\t\t\t\t\tNOBORDER\n\t\t\t\t\t\tBUTTON LABEL "Word" ICON 1\n'),
])
def test_borde_de_grupo_del_kit(modulo, trozo):
    test_fct_bits_de_los_proyectos(modulo, trozo)


@pytest.mark.parametrize(("modulo", "trozo"), [
    ("STOCKMDI/menu.OMD", "\t\t\t\t\tNOLABEL\n\t\t\t\t\tBORDER BLACK DOWN\n"),
    ("TryThisOneFirst/Menu_examples.OMD", "\t\t\t\t\tNOLABEL\n\t\t\t\t\tBORDER BLACK DOWN\n"),
    ("CalcRPN/calcu3.OMD", "\t\t\t\t\tBORDER BLACK\n"),
])
def test_border_black_del_kit(modulo, trozo):
    test_fct_bits_de_los_proyectos(modulo, trozo)


def test_grupo_de_punteros_partido():
    """prjbmapsdll EjBmapsdll: un grupo de 86 punteros junta dos bloques de memoria (ninguna base vale para todos; la
    mejor, para 61). Se parte en tramos, cada uno con su base única."""
    f = PROYECTOS_KIT / "prjbmapsdll" / "EjBmapsdll.OMD"
    if not f.is_file():
        pytest.skip(f"sin {f}")
    m = descompilador._Modulo(f.read_bytes())
    assert len(m.punteros) == 438  # antes, 155
    texto = descompilador.descompilar(f.read_bytes())
    assert "    UpDownZoom(1);\n" in texto and "Module.Rgb(255, 255, 255));\n" in texto  # argumentos escritos (ESCRITO_KIT)
    # Si un tramo queda con varias bases, el grupo entero no vale: si no, ALMAFAC eticli daría a 0x14e500 (la zona de
    # memoria del falso `document` de Word) la base de un tramo de un solo puntero.
    f = PROYECTOS_KIT / "ALMAFAC" / "eticli.OMD"
    if f.is_file():
        assert 0x14E500 not in descompilador._Modulo(f.read_bytes()).punteros


def _pares_kit_propio():
    for proy, propio in (("ALMAFAC", "almafac-86x64"), ("NIF", "nif-86x64"), ("prjbmapsdll", "bmaps-86x64")):
        kit, aqui = PROYECTOS_KIT / proy, KITS / "compilados" / propio
        if not kit.is_dir() or not aqui.is_dir():
            continue
        pk = {p.stem.lower(): p for p in kit.iterdir() if p.suffix.lower() == ".omd"}
        pp = {p.stem.lower(): p for p in aqui.iterdir() if p.suffix.lower() == ".omd"}
        for n in sorted(set(pk) & set(pp)):
            yield f"{proy}/{n}", pk[n], pp[n]


def test_kit_y_compilado_aqui_dan_lo_mismo():
    """El .omd que trae el kit y el que compilamos aquí del mismo fuente (cuya vuelta sale byte a byte) dan el mismo
    texto. Solo cambia el tamaño de los controles con AUTOSIZE, que el compilador calcula con las fuentes. Lo cazó
    prjbmapsdll: los smallint escritos del kit llevan 0x14 o el relleno 0xCC tras su valor, y salían como por defecto."""
    from hubble import repositorio

    pares = list(_pares_kit_propio())
    if not pares:
        pytest.skip("sin los proyectos del kit o sus compilados")
    iguales = 0
    for nombre, kit, aqui in pares:
        dbs = next((p for p in sorted(kit.parent.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs"), None)
        cat = repositorio.Catalogo(dbs) if dbs else None
        textos = []
        for f in (kit, aqui):
            try:
                textos.append(descompilador.descompilar(f.read_bytes(), dbs.stem if dbs else "repositorio", cat))
            except descompilador.NoSoportado as e:
                textos.append(f"NoSoportado: {e}")
        sin_pos = [re.sub(r"POSITION \d+ \d+ \d+ \d+", "POSITION", x) for x in textos]
        assert sin_pos[0] == sin_pos[1], nombre
        iguales += textos[0] == textos[1]
    assert (iguales, len(pares)) == (26, 29)


def test_punteros_que_caen_en_la_misma_posicion():
    """ActiveX Word: un grupo de 2 punteros cuadraba con una base falsa (`txtTemplate.Text` salía
    `txtTemplate.document`), que pone otro puntero en la misma posición de IDE que un grupo de 32. Se descarta."""
    f = PROYECTOS_KIT / "ActiveX" / "Word.OMD"
    if not f.is_file():
        pytest.skip(f"sin {f}")
    m = descompilador._Modulo(f.read_bytes())
    assert 0x14E470 not in m.punteros and 0x14E500 not in m.punteros
    assert m.punteros[0x2F4D0E4] == "document"  # el del grupo grande sigue
    # sin puntero, el nombre sale de su entrada de EOB (la de los otros `Text`): test_nombre_por_su_entrada
    assert "txtTemplate.Text" in descompilador.descompilar(f.read_bytes())


LLAMADAS = KITS / "compilados" / "llamadas-86x64"


def test_llamadas_vuelven_a_su_fuente():
    """Batería de llamadas: exactos salvo dos formas que dan los mismos bytes (comprobado con la vuelta):
    `!=` sale `<>`, `public f` sale `public f()` y `main(VAR x …)` sale `main(x …)`."""
    import importlib.util

    if not (LLAMADAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {LLAMADAS}")
    spec = importlib.util.spec_from_file_location("llamadas", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "llamadas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (LLAMADAS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in LLAMADAS.iterdir() if p.suffix.lower() == ".omd"}
    iguales = {"e_distinto": ("if a != 1", "if a <> 1"), "e_sin_parentesis": ("public f\n", "public f()\n"),
               "v_dos_decimal_local": ("public f\n", "public f()\n"),
               "v_tres_integer": ("x y z as integer default 0", "x as Integer default 0\n    y as Integer default 0\n    z as Integer default 0"),
               # los parámetros de main llevan siempre el 0x40: con VAR o sin él, los mismos bytes
               "m_main_param_var": ("main(VAR x", "main(x")}
    exactos = 0
    for programa, fuente in modulo.P.items():
        texto = descompilador.descompilar(omds[huecos[programa].lower()].read_bytes())
        if programa in iguales:
            fuente = fuente.replace(*iguales[programa])
        else:
            exactos += 1
        assert texto.lower() == fuente.lower(), programa
    assert exactos == 30


def test_argumento_por_defecto_de_una_llamada_creada_tarde():
    # `if o.Run then`: el compilador crea la llamada después del cuerpo (para convertir el resultado) y con
    # ella el null de Run; va antes que la llamada pero después de la raíz de la condición.
    if not (LLAMADAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {LLAMADAS}")
    huecos = dict(reversed(l.split("\t")) for l in (LLAMADAS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in LLAMADAS.iterdir() if p.suffix.lower() == ".omd"}
    assert "    if o.Run then\n" in descompilador.descompilar(omds[huecos["r_if_run"].lower()].read_bytes())
    assert "    if o.Run(null) then\n" in descompilador.descompilar(omds[huecos["r_if_run_null"].lower()].read_bytes())


def test_default_null_con_valor():
    if not (LLAMADAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {LLAMADAS}")
    huecos = dict(reversed(l.split("\t")) for l in (LLAMADAS / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in LLAMADAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["d_null"].lower()).read_bytes()
    assert "public f(x as Integer default null)" in descompilador.descompilar(datos)
    with pytest.raises(descompilador.NoSoportado, match="default null de x con valor"):
        descompilador.descompilar(_cambia(datos, "OBJ", 0, 0x28, 5))


VARIABLES = KITS / "compilados" / "variables-86x64"


def _variables():
    import importlib.util

    if not (VARIABLES / "manifiesto.tsv").exists():
        pytest.skip(f"sin {VARIABLES}")
    spec = importlib.util.spec_from_file_location("variables", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "variables.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (VARIABLES / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in VARIABLES.iterdir() if p.suffix.lower() == ".omd"}
    return {n: (f, omds[huecos[n].lower()].read_bytes()) for n, f in modulo.P.items() if huecos[n].lower() in omds}


def test_variables_vuelven_a_su_fuente():
    """Batería de variables y tablas de formulario (repositorio stock). Equivalentes (mismos bytes), no exactos:
    `required` en una columna NOT NULL del repositorio (con el catálogo, no se escribe), `Money (16,2)` (el de serie)
    y `Char (n)` con espacio. Con `depend on` (dos y tres tablas) también."""
    exactos = 0
    for programa, (fuente, datos) in _variables().items():
        texto = descompilador.descompilar(datos, "stock", _stock())
        esperado = re.sub(r"(Char|Decimal) \(", r"\1(", fuente).replace("state as column required", "state as column")
        esperado = esperado.replace("Money(16,2)", "Money").replace("Money (16,2)", "Money")
        assert texto.lower() == esperado.lower(), programa
        exactos += fuente == esperado
    assert exactos == 39


@pytest.mark.parametrize(("programa", "trozo"), [
    ("d_null", "\t\t\torder_date as column default null\n"),  # sin el bit de default; +0x28 ≠ 0
    ("o_boolean", '\t\t\tb as Boolean\n\t\t\t\tboolean values "0|1"\n'),
    ("o_enumerated", '\t\t\tb as Char(5)\n\t\t\t\tenumerated 4 values "d1|d2|d3|d4"\n'),
    ("c_todo", "\t\t\tstate as column noentry noupdate\n"),
    ("c_sname_noupdate_required", "\t\t\tsname as column required noupdate\n"),
    ("d_todo", "\t\t\tquantity as column default 5 required noentry noupdate\n"),
    ("d_today", "\t\t\torder_date as column default TODAY\n"),
    ("d_fecha_mdy", '\t\t\torder_date as column default "03/15/2026"\n'),
    ("d_fecha_1900", '\t\t\torder_date as column default "01/01/1900"\n'),
    ("d_negativo", "\t\t\tdiscount as column default -1\n"),
    ("d_decimal", "\t\t\tprice as column default 1.5\n"),
    ("o_fecha_today", "\t\t\tf as Date default TODAY\n"),
    ("t_order_by_dos", "\t\tTable orders is orders\n\t\t\torder by (customer, order_nbr)\n\t\tbegin\n"),
    ("t_vartable", "\t\tVartable orders is orders\n"),
    ("t_vartable_sin_is", "\t\tVartable orders\n\t\tbegin\n"),
    ("t_depend_on", "\t\tTable orderlines is orderlines\n\t\t\tdepend on orders join fk2_lines\n\t\tbegin\n\t\t\tline_nbr as column\n"),
    ("t_order_by_y_depend", "\t\t\tdepend on orders join fk2_lines\n\t\t\torder by (line_nbr)\n\t\tbegin\n"),
    ("t_tres", "\t\t\tdepend on customers join fk1_orders\n\t\tbegin\n\t\t\torder_nbr as column\n\t\tend\n"
               "\t\tTable orderlines is orderlines\n\t\t\tdepend on orders join fk2_lines\n"),
])
def test_variables_de_formulario(programa, trozo):
    assert trozo in descompilador.descompilar(_variables()[programa][1], "stock", _stock())


LPROARTS = ["ALMAFAC/LPROART.OMD", "ALMAFAC2/LPROART.OMD", "ALMAFAC3/LPROART.OMD", "almafac4/LPROART.OMD",
            "almafac4/LProArtB.OMD", "LookAndFeel7/ColoresPorDefecto/LPROART.OMD"]


@pytest.mark.parametrize("kit", [PROYECTOS_KIT, KITS / "extraido" / "86x86" / "Cosmos8.6eval" / "projects"])
@pytest.mark.parametrize("modulo", LPROARTS)
def test_likevar_con_mascara_de_una_columna(kit, modulo):
    # ALMAFAC LPROART: `pr_cost as articulos.pr_cost` (MONEY: el FOB da los mismos bytes que `as Money(12,2)`) y un
    # VAR con LIKEVAR que copia su máscara (4) del repositorio: del .crf, que la da a las 4 columnas Money(12,2)
    # (heredan de precio_tipo). Antes, NoSoportado. ALMAFAC lleva un .crf v1 en el kit x64 y v2 en el x86; almafac4, v2.
    from hubble import repositorio

    f = kit / modulo
    if not f.is_file():
        pytest.skip(f"sin {f}")
    dbs = next(p for p in sorted(f.parent.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs")
    avisos = []
    texto = descompilador.descompilar(f.read_bytes(), "almafac", repositorio.Catalogo(dbs), avisos)
    assert "\t\t\tpr_cost as articulos.pr_cost\n" in texto
    assert "\t\t\t\t\t\tVARIABLE pr_cost\n\t\t\t\t\t\tLIKEVAR\n" in texto or "VARIABLE pr_cost\n\t\t\t\tLIKEVAR\n" in texto
    assert ("pr_cost as articulos.pr_cost: una de 4 columnas del mismo tipo y la máscara 4 (el .omd no guarda cuál "
            "era; todas compilan igual)") in avisos


def test_likevar_con_mascara_sin_crf(tmp_path):
    # Sin el .crf no se sabe qué columna tiene la máscara: NoSoportado (el compilador tampoco compila sin él)
    import shutil

    from hubble import repositorio

    f = PROYECTOS_KIT / "ALMAFAC" / "LPROART.OMD"
    if not f.is_file():
        pytest.skip(f"sin {f}")
    shutil.copytree(PROYECTOS_KIT / "ALMAFAC" / "almafac.dbs", tmp_path / "almafac.dbs")
    with pytest.raises(descompilador.NoSoportado, match="sin el .crf del repositorio no se sabe cuál"):
        descompilador.descompilar(f.read_bytes(), "almafac", repositorio.Catalogo(tmp_path / "almafac.dbs"))


LIKEVAR_BAT = KITS / "compilados" / "likevar-86x64"  # batería likevar.py (proyecto ALMAFAC; 32 bits: likevar-86x86)


def _likevar(arq="86x64"):
    import importlib.util

    from hubble import repositorio

    d = KITS / "compilados" / f"likevar-{arq}"
    if not (LIKEVAR_BAT / "manifiesto.tsv").exists() or not d.is_dir():
        pytest.skip(f"sin {d}")
    spec = importlib.util.spec_from_file_location("likevar", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "likevar.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (LIKEVAR_BAT / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in d.iterdir() if p.suffix.lower() == ".omd"}
    return {n: (f, omds[huecos[n].lower()].read_bytes()) for n, f in modulo.P.items()}, repositorio.Catalogo(LIKEVAR_BAT / "almafac.dbs")


@pytest.mark.parametrize("arq", ["86x64", "86x86"])
def test_likevar_vuelve_a_su_fuente(arq):
    """LIKEVAR con la máscara de una columna (la vuelta de 64 y 32 bits da los mismos bytes). La columna escrita es
    una con el mismo tipo y la misma máscara (clientes va antes en el catálogo); sin columnas, sin REPOSITORY."""
    bateria, catalogo = _likevar(arq)
    exactos = 0
    for programa, (fuente, datos) in bateria.items():
        texto = descompilador.descompilar(datos, "almafac", catalogo)
        esperado = re.sub(r"p as (articulos\.pr_cost|articulos\.pr_vent|lineas\.precio)\n", "p as clientes.total_factura\n",
                          fuente).replace("p as articulos.existencias", "p as provincias.provincia")
        if programa == "lk_columna_datatype":  # sin LIKEVAR, la columna no deja huella: Money(12,2) da los mismos bytes
            esperado = fuente.replace("p as articulos.pr_cost", "p as Money(12,2)")
        if not re.search(r" as \w+\.\w+\n", esperado):  # sin ninguna columna, el REPOSITORY no se escribe
            esperado = esperado.replace("REPOSITORY almafac\n", "")
        assert texto == esperado, programa
        exactos += texto == fuente
    assert exactos == 2  # lk_money_total_factura y lk_date_columna


@pytest.mark.parametrize(("programa", "seccion", "k", "valor", "motivo"), [
    ("lk_dos_controles", "PCT", 2, 0x33, r"LIKEVAR con las máscaras \[3, 4\]"),  # una columna tiene una sola
    ("lk_decimal_a_mano", "PCT", 1, 0x43, r"ninguna columna del repositorio es Decimal\(12,2\) con la máscara 4"),
    ("lk_money_columna", "PCT", 1, 0x73, r"ninguna columna del repositorio es Money\(12,2\) con la máscara 7"),
    ("lk_date_columna", "PCT", 1, 0x05, r"ninguna columna del repositorio es Date con la máscara 0"),  # todas, la 5
    ("lk_texto_form", "FCT", 1, 0x73, r"Money\(12,2\) con la máscara 7"),
])
def test_likevar_con_mascara_imposible(programa, seccion, k, valor, motivo):
    bateria, catalogo = _likevar()
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia(bateria[programa][1], seccion, k, 0x22, valor), "almafac", catalogo)


def test_likevar_con_y_sin_upshift():
    # dos controles con LIKEVAR de la misma variable, uno con el bit y otro sin él: una columna lo es o no lo es
    bateria, catalogo = _likevar()
    with pytest.raises(descompilador.NoSoportado, match="LIKEVAR con UPSHIFT y sin él en distintos controles"):
        descompilador.descompilar(_cambia(bateria["lk_dos_controles"][1], "PCT", 2, 2, 0x04), "almafac", catalogo)


def test_likevar_la_mascara_dice_que_es_columna():
    # La misma variable escrita a mano (máscara 0) con la máscara 4 en el control: solo eso la hace columna
    bateria, catalogo = _likevar()
    texto = descompilador.descompilar(_cambia(bateria["lk_money_a_mano"][1], "PCT", 1, 0x22, 0x43), "almafac", catalogo)
    assert "\t\t\tp as clientes.total_factura\n" in texto


def test_likevar_guarda_del_control():
    # Si el escritor no ha sacado la variable `as tabla.columna`, el control con la máscara no se puede escribir
    from hubble.interfaz import Pagina

    bateria, _ = _likevar()
    m = descompilador._Modulo(bateria["lk_money_columna"][1])
    with pytest.raises(descompilador.NoSoportado, match="LIKEVAR con la máscara 4 de una columna que el .omd no nombra"):
        Pagina(m, descompilador.NoSoportado).mascara_de_columna(1, 0, m.u32("PCT", 1, 0x20))


def test_likevar_en_un_text_con_otra_alineacion():
    bateria, catalogo = _likevar()
    datos = _cambia(bateria["lk_texto_form"][1], "FCT", 1, 0x46, 0x40)  # CENTER (0x400000 de +0x44) en vez de RIGHT
    with pytest.raises(descompilador.NoSoportado, match="TEXT FCT 1 con LIKEVAR y ALIGNMENT 0x400000"):
        descompilador.descompilar(datos, "almafac", catalogo)


def test_likevar_en_un_text_alinea_como_la_variable():
    # TEXT con LIKEVAR de un Money: el ALIGNMENT RIGHT lo copia de la variable (escrito detrás de LIKEVAR, no compila)
    bateria, catalogo = _likevar()
    texto = descompilador.descompilar(bateria["lk_texto_form"][1], "almafac", catalogo)
    assert "ALIGNMENT" not in texto


def test_valores_y_columnas_imposibles():
    from hubble import contenedor

    datos = _variables()["o_enumerated"][1]
    with pytest.raises(descompilador.NoSoportado, match="valores del FOB 0"):  # 5 valores con una cadena de 4
        descompilador.descompilar(_cambia(datos, "FOB", 0, 0x60, 5), "stock", _stock())
    datos = _variables()["d_fecha"][1]
    s = contenedor.leer(datos).seccion("FOB")
    nuevo = bytearray(datos)
    nuevo[s.datos + s.tam_registro + 0x2C] = 0  # una fecha sin su marca de valor
    with pytest.raises(descompilador.NoSoportado, match="default de fecha"):
        descompilador.descompilar(bytes(nuevo), "stock", _stock())
    with pytest.raises(descompilador.NoSoportado, match="default TODAY de un smallint"):
        descompilador.descompilar(_cambia(_variables()["d_numero"][1], "FOB", 1, 2, 0x60), "stock", _stock())
    with pytest.raises(descompilador.NoSoportado, match="tabla FTA 0 con"):  # SIN_IS en una Table (sin Vartable)
        descompilador.descompilar(_cambia(_variables()["t_una"][1], "FTA", 0, 0, 0x04), "stock", _stock())


def _cambia_u32(datos: bytes, etiqueta: str, k: int, desp: int, valor: int) -> bytes:
    from hubble import contenedor

    s = contenedor.leer(datos).seccion(etiqueta)
    nuevo = bytearray(datos)
    struct.pack_into("<I", nuevo, s.datos + k * s.tam_registro + desp, valor)
    return bytes(nuevo)


def test_depend_on_imposibles():
    # t_depend_on: FTA 1 (orderlines) +0x30 → FTA 0 (orders), +0x38 → FRC 1 (order_nbr → FOB 0 de orders);
    # sus FJO: 2 (fk1_lines → items) y 3 (fk2_lines → orders); +0x68 = 3 (FOB 2, su primera columna, tiene la casilla 4)
    datos = _variables()["t_depend_on"][1]
    m = descompilador._Modulo(datos)
    assert "depend on orders join fk2_lines" in descompilador.descompilar(datos, "stock", _stock())
    casos = [
        (_cambia(datos, "FTA", 1, 0x68, 4), r"\+0x68 = 4"),  # la casilla no es la de antes de sus columnas
        (_cambia(datos, "FTA", 1, 0x32, 1), "depend on 0x11400"),  # padre: ella misma (no está antes)
        (_cambia(datos, "FRC", 1, 0x1A, 2), "fuera del padre"),  # la unión con una columna de la hija
        (_cambia_u32(datos, "FJO", 3, 0x18, m.u32("FJO", 2, 0x18)), "sin una clave"),  # ninguna FJO va al padre
        (_cambia_u32(_cambia_u32(datos, "FJO", 2, 0x18, m.u32("FJO", 3, 0x18)), "FJO", 2, 0x28, m.u32("FJO", 3, 0x28)),
         "sin una clave"),  # dos FJO van al padre, por las mismas columnas: no se sabe cuál
        (_cambia_u32(datos, "FJO", 3, 0x28, m.u32("FJO", 2, 0x28)), "sin una clave"),  # la clave une otras columnas
        (_cambia_u32(datos, "FTA", 0, 0x18, m.u32("FJO", 2, 0x18)), "depend on orders is items"),  # padre con alias
    ]
    for mutado, motivo in casos:
        with pytest.raises(descompilador.NoSoportado, match=motivo):
            descompilador.descompilar(mutado, "stock", _stock())


CODTABLAS = KITS / "compilados" / "codtablas-86x64"


def _codtablas(solo_compilados=True):
    import importlib.util

    if not (CODTABLAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {CODTABLAS}")
    spec = importlib.util.spec_from_file_location("codtablas", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "codtablas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    if not solo_compilados:
        return modulo.P
    huecos = dict(reversed(l.split("\t")) for l in (CODTABLAS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in CODTABLAS.iterdir() if p.suffix.lower() == ".omd"}
    return {n: (f, omds[huecos[n].lower()].read_bytes()) for n, f in modulo.P.items() if huecos[n].lower() in omds}


def test_tablas_en_el_codigo():
    """Batería codtablas: `orders.DisableCommand(…)` (la tabla como objeto: nodo 0x30 0x30, +0x10 → FTA) y
    `orders.columna` (PROPIEDAD de la tabla y la columna). La columna a secas no compila («Unknown identifier»)."""
    programas = _codtablas()
    assert sorted(set(_codtablas(False)) - set(programas)) == ["k_asigna_columna_sola", "k_columna_sola"]
    for programa, (fuente, datos) in programas.items():
        assert descompilador.descompilar(datos, "stock", _stock()).lower() == fuente.lower(), programa


def test_argumentos_delante_de_los_variables():
    # ALMAFAC provee: `Sql.SelectWindow(Self, …, 1, proveedores.provincia)`. Con argumentos variables escritos (la
    # lista 0xD0), los de delante también lo están, aunque sus bytes parezcan los de un literal copiado
    f = PROYECTOS_KIT / "ALMAFAC" / "provee.OMD"
    if f.is_file():
        from hubble import repositorio

        catalogo = repositorio.Catalogo(PROYECTOS_KIT / "ALMAFAC" / "almafac.dbs")
        assert '"Seleccione Provincia", 1, proveedores.provincia);' in descompilador.descompilar(f.read_bytes(), "almafac", catalogo)
    datos = _codtablas()["k_select_columna"][1]  # el 1 (REF 7), con la «basura» de un literal copiado (0x14)
    assert descompilador._Modulo(datos).rec("REF", 7)[:2] == bytes([descompilador.LIT_SMALLINT, 0xF0])
    datos = _cambia(datos, "REF", 7, 0x1A, 0x14)
    assert '"t", 1, orders.customer);' in descompilador.descompilar(datos, "stock", _stock())


def test_valores_del_repositorio_crf():
    # ALMAFAC provee: `sexo as column` y `ecivil as column` llevan en el FOB los valores del repositorio (ALMAFAC.CRF:
    # «V|M», «S|C|V|D»); el compilador los copia y escritos en la columna no compilan (7.4.2): no se escriben
    from hubble import repositorio

    f = PROYECTOS_KIT / "ALMAFAC" / "provee.OMD"
    if not f.is_file():
        pytest.skip(f"sin {f}")
    catalogo = repositorio.Catalogo(PROYECTOS_KIT / "ALMAFAC" / "almafac.dbs")
    assert {"V|M", "S|C|V|D"} <= catalogo.valores and not _stock().valores
    texto = descompilador.descompilar(f.read_bytes(), "almafac", catalogo)
    assert "\t\t\tsexo as column\n\t\t\tdireccion as column\n" in texto and "values" not in texto
    assert '\t\t\tsexo as column\n\t\t\t\tboolean values "V|M"\n' in descompilador.descompilar(f.read_bytes(), "almafac")
    # una variable que no es columna: sus valores se escriben aunque el repositorio tenga la misma cadena
    otro = _stock()
    otro.valores = {"0|1"}
    assert 'boolean values "0|1"' in descompilador.descompilar(_variables()["o_boolean"][1], "stock", otro)


def test_tabla_como_argumento():
    """`EditingTable.IsMe(orders)`: el nodo de la tabla lleva 0x05 en el byte 2, como cualquier argumento (ALMAFAC2
    albaran: `DisableCommand(cmd, not EditingTable.IsMe(albaranes))`)."""
    datos = _codtablas()["k_isme"][1]
    m = descompilador._Modulo(datos)
    assert [m.rec("REF", k)[2] for k in range(m.s["REF"].n) if m.rec("REF", k)[:2] == bytes([descompilador.TABLA] * 2)] == [5]
    f = PROYECTOS_KIT / "ALMAFAC2" / "albaran.OMD"
    if f.is_file():
        test_fct_bits_de_los_proyectos("ALMAFAC2/albaran.OMD", "        DisableCommand(cmd, not EditingTable.IsMe(albaranes));\n")


def test_tabla_en_el_codigo_imposible():
    for programa, desp, valor, motivo in [("k_disable", 2, 1, "tabla en REF"),  # un bit sin descifrar
                                          ("k_disable", 2, 4, "tabla en REF"),  # byte 2: 0 (objeto) o 5 (argumento)
                                          ("k_columna_tabla", 0x12, 1, "columna de otra tabla")]:  # la tabla: FTA 1
        datos = _codtablas()[programa][1]
        m = descompilador._Modulo(datos)
        k = next(k for k in range(m.s["REF"].n) if m.rec("REF", k)[:2] == bytes([descompilador.TABLA] * 2))
        with pytest.raises(descompilador.NoSoportado, match=motivo):
            descompilador.descompilar(_cambia(datos, "REF", k, desp, valor), "stock", _stock())


EVTABLAS = KITS / "compilados" / "evtablas-86x64"


def _evtablas(solo_compilados=True):
    import importlib.util

    if not (EVTABLAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {EVTABLAS}")
    spec = importlib.util.spec_from_file_location("evtablas", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "evtablas.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    if not solo_compilados:
        return modulo.P
    huecos = dict(reversed(l.split("\t")) for l in (EVTABLAS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in EVTABLAS.iterdir() if p.suffix.lower() == ".omd"}
    return {n: (f, omds[huecos[n].lower()].read_bytes()) for n, f in modulo.P.items() if huecos[n].lower() in omds}


def test_eventos_de_tabla():
    """Batería evtablas: `On Evento Table x` (PRO de tipo 6: +0x28 el evento, +0x20 → FTA) y `On Evento Table (t as
    Char)` (de cualquier tabla: +0x20 = 0). Los que no compilan: Error, BeginGroup, EndGroup, Eof y Locked no son eventos
    de tabla, el nombre distingue mayúsculas (`on fetch`) y sin tabla hace falta el parámetro. La línea en blanco entre
    procedimientos la pone Hubble."""
    programas = _evtablas()
    assert sorted(set(_evtablas(False)) - set(programas)) == ["e_begingroup", "e_edit_sin_parametro", "e_endgroup", "e_eof",
                                                             "e_error", "e_fetch_minusculas", "e_locked"]
    for programa, (fuente, datos) in programas.items():
        texto = descompilador.descompilar(datos, "stock", _stock())
        assert texto.replace("\n\n", "\n").lower() == fuente.lower(), programa


@pytest.mark.parametrize(("programa", "cabecera"), [
    ("e_fetch", "On Fetch Table orders\n"), ("e_changingrow", "On ChangingRow Table orders\n"),
    ("e_refetch", "On ReFetch Table orders\n"), ("e_edit_cualquiera", "On Edit Table (tab as Char)\n"),
])
def test_evento_de_tabla_exacto(programa, cabecera):
    assert cabecera in descompilador.descompilar(_evtablas()[programa][1], "stock", _stock())


def test_evento_de_tabla_imposible():
    for programa, desp, valor, motivo in [
        ("e_fetch", 0x28, 14, "evento de tabla 14"),  # el 14 no sale con ningún nombre de la lista
        ("e_fetch", 0x01, 0x06, "evento de tabla 13 .0x5000606"),  # otros bits en +0x00
        ("e_fetch", 0x21, 0, "evento de tabla 13"),  # sin tabla y sin parámetro
        ("e_edit_cualquiera", 0x21, 0x14, "evento de tabla 19"),  # con tabla y con el parámetro de cualquiera
    ]:
        with pytest.raises(descompilador.NoSoportado, match=motivo):
            descompilador.descompilar(_cambia(_evtablas()[programa][1], "PRO", 0, desp, valor), "stock", _stock())


GRUPOS = KITS / "compilados" / "grupos-86x64"


def _grupos(solo_compilados=True):
    import importlib.util

    if not (GRUPOS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {GRUPOS}")
    spec = importlib.util.spec_from_file_location("grupos", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "grupos.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    if not solo_compilados:
        return modulo.P
    huecos = dict(reversed(l.split("\t")) for l in (GRUPOS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in GRUPOS.iterdir() if p.suffix.lower() == ".omd"}
    return {n: (f, omds[huecos[n].lower()].read_bytes()) for n, f in modulo.P.items() if huecos[n].lower() in omds}


def test_grupos_vuelven_a_su_fuente():
    """Batería grupos (BUTTONGROUP 0xC, BOXGROUP 0xE). Equivalentes, no exactos: `CLICKTYPE CHECK` es el de serie (no
    deja huella), los colores salen en RGB y PAGE 1 no se escribe
    (se guarda como 0, igual que sin PAGE). No compilan: LABEL en un
    BUTTONGROUP, BORDER ALL y BORDER HILIGHT en un BOXGROUP, y tras NUMBER otro borde que BLACK, HILIGHT o NOBORDER
    («Expecting black, hilight»)."""
    programas = _grupos()
    assert sorted(set(_grupos(False)) - set(programas)) == [
        "g_b_double", "g_b_double_down", "g_b_down", "g_b_etched", "g_b_frame", "g_b_hilight_black",
        "g_cursor_bg", "g_cursor_bold", "g_cursor_fg", "g_label",
        "x_border_all", "x_cursor_bg", "x_cursor_bold", "x_cursor_fg", "x_hilight"]
    exactos = 0  # VARIABLE, delante de CLICKTYPE (detrás de NUMBER no compila)
    for programa, (fuente, datos) in programas.items():
        texto = descompilador.descompilar(datos)
        esperado = re.sub(r"\t+CLICKTYPE CHECK\n", "", fuente).replace("COLOR red", "RGB 255 0 0").replace("COLOR blue", "RGB 0 0 255")
        if programa == "g_page":  # PAGE 1 se guarda como 0 (PAGE n: n − 1), igual que sin PAGE
            esperado = esperado.replace("\t\t\t\t\tPAGE 1\n", "")
        assert texto.lower() == esperado.lower(), programa
        exactos += texto == fuente
    assert exactos == 27  # + g_b_noborder_iconos, x_b_noborder, x_bold_cursor y g_bold_cursor


@pytest.mark.parametrize(("programa", "trozo"), [
    ("g_radio", "\t\t\t\tCLICKTYPE RADIO\n\t\t\t\tNUMBER 2 ROWS 1\n"),
    ("x_manual", "\t\t\t\tCLICKTYPE MANUAL\n\t\t\t\tNUMBER 2 COLUMNS 1\n"),
    ("g_columns2", "\t\t\t\tNUMBER 4 COLUMNS 2\n"),
    ("g_hilight", "\t\t\t\tNUMBER 2 ROWS 1\n\t\t\t\tBORDER HILIGHT\n"),
    ("g_iconos_vertical", '\t\t\t\tICON FILE "_MBSTDBMP_" CENTER VERTICAL\n'),
    ("g_iconos_sin_center", '\t\t\t\tICON FILE "_MBSTDBMP_"\n'),
    ("g_label_icono", '\t\t\t\t\tBUTTON LABEL "a" ICON 3\n\t\t\t\t\tBUTTON LABEL "b" ICON 5\n'),
    ("g_label_vacio", '\t\t\t\t\tBUTTON LABEL ""\n'),
    ("x_box_vacio", "\t\t\t\t\tBOX\n\t\t\t\t\tBOX\n"),
    ("x_iconos", "\t\t\t\t\tBOX ICON 2\n\t\t\t\t\tBOX ICON 3\n"),
    ("x_color_label", '\t\t\t\t\tBOX LABEL "1" BACKGROUND RGB 255 0 0\n'),
    ("x_color_rgb", '\t\t\t\t\tBOX LABEL "1" BACKGROUND RGB 1 2 3\n'),
    ("x_allowdrag", "\t\t\t\tALLOWDRAG\n\t\t\t\tNUMBER 2 COLUMNS 1\n"),
    # borde de los elementos tras NUMBER (u16 alto de +0x20): 0x40 NOBORDER (ALMAFAC3 inicio, ActiveX demo), 0x10 BLACK
    ("g_b_noborder", "\t\t\t\tNUMBER 2 ROWS 1\n\t\t\t\tNOBORDER\n\t\t\t\t\tBUTTON"),
    ("g_b_black", "\t\t\t\tNUMBER 2 ROWS 1\n\t\t\t\tBORDER BLACK\n\t\t\t\t\tBUTTON"),
    ("g_b_noborder_iconos", "\t\t\t\tNOBORDER\n\t\t\t\tICON FILE"),  # el del control, delante; el de los botones, detrás
    ("g_b_noborder_iconos", "\t\t\t\tNUMBER 2 ROWS 1\n\t\t\t\tNOBORDER\n\t\t\t\t\tBUTTON"),
    ("x_b_noborder", "\t\t\t\tNUMBER 2 COLUMNS 1\n\t\t\t\tNOBORDER\n\t\t\t\t\tBOX"),
    # CURSOR en un grupo, detrás de los colores, BOLD y FONT (delante no compila: «Expecting number»)
    ("x_fg_cursor", "\t\t\t\tFOREGROUND RGB 0 0 255\n\t\t\t\tCURSOR\n\t\t\t\tNUMBER"),
    ("g_bold_cursor", "\t\t\t\tBOLD\n\t\t\t\tCURSOR\n\t\t\t\tCLICKTYPE MANUAL\n"),
    ("g_bg_cursor", "\t\t\t\tBACKGROUND RGB 0 0 255\n\t\t\t\tCURSOR\n"),
])
def test_grupo_exacto(programa, trozo):
    assert trozo in descompilador.descompilar(_grupos()[programa][1])


def test_grupo_imposible():
    # FCT 1 de g_base: +0x00 = 0x90000100 (LABEL, sin ICON: 0x100), +0x40 = NUMBER 2; su binario, en SVL
    for programa, desp, valor, motivo in [
        ("g_base", 0x02, 0x0C, "RADIO y MANUAL juntos"),
        ("g_base", 0x22, 0x08, "borde 0x8"),  # tras NUMBER solo compilan BLACK, HILIGHT y NOBORDER
        ("g_base", 0x22, 0x50, "borde 0x50"),  # BLACK con NOBORDER
        ("x_base", 0x22, 0x0C, "BOXGROUP FCT 1: borde 0xc"),  # BORDER HILIGHT en un BOXGROUP no compila
        ("x_base", 0x22, 0x10, "BOXGROUP FCT 1: borde 0x10"),
        ("g_base", 0x40, 3, "3 elementos"),
        ("g_base", 0x70, 1, r"\+0x70 0x1"),
        ("g_base", 0x01, 0x03, "bits de icono 0x300 sin ICON"),
        ("g_iconos", 0x70, 1, r"\+0x70 0x1"),  # el fichero del binario (0) y el de +0x70, distintos
        ("x_allowdrag", 0x45, 0x01, "ALLOWDRAG a medias"),
    ]:
        with pytest.raises(descompilador.NoSoportado, match=motivo):
            descompilador.descompilar(_cambia(_grupos()[programa][1], "FCT", 1, desp, valor))


def test_grid_autosize_delante_de_parentgrid():
    # samples loadCustomFonts: `ctr_grid AS GRID … AUTOSIZE` y PARENTGRID; detrás de PARENTGRID no compila (lo cazó la
    # vuelta en cuanto sus grupos se descompilaron)
    f = next((p for p in SAMPLES.iterdir() if p.name.lower() == "loadcustomfonts.omd"), None) if SAMPLES.is_dir() else None
    if f is None:
        pytest.skip(f"sin loadcustomfonts en {SAMPLES}")
    texto = descompilador.descompilar(f.read_bytes())
    grid = texto[texto.index("ctr_grid AS GRID"):]
    grid = grid[:grid.index("BEGIN")]
    assert grid.endswith("\t\t\t\t\tBORDER ETCHED\n\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tPARENTGRID\n\t\t\t\t") and grid.count("AUTOSIZE") == 1
    # ALMAFAC auxiliar: también delante de SCROLL y de TABLE (lo cazó la vuelta en cuanto su On Command se descompiló)
    from hubble import repositorio

    c = PROYECTOS_KIT / "ALMAFAC"
    if (c / "auxiliar.OMD").is_file():
        texto = descompilador.descompilar((c / "auxiliar.OMD").read_bytes(), "almafac", repositorio.Catalogo(c / "almafac.dbs"))
        assert ("\t\t\t\t\tNOBORDER\n\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tSCROLL VERTICAL\n\t\t\t\t\tTABLE provincias\n"
                "\t\t\t\t\tPARENTGRID\n") in texto


COMENTARIOS = KITS / "compilados" / "comentarios-86x64"
_BLOQUE = re.compile(r"\{\*.*?\*\}", re.S)


def test_comentarios_en_modulos_con_clases():
    """Batería comentarios: el sitio de un {* … *} no se guarda, solo su orden entre las cadenas. Sin cadenas alrededor,
    o en la frontera entre dos secciones (k_frontera), cabe en varios sitios con los mismos bytes: va en el primero posible y se avisa. Sin los comentarios, el
    texto es el del fuente (salvo TRUE/FALSE y las líneas en blanco); los comentarios, los mismos y en el mismo orden.
    `@global` lo quita el compilador, pero deja detrás del 0 la cola del texto viejo: con ella vuelve a su sitio."""
    import importlib.util

    if not (COMENTARIOS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {COMENTARIOS}")
    spec = importlib.util.spec_from_file_location("comentarios", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "comentarios.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (COMENTARIOS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in COMENTARIOS.iterdir() if p.suffix.lower() == ".omd"}
    assert len(modulo.P) == 10 and all(huecos[p].lower() in omds for p in modulo.P)

    def sin(t):
        return re.sub(r"\n+", "\n", _BLOQUE.sub("", t)).lower()

    for programa, fuente in modulo.P.items():
        avisos = []
        texto = descompilador.descompilar(omds[huecos[programa].lower()].read_bytes(), None, None, avisos)
        assert sin(texto) == sin(fuente), programa
        assert _BLOQUE.findall(texto) == _BLOQUE.findall(fuente), programa
        sitio = [a for a in avisos if "su sitio no se guarda" in a]
        # con cadenas a los dos lados y sin frontera de sección (k_exacto), el sitio es seguro: sin aviso
        assert len(sitio) == (0 if programa == "k_exacto" else len(_BLOQUE.findall(fuente))), programa
        # « *  El» puede venir de « * @global El» o de «{*@global» + « *  El»: los mismos bytes
        assert [a for a in avisos if a not in sitio] == (["comentario {* El módulo. … }: @global cabe en 2 sitios con los mismos bytes"]
                                                        if programa == "k_global" else []), programa


def test_comentario_al_principio_de_un_code_class():
    # STOCKMDI cust_lab: `{* … *}` delante del primer procedimiento de CODE CLASS CLimits; las cadenas de alrededor
    # fijan su sitio: sin aviso
    from hubble import repositorio

    c = PROYECTOS_KIT / "STOCKMDI"
    f = next((p for p in c.iterdir() if p.name.lower() == "cust_lab.omd"), None) if c.is_dir() else None
    dbs = next((p for p in c.iterdir() if p.suffix.lower() == ".dbs"), None) if c.is_dir() else None
    if f is None or dbs is None:
        pytest.skip(f"sin cust_lab en {c}")
    avisos = []
    texto = descompilador.descompilar(f.read_bytes(), dbs.stem, repositorio.Catalogo(dbs), avisos)
    assert "CODE CLASS CLimits BEGIN\n//{{CODEBEGIN\n{*" in texto and not [a for a in avisos if "comentario" in a]
    assert "selected limits..\n * @global\n *}" in texto  # el @global, de vuelta en su línea


def test_global_por_la_cola_del_texto_viejo():
    con = descompilador._con_global
    assert con("\r\n * Hola\r\n *", b"\r\n * Hola\r\n *\0\0\0\0", []) == "\r\n * Hola\r\n *"  # sin resto: tal cual
    # « * @global\r\n *» sin @global y con la cola vieja (6 bytes) tras el 0
    viejo = "\r\n * Uno.\r\n * @global\r\n *"
    nuevo = viejo.replace("@global", "")
    cuerpo = nuevo.encode() + b"\0" + viejo.encode()[len(nuevo) + 1:] + b"\0"
    avisos = []
    assert con(nuevo, cuerpo, avisos) == viejo and not avisos
    with pytest.raises(descompilador.NoSoportado, match="quitaron 8 bytes"):  # no es lo que mide @global
        con(nuevo, nuevo.encode() + b"\0" + b"abcdefg" + b"\0", [])
    with pytest.raises(descompilador.NoSoportado, match="sin sitio"):  # una cola que no cuadra con ningún sitio
        con(nuevo, nuevo.encode() + b"\0" + b"xxxxxx" + b"\0", [])


# --- 32 bits, con el compilador del kit 8.6 x86 en el laboratorio (hubble-lab:32a, lab/README.md)
PROYECTOS_KIT_32 = KITS / "extraido" / "86x86" / "Cosmos8.6eval" / "projects"
PROPIOS_32 = KITS / "compilados" / "proy32"
SAMPLES_32 = KITS / "compilados" / "samples-86x86"


def _necesita(*rutas):
    for r in rutas:
        if not r.exists():
            pytest.skip(f"sin {r}")


def test_kit_x86_y_compilado_aqui_en_32_bits():
    """Los 16 proyectos del kit x86 (compilados con 7.2.3) y los mismos fuentes compilados aquí en 32 bits dan el mismo
    texto, salvo la POSITION de AUTOSIZE (12, sobre todo ALMAFAC: las medidas de 7.2.3 no son las de 8.6), y lo
    compilado aquí se descompila en los 120 módulos (antes de LIKEVAR con máscara, 115).
    Antes del laboratorio de 32 bits: 19 (sin los mapas de FTA, PAG, FJO, FRC, PCT ni las cadenas de FOB)."""
    from hubble import repositorio

    _necesita(PROYECTOS_KIT_32, PROPIOS_32)
    iguales = ambos = solo_uno = total = descompilados = 0
    for propio in sorted(p for p in PROPIOS_32.iterdir() if p.is_dir()):
        kit = PROYECTOS_KIT_32 / propio.name
        dbs = next((p for p in sorted(kit.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs"), None)
        cat = repositorio.Catalogo(dbs) if dbs else None
        pk = {p.stem.lower(): p for p in kit.iterdir() if p.suffix.lower() == ".omd"}
        for f in sorted(p for p in propio.iterdir() if p.suffix.lower() == ".omd"):
            textos = []
            for g in (pk[f.stem.lower()], f):
                try:
                    textos.append(descompilador.descompilar(g.read_bytes(), dbs.stem if dbs else "repositorio", cat))
                except descompilador.NoSoportado as e:
                    textos.append(f"NoSoportado: {e}")
            total += 1
            descompilados += not textos[1].startswith("NoSoportado")
            if any(x.startswith("NoSoportado") for x in textos):
                solo_uno += textos[0].startswith("NoSoportado") != textos[1].startswith("NoSoportado")
                continue
            sin_pos = [re.sub(r"POSITION \d+ \d+ \d+ \d+", "POSITION", x) for x in textos]
            assert sin_pos[0] == sin_pos[1], f"{propio.name}/{f.stem}"
            iguales += textos[0] == textos[1]
            ambos += 1
    # almafac4 lisalba1 (2026-10-31): en el kit tenía dos punteros dudosos (`Clear` y `pagina`) y aquí no; ahora son del
    # tramo y da el mismo texto (antes solo_uno = 1, ambos 114, iguales 100). LIKEVAR con máscara (2026-10-31): los 5
    # LPROART y LProArtB salen en los dos, con el mismo texto (antes 101, 115, 0, 120, 115)
    assert (iguales, ambos, solo_uno, total, descompilados) == (106, 120, 0, 120, 120)  # 14: POSITION de AUTOSIZE
    # (Events, con el ACTIVEX, entra en 2026-10-31: sus cuatro TEXT con AUTOSIZE)


def test_smallint_escrito_en_32_bits():
    """En 32 bits un smallint escrito y uno por defecto llevan lo mismo tras su valor (0xCC 0xCC y ceros); delante de
    la llamada, el escrito lleva la variante normal (0xF0). EjBmapsdll compilado aquí: `SetColumnChars(1, 200)`."""
    f = KITS / "compilados" / "bmaps-86x86" / "EjBmapsdll.OMD"
    _necesita(f)
    datos = f.read_bytes()
    assert descompilador._Modulo(datos).rec("REF", 174)[:2] == bytes([0x60, 0xF0])
    assert "    de_BuscarDireccion.SetColumnChars(1, 200);\n" in descompilador.descompilar(datos)
    with pytest.raises(descompilador.NoSoportado, match="argumento 200 en 32 bits .*no se sabe si se escribió"):
        descompilador.descompilar(_cambia(datos, "REF", 174, 1, 0x60))


def test_default_del_repositorio_en_32_bits():
    """En 32 bits, el default smallint que el compilador copia del repositorio lleva memoria sin limpiar tras su valor,
    y el escrito, el relleno de MSVC: triple de ALMAFAC tal cual (sin default) y con `default` escrito, igual que el
    del repositorio (1 y 0) y distinto (2 y 7)."""
    tal_cual = PROPIOS_32 / "ALMAFAC" / "triple.OMD"
    escritos = KITS / "compilados" / "defaults-86x86"
    _necesita(tal_cual, escritos)
    texto = descompilador.descompilar(tal_cual.read_bytes(), "almafac")
    assert "\t\t\tcantidad as column\n" in texto and "\t\t\tdescuento as column\n" in texto
    igual = descompilador.descompilar((escritos / "escrito-igual" / "triple.OMD").read_bytes(), "almafac")
    assert "cantidad as column default 1\n" in igual and "descuento as column default 0\n" in igual
    otro = descompilador.descompilar((escritos / "escrito-otro" / "triple.OMD").read_bytes(), "almafac")
    assert "cantidad as column default 2\n" in otro and "descuento as column default 7\n" in otro
    m = descompilador._Modulo(tal_cual.read_bytes())
    k = next(k for k in range(m.s["FOB"].n) if m.texto_ide(m.u32("FOB", k, 0x10)) == "cantidad")
    datos = _cambia(_cambia(tal_cual.read_bytes(), "FOB", k, 0x16, 0), "FOB", k, 0x17, 0)
    with pytest.raises(descompilador.NoSoportado, match="default smallint del FOB .* no se sabe si se escribió"):
        descompilador.descompilar(datos, "almafac")


def test_punteros_dudosos_entre_dos_tramos():
    """El tramo de punteros crece mientras le vale su base y se comía los primeros del siguiente: EjBmapsdll del kit x86
    (`staticitem1` salía `BMapsLockZoom`, que cae donde otro puntero del tramo siguiente: es de ese tramo) y RichText
    en 32 bits (`RichTextGetProperty` salía `edtMultiline`: vale con las dos bases, se queda sin nombre)."""
    kit = PROYECTOS_KIT_32 / "prjbmapsdll" / "EjBmapsdll.OMD"
    rich = SAMPLES_32 / "RichText.OMD"
    _necesita(kit, rich)
    assert descompilador._Modulo(kit.read_bytes()).punteros[0x288F2B4] == "staticitem1"
    m = descompilador._Modulo(rich.read_bytes())
    assert 0x1FB8690 not in m.punteros and m.punteros[0x1FB86A8] == "alignmenttypeold"


# Dudosos entre dos tramos que, con la base del siguiente, caerían donde un puntero seguro del tramo: son del tramo, y
# también los de antes. Los 36 del corpus (17 módulos), cada uno con el nombre que da el .omd de la otra arquitectura
# en el mismo REF (comprobado el 2026-10-31; ninguno distinto).
DUDOSOS_DEL_TRAMO = [
    ("compilados/outlook-86x86/OutlookActiveX.OMD", 0x1CE22B8, "Text"),
    ("compilados/samples-86x86/ChartAndLegendXShift.OMD", 0x1B81A08, "Min"),
    ("compilados/samples-86x86/ChartSample.OMD", 0x1B62CB4, "MessageBox"),
    ("compilados/samples-86x86/ChartSample.OMD", 0x1B62CC4, "NewChartLayer"),
    ("compilados/samples-86x86/EJUNLOADTODOMDOCUMENT.OMD", 0x2B61CC0, "lChType"),
    ("compilados/samples-86x86/EjCompacto.OMD", 0x2B83460, "SetColumnChars"),
    ("compilados/samples-86x86/EjEStilosEnLista.OMD", 0x1D7F888, "pList"),
    ("compilados/samples-86x86/EjEStilosEnLista.OMD", 0x1D7F894, "SetColumnAlign"),
    ("compilados/samples-86x86/EjTCAFITTOTALSWIDTH.OMD", 0x2B6A114, "pList"),
    ("compilados/samples-86x86/EjTCAFITTOTALSWIDTH.OMD", 0x2B6A120, "SetColumnAlign"),
    ("compilados/samples-86x86/EjTCAFITTOTALSWIDTH.OMD", 0x2B6A134, "pNumColumn"),
    ("compilados/samples-86x86/FnTO_CHARDate.OMD", 0x1CB9D18, "AddFormat"),
    ("compilados/samples-86x86/FnTO_CHARDate.OMD", 0x1CB9D28, "AddFormat"),
    ("compilados/samples-86x86/FnTO_CHARDate.OMD", 0x1CB9D38, "AddFormat"),
    ("compilados/samples-86x86/TOCHARCLASEDATE.OMD", 0x1CB95FC, "AddFormat"),
    ("compilados/samples-86x86/TOCHARCLASEDATE.OMD", 0x1CB960C, "AddFormat"),
    ("compilados/samples-86x86/TOCHARCLASEDATE.OMD", 0x1CB961C, "AddFormat"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/ReadReport.OMD", 0x57D47EC, "GetWord"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5834E64, "idxTable"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5834E8C, "GetTreeParent"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5937B8C, "condVal"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5939B1C, "editLstAccepted"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x59C5084, "joinName"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5ABA49C, "Text"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5ABA9FC, "Disabled"),
    ("extraido/86x64/Cosmos8.6x64eval/CosmosData/main.OMD", 0x5ABAA1C, "Disabled"),
    ("extraido/86x64/Cosmos8.6x64eval/dbmanager/main.OMD", 0x287D3A4, "ColPrecission"),
    ("extraido/86x64/Cosmos8.6x64eval/dbmanager/main.OMD", 0x544AF3C, "EOF"),
    ("extraido/86x64/Cosmos8.6x64eval/dbmanager/main.OMD", 0x554A394, "Control"),
    ("extraido/86x64/Cosmos8.6x64eval/dbmanager/main.OMD", 0x554A3A4, "Text"),
    ("extraido/86x64/Cosmos8.6x64eval/projects/LookAndFeel7/personalizado/listalba.OMD", 0x30F2F0C, "curLineas"),
    ("extraido/86x86/Cosmos8.6eval/CosmosData/main.OMD", 0x56DC8AC, "i"),
    ("extraido/86x86/Cosmos8.6eval/dbmanager/main.OMD", 0x56BFF54, "children"),
    ("extraido/86x86/Cosmos8.6eval/projects/almafac4/lisalba1.OMD", 0x2A360EC, "Clear"),
    ("extraido/86x86/Cosmos8.6eval/projects/almafac4/lisalba1.OMD", 0x2A360F8, "pagina"),
    ("extraido/86x86/Cosmos8.6eval/projects/mail/Includes/IncViews.OMD", 0x297EFA0, "Text"),
]


# Y los que solo caerían donde otro dudoso (con la base del tramo) siguen sin nombre: si los dos fueran del siguiente
# tramo no habría choque, así que no se sabe de cuál son (la cadena de `AddFormat` cada 0x10 de los samples TO_CHAR).
SIGUEN_DUDOSOS = [
    ("compilados/samples-86x86/EjTCAFITTOTALSWIDTH.OMD", 0x2B6A144),
    ("compilados/samples-86x86/FnTO_CHARDate.OMD", 0x1CB9D48),
    ("compilados/samples-86x86/TOCHARCLASEDATE.OMD", 0x1CB962C),
]


@pytest.mark.parametrize("ruta", sorted({r for r, _, _ in DUDOSOS_DEL_TRAMO}))
def test_dudosos_que_son_del_tramo(ruta):
    """Un dudoso entre dos tramos que, con la base del siguiente, caería en la posición de IDE de un puntero seguro del
    tramo es del tramo (una aparición en IDE es de un solo puntero), y con él los dudosos de antes (solo hay un corte)."""
    f = KITS / ruta
    _necesita(f)
    m = descompilador._Modulo(f.read_bytes())
    esperados = {p: n for r, p, n in DUDOSOS_DEL_TRAMO if r == ruta}
    assert {p: m.punteros.get(p) for p in esperados} == esperados
    assert not {p for r, p in SIGUEN_DUDOSOS if r == ruta} & set(m.punteros)


def test_almafac4_lisalba1_del_kit_x86():
    """almafac4 lisalba1 del kit x86: `Clear` (REF 352, 0x2A360EC) y `pagina` (REF 127, 0x2A360F8) quedaban dudosos
    entre dos tramos a 0x48 y el método sin nombre daba NoSoportado («nombre sin hueco en IDE en REF 352»). `pagina`,
    con la base del siguiente, caería en la posición 1196 (`acum`), la del puntero seguro 0x2A360B0 (REF 350) del tramo:
    es del tramo, y `Clear`, delante, también. Da el mismo texto que el kit x64 y que el mismo fuente compilado aquí."""
    from hubble import repositorio

    kit = PROYECTOS_KIT_32 / "almafac4"
    propio = PROPIOS_32 / "almafac4" / "lisalba1.OMD"
    x64 = PROYECTOS_KIT / "almafac4" / "lisalba1.OMD"
    _necesita(kit, propio, x64)
    dbs = next(p for p in sorted(kit.iterdir()) if p.is_dir() and p.suffix.lower() == ".dbs")
    cat = repositorio.Catalogo(dbs)
    datos = (kit / "lisalba1.OMD").read_bytes()
    m = descompilador._Modulo(datos)
    assert (m.punteros[0x2A360EC], m.punteros[0x2A360F8], m.punteros[0x2A360B0]) == ("Clear", "pagina", "acum")
    texto = descompilador.descompilar(datos, dbs.stem, cat)
    assert "    Clear;\nend\n" in texto and "            pagina = 1;\n" in texto
    assert texto == descompilador.descompilar(propio.read_bytes(), dbs.stem, cat)
    assert texto == descompilador.descompilar(x64.read_bytes(), dbs.stem, cat)


def test_nombre_por_su_entrada():
    """Un método o una propiedad externos cuyo puntero no da nombre (una dirección estática del compilador, o un
    puntero descartado) lo toman de su entrada de EPR/EOB, la misma que la de los otros nodos con ese miembro: en el
    corpus ninguna entrada da dos nombres. AGENDA mes: `MDY` dentro de `myCursor.Open(MDY(…))` va en 0x14E120."""
    f = PROYECTOS_KIT / "AGENDA" / "mes.OMD"
    _necesita(f)
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    assert struct.unpack_from("<Q", m.rec("REF", 250), 0x18)[0] == 0x14E120
    e = m.refa("REF", 250, 0x10, descompilador.EPR)
    assert m.por_entrada[(descompilador.EPR, e)] == "MDY"
    texto = descompilador.descompilar(datos, "agenda")  # con la clase delante (0x50), como los otros MDY
    assert "myCursor.Open(Module.MDY(mydate.Month, j, mydate.Year)).Fetch.Found" in texto
    # otra entrada de EPR (una sin nombre conocido): ya no se sabe
    otra = next(i for i in range(m.s["EPR"].n) if (descompilador.EPR, i) not in m.por_entrada)
    r = m.rec("REF", 250)
    w = struct.unpack_from("<I", r, 0x10)[0]
    nuevo = bytearray(datos)
    s = m.s["REF"]
    struct.pack_into("<I", nuevo, s.datos + 250 * s.tam_registro + 0x10, (w & 0xFFFF) | (otra << 16))
    nuevo[s.datos + 250 * s.tam_registro + 1] = 0x20  # sin la clase escrita (de otra clase que Module, NoSoportado)
    with pytest.raises(descompilador.NoSoportado, match="nombre sin hueco en IDE en REF 250"):  # ni en IDE (con_externas)
        descompilador.descompilar(bytes(nuevo), "agenda")
    # una entrada con dos nombres no vale: REF 42 (`MDY`, resuelto) a la entrada de `Month` (la 3), que usa REF 252
    nuevo = bytearray(datos)
    struct.pack_into("<I", nuevo, s.datos + 42 * s.tam_registro + 0x10, 0x31B00)
    nuevo[s.datos + 42 * s.tam_registro + 1] = 0x20  # sin la clase escrita
    assert (descompilador.EPR, 3) not in descompilador._Modulo(bytes(nuevo)).por_entrada
    with pytest.raises(descompilador.NoSoportado, match="nombre sin hueco en IDE"):  # ni por su hueco en IDE
        descompilador.descompilar(bytes(nuevo), "agenda")


@pytest.mark.parametrize("carpeta, modulo, variable, avisa", [
    ("kit", "AGENDA/mes", "aux", False),
    ("samples", "loadjvm", "classpathStr", False),
    ("samples", "coscompressextract", "lChExtenxion", True),  # en el fuente, lChFichero: las tres dan los mismos bytes
    ("samples", "fnto_char_number", "lChNumber", True),  # en el fuente, lChNLS
])
def test_char_default_null(carpeta, modulo, variable, avisa):
    """`x as Char default null` no deja nada en el OBJ, solo la cadena 'NULL' en STR, sin que la apunte nada, donde
    se declaró. Se coloca en la Char sin default cuyo nombre cae entre los de los literales de antes y de después."""
    if carpeta == "kit":
        f = PROYECTOS_KIT / f"{modulo}.OMD"
        rep = "agenda"
    else:
        d = KITS / "compilados" / "samples-86x64"
        _necesita(d)
        f = next(p for p in d.iterdir() if p.stem.lower() == modulo and p.suffix.lower() == ".omd")
        rep = "stock"
    _necesita(f)
    avisos = []
    texto = descompilador.descompilar(f.read_bytes(), rep, None, avisos)
    assert re.search(rf"\b{variable} as Char default null\n", texto)
    assert texto.count("default null") == 1
    assert any("default null de" in a for a in avisos) == avisa


@pytest.mark.parametrize("modulo, esta, no_esta", [
    ("utilshtml", 'if colorStr.Trim[1] == "#" then', "Trim[1, 1]"),  # la longitud la añade el compilador, al final
    ("cor", "s1 = s[-5, 5];", None),  # escrita: se queda
    ("if", 'if today.Char[1, 5] between "03-21" and "06-20" then', None),
])
def test_indice_de_un_char(modulo, esta, no_esta):
    """`c[i]` de un Char lleva dos argumentos en el .omd: el segundo (la longitud, 1) lo crea el compilador después del
    operador, como un argumento por defecto; escrito (`s[-5, 5]`), va antes."""
    d = KITS / "compilados" / "samples-86x64"
    _necesita(d)
    f = next(p for p in d.iterdir() if p.stem.lower() == modulo and p.suffix.lower() == ".omd")
    texto = descompilador.descompilar(f.read_bytes(), "stock")
    assert esta in texto and (no_esta is None or no_esta not in texto)


def test_orden_de_likevar_y_autosize():
    """En un EDIT, LIKEVAR va delante de SCROLL (detrás no compila: AGENDA mes); en un BITMAP, AUTOSIZE delante de
    BITMAP FILE (samples almacen). Los cazó la vuelta: «Actual likevar/autosize. Expecting control, end»."""
    mes = PROYECTOS_KIT / "AGENDA" / "mes.OMD"
    d = KITS / "compilados" / "samples-86x64"
    _necesita(mes, d)
    assert "\t\t\t\t\t\tLIKEVAR\n\t\t\t\t\t\tSCROLL VERTICAL\n" in descompilador.descompilar(mes.read_bytes(), "agenda")
    f = next(p for p in d.iterdir() if p.stem.lower() == "almacen" and p.suffix.lower() == ".omd")
    assert '\t\t\t\t\tAUTOSIZE\n\t\t\t\t\tBITMAP FILE "almacen.png"\n' in descompilador.descompilar(f.read_bytes(), "stock")


def test_tab_con_las_paginas_en_el_label():
    """ALMAFAC2 FRMTMPL: `LABEL "Datos 1|Datos 2|...."` sin NUMBER ni TAB LABEL; todas las páginas con 0xFFFF en el
    icono. Si alguna no lo lleva, NoSoportado."""
    from hubble import interfaz

    f = PROYECTOS_KIT / "ALMAFAC2" / "FRMTMPL.OMD"
    _necesita(f)
    datos = f.read_bytes()
    texto = descompilador.descompilar(datos)
    assert '\t\t\t\tCONTROL AS TAB\n\t\t\t\t\tPOSITION 1 6 450 260\n\t\t\t\t\tLABEL "Datos 1|Datos 2|...."\n' \
           '\t\t\t\t\tBORDER DOUBLE FRAME\n\t\t\t\t\tLOWTAB\n' in texto and "NUMBER 3" not in texto
    m = descompilador._Modulo(datos)
    i = Interfaz(m, descompilador.NoSoportado)
    k = next(k for k in range(m.s["FCT"].n) if i.tab_con_label(k))
    binario = i.svl[i.ref(k, 0x68, interfaz.SVL) * 4]
    nuevo = bytearray(datos)
    nuevo[binario.desplazamiento + 12 + 12 + 4 + 2] = 0xFE  # la página 2, con 0xFFFE
    with pytest.raises(descompilador.NoSoportado, match="icono 0xffff0000 de la página 1"):
        descompilador.descompilar(bytes(nuevo))


@pytest.mark.parametrize("bits, texto", [
    (0x0A, "BORDER ETCHED EXTRA 2"), (0x82, "BORDER FRAME EXTRA 2"), (0x03, "BORDER EXTRA 3"), (0x22, "BORDER DOWN EXTRA 2"),
    (0x26, None), (0x12, None),  # DOUBLE DOWN EXTRA 2 y BLACK EXTRA 2: sin probar con el compilador
])
def test_bordes_con_extra(bits, texto):
    """EXTRA n, solo o con DOUBLE, DOWN, FRAME o ETCHED (batería controles.py: 8 de 8; CalcALG calcu3). Lo demás, sin
    probar: NoSoportado."""
    i = object.__new__(Interfaz)
    i.NoSoportado = descompilador.NoSoportado
    if texto is None:
        with pytest.raises(descompilador.NoSoportado, match="borde"):
            i.borde(bits)
    else:
        assert i.borde(bits) == texto


CLASES = KITS / "compilados" / "clases-86x64"


def _esperado_de_clase(fuente: str) -> str:
    """El fuente de la batería clases.py tal como sale: lo que da los mismos bytes escrito de otra forma (comprobado
    con la vuelta) sale de una sola manera."""
    t = re.sub(r"(?m)^\t(?=(PROTECTED |PRIVATE |PUBLIC )?\w+( \w+)* (=|as) )", "    ", fuente)  # CONSTANTS y OBJECTS
    t = re.sub(r"\bPUBLIC ", "", t)  # public es la visibilidad por defecto: no se escribe
    t = re.sub(r"(?m)^(public|protected|private) (\w+)( return|\n)", r"\1 \2()\3", t)
    t = re.sub(r" \((\d+)\)", r"(\1)", t).replace("Decimal(10)", "Decimal(10,0)")
    t = re.sub(r" \((\d+),(\d+)\)", r"(\1,\2)", t)
    return t.replace("    PRIVATE g h as Integer\n", "    PRIVATE g as Integer\n    PRIVATE h as Integer\n").lower()


def test_clases_vuelven_a_su_fuente():
    """Batería de clases que no son formulario: herencia (`B is A begin … end`, solo de una abstracta; `B is A`, con un
    puntero de memoria en +0x40 si A tiene miembros), visibilidad de clases, miembros, objetos y métodos, `X is Decimal
    (32,2)` y sus objetos, constantes Char, Decimal y Boolean, `operator` y `conversor`, `PI`, case de varios valores y
    defaults Char compartidos. `K = null` no se sabe leer (su valor parece basura): NoSoportado."""
    import importlib.util

    if not (CLASES / "manifiesto.tsv").exists():
        pytest.skip(f"sin {CLASES}")
    spec = importlib.util.spec_from_file_location("clases", Path(__file__).resolve().parents[1] / "lab" / "bateria" / "clases.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    huecos = dict(reversed(l.split("\t")) for l in (CLASES / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in CLASES.iterdir() if p.suffix.lower() == ".omd"}
    exactos = 0
    for programa, fuente in modulo.P.items():
        if huecos[programa].lower() not in omds:
            continue
        datos = omds[huecos[programa].lower()].read_bytes()
        if programa == "k_null":
            with pytest.raises(descompilador.NoSoportado, match="clase 0x0"):
                descompilador.descompilar(datos)
            continue
        if programa == "en_traza":  # `red.Trace` con el método sin puntero: sin paréntesis se lee como una conversión
            with pytest.raises(descompilador.NoSoportado, match="nombre sin hueco"):  # y Trace no es una clase
                descompilador.descompilar(datos)
            continue
        if programa in ("en_argumento", "al_var"):  # `objects begin end` vacío y VAR de un ArgList: los mismos bytes
            fuente = fuente.replace("objects begin\nend\n", "").replace("VAR a as l", "a as l")
        # familia «codigo»: FUNCTION es opcional (manual refer ref00029) y VAR en un Struct, el de siempre: los mismos bytes
        fuente = re.sub(r"\b(function|FUNCTION) ", "", fuente).replace("VAR o as A", "o as A").replace("PUBLIC DLL", "public DLL")
        # un dll del módulo sale con su línea en blanco detrás, como los demás procedimientos (los mismos bytes)
        fuente = re.sub(r"(?m)^((public|private) (self |SELF )?(dll|DLL|javaclass) .*\n)(?=main)", r"\1\n", fuente)
        if programa.startswith("h_"):  # Time: `default 1` es una hora; `default null` no se guarda
            fuente = fuente.replace("default 1\n", 'default "01:00:00"\n').replace(" default null", "")
        if programa.startswith("sa_"):  # `S is Struct as tabla`: con el repositorio; a mano, los mismos bytes
            fuente = fuente.replace("\tS is Struct begin\n\t\tstate as states.state\n\t\tsname as states.sname\n\tend\n",
                                    "\tS is Struct as states\n")
            esperado = _esperado_de_clase(fuente).replace("\n    s is struct as ", "\n\ts is struct as ")  # no es un objeto
            assert descompilador.descompilar(datos, "stock", _stock()).lower() == esperado, programa
            exactos += 1
            continue
        assert descompilador.descompilar(datos).lower() == _esperado_de_clase(fuente), programa
        exactos += 1
    assert exactos == 148  # + 29 de la familia «codigo» (SELF de dll y javaclass, function, VAR, grafías)
    # y 6 de parámetros `a as ArgList of X` (alp_; of Char(10), of Decimal(10,2), sin of y uno local no compilan)


NIF = PROYECTOS_KIT / "NIF"
CALC = PROYECTOS_KIT / "CalcALG"


@pytest.mark.parametrize(("ruta", "texto"), [
    ("NIF/absnif.OMD", '    LETRAS_NIF = "TRWAGMYFPDXBNJZSQVHLCKE"\n'),          # constante Char
    ("NIF/absnif.OMD", "\tBaseNif is abstract Struct\n"),
    ("NIF/absnif.OMD", "protected Valida(c as Char) return Char\n"),             # 0x25: protected (antes salía private)
    ("NIF/absnif.OMD", "public operator = (c as Char)\n"),                       # PRO de tipo 2, el operador en +0x28
    ("NIF/absnif.OMD", "public conversor Integer\n"),                            # PRO de tipo 3, la clase en +0x20
    ("NIF/Nif_1.OMD", "\tPROTECTED Nif1 is BaseNif begin\n\t\tvalor as Char\n\tend\n"),
    ("NIF/Nif_1.OMD", "    return valor[1, LONGITUD_NIF - 1];\n"),             # constante del módulo incluido
    ("NIF/Nif_1.OMD", "    return valor[LONGITUD_NIF];\n"),
    ("NIF/sample02.OMD", "\tPROTECTED Nif11 is Nif1\n"),                         # +0x40: puntero de memoria
    ("CalcALG/abseval.OMD", "\tMaxDecimal is Decimal(32,2)\n"),
    ("CalcALG/ScEval.OMD", "\tSciEval is AriEval\n"),
    ("CalcALG/ScEval.OMD", "    if not Eof and type == TOKEN_IS_UKN then\n"),     # dos constantes incluidas distintas
    ("CalcALG/ScEval.OMD", "            type = TOKEN_IS_ID;\n"),
    ("CalcALG/ScEval.OMD", "    d as MaxDecimal\n"),                             # el (32,2) del OBJ es el de la clase
    ("CalcALG/ScEval.OMD", "                if d1 > 0.0 then\n"),               # un decimal entero, con su punto
    ("CalcALG/AbsAriEval.OMD", '    str1 str2 str3 as Char default ""\n'),     # una sola cadena en STR
    ("CalcALG/calcu3.OMD", '        case "=", "Enter":\n'),                     # antes salía `case "=":`
    ("CalcALG/calcu3.OMD", "display1.Text + PI.Char();\n"),                      # constante predefinida
])
def test_clases_del_kit(ruta, texto):
    f = PROYECTOS_KIT / ruta
    _necesita(f)
    assert texto in descompilador.descompilar(f.read_bytes())


def test_constante_incluida_sin_hueco():
    """Una constante de un módulo incluido va en el hueco de IDE entre los nombres de antes y de después; si el hueco no
    deja un nombre libre por constante, NoSoportado. En Nif_1, el `1` de `valor[1, LONGITUD_NIF - 1]` (REF 3) hecho
    constante incluida: dos en un hueco con un solo nombre libre."""
    f = NIF / "Nif_1.OMD"
    _necesita(f)
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    assert m.rec("REF", 3)[:2] == bytes([descompilador.LIT_SMALLINT, 0xF0]) and m.rec("REF", 2)[1] == descompilador.EXTERNA
    with pytest.raises(descompilador.NoSoportado, match="nombre sin hueco en IDE en REF 3"):  # el 2 se lleva el nombre
        descompilador.descompilar(_cambia(datos, "REF", 3, 1, descompilador.EXTERNA))


def test_constante_sin_nombre():
    """Un literal de constante (variante 0x50) que no es ninguna del módulo ni PI: NoSoportado (antes salía su valor)."""
    from hubble import contenedor

    f = CALC / "calcu3.OMD"
    _necesita(f)
    datos = f.read_bytes()
    s = contenedor.leer(datos).seccion("DEC")
    nuevo = bytearray(datos)
    assert nuevo[s.datos + 6] == 3
    nuevo[s.datos + 6] = 4  # la primera cifra de PI (3 → 4)
    with pytest.raises(descompilador.NoSoportado, match="constante sin nombre"):
        descompilador.descompilar(bytes(nuevo))


def test_objeto_de_una_clase_con_otros_parametros():
    """`g as A`, con `A is Decimal (32,2)`: el OBJ lleva (32,2), los de la clase. Con otros, NoSoportado (`g as A (10,2)`
    no compila)."""
    f = next((p for p in CLASES.iterdir() if p.stem.lower() == "days" and p.suffix.lower() == ".omd"), None) \
        if CLASES.is_dir() else None
    if f is None:
        pytest.skip(f"sin {CLASES}")
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    k = next(k for k in range(m.s["OBJ"].n) if m.nombre_obj(k) == "g")
    assert "    g as A\n" in descompilador.descompilar(datos) and m.rec("OBJ", k)[0x30] == 32
    with pytest.raises(descompilador.NoSoportado, match="g as A con"):
        descompilador.descompilar(_cambia(datos, "OBJ", k, 0x30, 10))


def test_puntero_de_clase_derivada():
    """`SciEval is AriEval`: +0x40 lleva un puntero de memoria (no una referencia a sus miembros). Un valor pequeño no
    es un puntero: NoSoportado."""
    f = CALC / "ScEval.OMD"
    _necesita(f)
    datos = f.read_bytes()
    assert "\tSciEval is AriEval\n" in descompilador.descompilar(datos)
    with pytest.raises(descompilador.NoSoportado, match="Struct SciEval"):
        descompilador.descompilar(_cambia_u32(datos, "CLA", 1, 0x40, 0x1234))


def test_visibilidad_de_un_local():
    """Las variables locales y los parámetros llevan siempre private (3); otra visibilidad, NoSoportado."""
    f = NIF / "absnif.OMD"
    _necesita(f)
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    k = next(k for k in range(m.s["OBJ"].n) if m.rec("OBJ", k)[0] & 0x0F == 2)
    assert m.rec("OBJ", k)[3] == 0xB4
    with pytest.raises(descompilador.NoSoportado, match="visibilidad 1 en un OBJ de tipo 2"):
        descompilador.descompilar(_cambia(datos, "OBJ", k, 3, 0x94))


def test_case_de_varios_valores_con_otro_operador():
    """`case "=", "Enter":` encadena una condición «==» por valor; si una no lo es, NoSoportado (antes se perdía)."""
    f = CALC / "calcu3.OMD"
    _necesita(f)
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    # el «==» de la segunda condición del primer case de varios valores (REF 34, token 31)
    assert struct.unpack_from("<Q", m.rec("REF", 34), 0x18)[0] == 31
    with pytest.raises(descompilador.NoSoportado, match="case de varios valores"):
        descompilador.descompilar(_cambia(datos, "REF", 34, 0x18, 20))


OUTLOOK = PROYECTOS_KIT / "OutlookActiveX"
MAIL = PROYECTOS_KIT / "mail"


@pytest.mark.parametrize(("ruta", "texto"), [
    ("OutlookActiveX/INC_OUTLOOK.OMD", '    OutlookApplication.Invoke("CreateItem", Item, 0.integer);\n'),  # nombre en IDE
    ("OutlookActiveX/INC_OUTLOOK.OMD", 'pListContactEmail1Address.GetWord("|", i));\n'),  # la conversión del compilador
    ("OutlookActiveX/OutlookActiveX.OMD", "\t\t\t\tCONTROL AS SPLIT\n\t\t\t\t\tPOSITION 320 0 7 784\n\t\t\t\t\tATTACH TOP BOTTOM\n"
                                          "\t\t\t\t\tBORDER DOUBLE\n\t\t\t\t\tVERTICAL\n"),
    ("OutlookActiveX/OutlookActiveX.OMD", "    tab_ctr.SetTabVerticalPages(true, 0);\n"),  # tramo recortado por su extremo
    ("mail/Includes/IncEncoders.OMD", "\tcBinTable is Array [256] of Char(8)\n"),
    ("mail/Includes/IncViews.OMD", "\t\t\tvTmCrono as Time default 0\n"),
    ("mail/Includes/IncSMTPClient.OMD", ", pChFiles as Char default null) return Boolean\n"),   # su 'NULL', usada
    ("mail/PROGRAMS/SendModule.OMD", "    pChFrom as Char default null\n"),                     # cabe en 6: la primera
])
def test_outlook_y_mail(ruta, texto):
    f = PROYECTOS_KIT / ruta
    _necesita(f)
    assert texto in descompilador.descompilar(f.read_bytes())


def test_conversion_sin_nombre_en_ide():
    """INC_OUTLOOK (compilador 7.42): el método `integer` de Numeric lleva una dirección estática del compilador,
    escrito (`0.integer`) o puesto por el compilador (`GetWord("|", i)`). El escrito deja su nombre en IDE; si se quita
    esa entrada de IDE (se hace declaración, como un nombre de procedimiento), ya no se escribe."""
    f = OUTLOOK / "INC_OUTLOOK.OMD"
    _necesita(f)
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    escritos = sorted(p for p, t in m.ide.items() if t == "integer")
    assert len(escritos) == 8 and not set(escritos) & (m.declarados | set(m.pos_ide.values()))
    texto = descompilador.descompilar(datos)
    assert texto.count(".integer") == 8 and 'GetWord("|", i)' in texto
    # El PRO 0 nombrado con la posición del primer `integer`: deja de estar libre, y su `0.integer` ya no cuadra
    k = next(k for k in range(m.s["PRO"].n) if m.nombre_pro(k) == "CreateItemSendMail")
    nuevo = _cambia_u32(datos, "PRO", k, 0x28, (escritos[0] // 4) << 16 | 0x0100)
    assert "0.integer" not in descompilador.descompilar(nuevo)


def test_tramo_recortado_sin_base_unica():
    """ActiveX Word: el tramo falso de 2 punteros choca entero con el de 32. Si el segundo (`saveFileName`, REF 207) se
    lleva a otra aparición libre de su nombre (IDE 1672), solo choca el primero, y el que queda cabe en dos bases (las
    dos apariciones libres de `saveFileName`): no se recorta, se descarta."""
    f = PROYECTOS_KIT / "ActiveX" / "Word.OMD"
    _necesita(f)
    datos = f.read_bytes()
    m = descompilador._Modulo(datos)
    assert struct.unpack_from("<Q", m.rec("REF", 207), 0x18)[0] == 0x14E500 and m.ide[1672] == "saveFileName"
    nuevo = bytearray(datos)
    s = m.s["REF"]
    struct.pack_into("<Q", nuevo, s.datos + 207 * s.tam_registro + 0x18, 0x14E470 - 1392 + 1672)
    m2 = descompilador._Modulo(bytes(nuevo))
    assert 0x14E470 not in m2.punteros and 0x14E470 - 1392 + 1672 not in m2.punteros


def test_conversion_con_el_nombre_de_su_entrada():
    """Una entrada de EPR, un nombre: si el `integer` libre de un procedimiento de INC_OUTLOOK se llamara `char` (en
    memoria), su `n.integer` no se lo queda (la entrada ya se llama `integer`), sobra un nombre libre y NoSoportado."""
    f = OUTLOOK / "INC_OUTLOOK.OMD"
    _necesita(f)
    m = descompilador._Modulo(f.read_bytes())
    ultimo = max(p for p, t in m.ide.items() if t == "integer")
    m.ide[ultimo] = "char"
    with pytest.raises(descompilador.NoSoportado, match="nombre sin hueco en IDE"):
        descompilador._Escritor(m).modulo()


def test_conversion_solo_con_nombre_de_clase():
    """samples ejactivexopenofficecalc: la conversión implícita de `"=C" + (fila + 1)` no se queda el `fila` libre de su
    hueco (una conversión se llama como una clase)."""
    assert '"=C" + (fila + 1) + "-D" + (fila + 1));\n' in _sample("ejactivexopenofficecalc")


def test_metodo_con_otra_clase_escrita():
    """samples activexexcel: `Module.Name` es un método de Object (su entrada de EPR), y `Object.Name` no compila; con
    la clase escrita solo se ha visto Module: con otra, NoSoportado."""
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "activexexcel").read_bytes()
    with pytest.raises(descompilador.NoSoportado, match="método de Object con la clase escrita"):
        descompilador.descompilar(datos)


def test_tramo_recortado_por_su_extremo():
    """OutlookActiveX: el tramo del `On Open` (21 punteros) se alargó con un puntero que cae en el `AttachFile` de
    otro tramo de 39. Se quita ese, que se queda sin nombre de puntero (lo toma de su entrada, `Text`), y el resto vale."""
    f = OUTLOOK / "OutlookActiveX.OMD"
    _necesita(f)
    m = descompilador._Modulo(f.read_bytes())
    assert m.punteros[0x2F5AACC] == "SetTabVerticalPages" and 0x2F5AD24 not in m.punteros
    assert m.punteros[0x2F5D2A4] == "AttachFile"
    k = next(k for k in range(m.s["REF"].n) if struct.unpack_from("<Q", m.rec("REF", k), 0x18)[0] == 0x2F5AD24)
    assert m.por_entrada[(descompilador.EOB, m.refa("REF", k, 0x10, descompilador.EOB))] == "Text"


@pytest.mark.parametrize(("modulo", "linea"), [
    ("dbl", '    Miform.milist.AddString("a1");\n'),                          # objeto.control (nodo 0x01 0x01)
    ("fnnvl", '    ofrm.txt_1.Text = "SELECT customer," + " company "'),       # objeto.control.propiedad
    ("modu", "begin\n    Module.Clear;\nend"),                                 # procedimiento del módulo desde una clase
    ("cosregexpdll", "    regexp_1 = Module.CosNewRegExpr(strExpresionRegular, strBuscar, false, true);\n"),  # dll
    ("cosmosjava", "\nOn Error\nbegin"),                                       # evento del módulo (PRO de tipo 0x0C)
    ("sndmsg", "\nOn ExMessage (wparam as Integer, lparam as Integer)\nbegin"),  # evento de formulario 24
    ("coshttpdllpostcommand", "\t\tPOSITION 119 13 112 22\n\t\t\t\t\t\tDISABLED\n\t\t\t\t\t\tFOREGROUND RGB 0 0 255\n"),
    ("newlook", '\t\tLABEL "Botón Transparente"\n\t\t\t\t\t\t\tNOBORDER\n\t\t\t\t\t\t\tICON 15 FILE "listaiconosgif32" CENTER\n'),
    ("getsystemtymeutc", "    nowTime = current;\n"),                     # palabra reservada de DateTime
    ("tree1", "\t\t\t\t\tPANELTYPE MESSAGE\n"),
    ("menu", '    mm.a.Add("Hello2", null, "New2");\n'),                    # opción de menú como miembro (0xF1 0x00)
    ("richtextprintex", "\t\tBORDER ETCHED\n\t\t\t\t\tRICHTEXTEDIT\n\t\t\t\t\tWRAP\n"),
    ("richtext", '\t\t\tLABEL "Nº Romanos"\n\t\t\tNOLABEL\n'),                  # NOLABEL del formulario
    ("newlook", '\t\tLABEL "Aceptar"\n\t\t\t\t\t\t\tBORDER HILIGHT\n\t\t\t\t\t\t\tDEFPUSH\n'),
    ("transparent", "\t\tCONTROL bar1 AS BAR\n\t\t\t\t\tPOSITION 0 495 805 32\n\t\t\t\t\tATTACH LEFT RIGHT BOTTOM\n"),
])
def test_controles_de_objeto_y_eventos_de_samples(modulo, linea):
    assert linea in _sample(modulo)


def test_miembro_que_no_es_un_control():
    """`objeto.control` (0x01 0x01) solo con un control de variante 0x21 en +0x18: con otro nodo, NoSoportado."""
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "dbl").read_bytes()
    m = descompilador._Modulo(datos)
    k = m.refa("REF", 5, 0x18, descompilador.REF)
    assert m.rec("REF", 5)[:2] == bytes([1, 1]) and m.rec("REF", k)[:2] == bytes([0, 0x21])
    with pytest.raises(descompilador.NoSoportado, match="que no es un control"):  # el control, como del formulario
        descompilador.descompilar(_cambia_u32(datos, "REF", k, 0, m.u32("REF", k, 0) & ~0xFF00 | 0x3100))


def test_noborder_de_boton_con_borde():
    """NOBORDER de un BUTTON (0x40 en +0x20) con un BORDER de los de siempre: NoSoportado."""
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    from hubble import interfaz
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "newlook").read_bytes()
    m = descompilador._Modulo(datos)
    assert m.u32("FCT", 13, 0x20) >> 16 == interfaz.SIN_BORDE_BOTON
    with pytest.raises(descompilador.NoSoportado, match="NOBORDER de botón"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 13, 0, m.u32("FCT", 13, 0) | interfaz.DOWN))


def test_evento_del_modulo_desconocido():
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "cosmosjava").read_bytes()
    with pytest.raises(descompilador.NoSoportado, match="evento del módulo 37"):
        descompilador.descompilar(_cambia_u32(datos, "PRO", 9, 0x28, 37))


@pytest.mark.parametrize(("modulo", "linea"), [
    ("arg", "\taChar is ArgList of Char\n"),
    ("arg", "    aCharArgList.Size.Trace;\n"),
    ("enum", "\tcolor is Enum of [red yellow green]\n\topen is EnumSet of [read write append]\n"),
    ("enum", "    (foot + hands).Trace;\n    Monday.Trace;\n    d = Monday;\n"),   # valores de EnumSet (máscara) y de Enum
    ("enum", "    t = t + head;\n"),
])
def test_arglist_y_enum_de_samples(modulo, linea):
    assert linea in _sample(modulo)


def test_valor_de_enumset_de_dos_bits():
    """Un valor de EnumSet es una máscara de un solo bit (1 << su índice): con dos, NoSoportado."""
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "enum").read_bytes()
    m = descompilador._Modulo(datos)
    assert m.rec("REF", 0)[:2] == descompilador.VALOR_ENUMSET and m.u32("REF", 0, 0x18) == 2
    with pytest.raises(descompilador.NoSoportado, match="valor 0x6 de la clase"):
        descompilador.descompilar(_cambia_u32(datos, "REF", 0, 0x18, 6))


def test_enum_con_otro_numero_de_valores():
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "enum").read_bytes()
    with pytest.raises(descompilador.NoSoportado, match="Enum CLA 1 con valores"):
        descompilador.descompilar(_cambia_u32(datos, "CLA", 1, 0x30, 4))


@pytest.mark.parametrize(("modulo", "linea"), [
    ("boolop", "\t\t\t\tAUTOSIZE\n\t\t\t\tREPEAT 9\n\t\t\t\tFIXED\n"),                     # GROUP: AUTOSIZE y FIXED
    ("ejprintchart", "\t\t\t\tNOLABEL\n\t\t\t\tBORDER DOWNSHADOW ALL\n\t\t\t\tSTRETCH\n"),  # BITMAP de página
    ("ejprintchart", "\t\t\t\tBACKGROUND COLOR transparent\n\t\t\t\tBOLD\n\t\t\t\tBORDER ALL\n\t\t\t\tGRID"),  # GROUP BOLD
    ("ejreportprov", '\t\tTAGS "PRUEBA DE TEXTO VERTICAL HACIA LA IZQUIERDA EN LISTADO"\n\t\t\t\tVERTICALTEXTLEFT\n'),
    ("ejreportprov", "\t\t\t\tCONTROL AS CHECK\n"),                                              # CHECK de página
    ("openprinterpdf", "\t\t\t\t\tNOLABEL\n\t\t\t\t\tCURRENT PAGE 2\n"),                          # BOX con CURRENT PAGE
    ("impresionpdfmulticharset", '\t\t\t\tFONT "FangSong" 12 CHARSET Gb2312\n'),
    ("impresionpdfmulticharset", "\t\t\t\tMULTILINE\n\t\t\t\tWRAP\n"),                          # TEXT de página
    ("listadocaja", "AS BOXGROUP\n\t\t\t\tPOSITION 33 213 533 526\n\t\t\t\tNOLABEL\n\t\t\t\tNUMBER 1 COLUMNS 1\n"
                    "\t\t\t\tBORDER ALL\n\t\t\t\t\tBOX\n\t\tEND\n"),                     # BOXGROUP de página
    ("setboxicofile", '\t\t\t\t\t\tAUTOSIZE\n\t\t\t\t\t\tICON FILE "_MBSTDBMP_"\n\t\t\t\t\t\tSHOW 8 LINES\n'),  # DROPLIST
    ("setboxicofile", '\t\t\t\t\t\tICON FILE "_MBSTDBMP_"\n\t\t\t\t\t\tDATATYPE CHAR\n'),                 # DROPEDIT
    ("drag1", '\t\t\t\t\t\tNOBORDER\n\t\t\t\t\t\tDATATYPE CHAR FORMAT "AAAAAAAAAAA"\n'),
    ("drag1", "On Dragover pcolor (fromCtr as SimpleFormControl, fromItem as Integer, VAR result as Integer)\n"),
    ("ejlookupcolumns", "\t\t\tstate as states.state\n\t\t\tstatename as states.sname\n\t\tend\n"),  # sin join
])
def test_controles_de_pagina_de_samples(modulo, linea):
    assert linea in _sample_stock(modulo)


def _sample_stock(nombre: str, datos: bytes | None = None) -> str:
    """Un sample descompilado con el catálogo de stock (para los objetos del tipo de una columna)."""
    from hubble import repositorio

    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    if datos is None:
        datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == nombre).read_bytes()
    dbs = KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "samples" / "stock.dbs"
    return descompilador.descompilar(datos, "stock", repositorio.Catalogo(dbs))


def test_group_fixed_con_bycols():
    """FIXED (sin el 0x40000000 de +0x44) con BYCOLS no compila: NoSoportado."""
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    from hubble import interfaz
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "boolop").read_bytes()
    m = descompilador._Modulo(datos)
    assert not m.u32("PCT", 1, 0x44) & interfaz.GRUPO_44
    with pytest.raises(descompilador.NoSoportado, match="FIXED con BYCOLS"):
        descompilador.descompilar(_cambia_u32(datos, "PCT", 1, 0, m.u32("PCT", 1, 0) | interfaz.GRUPO_BYCOLS))


def test_boxgroup_de_pagina_con_variable():
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "listadocaja").read_bytes()
    with pytest.raises(descompilador.NoSoportado, match="BOXGROUP PCT 4 con VARIABLE"):
        _sample_stock("listadocaja", _cambia_u32(datos, "PCT", 4, 0x78, 0x1100))


def test_boxgroup_de_pagina_dos_box_sin_label():
    """Un BOX solo y sin etiqueta no deja LABEL; con dos (NOLABEL, `BOX` y `BOX`) sí, y el texto «|». Sin LABEL y
    con dos, no se ha visto: NoSoportado."""
    if not (PAGINAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {PAGINAS}")
    from hubble import interfaz
    huecos = dict(reversed(l.split("\t")) for l in (PAGINAS / "manifiesto.tsv").read_text().splitlines())
    hueco = huecos["pxg_nolabel_number_2_columns_1__box__box"].lower()
    datos = next(p for p in PAGINAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == hueco).read_bytes()
    m = descompilador._Modulo(datos)
    assert m.u32("PCT", 1, 0) & interfaz.LABEL and m.u32("PCT", 1, 0x40) == 2
    datos = _cambia_u32(_cambia_u32(datos, "PCT", 1, 0, m.u32("PCT", 1, 0) & ~interfaz.LABEL), "PCT", 1, 0x48, 0)
    with pytest.raises(descompilador.NoSoportado, match="BOXGROUP PCT 1: 2 elementos"):
        descompilador.descompilar(datos)



def _sample_datos(nombre: str) -> bytes:
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    return next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == nombre).read_bytes()


def test_format_con_otro_tipo():
    """FORMAT solo compila con DATATYPE CHAR (con SMALLINT, DATE o DECIMAL, no): con otro, NoSoportado."""
    datos = _sample_datos("drag1")
    m = descompilador._Modulo(datos)
    assert m.u32("FCT", 3, 0xA0) and m.u32("FCT", 3, 0x20) >> 16 == 0
    with pytest.raises(descompilador.NoSoportado, match="FORMAT con DATATYPE SMALLINT"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 3, 0x20, m.u32("FCT", 3, 0x20) | 0x10000))


def test_columna_de_otra_tabla_con_default():
    datos = _sample_datos("ejlookupcolumns")
    m = descompilador._Modulo(datos)
    assert m.texto_ide(m.u32("FOB", 11, 0x10)) == "state" and not m.u32("FOB", 11, 0x78)
    with pytest.raises(descompilador.NoSoportado, match="columna FOB 11 de otra tabla"):
        _sample_stock("ejlookupcolumns", _cambia_u32(datos, "FOB", 11, 0, m.u32("FOB", 11, 0) | 0x200000))


def test_struct_a_mano_no_es_de_tabla():
    """Un Struct con los nombres de las columnas de una tabla, pero con un miembro de tipo escrito a mano (escala 0, no
    −1), no es `Struct as tabla`."""
    if not (CLASES / "manifiesto.tsv").exists():
        pytest.skip(f"sin {CLASES}")
    huecos = dict(reversed(l.split("\t")) for l in (CLASES / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in CLASES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["sa_states"].lower()).read_bytes()
    m = descompilador._Modulo(datos)
    assert m.nombre_obj(0) == "state" and m.u32("OBJ", 0, 0x30) >> 16 == 0xFFFF
    texto = descompilador.descompilar(_cambia_u32(datos, "OBJ", 0, 0x30, m.u32("OBJ", 0, 0x30) & 0xFFFF), "stock", _stock())
    assert "\tS is Struct begin\n\t\tstate as Char(2)\n" in texto



def test_struct_de_una_tabla_con_mas_columnas():
    """Si la tabla tiene más columnas que el Struct, no es `Struct as tabla` (le faltarían miembros)."""
    from hubble import repositorio

    if not (CLASES / "manifiesto.tsv").exists():
        pytest.skip(f"sin {CLASES}")
    huecos = dict(reversed(l.split("\t")) for l in (CLASES / "manifiesto.tsv").read_text().splitlines())
    datos = next(p for p in CLASES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["sa_states"].lower()).read_bytes()
    catalogo = repositorio.Catalogo(KITS / "extraido" / "86x64" / "Cosmos8.6x64eval" / "samples" / "stock.dbs")
    i = max(n for n, c in enumerate(catalogo.columnas) if c.tabla == "states")
    catalogo.columnas.insert(i + 1, repositorio.Columna("states", "otra", 0, 5, False))
    assert "\tS is Struct begin\n" in descompilador.descompilar(datos, "stock", catalogo)


def test_current_page_con_attach():
    if not SAMPLES.is_dir():
        pytest.skip(f"sin {SAMPLES}")
    from hubble import interfaz
    datos = next(p for p in SAMPLES.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "openprinterpdf").read_bytes()
    m = descompilador._Modulo(datos)
    assert m.u32("PCT", 7, 0x60) == 0x10000
    with pytest.raises(descompilador.NoSoportado, match="CURRENT PAGE con ATTACH"):
        _sample_stock("openprinterpdf", _cambia_u32(datos, "PCT", 7, 0x44, m.u32("PCT", 7, 0x44) | interfaz.A_TOP))


# --- familia «ventana» (2026-10-31): THINFRAME, THINCAPTION, CHECKMETHOD y FRAMEAUTOSIZE
def test_ventana_de_la_bateria(fuentes_formularios):
    """Variantes vw_ y vw2_ de formularios.py: las que compilan dan su fuente. No exactas (mismos bytes): LIKEVAR sin
    VARIABLE, que el compilador no guarda, y `v as char` con LIKEVAR (sale `Char` y el DATATYPE de la variable)."""
    if not (FORMULARIOS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {FORMULARIOS}")
    huecos = dict(reversed(l.split("\t")) for l in (FORMULARIOS / "manifiesto.tsv").read_text().splitlines())
    omds = {p.stem.lower(): p for p in FORMULARIOS.iterdir() if p.suffix.lower() == ".omd"}
    exactos, compilan = 0, 0
    for programa, fuente in fuentes_formularios.items():
        if not programa.startswith(("vw_", "vw2_")) or huecos[programa].lower() not in omds:
            continue
        compilan += 1
        texto = descompilador.descompilar(omds[huecos[programa].lower()].read_bytes())
        if programa in ("vw_checkmethod_edit_variable", "vw2_cm_edit_likevar_tras"):
            assert "\t\t\t\tCHECKMETHOD Chequear\n" in texto
            continue
        assert texto.lower() == fuente.lower(), programa
        exactos += 1
    assert (compilan, exactos) == (42, 40)


@pytest.mark.parametrize(("programa", "trozo"), [
    ("vw_thinframe", "\t\t\tPOSITION 0 0 200 100\n\t\t\tTHINFRAME\n\t\tBEGIN"),
    ("vw_label__hola__thinframe", '\t\t\tLABEL "Hola"\n\t\t\tTHINFRAME\n'),
    ("vw2_nolabel_thinframe", "\t\t\tNOLABEL\n\t\t\tTHINFRAME\n"),
    ("vw_thinframe_maximize", "\t\t\tTHINFRAME\n\t\t\tMAXIMIZE\n"),
    ("vw_thinframe_thincaption", "\t\t\tTHINFRAME\n\t\t\tTHINCAPTION\n"),
    ("vw_noborder_sysmenu", "\t\t\tNOBORDER\n\t\t\tSYSMENU\n"),  # NOBORDER, delante: detrás de SYSMENU no compila
    ("vw2_noborder_allowdrop", "\t\t\tNOBORDER\n\t\t\tALLOWDROP\n"),
    ("vw_noborder_thincaption", "\t\t\tNOBORDER\n\t\t\tTHINCAPTION\n"),
    ("vw_minimize_thincaption", "\t\t\tMINIMIZE\n\t\t\tTHINCAPTION\n"),
    ("vw_thincaption_sysmenu", "\t\t\tTHINCAPTION\n\t\t\tSYSMENU\n"),
    ("vw2_thincaption_allowdrop", "\t\t\tTHINCAPTION\n\t\t\tALLOWDROP\n"),
    ("vw_checkmethod_otro", "\t\t\t\tDATATYPE CHAR\n\t\t\t\tCHECKMETHOD Otro\n"),
    ("vw_checkmethod_readonly", "\t\t\t\tREADONLY\n\t\t\t\tCHECKMETHOD Chequear\n"),
    ("vw_checkmethod_picker", "\t\t\t\tDATETIMEPICKER\n\t\t\t\tCHECKMETHOD Chequear\n"),
    ("vw2_cm_dropedit_show", "\t\t\t\tSHOW 3 LINES\n\t\t\t\tCHECKMETHOD Chequear\n"),
    ("vw_checkmethod_dropedit_readonly", "\t\t\t\tREADONLY\n\t\t\t\tCHECKMETHOD Chequear\n"),
    ("vw_checkmethod_dos_edits", "\t\t\t\tCHECKMETHOD Otro\n"),
])
def test_ventana_por_su_linea(programa, trozo):
    assert trozo in descompilador.descompilar(_formulario(programa))


@pytest.mark.parametrize(("bits", "motivo"), [
    (0x80000044, "borde del formulario FCT 0: 0x44"),  # DOUBLE y NOBORDER
    (0x80000200, "borde del formulario FCT 0: 0x200"),  # RESIZING sin DOUBLE
    (0x80000240, "borde del formulario FCT 0: 0x240"),  # NOBORDER con RESIZING no compila
    (0x80000002, "bits 0x2 sin descifrar en FCT 0"),  # solo 0x1 es del formulario (en un control, EXTRA n)
])
def test_borde_del_formulario_no_visto(bits, motivo):
    datos = _formulario("vw_thinframe")
    with pytest.raises(descompilador.NoSoportado, match=re.escape(motivo)):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 0, 0, bits))


def test_formulario_sin_double_es_thinframe():
    """Antes, a un formulario sin DOUBLE se le escribía NOBORDER aunque no tuviera el 0x40: era THINFRAME."""
    m = descompilador._Modulo(_formulario("vw_thinframe"))
    assert m.u32("FCT", 0, 0) == 0x80000000
    assert m.u32("FCT", 0, 0) == descompilador._Modulo(_formulario("f_base")).u32("FCT", 0, 0) & ~0x04
    assert "NOBORDER" not in descompilador.descompilar(_formulario("vw_thinframe"))
    assert "\t\t\tNOBORDER\n" in descompilador.descompilar(_formulario("f_noborder"))


def test_checkmethod_que_no_es_un_nombre():
    datos = _formulario("vw_checkmethod_sin_metodo")  # sin el método, el nombre solo está en SVL
    assert datos.count(b"Chequear") == 1
    with pytest.raises(descompilador.NoSoportado, match="CHECKMETHOD 'Chequ ar'"):
        descompilador.descompilar(datos.replace(b"Chequear", b"Chequ ar"))


def test_checkmethod_con_tags():
    """TAGS con CHECKMETHOD no compila en ningún orden de los probados: NoSoportado."""
    from hubble import interfaz

    datos = _formulario("vw_checkmethod")
    m = descompilador._Modulo(datos)
    datos = _cambia_u32(_cambia_u32(datos, "FCT", 1, 0, m.u32("FCT", 1, 0) | interfaz.TAGS), "FCT", 1, 0x58, m.u32("FCT", 1, 0xB8))
    with pytest.raises(descompilador.NoSoportado, match="CHECKMETHOD en FCT 1 con TAGS"):
        descompilador.descompilar(datos)


def test_checkmethod_de_una_columna():
    """Con LIKEVAR de una columna del repositorio, el compilador podría copiar el check method de la columna: no se
    sabe si se escribió (ITEMS FCT 11, un EDIT LIKEVAR de columna)."""
    datos = _sample_datos("items")
    m = descompilador._Modulo(datos)
    assert not m.u32("FCT", 11, 0xB8) and m.u32("FCT", 11, 0x48)
    with pytest.raises(descompilador.NoSoportado, match="CHECKMETHOD en FCT 11 con TAGS o con LIKEVAR"):
        _sample_stock("items", _cambia_u32(datos, "FCT", 11, 0xB8, m.u32("FCT", 11, 0x48)))


def test_checkmethod_de_un_text():
    """En un TEXT, CHECKMETHOD no compila: +0xB8 sigue sin leerse."""
    datos = _formulario("c_text")
    with pytest.raises(descompilador.NoSoportado, match=r"TEXT FCT 1: \+0xb8"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 1, 0xB8, 0x2100))


def test_checkmethod_en_32_bits():
    from hubble.descompilador import MAPA_32

    assert MAPA_32["FCT"][0xB8] == 0x6C  # batería formularios.py compilada en 32 bits (vw_checkmethod*)
    d32 = KITS / "compilados" / "formularios-86x86"
    if not d32.is_dir():  # la compila la vuelta de 32 bits (los mismos huecos que la de 64)
        pytest.skip(f"sin {d32}")
    huecos = dict(reversed(l.split("\t")) for l in (FORMULARIOS / "manifiesto.tsv").read_text().splitlines())
    omd32 = next(p for p in d32.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos["vw_checkmethod_dos_edits"].lower())
    assert descompilador.descompilar(omd32.read_bytes()) == descompilador.descompilar(_formulario("vw_checkmethod_dos_edits"))


@pytest.mark.parametrize(("programa", "trozo"), [
    ("vw_bx_icon_frameautosize", 'CENTER\n\t\t\t\tFRAMEAUTOSIZE\n\t\t\t\tNUMBER 2'),
    ("vw2_bx_autosize_icon_frameautosize", '\t\t\t\tAUTOSIZE\n\t\t\t\tICON FILE "_MBSTDBMP_" CENTER\n\t\t\t\tFRAMEAUTOSIZE\n'),
    ("vw2_bx_icon_frameautosize_allowdrag", 'CENTER\n\t\t\t\tFRAMEAUTOSIZE\n\t\t\t\tALLOWDRAG\n'),
    ("vw2_bx_frameautosize_variable", "\t\t\t\tFRAMEAUTOSIZE\n\t\t\t\tVARIABLE v\n"),
    ("vw_bx_nolabel_frameautosize", "\t\t\t\tNOLABEL\n\t\t\t\tFRAMEAUTOSIZE\n"),
    ("vw_bg_radio_frameautosize", "\t\t\t\tFRAMEAUTOSIZE\n\t\t\t\tCLICKTYPE RADIO\n"),
])
def test_frameautosize_de_los_grupos(programa, trozo):
    assert trozo in descompilador.descompilar(_omd_control(programa))


def test_frameautosize_en_un_box():
    """FRAMEAUTOSIZE en un BOX, un BITMAP o un EDIT no compila: el bit sigue sin descifrar fuera de los grupos."""
    datos = _formulario("c_box")
    m = descompilador._Modulo(datos)
    with pytest.raises(descompilador.NoSoportado, match="bits 0x10000 sin descifrar en FCT 1"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 1, 0, m.u32("FCT", 1, 0) | 0x10000))


def _pagina(programa: str) -> bytes:
    if not (PAGINAS / "manifiesto.tsv").exists():
        pytest.skip(f"sin {PAGINAS}")
    huecos = dict(reversed(l.split("\t")) for l in (PAGINAS / "manifiesto.tsv").read_text().splitlines())
    return next(p for p in PAGINAS.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()).read_bytes()


@pytest.mark.parametrize(("programa", "trozo"), [
    ("pvw_nolabel_autosize_frameautosize_number_1_columns_1__box", "\t\t\t\tNOLABEL\n\t\t\t\tAUTOSIZE\n\t\t\t\tFRAMEAUTOSIZE\n"),
    ("pvw2_nolabel_border_all_frameautosize_number_1_columns_1__box", "\t\t\t\tBORDER ALL\n\t\t\t\tFRAMEAUTOSIZE\n\t\t\t\tNUMBER"),
    ("pvw2_nolabel_page_2_frameautosize_number_1_columns_1__box", "\t\t\t\tPAGE 2\n\t\t\t\tFRAMEAUTOSIZE\n"),
])
def test_frameautosize_de_pagina(programa, trozo):
    assert trozo in descompilador.descompilar(_pagina(programa))


def test_autosize_de_boxgroup_de_pagina_con_attach():
    from hubble import interfaz

    datos = _pagina("pvw_nolabel_autosize_frameautosize_number_1_columns_1__box")
    m = descompilador._Modulo(datos)
    with pytest.raises(descompilador.NoSoportado, match="AUTOSIZE con ATTACH"):
        descompilador.descompilar(_cambia_u32(datos, "PCT", 1, 0x44, m.u32("PCT", 1, 0x44) | interfaz.A_TOP))


# --- familia «rejilla» (2026-10-31): NOROWNUM, NOARROW y NOALLOWADD de GRID, SORT de las listas
@pytest.mark.parametrize(("programa", "trozo"), [
    ("rj_norownum", "\t\t\t\tPARENTGRID\n\t\t\t\tNOROWNUM\n\t\t\tBEGIN"),
    ("rj_noarrow", "\t\t\t\tPARENTGRID\n\t\t\t\tNOARROW\n\t\t\tBEGIN"),
    ("rj_noallowadd", "\t\t\t\tPARENTGRID\n\t\t\t\tNOALLOWADD\n\t\t\tBEGIN"),
    ("rj_tres", "\t\t\t\tPARENTGRID\n\t\t\t\tNOROWNUM\n\t\t\t\tNOARROW\n\t\t\t\tNOALLOWADD\n\t\t\tBEGIN"),
    ("rj_cuatro", "\t\t\t\tNOALLOWADD\n\t\t\t\tAUTOSORT\n\t\t\tBEGIN"),
    ("rj_scroll_norownum", "\t\t\t\tSCROLL VERTICAL\n\t\t\t\tTABLE states\n\t\t\t\tPARENTGRID\n\t\t\t\tNOROWNUM\n"),
])
def test_rejilla_por_su_linea(programa, trozo):
    assert trozo in descompilador.descompilar(_tablas()[programa][1], "stock", _stock())


@pytest.mark.parametrize(("programa", "bit"), [("rj_noarrow", 0x20000), ("rj_norownum", 0x40000), ("rj_noallowadd", 0x80000)])
def test_rejilla_no_es_password_ni_upshift(programa, bit):
    """En un GRID, los bits de NOARROW, NOROWNUM y NOALLOWADD son los de PASSWORD, UPSHIFT y DOWNSHIFT, que ahí no
    compilan (rj2_): antes salían esos, en silencio, y el fuente no compilaba."""
    datos = _tablas()[programa][1]
    m = descompilador._Modulo(datos)
    assert m.u32("FCT", 1, 0) == descompilador._Modulo(_tablas()["rj_base"][1]).u32("FCT", 1, 0) | bit
    texto = descompilador.descompilar(datos, "stock", _stock())
    assert not re.search(r"PASSWORD|UPSHIFT|DOWNSHIFT", texto)


def test_rejilla_rj2_no_compilan():
    """PASSWORD, UPSHIFT y DOWNSHIFT en un GRID no compilan, delante ni detrás de PARENTGRID: los bits no son ambiguos."""
    nombres = list(_tablas())  # solo las que compilan
    assert "rj_norownum" in nombres and not [n for n in nombres if n.startswith("rj2_")]


@pytest.mark.parametrize(("programa", "trozo"), [
    ("so_list_sort", "\t\t\t\tPOSITION 10 10 100 50\n\t\t\t\tSORT\n"),
    ("so_list_sort_sortonclick", "\t\t\t\tSORT\n\t\t\t\tSORTONCLICK\n"),
    ("so_list_allowdrop_sort", "\t\t\t\tALLOWDROP\n\t\t\t\tSORT\n"),
    ("so_list_sort_listtype_listcols_2", "\t\t\t\tSORT\n\t\t\t\tLISTTYPE LISTCOLS 2\n"),
    ("so_list_sort_selecttype_multiple", "\t\t\t\tSORT\n\t\t\t\tSELECTTYPE MULTIPLE\n"),
    ("so2_list_icon_file__mbstdbmp__sort", '\t\t\t\tICON FILE "_MBSTDBMP_"\n\t\t\t\tSORT\n'),
    ("so_droplist_sort_show_8_lines", "\t\t\t\tSORT\n\t\t\t\tSHOW 8 LINES\n"),
    ("so2_droplist_sort_tags_a__b", '\t\t\t\tSORT\n\t\t\t\tTAGS "a" "b"\n'),
    ("so_dropedit_sort", "\t\t\t\tDATATYPE CHAR\n\t\t\t\tSORT\n"),
    ("so2_dropedit_icon_file__mbstdbmp__datatype_char_sort", '"_MBSTDBMP_"\n\t\t\t\tDATATYPE CHAR\n\t\t\t\tSORT\n'),
    ("so3_droplist_sortonclick_show_8_lines", "\t\t\t\tSORTONCLICK\n\t\t\t\tSHOW 8 LINES\n"),
    ("so3_dropedit_sort_sortonclick_show_8_lines", "\t\t\t\tSORT\n\t\t\t\tSORTONCLICK\n\t\t\t\tSHOW 8 LINES\n"),
])
def test_sort_por_su_linea(programa, trozo):
    assert trozo in descompilador.descompilar(_fct(programa))


def test_sort_es_0x200_de_a8():
    from hubble import interfaz

    assert interfaz.ORDENADA == 0x200
    m = descompilador._Modulo(_fct("so_list_sort"))
    assert m.u32("FCT", 1, 0xA8) == 0x200
    assert m.u32("FCT", 1, 0xA8) | 0x30 == descompilador._Modulo(_fct("so_list_sort_selecttype_multiple")).u32("FCT", 1, 0xA8)


def test_sortonclick_delante_de_show():
    """SHOW n LINES y luego SORTONCLICK no compila (so3_): antes Hubble los escribía en ese orden."""
    texto = descompilador.descompilar(_fct("so3_dropedit_sortonclick_show_8_lines"))
    assert texto.index("SORTONCLICK") < texto.index("SHOW 8 LINES")


@pytest.mark.parametrize(("off", "bit", "motivo"), [
    (0x44, 0x40000000, "SORT en DROPEDIT FCT 1 con READONLY o LIKEVAR"),  # READONLY
    (0x00, 0x4000, "SORT en DROPEDIT FCT 1 con READONLY o LIKEVAR"),  # LIKEVAR
    (0xA8, 0x800, r"lista FCT 1: \+0xA8 0xa10"),  # un bit de +0xA8 que no se ha visto
])
def test_sort_no_visto(off, bit, motivo):
    datos = _fct("so_dropedit_sort")
    m = descompilador._Modulo(datos)
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 1, off, m.u32("FCT", 1, off) | bit))


# --- familia «codigo» (2026-10-31): SELF de un método externo, PANELTYPE OPERATION, VAR de una clase simple del módulo
def _bateria(nombre: str, programa: str) -> bytes | None:
    """El .omd de una variante de la batería instalada `nombre`, o None si no compila."""
    d = KITS / "compilados" / f"{nombre}-86x64"
    if not (d / "manifiesto.tsv").exists():
        pytest.skip(f"sin {d}")
    huecos = dict(reversed(l.split("\t")) for l in (d / "manifiesto.tsv").read_text().splitlines())
    o = next((p for p in d.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()), None)
    return o.read_bytes() if o else None


@pytest.mark.parametrize(("programa", "linea"), [
    ("sd_self", 'public self dll "user32.dll" GetTickCount() return Integer\n'),
    ("sd_self_mayus", 'public self dll "user32.dll" GetTickCount() return Integer\n'),  # SELF DLL: los mismos bytes
    ("sd_self_sin_return", 'public self dll "user32.dll" MessageBeep(t as Integer)\n'),
    ("sd_self_private", 'private self dll "user32.dll" GetTickCount() return Integer\n'),
    ("sd_clase_self", 'public self dll "user32.dll" GetTickCount() return Integer\n'),
    ("sd_struct_self", 'public self dll "user32.dll" GetTickCount() return Integer\n'),
    ("sj_self", 'public self javaclass "Test1" FuncionJava1()\n'),
    ("sj_clase_self", 'public self javaclass "Test1" FuncionJava1()\n'),
    ("sd_base", 'public dll "user32.dll" GetTickCount() return Integer\n'),
    ("sj_base", 'public javaclass "Test1" FuncionJava1()\n'),
])
def test_self_de_un_externo(programa, linea):
    texto = descompilador.descompilar(_bateria("clases", programa))
    assert linea in texto
    assert ("self" in linea) == (" self " in texto)


@pytest.mark.parametrize(("base", "con_self"), [("sd_base", "sd_self"), ("sd_sin_return", "sd_self_sin_return"),
                                                ("sd_clase_base", "sd_clase_self"), ("sj_base", "sj_self")])
def test_self_es_0x20_del_byte_1(base, con_self):
    """SELF solo cambia el 0x20 del byte 1 del PRO (y no añade ningún parámetro)."""
    a, b = (descompilador._Modulo(_bateria("clases", p)) for p in (base, con_self))
    assert b.u32("PRO", 0, 0) == a.u32("PRO", 0, 0) | 0x2000
    assert a.u32("PRO", 0, 0x10) == b.u32("PRO", 0, 0x10)


@pytest.mark.parametrize(("bits", "quita"), [(0x0200, 0), (0x4000, 0), (0x010000, 0), (0x40000000, 0), (0, 0x0100)])
def test_externo_con_bits_no_vistos(bits, quita):
    """Un bit del PRO externo que no se ha visto no se ignora (antes no se miraba ninguno): NoSoportado."""
    datos = _bateria("clases", "sd_self")
    w0 = descompilador._Modulo(datos).u32("PRO", 0, 0)
    with pytest.raises(descompilador.NoSoportado, match="dll con"):
        descompilador.descompilar(_cambia_u32(datos, "PRO", 0, 0, (w0 | bits) & ~quita))


def test_selfclass_function_y_self_delante():
    """`return selfclass` y `x as selfclass` no compilan en 8.6 («Unknown class identifier selfclass»): la clase propia
    se escribe por su nombre. `self public dll`, `self dll` y `function f` sin acceso tampoco compilan."""
    for programa in ("sc_return_selfclass", "sc_return_selfclass_mayus", "sc_param_selfclass", "sc_dll_return_selfclass",
                     "sd_self_delante", "sd_self_sin_acceso", "fn_function_sin_acceso"):
        assert _bateria("clases", programa) is None, programa
    assert "public f() return sm\n" in descompilador.descompilar(_bateria("clases", "sc_return_clase"))


def test_var_de_una_clase_simple_del_modulo():
    """`f(VAR o as sm)` con `sm is Smallint`: el 0x40 del OBJ solo está con VAR (antes se perdía). En un Struct lo pone
    el compilador siempre (con VAR o sin él, los mismos bytes)."""
    assert "public f(VAR o as sm)\n" in descompilador.descompilar(_bateria("clases", "sc_param_var_clase"))
    assert "public f(o as sm)\n" in descompilador.descompilar(_bateria("clases", "sc_param_clase"))
    assert "public f(o as A)\n" in descompilador.descompilar(_bateria("clases", "sc_param_var_struct"))


def test_var_de_otra_clase_simple():
    datos = _bateria("clases", "sc_param_var_clase")
    with pytest.raises(descompilador.NoSoportado, match="VAR de una clase 0x1"):
        descompilador.descompilar(_cambia(datos, "CLA", 1, 0, 0x01))


def test_clase_sin_nombre():
    """Una CLA sin nombre en IDE daba un nombre inventado («cla1»): NoSoportado."""
    datos = _bateria("clases", "sd_clase_base")
    with pytest.raises(descompilador.NoSoportado, match="sin nombre"):
        descompilador.descompilar(_cambia_u32(datos, "CLA", 1, 0x10, 0))
    datos = _bateria("clases", "sc_return_clase")  # `return sm`: +0x20 del PRO → la CLA de sm
    m = descompilador._Modulo(datos)
    assert m.nombre_clase(m.u32("PRO", 0, 0x20)) == "sm"
    m = descompilador._Modulo(_cambia_u32(datos, "CLA", 1, 0x10, 0))
    with pytest.raises(descompilador.NoSoportado, match="CLA 1 sin nombre"):
        m.nombre_clase(m.u32("PRO", 0, 0x20))


@pytest.mark.parametrize(("programa", "trozo"), [
    ("pop_operation", "\t\t\t\tPANELTYPE OPERATION\n"),
    ("pop_operation_bar", "\t\t\t\t\tPANELTYPE OPERATION\n"),
    ("pop_operation_label", '\t\t\t\tLABEL "x"\n\t\t\t\tPANELTYPE OPERATION\n'),
])
def test_paneltype_operation(programa, trozo):
    datos = _bateria("datos", programa)
    assert trozo in descompilador.descompilar(datos)


def test_paneltype_operation_es_4():
    m = descompilador._Modulo(_bateria("datos", "pop_operation"))
    assert m.u32("FCT", 1, 0x20) >> 16 == 4
    assert descompilador._Modulo(_bateria("datos", "pop_message")).u32("FCT", 1, 0x20) >> 16 == 2
    datos = _bateria("datos", "pop_operation")
    with pytest.raises(descompilador.NoSoportado, match="PANELTYPE 5"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 1, 0x20, (m.u32("FCT", 1, 0x20) & 0xFFFF) | 5 << 16))


def test_ticks_y_references_no_compilan():
    """`TICKS n` no compila en ningún sitio (tks_, tkp_: «Actual ticks(TICKS). Expecting  control, end»), y `references`
    / `joining` tampoco, en ninguna de las 16 formas de rf_ (detrás de la cabecera, dentro del begin, en una columna)."""
    import importlib.util

    for bateria, prefijos in (("fct", ("tks_", "tkp_")), ("variables", ("rf_",))):
        spec = importlib.util.spec_from_file_location(bateria, Path(__file__).resolve().parents[1] / "lab" / "bateria" / f"{bateria}.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        nombres = [p for p in modulo.P if p.startswith(prefijos)]
        assert len(nombres) == {"fct": 15, "variables": 16}[bateria]
        assert all(_bateria(bateria, p) is None for p in nombres)


# --- ACTIVEX: CLSID y PROPERTY (batería controles.py, ax_; Events.smd del kit 86x86)
EVENTS = [KITS / "extraido" / "86x86" / "Cosmos8.6eval" / "projects" / "ActiveX" / "Events.OMD",
          KITS / "compilados" / "activex-86x86" / "Events.OMD", KITS / "compilados" / "proy32" / "ActiveX" / "Events.OMD"]


@pytest.mark.parametrize("ruta", EVENTS, ids=["kit", "activex-86x86", "proy32"])
def test_activex_de_events(ruta):
    """El único ACTIVEX del kit (32 bits): el CLSID, las 19 PROPERTY en el orden del fuente y `On Control xcalendar`."""
    if not ruta.exists():
        pytest.skip(f"sin {ruta}")
    texto = descompilador.descompilar(ruta.read_bytes())
    assert ('\t\t\t\tCONTROL xcalendar AS ACTIVEX\n\t\t\t\t\tPOSITION 7 5 443 284\n'
            '\t\t\t\t\tCLSID "{8E27C92B-1264-101C-8A2F-040224009C02}"\n\t\t\t\t\tPROPERTY "BackColor" "2147483663"\n'
            '\t\t\t\t\tPROPERTY "Day" "2"\n') in texto
    assert texto.count("PROPERTY ") == 19
    assert '\t\t\t\t\tPROPERTY "Value" "02/06/1999"\n\t\t\t\t\tPROPERTY "ValueIsNull" "0"\n\t\t\t\t\tPROPERTY "Year" "1999"\n\t\t\t\tCONTROL txtDay' in texto
    assert "\nOn Control xcalendar (e as Event)\n" in texto
    # los eventos de un ACTIVEX, entre comillas (sin ellas, «Unknown control event AfterUpdate»: vuelta actx32); los de
    # los demás controles, sin ellas (los mismos bytes)
    assert '\nOn event "AfterUpdate" control "xcalendar"\n' in texto
    assert "\nOn event Click control buttonUpdate\n" in texto


@pytest.mark.parametrize(("programa", "trozo"), [
    ("ax_base", '\t\t\t\tPOSITION 10 10 50 20\n\t\t\t\tCLSID "{8E27C92B-1264-101C-8A2F-040224009C02}"\n\t\tEND\n'),
    ("ax_progid", '\t\t\t\tCLSID "Word.Application"\n'),  # el texto tal cual, sin comprobar que sea un CLSID
    ("ax_minusculas", '\t\t\t\tCLSID "{8e27c92b-1264-101c-8a2f-040224009c02}"\n'),
    ("ax_prop_orden", '\t\t\t\tPROPERTY "Month" "6"\n\t\t\t\tPROPERTY "Day" "2"\n'),  # en el orden del fuente
    ("ax_prop_repetida", '\t\t\t\tPROPERTY "Day" "1"\n\t\t\t\tPROPERTY "Day" "2"\n'),
    ("ax_prop_vacia", '\t\t\t\tPROPERTY "Day" ""\n'),
    ("ax_varios_antes", '\t\t\t\tATTACH ALL\n\t\t\t\tBORDER DOUBLE DOWN\n\t\t\t\tCLSID'),  # CLSID, el último
    ("onc_activex", "\nOn Control c (e as Event)\nbegin\n"),
    ("onc_button", "\nOn Control c (e as Event)\nbegin\n"),
    ("onc_sin_param", "\nOn Control c\nbegin\n"),
])
def test_activex_por_su_linea(programa, trozo):
    assert trozo in descompilador.descompilar(_bateria("controles", programa))


def test_activex_que_no_compilan():
    """CLSID es obligatorio y el último: detrás solo PROPERTY (LABEL, NOLABEL, TAGS, BORDER, NOBORDER y ATTACH detrás no
    compilan; LABEL, NOLABEL y BACKGROUND, tampoco delante). PROPERTY sin CLSID o delante, tampoco."""
    for programa in ("ax_sin_clsid", "ax_label_antes", "ax_label_despues", "ax_nolabel_antes", "ax_tags_despues",
                     "ax_border_double_down_despues", "ax_attach_despues", "ax_prop_antes_clsid", "ax_prop_tags",
                     "ax_prop_sin_clsid", "ax_prop_label", "ax_cursor_background_bold_notabstop"):
        assert _bateria("controles", programa) is None, programa


def test_activex_clsid_y_property_son_label_y_tags():
    m = descompilador._Modulo(_bateria("controles", "ax_prop2"))
    i = Interfaz(m, descompilador.NoSoportado)
    assert m.u32("FCT", 1, 0x00) == 0xB0000000 and m.u32("FCT", 1, 0x20) == 0x1A
    assert i.texto_svl(1, 0x48) == "{8E27C92B-1264-101C-8A2F-040224009C02}"
    assert i.texto_svl(1, 0x58) == "Day=2|Month=6|"
    assert Interfaz(descompilador._Modulo(_bateria("controles", "ax_base")), descompilador.NoSoportado).texto_svl(1, 0x58) == ""


@pytest.mark.parametrize(("off", "bits", "motivo"), [
    (0x00, 0x10000000, "sin CLSID"),          # sin el bit de CLSID (LABEL), y sin su texto (+0x48)
    (0x00, 0x20000000, "sin CLSID"),          # sin el de PROPERTY (TAGS), y sin su texto (+0x58)
    (0x00, 0x800000, "no vistos"),            # BOLD
    (0x00, 0x80, "no vistos"),                # BORDER FRAME
    (0x00, 0x40000000, "no vistos"),          # COMMENT
    (0x44, 0x200000, "no vistos"),            # NOTABSTOP
    (0x44, 0x8000000, "no vistos"),           # CURSOR
])
def test_activex_no_visto(off, bits, motivo):
    datos = _bateria("controles", "ax_base")
    m = descompilador._Modulo(datos)
    if bits in (LABEL_, TAGS_):  # el campo, también a 0 (si no, salta antes la guarda de siempre: «sin su bit»)
        datos = _cambia_u32(datos, "FCT", 1, 0x48 if bits == LABEL_ else 0x58, 0)
    with pytest.raises(descompilador.NoSoportado, match=motivo):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 1, off, m.u32("FCT", 1, off) ^ bits))


LABEL_, TAGS_ = 0x10000000, 0x20000000


@pytest.mark.parametrize(("off", "valor"), [(0x50, 0xFF), (0x60, 1)])  # BACKGROUND (no compila), PAGE
def test_activex_con_campos_no_vistos(off, valor):
    with pytest.raises(descompilador.NoSoportado, match="BACKGROUND, PAGE"):
        descompilador.descompilar(_cambia_u32(_bateria("controles", "ax_base"), "FCT", 1, off, valor))


def test_activex_con_hijos():
    datos = _bateria("controles", "ax_dos")  # el segundo ACTIVEX, hijo del primero
    with pytest.raises(descompilador.NoSoportado, match="hijos"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 1, 0x10, 2 << 16 | 0x10 << 8))


def test_activex_focus():
    datos = _bateria("controles", "ax_base")
    with pytest.raises(descompilador.NoSoportado, match="FOCUS"):
        descompilador.descompilar(_cambia_u32(datos, "FCT", 0, 0x58, 1 << 16 | 0x10 << 8))


@pytest.mark.parametrize(("texto", "propiedades"), [
    ("", []), ("Day=2|", [("Day", "2")]), ("Day=|", [("Day", "")]), ("a=1|a=2|", [("a", "1"), ("a", "2")]),
    ("Day=2", None), ("a=b=c|", None), ("Day=a|b|", None), ("=x|", None), ("|", None)])
def test_activex_propiedades(monkeypatch, texto, propiedades):
    """Sin escape, un `=` o un `|` de más no se puede partir: NoSoportado (ax_prop_igual_nombre, ax_prop_barra_valor)."""
    i = Interfaz(descompilador._Modulo(_bateria("controles", "ax_base")), descompilador.NoSoportado)
    monkeypatch.setattr(i, "texto_svl", lambda k, off: texto)
    if propiedades is None:
        with pytest.raises(descompilador.NoSoportado, match="PROPERTY"):
            i.propiedades(1)
    else:
        assert i.propiedades(1) == propiedades


def test_on_control_sin_control():
    """`On Control x`: +0x28 = 0 (sin evento) y el control en STR (+0x20). Sin los dos, NoSoportado."""
    datos = _bateria("controles", "onc_activex")
    with pytest.raises(descompilador.NoSoportado, match="On event sin nombre"):
        descompilador.descompilar(_cambia_u32(datos, "PRO", 0, 0x20, 0))


def test_on_control_con_otro_byte_2():
    datos = _bateria("controles", "onc_activex")
    m = descompilador._Modulo(datos)
    with pytest.raises(descompilador.NoSoportado, match="On event sin nombre"):
        descompilador.descompilar(_cambia_u32(datos, "PRO", 0, 0x00, m.u32("PRO", 0, 0x00) ^ 0x30000))


# --- los tres samples que solo fallaban en 32 bits (2026-10-31): ArgList de un parámetro, geometría que parecía una
# declaración y un método sin paréntesis cuyo puntero cae en otro bloque de memoria
@pytest.mark.parametrize(("nombre", "linea"), [
    ("ChartRadar", "valores as ArgList of Decimal)\n"),                   # OBJ +0x24 de 32 bits = +0x40 de 64
    ("EjDisableAceleradores", '    btn_deshabilitar.Text = "Deshabilitar";\n'),  # `POSITION 256 39`: 39 × 4 = PutEnv
    ("ListasArbolEventoClick_Check", "    Miform.Run;\n"),             # Run, el último libre de su tramo
])
def test_samples_que_solo_fallaban_en_32_bits(nombre, linea):
    _necesita(SAMPLES_32)
    t32 = _sample_stock(nombre, next(p for p in SAMPLES_32.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == nombre.lower()).read_bytes())
    assert linea in t32
    assert t32 == _sample_stock(nombre.lower())


def _bateria_32(nombre: str, programa: str) -> bytes | None:
    """El .omd de 32 bits de una variante (los mismos huecos que la de 64), o None si no compila."""
    d64, d32 = KITS / "compilados" / f"{nombre}-86x64", KITS / "compilados" / f"{nombre}-86x86"
    _necesita(d64 / "manifiesto.tsv", d32)
    huecos = dict(reversed(l.split("\t")) for l in (d64 / "manifiesto.tsv").read_text().splitlines())
    o = next((p for p in d32.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == huecos[programa].lower()), None)
    return o.read_bytes() if o else None


@pytest.mark.parametrize(("programa", "linea"), [
    ("alp_integer", "public f(a as ArgList of Integer)\n"),
    ("alp_decimal_sin", "public f(a as ArgList of Decimal)\n"),
    ("alp_clase", "public f(a as ArgList of A)\n"),                       # +0x40 → una CLA del módulo
    ("alp_dos", "public f(n as Integer, a as ArgList of Decimal)\n"),
    ("alp_minusculas", "public f(a as ArgList of Decimal)\n"),
    ("alp_llamada", "    f(1.5, 2.5);\n"),
])
def test_arglist_de_un_parametro_en_32_bits(programa, linea):
    """La clase X de `a as ArgList of X` va en el +0x40 del OBJ en 64 bits y en el +0x24 en 32 (batería clases.py,
    alp_): el mismo texto en las dos. Con `of Char(10)`, `of Decimal(10,2)`, sin `of` o en un objeto local no compila."""
    d64, d32 = _bateria("clases", programa), _bateria_32("clases", programa)
    if d32 is None:
        pytest.skip("sin el .omd de 32 bits")
    texto = descompilador.descompilar(d64, "stock", _stock())
    assert linea in texto
    assert descompilador.descompilar(d32, "stock", _stock()) == texto


def test_arglist_de_un_fob_en_32_bits():
    """Un FOB (variable de formulario) de clase ArgList no se ha visto: en 32 bits su +0x40 no tiene mapa, y sin
    NoSoportado saldría `ArgList` sin su `of`."""
    _necesita(SAMPLES_32)
    datos = next(p for p in SAMPLES_32.iterdir() if p.suffix.lower() == ".omd" and p.stem.lower() == "chartradar").read_bytes()
    m = descompilador._Modulo(datos)
    assert m.texto_ide(m.u32("FOB", 6, 0x10)) == "valueT1" and m.ecl[5] == "ArgList"
    with pytest.raises(descompilador.NoSoportado, match="valueT1: ArgList de un FOB en 32 bits"):
        _sample_stock("chartradar", _cambia_u32(datos, "FOB", 6, 0x0C, 0x51900))  # +0x18 de 64 = +0x0C de 32: ECL 5


@pytest.mark.parametrize(("bateria", "programa", "bits", "nombre", "linea"), [
    ("fct", "geo_x_text32", 32, "Text", '    b.Text = "x";\n'),
    ("fct", "geo_x_putenv32", 32, "PutEnv", '    Module.PutEnv("A", "TRUE");\n'),
    ("fct", "geo_x_run32", 32, "Run", "    o.Run;\n"),
    ("fct", "geo_x_text64", 64, "Text", '    b.Text = "x";\n'),
    ("fct", "geo_x_putenv64", 64, "PutEnv", '    Module.PutEnv("A", "TRUE");\n'),
    ("fct", "geo_x_run64", 64, "Run", "    o.Run;\n"),
    ("fct", "geo_ancho_putenv32", 32, "PutEnv", '    Module.PutEnv("A", "TRUE");\n'),   # el ancho, en +0x3C
    ("fct", "geo_ancho_putenv64", 64, "PutEnv", '    Module.PutEnv("A", "TRUE");\n'),
    ("fct", "geo_form_ancho_putenv32", 32, "PutEnv", '    Module.PutEnv("A", "TRUE");\n'),  # el del formulario
    ("paginas", "pgeo_x_trace32", 32, "Trace", '    "x".Trace();\n'),  # antes `"x".t()`, sin avisar
    ("paginas", "pgeo_x_trace64", 64, "Trace", '    "x".Trace();\n'),
    ("paginas", "pgeo_ancho_trace32", 32, "Trace", '    "x".Trace();\n'),
    ("paginas", "pgeo_ancho_trace64", 64, "Trace", '    "x".Trace();\n'),
])
def test_la_geometria_no_es_una_declaracion(bateria, programa, bits, nombre, linea):
    """x o ancho 256 deja el u16 bajo de la geometría en 0x0100, el código de las declaraciones, y y o el alto por 4
    puede caer en el registro de IDE de un nombre que solo se usa por puntero: no es una declaración (batería fct.py,
    geo_, y paginas.py, pgeo_; samples EjDisableAceleradores en 32 bits)."""
    datos = {64: _bateria(bateria, programa), 32: _bateria_32(bateria, programa)}
    if datos[32] is None:
        pytest.skip("sin el .omd de 32 bits")
    m = descompilador._Modulo(datos[bits])
    seccion = "FCT" if bateria == "fct" else "PCT"
    choques = [(w >> 16) * 4 for k in range(m.s[seccion].n) for o in (0x38, 0x3C)
               if (w := m.u32(seccion, k, o)) & 0xFFFF == 0x0100 and (w >> 16) * 4 in m.ide]
    assert [m.ide[p] for p in choques] == [nombre]
    assert choques[0] not in m.declarados
    texto = descompilador.descompilar(datos[64])
    assert linea in texto
    assert descompilador.descompilar(datos[32]) == texto


def test_metodo_sin_parentesis_y_sin_puntero():
    """`o.Run;` sin el puntero de Run (como en ListasArbolEventoClick_Check de 32 bits, donde cae en otro bloque de
    memoria): es el último del tramo y Run, el único nombre libre detrás, que no es una clase. Sin la regla, NoSoportado."""
    datos = _formulario("f_base")
    m = descompilador._Modulo(datos)
    k = next(k for k in range(m.s["REF"].n) if m.rec("REF", k)[0] == descompilador.METODO
             and m.punteros.get(struct.unpack_from("<Q", m.rec("REF", k), 0x18)[0]) == "Run")
    p, e = struct.unpack_from("<Q", m.rec("REF", k), 0x18)[0], m.refa("REF", k, 0x10, descompilador.EPR)
    del m.punteros[p], m.pos_ide[p], m.por_entrada[(descompilador.EPR, e)]
    texto = descompilador._Escritor(m).modulo()
    assert "    o.Run;\n" in texto and texto == descompilador.descompilar(datos)

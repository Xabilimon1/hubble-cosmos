#pragma author Hubble
#pragma description MultiBase Cosmos compiled module (.omd)
#pragma magic [ 43 4F 4D 44 ] @ 0x00
#pragma endian little

// Patrón de Hubble para ImHex. Solo describe lo comprobado en docs/formato-omd.md (con la
// vuelta completa: descompilar, recompilar y comparar byte a byte). Lo que sigue siendo
// hipótesis va marcado [hipótesis] y lo que no se entiende va en gris como «sin descifrar».
// Los registros con estructura son los de 64 bits; en 32 bits se ven en bruto.

import std.mem;
import std.string;
import std.core;
import std.io;

#define GRIS "505050"

// 32 o 64 bits, por el tamaño de registro de REF (16 / 32 bytes): entrada 18 de la lista B.
u32 tam_ref_ = std::mem::read_unsigned(std::mem::read_unsigned(0x24, 4) + 18 * 32 + 0x1C, 4);
u8 unidad = tam_ref_ == 32 ? 8 : 4;
bool es64 = tam_ref_ == 32;

// --- referencias entre registros: byte 1 = número de sección, 16 bits altos = índice
// (en IDE y STR, la posición en el flujo / 4).
fn nombre_seccion(u8 s) {
    if (s == 0x01) return "IDE"; if (s == 0x02) return "STR"; if (s == 0x03) return "DEC";
    if (s == 0x04) return "LIB"; if (s == 0x05) return "INC"; if (s == 0x07) return "CLA";
    if (s == 0x08) return "OBJ"; if (s == 0x09) return "MNU"; if (s == 0x0A) return "MOP";
    if (s == 0x0B) return "PRO"; if (s == 0x0D) return "FOR"; if (s == 0x0E) return "STM";
    if (s == 0x0F) return "REF"; if (s == 0x10) return "FCT"; if (s == 0x12) return "FOB";
    if (s == 0x14) return "FTA"; if (s == 0x16) return "FRC"; if (s == 0x18) return "EMO";
    if (s == 0x19) return "ECL"; if (s == 0x1A) return "EOB"; if (s == 0x1B) return "EPR";
    if (s == 0x21) return "SVL";
    return "";
};

struct Ref {
    u8 b0 [[hidden]];
    u8 seccion;
    u16 indice;
} [[format("fmt_ref"), single_color]];

fn fmt_ref(Ref r) {
    if (r.seccion == 0 && r.indice == 0 && r.b0 == 0) return "—";
    str s = nombre_seccion(r.seccion);
    if (s == "") return std::format("→ ¿{:02X}? {}  [sin descifrar]", r.seccion, r.indice);
    if (s == "IDE" || s == "STR") return std::format("→ {} @{}", s, r.indice * 4);
    return std::format("→ {} {}", s, r.indice);
};

// --- REF: nodos del árbol de expresiones (32 bytes). Los operadores son llamadas a métodos:
// `a = 1` es `a.=(1)`, y el nodo del método lleva en +0x18 el código del operador.
enum TipoNodo : u8 {
    control     = 0x00,  // de formulario (+0x10 → FCT)
    variable    = 0x10,  // +0x10 → OBJ, FOB o EOB (propiedad)
    propiedad   = 0x11,  // `obj.prop`: +0x10 objeto, +0x18 la propiedad
    metodo      = 0x20,  // +0x10 → EPR o PRO; +0x18 operador o puntero a su nombre en IDE
    acceso      = 0x21,  // `obj.metodo`: +0x10 objeto, +0x18 método
    llamada     = 0x22,  // +0x10 lo llamado, +0x18 primer argumento
    lit_smallint = 0x60, // variante 0x31: `self`
    lit_integer = 0x70,
    lit_decimal = 0x80,  // +0x18 → DEC
    lit_char    = 0x90,  // +0x18 → STR
    lit_boolean = 0xA0,
    lit_null    = 0xC0,
    lista       = 0xD0,  // `in (…)` y argumentos variables: +0x08 primer elemento
    valor_switch = 0xE0
};

fn operador(u64 c) {
    if (c == 0) return "conversión implícita"; if (c == 1) return "="; if (c == 2) return "**";
    if (c == 3) return "*"; if (c == 4) return "/"; if (c == 5) return "%"; if (c == 6) return "*=";
    if (c == 7) return "/="; if (c == 8) return "%="; if (c == 9) return "+"; if (c == 10) return "-";
    if (c == 11) return "+="; if (c == 12) return "-="; if (c == 13) return "++"; if (c == 14) return "--";
    if (c == 15) return "not"; if (c == 16) return "and"; if (c == 17) return "xor"; if (c == 18) return "or";
    if (c == 19) return "<>"; if (c == 20) return ">"; if (c == 21) return ">="; if (c == 22) return "<";
    if (c == 23) return "<="; if (c == 24) return "matches"; if (c == 25) return "like";
    if (c == 26) return "between"; if (c == 27) return "in"; if (c == 28) return "is null";
    if (c == 29) return "is not null"; if (c == 30) return "[ ] (índice)"; if (c == 31) return "==";
    if (c == 33) return "- (unario)";
    return "";
};

fn es_literal(u8 t) { return t >= 0x60 && t <= 0xC0 && t != 0xB0; };

struct NodoRef {
    u8 t_ = std::mem::read_unsigned($, 1);
    TipoNodo tipo;
    u8 variante [[comment("0xF0 literal; 0x50 constante o clase escrita delante; 0x31 self/control; 0x40 parent")]];
    u8 b2 [[color(GRIS), comment("sin descifrar")]];
    u8 seccion_propia [[comment("0x07 en REF")]];
    u32 x04 [[color(GRIS), comment("sin descifrar")]];
    Ref siguiente [[comment("argumentos y elementos encadenados")]];
    u32 x0c [[hidden]];
    Ref r10;
    u32 x14 [[hidden]];
    if (tipo == TipoNodo::lit_smallint) {
        s16 valor; u8 resto[6] [[comment("basura = argumento por defecto")]];
    } else if (tipo == TipoNodo::lit_integer) {
        s32 valor; u32 resto [[comment("basura = argumento por defecto")]];
    } else if (tipo == TipoNodo::lit_boolean) {
        u32 valor; u32 resto [[comment("0 o cccccccc si se escribió; otra cosa: por defecto")]];
    } else if (tipo == TipoNodo::lit_char || tipo == TipoNodo::lit_decimal) {
        Ref valor; u32 x1c [[hidden]];
    } else if (tipo == TipoNodo::metodo) {
        u64 codigo [[comment("código de operador (< 0x10000) o puntero de memoria del compilador")]];
    } else if (tipo == TipoNodo::propiedad || tipo == TipoNodo::acceso || tipo == TipoNodo::llamada) {
        Ref r18; u32 x1c [[hidden]];
    } else {
        u64 x18 [[comment("puntero de memoria del compilador (el nombre en IDE) o valor")]];
    }
} [[format("fmt_nodo")]];

fn fmt_nodo(NodoRef n) {
    if (n.tipo == TipoNodo::lit_smallint && n.variante == 0x31) return "self";
    if (n.tipo == TipoNodo::lit_smallint || n.tipo == TipoNodo::lit_integer) return std::format("literal {}", n.valor);
    if (n.tipo == TipoNodo::lit_boolean) return n.valor == 1 ? "literal true" : "literal false";
    if (n.tipo == TipoNodo::lit_null) return "literal null";
    if (n.tipo == TipoNodo::lit_char) return "literal char " + fmt_ref(n.valor);
    if (n.tipo == TipoNodo::lit_decimal) return "literal decimal " + fmt_ref(n.valor);
    if (n.tipo == TipoNodo::metodo && n.codigo < 0x10000) return "método «" + operador(n.codigo) + "»";
    if (n.tipo == TipoNodo::metodo) return "método con nombre " + fmt_ref(n.r10);
    if (n.tipo == TipoNodo::variable) return "variable " + fmt_ref(n.r10);
    if (n.tipo == TipoNodo::propiedad) return "propiedad";
    if (n.tipo == TipoNodo::acceso) return "acceso obj.método";
    if (n.tipo == TipoNodo::llamada) return "llamada";
    if (n.tipo == TipoNodo::lista) return "lista";
    if (n.tipo == TipoNodo::control) return "control " + fmt_ref(n.r10);
    return std::format("nodo 0x{:02X} [sin descifrar]", n.t_);
};

// --- STM: sentencias (48 bytes), lista enlazada por +0x08
enum TipoSentencia : u8 {
    begin_end = 0x00, si = 0x01, expresion = 0x02, devolver = 0x03, para = 0x04, mientras = 0x05,
    siempre = 0x06, repetir = 0x07, romper = 0x08, switch_valor = 0x0A, switch_condiciones = 0x0B,
    case_condicion = 0x0C, case_valor = 0x0D, defecto = 0x0E, vacia = 0x0F, para_lista = 0x11,
    para_hacia_abajo = 0x24
};

struct Sentencia {
    TipoSentencia tipo;
    u8 b1[3] [[color(GRIS)]];
    u32 x04 [[hidden]];
    Ref siguiente;
    u32 x0c [[hidden]];
    Ref r10 [[comment("condición / variable del for")]];
    u32 x14 [[hidden]];
    Ref r18 [[comment("then / primera / límite / primer case")]];
    u32 x1c [[hidden]];
    Ref r20 [[comment("expresión / valor de return o switch / step")]];
    u32 x24 [[hidden]];
    Ref r28 [[comment("else / cuerpo / default")]];
    u32 x2c [[hidden]];
} [[format("fmt_stm")]];

fn fmt_stm(Sentencia s) { return std::format("{}  · siguiente {}", s.tipo, fmt_ref(s.siguiente)); };

// --- PRO: procedimientos (64 bytes)
enum TipoProc : u8 {
    main_ = 0, funcion = 1, evento_formulario = 4, evento_control = 5, evento_tabla = 6,
    on_command = 7, dll = 9, javaclass = 0x0D
};

struct Procedimiento {
    TipoProc tipo;
    u8 b1 [[comment("0x04: no devuelve nada; 0x80: `On event X control Y`")]];
    u8 b2 [[color(GRIS)]];
    u8 b3 [[comment("0x20: private")]];
    u32 x04 [[hidden]];
    Ref siguiente; u32 x0c [[hidden]];
    Ref parametros [[comment("primer OBJ")]]; u32 x14 [[hidden]];
    Ref clase [[comment("CLA propietaria")]]; u32 x1c [[hidden]];
    Ref r20 [[comment("clase devuelta; en eventos de control, el control")]]; u32 x24 [[hidden]];
    Ref r28 [[comment("nombre (IDE); en eventos: el código o el nombre en STR")]]; u32 x2c [[hidden]];
    Ref r30 [[comment("primer local (OBJ); en dll y javaclass, la DLL o la clase en STR")]]; u32 x34 [[hidden]];
    Ref cuerpo [[comment("primera sentencia")]]; u32 x3c [[hidden]];
} [[format("fmt_pro")]];

fn fmt_pro(Procedimiento p) { return std::format("{} · nombre {}", p.tipo, fmt_ref(p.r28)); };

// --- OBJ: objetos (80 bytes): globales, locales, parámetros y miembros de Struct
struct Objeto {
    u8 tipo [[comment("0 global, 1 local, 2 parámetro, 3 miembro; +0x40 VAR")]];
    u8 b1 [[color(GRIS)]];
    u8 b2 [[comment("0x20: tiene default")]];
    u8 b3 [[color(GRIS)]];
    u32 x04 [[hidden]];
    Ref siguiente; u32 x0c [[hidden]];
    Ref nombre; u32 x14 [[hidden]];
    Ref clase; u32 x1c [[hidden]];
    Ref procedimiento; u32 x24 [[hidden]];
    u64 valor_default [[comment("como el valor de un literal")]];
    u16 largo [[comment("Char(n), o precisión de Decimal; 0xFFFF0000 en total = de una tabla")]];
    s16 escala;
    u8 x34[12] [[color(GRIS)]];
    Ref elemento [[comment("ArgList of X")]]; u32 x44 [[hidden]];
    u8 x48[8] [[color(GRIS)]];
} [[format("fmt_obj")]];

fn fmt_obj(Objeto o) { return std::format("objeto · nombre {} · clase {}", fmt_ref(o.nombre), fmt_ref(o.clase)); };

// --- CLA: clases (88 bytes); CLA 0 es el propio módulo
struct Clase {
    u8 tipo_base [[comment("Struct 0x20, Form 0x21, Menu 0x22, Page 0x23, Array 0x24…; +0x80 abstract")]];
    u8 b1[2] [[color(GRIS)]];
    u8 b3 [[comment("0x10: escrita en el fuente (sin él, la crea el compilador)")]];
    u32 x04 [[hidden]];
    Ref siguiente; u32 x0c [[hidden]];
    Ref nombre; u32 x14 [[hidden]];
    Ref base; u32 x1c [[hidden]];
    Ref modulo [[comment("EMO")]]; u32 x24 [[hidden]];
    u8 x28[12] [[color(GRIS)]];
    u32 tamano_array;
    u8 x38[8] [[color(GRIS)]];
    Ref r40 [[comment("formulario (FOR), elementos del Array, miembros (OBJ) o menú (MNU)")]]; u32 x44 [[hidden]];
    u32 x48 [[color(GRIS)]]; u32 x4c [[hidden]];
    Ref procedimientos [[comment("primer PRO")]]; u32 x54 [[hidden]];
} [[format("fmt_cla")]];

fn fmt_cla(Clase c) { return std::format("clase · nombre {} · base {}", fmt_ref(c.nombre), fmt_ref(c.base)); };

// --- FCT: controles de formulario (208 bytes); FCT 0 es el formulario
enum TipoControl : u16 {
    formulario = 0, BUTTON = 1, RADIO = 2, CHECK = 3, DROPLIST = 4, DROPEDIT = 5, EDIT = 6, TEXT = 7,
    BOX = 8, PERCENT = 0x0A, TAB = 0x0B, BUTTONGROUP = 0x0C, LIST = 0x0D, BOXGROUP = 0x0E,
    BITMAP = 0x0F, BAR = 0x10, PANEL = 0x11, USER = 0x13, MENU = 0x14, GRID = 0x15, SPIN = 0x17,
    SLIDER = 0x18, MDICLIENT = 0x1B
};

struct Control {
    u32 bits [[comment("borde, LABEL, TAGS, COMMENT… y otros según el tipo (docs/formato-omd.md)")]];
    u32 x04 [[hidden]];
    Ref hermano; u32 x0c [[hidden]];
    Ref hijo; u32 x14 [[hidden]];
    Ref padre; u32 x1c [[hidden]];
    TipoControl tipo;
    u16 dato [[comment("DATATYPE (y MASK en el nibble alto); BARTYPE; PANELTYPE; borde de BUTTON")]];
    u32 x24 [[color(GRIS)]];
    u32 numero; u32 x2c [[hidden]];
    u32 nombre [[comment("posición en IDE / 4, más 1 (0 = sin nombre)")]]; u32 x34 [[hidden]];
    u16 x; u16 y; u16 ancho; u16 alto;
    u16 x40 [[comment("NUMBER, Char(n), DECIMAL(p,s) o el comando de un botón")]];
    u16 fuente [[comment("1 + índice en FON")]];
    u32 bits44 [[comment("ATTACH, ALIGNMENT, NOTABSTOP, READONLY, CURSOR…")]];
    Ref label; u32 x4c [[hidden]];
    u32 fondo [[comment("COLORREF; 0x80000000 sin color; 0xC0000000 transparent")]];
    u32 texto;
    Ref tags_o_focus; u32 x5c [[hidden]];
    u16 pagina [[comment("PAGE n − 1")]];
    u16 x62 [[comment("SHOW n LINES; CURRENT PAGE n − 1")]];
    u32 x64 [[hidden]];
    u32 x68 [[comment("binario de SVL (listas, TAB), RANGE de SLIDER, raíz de un MENU")]];
    u32 x6c [[hidden]];
    u32 icono [[comment("(n − 1) << 16 | índice en ICO")]];
    u32 x74 [[hidden]];
    Ref variable [[comment("FOB")]]; u32 x7c [[hidden]];
    Ref comentario; u32 x84 [[hidden]];
    Ref clase [[comment("ECL: SimpleFormControl")]]; u32 x8c [[hidden]];
    u8 x90[0x40] [[color(GRIS), comment("listas: +0xA8 bits y +0xB0 columnas/CURSORTYPE")]];
} [[format("fmt_fct")]];

fn fmt_fct(Control c) { return std::format("{} · {} {} {} {}", c.tipo, c.x, c.y, c.ancho, c.alto); };

// --- LIB e INC (24 bytes): LIBRARIES e INCLUDES
struct Libreria {
    u32 cab;
    u32 x04 [[hidden]];
    Ref siguiente; u32 x0c [[hidden]];
    Ref nombre [[comment("EMO")]]; u32 x14 [[hidden]];
} [[format("fmt_lib")]];
fn fmt_lib(Libreria l) { return "librería " + fmt_ref(l.nombre); };

// --- MOP: opciones de menú (104 bytes), en árbol
struct OpcionMenu {
    u8 b0 [[hidden]];
    u8 marcas [[comment("0x40 submenú (MENU), 0x01 CHECKED, 0x02 SEPARATOR detrás; raíz: 0x40")]];
    u16 b2 [[hidden]];
    u32 x04 [[hidden]];
    Ref siguiente; u32 x0c [[hidden]];
    Ref padre; u32 x14 [[hidden]];
    Ref texto; u32 x1c [[hidden]];
    u8 x20[8] [[hidden]];
    u32 orden [[comment("correlativo, lo pone el compilador")]];
    u32 nombre [[comment("posición en IDE / 4, más 1")]];
    u16 comando; u16 x32 [[hidden]];
    u8 x34[12] [[hidden]];
    Ref hijo; u32 x44 [[hidden]];
    u8 x48[0x20] [[color(GRIS)]];
} [[format("fmt_mop")]];
fn fmt_mop(OpcionMenu o) { return "opción " + fmt_ref(o.texto); };

// --- registros sin descifrar
struct Bruto {
    u8 bytes[parent.tam] [[color(GRIS)]];
} [[format("fmt_bruto")]];
fn fmt_bruto(Bruto b) { return "[sin descifrar]"; };

// --- secciones empaquetadas: IDE, STR, SVL
// Un registro de texto acaba en el primer límite cuyo último byte es 0: el primero a
// `primero` bytes, después de `unidad` en `unidad`. Nunca pasa del fin del bloque.
fn largo_texto(u128 q, u128 primero, u128 fin) {
    u128 largo = primero;
    while (q + largo < fin && std::mem::read_unsigned(q + largo - 1, 1) != 0) largo += unidad;
    if (q + largo > fin) return fin - q;
    return largo;
};

struct RegistroEmpaquetado {
    u128 inicio = $;
    u128 fin = parent.fin;
    u32 valor [[hidden]];
    if (valor == 0) {
        char texto[] [[format("fmt_texto")]];
        u8 relleno[largo_texto(inicio, 8, fin) - ($ - inicio)] [[hidden]];
    } else if (parent.parent.parent.etq == "SVL") {
        u8 cuerpo[((valor & 0xFFFF) + unidad - 1) / unidad * unidad - 4] [[color(GRIS), comment("binario: columnas de una lista, páginas de un TAB…")]];
    } else {
        u8 resto[largo_texto(inicio, unidad, fin) - 4] [[color(GRIS), comment("restos de memoria del registro anterior")]];
    }
} [[format("fmt_reg")]];

fn fmt_texto(str t) { return "\"" + t + "\""; };
fn fmt_reg(RegistroEmpaquetado r) {
    if (r.valor == 0) return fmt_texto(r.texto);
    return "[binario o restos]";
};

struct Bloque {
    u16 sin_empaquetar [[comment("el bloque cuenta como si ocupara esto entero (posiciones)")]];
    u16 guardados;
    u128 fin = $ + guardados;
    RegistroEmpaquetado registros[while($ < fin)];
};

struct Empaquetada {
    u32 n;
    u16 nbloques;
    Bloque bloques[nbloques];
};

// --- datos de una sección
// La entrada aún no ha leído su etiqueta ni su número de registros cuando se sigue el
// puntero: se leen de memoria, desde el principio de la entrada.
struct Datos {
    u128 e = addressof(parent);
    str etq = std::mem::read_string(e + 0x14, 3);
    u32 n = std::mem::read_unsigned(e + 0x18, 4);
    u32 tam = std::mem::read_unsigned(e + 0x1C, 4);
    if (etq == "IDE" || etq == "STR" || etq == "SVL") {
        Empaquetada empaquetada;
    } else if (es64 && etq == "REF" && tam == 32) {
        NodoRef nodos[n];
    } else if (es64 && etq == "STM" && tam == 48) {
        Sentencia sentencias[n];
    } else if (es64 && etq == "PRO" && tam == 64) {
        Procedimiento procedimientos[n];
    } else if (es64 && etq == "OBJ" && tam == 80) {
        Objeto objetos[n];
    } else if (es64 && etq == "CLA" && tam == 88) {
        Clase clases[n];
    } else if (es64 && etq == "FCT" && tam == 208) {
        Control controles[n];
    } else if (es64 && (etq == "LIB" || etq == "INC") && tam == 24) {
        Libreria librerias[n];
    } else if (es64 && etq == "MOP" && tam == 104) {
        OpcionMenu opciones[n];
    } else {
        Bruto registros[n];
    }
};

struct Entrada {
    u32 marca [[comment("2 = presente (0 en secciones vacías)")]];
    u32 cero [[hidden]];
    u32 tam_entrada [[hidden]];
    u32 siguiente [[hidden]];
    if (std::mem::read_unsigned($ + 8, 4) > 0) Datos *datos : u32;
    else u32 datos;
    char etiqueta[4] [[format("fmt_etq")]];
    u32 n [[name("registros")]];
    u32 tam_registro;
} [[format("fmt_entrada")]];

fn fmt_etq(str e) { return std::string::substr(e, 0, 3); };
fn fmt_entrada(Entrada e) { return std::format("{} · {} registros de {} bytes", fmt_etq(e.etiqueta), e.n, e.tam_registro); };

struct Cabecera {
    char magia[4];
    u8 fijo[0x1C] [[color(GRIS), comment("36 bytes fijos: sin descifrar")]];
    u32 lista_a;
    u32 lista_b;
    u32 lista_c;
    u32 x2c [[color(GRIS)]];
    u32 messages [[comment("MESSAGES: posición del nombre en IDE / 4 (0xFFFFFFFF sin él)")]];
    u8 x34[24] [[color(GRIS), comment("sin descifrar")]];
};

struct Omd {
    Cabecera cabecera;
    Entrada lista_a[6] @ cabecera.lista_a;
    Entrada lista_b[24] @ cabecera.lista_b;
    Entrada lista_c[7] @ cabecera.lista_c;
};

Omd omd @ 0x00;

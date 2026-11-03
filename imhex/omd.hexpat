#pragma author Hubble
#pragma description MultiBase Cosmos compiled module (.omd)
#pragma magic [ 43 4F 4D 44 ] @ 0x00
#pragma endian little

// Patrón de Hubble para ImHex. Solo describe lo comprobado en docs/formato-omd.md (con la
// vuelta completa: descompilar, recompilar y comparar byte a byte). Lo que sigue siendo
// hipótesis va marcado [hypothesis] y lo que no se entiende va en gris como «not decoded».
// Los registros con estructura son los de 64 bits; en 32 bits se ven en bruto.
// Todo lo que se ve en ImHex (nombres, comentarios y textos) está en inglés.

import std.mem;
import std.string;
import std.core;
import std.io;

#define GREY "505050"

// 32 o 64 bits, por el tamaño de registro de REF (16 / 32 bytes): entrada 18 de la lista B.
u32 ref_size_ = std::mem::read_unsigned(std::mem::read_unsigned(0x24, 4) + 18 * 32 + 0x1C, 4);
u8 unit = ref_size_ == 32 ? 8 : 4;
bool is64 = ref_size_ == 32;

// --- referencias entre registros: byte 1 = número de sección, 16 bits altos = índice
// (en IDE y STR, la posición en el flujo / 4).
fn section_name(u8 s) {
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
    u8 section;
    u16 index;
} [[format("fmt_ref"), single_color]];

fn fmt_ref(Ref r) {
    if (r.section == 0 && r.index == 0 && r.b0 == 0) return "—";
    str s = section_name(r.section);
    if (s == "") return std::format("→ ?{:02X}? {}  [not decoded]", r.section, r.index);
    if (s == "IDE" || s == "STR") return std::format("→ {} @{}", s, r.index * 4);
    return std::format("→ {} {}", s, r.index);
};

// --- REF: nodos del árbol de expresiones (32 bytes). Los operadores son llamadas a métodos:
// `a = 1` es `a.=(1)`, y el nodo del método lleva en +0x18 el código del operador.
enum NodeType : u8 {
    control      = 0x00,  // de formulario (+0x10 → FCT)
    variable     = 0x10,  // +0x10 → OBJ, FOB o EOB (propiedad)
    property     = 0x11,  // `obj.prop`: +0x10 objeto, +0x18 la propiedad
    method       = 0x20,  // +0x10 → EPR o PRO; +0x18 operador o puntero a su nombre en IDE
    member       = 0x21,  // `obj.metodo`: +0x10 objeto, +0x18 método
    call         = 0x22,  // +0x10 lo llamado, +0x18 primer argumento
    lit_smallint = 0x60,  // variante 0x31: `self`
    lit_integer  = 0x70,
    lit_decimal  = 0x80,  // +0x18 → DEC
    lit_char     = 0x90,  // +0x18 → STR
    lit_boolean  = 0xA0,
    lit_null     = 0xC0,
    list         = 0xD0,  // `in (…)` y argumentos variables: +0x08 primer elemento
    switch_value = 0xE0
};

fn operator(u64 c) {
    if (c == 0) return "implicit conversion"; if (c == 1) return "="; if (c == 2) return "**";
    if (c == 3) return "*"; if (c == 4) return "/"; if (c == 5) return "%"; if (c == 6) return "*=";
    if (c == 7) return "/="; if (c == 8) return "%="; if (c == 9) return "+"; if (c == 10) return "-";
    if (c == 11) return "+="; if (c == 12) return "-="; if (c == 13) return "++"; if (c == 14) return "--";
    if (c == 15) return "not"; if (c == 16) return "and"; if (c == 17) return "xor"; if (c == 18) return "or";
    if (c == 19) return "<>"; if (c == 20) return ">"; if (c == 21) return ">="; if (c == 22) return "<";
    if (c == 23) return "<="; if (c == 24) return "matches"; if (c == 25) return "like";
    if (c == 26) return "between"; if (c == 27) return "in"; if (c == 28) return "is null";
    if (c == 29) return "is not null"; if (c == 30) return "[ ] (index)"; if (c == 31) return "==";
    if (c == 33) return "- (unary)";
    return "";
};

fn is_literal(u8 t) { return t >= 0x60 && t <= 0xC0 && t != 0xB0; };

struct RefNode {
    u8 t_ = std::mem::read_unsigned($, 1);
    NodeType type;
    u8 variant [[comment("0xF0 literal; 0x50 constant or class written before it; 0x31 self/control; 0x40 parent")]];
    u8 b2 [[color(GREY), comment("not decoded")]];
    u8 own_section [[comment("0x07 in REF")]];
    u32 x04 [[color(GREY), comment("not decoded")]];
    Ref next [[comment("chained arguments and elements")]];
    u32 x0c [[hidden]];
    Ref r10;
    u32 x14 [[hidden]];
    if (type == NodeType::lit_smallint) {
        s16 value; u8 rest[6] [[comment("garbage = default argument")]];
    } else if (type == NodeType::lit_integer) {
        s32 value; u32 rest [[comment("garbage = default argument")]];
    } else if (type == NodeType::lit_boolean) {
        u32 value; u32 rest [[comment("0 or cccccccc if written; anything else: default")]];
    } else if (type == NodeType::lit_char || type == NodeType::lit_decimal) {
        Ref value; u32 x1c [[hidden]];
    } else if (type == NodeType::method) {
        u64 code [[comment("operator code (< 0x10000) or compiler memory pointer")]];
    } else if (type == NodeType::property || type == NodeType::member || type == NodeType::call) {
        Ref r18; u32 x1c [[hidden]];
    } else {
        u64 x18 [[comment("compiler memory pointer (the name in IDE) or value")]];
    }
} [[format("fmt_node")]];

fn fmt_node(RefNode n) {
    if (n.type == NodeType::lit_smallint && n.variant == 0x31) return "self";
    if (n.type == NodeType::lit_smallint || n.type == NodeType::lit_integer) return std::format("literal {}", n.value);
    if (n.type == NodeType::lit_boolean) return n.value == 1 ? "literal true" : "literal false";
    if (n.type == NodeType::lit_null) return "literal null";
    if (n.type == NodeType::lit_char) return "literal char " + fmt_ref(n.value);
    if (n.type == NodeType::lit_decimal) return "literal decimal " + fmt_ref(n.value);
    if (n.type == NodeType::method && n.code < 0x10000) return "method «" + operator(n.code) + "»";
    if (n.type == NodeType::method) return "named method " + fmt_ref(n.r10);
    if (n.type == NodeType::variable) return "variable " + fmt_ref(n.r10);
    if (n.type == NodeType::property) return "property";
    if (n.type == NodeType::member) return "member access obj.method";
    if (n.type == NodeType::call) return "call";
    if (n.type == NodeType::list) return "list";
    if (n.type == NodeType::control) return "control " + fmt_ref(n.r10);
    return std::format("node 0x{:02X} [not decoded]", n.t_);
};

// --- STM: sentencias (48 bytes), lista enlazada por +0x08.
// `if`, `for`, `return`… son palabras reservadas del lenguaje de patrones: van con mayúscula.
enum StatementType : u8 {
    BeginEnd = 0x00, If = 0x01, Expression = 0x02, Return = 0x03, For = 0x04, While = 0x05,
    Loop = 0x06, Repeat = 0x07, Break = 0x08, SwitchValue = 0x0A, SwitchConditions = 0x0B,
    CaseCondition = 0x0C, CaseValue = 0x0D, Default = 0x0E, Empty = 0x0F, ForList = 0x11,
    ForDownTo = 0x24
};

struct Statement {
    StatementType type;
    u8 b1[3] [[color(GREY)]];
    u32 x04 [[hidden]];
    Ref next;
    u32 x0c [[hidden]];
    Ref r10 [[comment("condition / for variable")]];
    u32 x14 [[hidden]];
    Ref r18 [[comment("then / first / limit / first case")]];
    u32 x1c [[hidden]];
    Ref r20 [[comment("expression / return or switch value / step")]];
    u32 x24 [[hidden]];
    Ref r28 [[comment("else / body / default")]];
    u32 x2c [[hidden]];
} [[format("fmt_stm")]];

fn fmt_stm(Statement s) { return std::format("{}  · next {}", s.type, fmt_ref(s.next)); };

// --- PRO: procedimientos (64 bytes)
enum ProcType : u8 {
    main_ = 0, function = 1, form_event = 4, control_event = 5, table_event = 6,
    on_command = 7, dll = 9, javaclass = 0x0D
};

struct Procedure {
    ProcType type;
    u8 b1 [[comment("0x04: returns nothing; 0x80: `On event X control Y`")]];
    u8 b2 [[color(GREY)]];
    u8 b3 [[comment("0x20: private")]];
    u32 x04 [[hidden]];
    Ref next; u32 x0c [[hidden]];
    Ref parameters [[comment("first OBJ")]]; u32 x14 [[hidden]];
    Ref class [[comment("owning CLA")]]; u32 x1c [[hidden]];
    Ref r20 [[comment("return class; in control events, the control")]]; u32 x24 [[hidden]];
    Ref r28 [[comment("name (IDE); in events: the code or the name in STR")]]; u32 x2c [[hidden]];
    Ref r30 [[comment("first local (OBJ); in dll and javaclass, the DLL or the class in STR")]]; u32 x34 [[hidden]];
    Ref body [[comment("first statement")]]; u32 x3c [[hidden]];
} [[format("fmt_pro")]];

fn fmt_pro(Procedure p) { return std::format("{} · name {}", p.type, fmt_ref(p.r28)); };

// --- OBJ: objetos (80 bytes): globales, locales, parámetros y miembros de Struct
struct Object {
    u8 type [[comment("0 global, 1 local, 2 parameter, 3 member; +0x40 VAR")]];
    u8 b1 [[color(GREY)]];
    u8 b2 [[comment("0x20: has default")]];
    u8 b3 [[color(GREY)]];
    u32 x04 [[hidden]];
    Ref next; u32 x0c [[hidden]];
    Ref name; u32 x14 [[hidden]];
    Ref class; u32 x1c [[hidden]];
    Ref procedure; u32 x24 [[hidden]];
    u64 default_value [[comment("same as a literal's value")]];
    u16 length [[comment("Char(n), or Decimal precision; 0xFFFF0000 overall = from a table")]];
    s16 scale;
    u8 x34[12] [[color(GREY)]];
    Ref element [[comment("ArgList of X")]]; u32 x44 [[hidden]];
    u8 x48[8] [[color(GREY)]];
} [[format("fmt_obj")]];

fn fmt_obj(Object o) { return std::format("object · name {} · class {}", fmt_ref(o.name), fmt_ref(o.class)); };

// --- CLA: clases (88 bytes); CLA 0 es el propio módulo
struct Class {
    u8 base_type [[comment("Struct 0x20, Form 0x21, Menu 0x22, Page 0x23, Array 0x24…; +0x80 abstract")]];
    u8 b1[2] [[color(GREY)]];
    u8 b3 [[comment("0x10: written in the source (without it, created by the compiler)")]];
    u32 x04 [[hidden]];
    Ref next; u32 x0c [[hidden]];
    Ref name; u32 x14 [[hidden]];
    Ref base; u32 x1c [[hidden]];
    Ref module [[comment("EMO")]]; u32 x24 [[hidden]];
    u8 x28[12] [[color(GREY)]];
    u32 array_size;
    u8 x38[8] [[color(GREY)]];
    Ref r40 [[comment("form (FOR), Array elements, members (OBJ) or menu (MNU)")]]; u32 x44 [[hidden]];
    u32 x48 [[color(GREY)]]; u32 x4c [[hidden]];
    Ref procedures [[comment("first PRO")]]; u32 x54 [[hidden]];
} [[format("fmt_cla")]];

fn fmt_cla(Class c) { return std::format("class · name {} · base {}", fmt_ref(c.name), fmt_ref(c.base)); };

// --- FCT: controles de formulario (208 bytes); FCT 0 es el formulario
enum ControlType : u16 {
    form = 0, BUTTON = 1, RADIO = 2, CHECK = 3, DROPLIST = 4, DROPEDIT = 5, EDIT = 6, TEXT = 7,
    BOX = 8, PERCENT = 0x0A, TAB = 0x0B, BUTTONGROUP = 0x0C, LIST = 0x0D, BOXGROUP = 0x0E,
    BITMAP = 0x0F, BAR = 0x10, PANEL = 0x11, USER = 0x13, MENU = 0x14, GRID = 0x15, SPIN = 0x17,
    SLIDER = 0x18, MDICLIENT = 0x1B
};

struct Control {
    u32 bits [[comment("border, LABEL, TAGS, COMMENT… and others depending on the type (docs/formato-omd.md)")]];
    u32 x04 [[hidden]];
    Ref sibling; u32 x0c [[hidden]];
    Ref child; u32 x14 [[hidden]];
    Ref container; u32 x1c [[hidden]];
    ControlType type;
    u16 data [[comment("DATATYPE (and MASK in the high nibble); BARTYPE; PANELTYPE; BUTTON border")]];
    u32 x24 [[color(GREY)]];
    u32 number; u32 x2c [[hidden]];
    u32 name [[comment("position in IDE / 4, plus 1 (0 = no name)")]]; u32 x34 [[hidden]];
    u16 x; u16 y; u16 width; u16 height;
    u16 x40 [[comment("NUMBER, Char(n), DECIMAL(p,s) or a button's command")]];
    u16 font [[comment("1 + index in FON")]];
    u32 bits44 [[comment("ATTACH, ALIGNMENT, NOTABSTOP, READONLY, CURSOR…")]];
    Ref label; u32 x4c [[hidden]];
    u32 background [[comment("COLORREF; 0x80000000 no color; 0xC0000000 transparent")]];
    u32 foreground;
    Ref tags_or_focus; u32 x5c [[hidden]];
    u16 page [[comment("PAGE n − 1")]];
    u16 x62 [[comment("SHOW n LINES; CURRENT PAGE n − 1")]];
    u32 x64 [[hidden]];
    u32 x68 [[comment("SVL binary (lists, TAB), SLIDER RANGE, root of a MENU")]];
    u32 x6c [[hidden]];
    u32 icon [[comment("(n − 1) << 16 | index in ICO")]];
    u32 x74 [[hidden]];
    Ref variable [[comment("FOB")]]; u32 x7c [[hidden]];
    Ref comment; u32 x84 [[hidden]];
    Ref class [[comment("ECL: SimpleFormControl")]]; u32 x8c [[hidden]];
    u8 x90[0x40] [[color(GREY), comment("lists: +0xA8 bits and +0xB0 columns/CURSORTYPE")]];
} [[format("fmt_fct")]];

fn fmt_fct(Control c) { return std::format("{} · {} {} {} {}", c.type, c.x, c.y, c.width, c.height); };

// --- LIB e INC (24 bytes): LIBRARIES e INCLUDES
struct Library {
    u32 head;
    u32 x04 [[hidden]];
    Ref next; u32 x0c [[hidden]];
    Ref name [[comment("EMO")]]; u32 x14 [[hidden]];
} [[format("fmt_lib")]];
fn fmt_lib(Library l) { return "library " + fmt_ref(l.name); };

// --- MOP: opciones de menú (104 bytes), en árbol
struct MenuOption {
    u8 b0 [[hidden]];
    u8 flags [[comment("0x40 submenu (MENU), 0x01 CHECKED, 0x02 SEPARATOR after it; root: 0x40")]];
    u16 b2 [[hidden]];
    u32 x04 [[hidden]];
    Ref next; u32 x0c [[hidden]];
    Ref owner; u32 x14 [[hidden]];
    Ref text; u32 x1c [[hidden]];
    u8 x20[8] [[hidden]];
    u32 order [[comment("sequential, set by the compiler")]];
    u32 name [[comment("position in IDE / 4, plus 1")]];
    u16 command; u16 x32 [[hidden]];
    u8 x34[12] [[hidden]];
    Ref child; u32 x44 [[hidden]];
    u8 x48[0x20] [[color(GREY)]];
} [[format("fmt_mop")]];
fn fmt_mop(MenuOption o) { return "option " + fmt_ref(o.text); };

// --- registros sin descifrar
struct Raw {
    u8 bytes[parent.size] [[color(GREY)]];
} [[format("fmt_raw")]];
fn fmt_raw(Raw b) { return "[not decoded]"; };

// --- secciones empaquetadas: IDE, STR, SVL
// Un registro de texto acaba en el primer límite cuyo último byte es 0: el primero a
// `first` bytes, después de `unit` en `unit`. Nunca pasa del fin del bloque.
fn text_length(u128 q, u128 first, u128 end) {
    u128 length = first;
    while (q + length < end && std::mem::read_unsigned(q + length - 1, 1) != 0) length += unit;
    if (q + length > end) return end - q;
    return length;
};

struct PackedRecord {
    u128 start = $;
    u128 end = parent.end;
    u32 value [[hidden]];
    if (value == 0) {
        char text[] [[format("fmt_text")]];
        u8 pad[text_length(start, 8, end) - ($ - start)] [[hidden]];
    } else if (parent.parent.parent.tag == "SVL") {
        u8 body[((value & 0xFFFF) + unit - 1) / unit * unit - 4] [[color(GREY), comment("binary: list columns, TAB pages…")]];
    } else {
        u8 rest[text_length(start, unit, end) - 4] [[color(GREY), comment("leftover memory from the previous record")]];
    }
} [[format("fmt_rec")]];

fn fmt_text(str t) { return "\"" + t + "\""; };
fn fmt_rec(PackedRecord r) {
    if (r.value == 0) return fmt_text(r.text);
    return "[binary or leftovers]";
};

struct Block {
    u16 unpacked [[comment("the block counts as if it took up all of this (positions)")]];
    u16 stored;
    u128 end = $ + stored;
    PackedRecord records[while($ < end)];
};

struct Packed {
    u32 n;
    u16 block_count;
    Block blocks[block_count];
};

// --- datos de una sección
// La entrada aún no ha leído su etiqueta ni su número de registros cuando se sigue el
// puntero: se leen de memoria, desde el principio de la entrada.
struct Data {
    u128 e = addressof(parent);
    str tag = std::mem::read_string(e + 0x14, 3);
    u32 n = std::mem::read_unsigned(e + 0x18, 4);
    u32 size = std::mem::read_unsigned(e + 0x1C, 4);
    if (tag == "IDE" || tag == "STR" || tag == "SVL") {
        Packed packed;
    } else if (is64 && tag == "REF" && size == 32) {
        RefNode nodes[n];
    } else if (is64 && tag == "STM" && size == 48) {
        Statement statements[n];
    } else if (is64 && tag == "PRO" && size == 64) {
        Procedure procedures[n];
    } else if (is64 && tag == "OBJ" && size == 80) {
        Object objects[n];
    } else if (is64 && tag == "CLA" && size == 88) {
        Class classes[n];
    } else if (is64 && tag == "FCT" && size == 208) {
        Control controls[n];
    } else if (is64 && (tag == "LIB" || tag == "INC") && size == 24) {
        Library libraries[n];
    } else if (is64 && tag == "MOP" && size == 104) {
        MenuOption options[n];
    } else {
        Raw records[n];
    }
};

struct Entry {
    u32 marker [[comment("2 = present (0 in empty sections)")]];
    u32 zero [[hidden]];
    u32 entry_size [[hidden]];
    u32 next [[hidden]];
    if (std::mem::read_unsigned($ + 8, 4) > 0) Data *data : u32;
    else u32 data;
    char tag[4] [[format("fmt_tag")]];
    u32 n [[name("records")]];
    u32 record_size;
} [[format("fmt_entry")]];

fn fmt_tag(str e) { return std::string::substr(e, 0, 3); };
fn fmt_entry(Entry e) { return std::format("{} · {} records of {} bytes", fmt_tag(e.tag), e.n, e.record_size); };

struct Header {
    char magic[4];
    u8 fixed[0x1C] [[color(GREY), comment("36 fixed bytes: not decoded")]];
    u32 list_a;
    u32 list_b;
    u32 list_c;
    u32 x2c [[color(GREY)]];
    u32 messages [[comment("MESSAGES: position of the name in IDE / 4 (0xFFFFFFFF if none)")]];
    u8 x34[24] [[color(GREY), comment("not decoded")]];
};

struct Omd {
    Header header;
    Entry list_a[6] @ header.list_a;
    Entry list_b[24] @ header.list_b;
    Entry list_c[7] @ header.list_c;
};

Omd omd @ 0x00;

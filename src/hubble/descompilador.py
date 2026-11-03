"""Descompilador de módulos .omd a fuente COOL (.SMD), de momento solo 64 bits.

Lo que se sabe del formato del código está en docs/formato-omd.md («el código»).
En resumen:
- Las referencias entre registros son u32: byte 1 = número de sección (`SECCION`),
  16 bits altos = índice.
- `PRO`: procedimientos. `OBJ`: objetos (parámetros y locales). `STM`: sentencias,
  cada una con su tipo y enlazada con la siguiente. `REF`: nodos de expresión.
- Los operadores son llamadas a métodos de clase: `a = 1` es `a.=(1)`. El nodo del
  método lleva el código del operador o, si tiene nombre, un puntero de memoria del
  compilador a su identificador en `IDE`.
"""
from __future__ import annotations

import datetime
import re
import struct
from collections import defaultdict
from decimal import Decimal

from . import contenedor, empaquetado

# Número de sección de las referencias (no es la posición de la sección en el fichero).
IDE, STR, DEC, LIB, INC, CLA, OBJ, MNU, MOP, PRO, PAG, FOR, FTA, STM, REF, FCT, FOB, EMO, ECL, EOB, EPR = (
    0x01, 0x02, 0x03, 0x04, 0x05, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x14, 0x0E, 0x0F, 0x10, 0x12, 0x18, 0x19, 0x1A, 0x1B)
# Procedimientos externos (sin cuerpo): tipo de PRO → palabra de la declaración.
EXTERNOS = {0x09: "dll", 0x0D: "javaclass"}
SIN_RETURN = 0x04  # bit del byte 1 de PRO: la función no devuelve nada
# `public self dll …` / `public self javaclass …`: bit 0x20 del byte 1 de un PRO externo (batería clases.py, sd_ y sj_;
# manual refer ref00030: el objeto se pasa por referencia como primer parámetro, que no deja OBJ). El 0x01 del byte 1
# lo llevan todos los externos del corpus (904); el byte 2, siempre 0, y el byte 3, 0x05 más la visibilidad.
SELF_EXTERNO = 0x20
BITS_EXTERNO = 0x01 | SIN_RETURN | SELF_EXTERNO
# Visibilidad: campo 0x30 del byte 3 de CLA, PRO y OBJ (batería clases.py). 1 = public (la de por defecto: escrita
# o no, los mismos bytes), 2 = protected, 3 = private; 0, en las clases implícitas, main y los eventos. Las variables
# locales y los parámetros llevan siempre 3.
VISIBILIDAD = {1: "public", 2: "protected", 3: "private"}
CONVERSION = "conversión"  # en orden_ide: un método sin nombre que puede ser una conversión implícita
OPERADOR, CONVERSOR = 2, 3  # tipos de PRO (byte 0): `operator <op> (…)` y `conversor <clase>`
# Propiedad implícita (el valor de un control: `medit = "x"`): su nombre no está en IDE sino en
# la memoria estática del compilador; esta dirección es la de cosmakecon 8.6 x64.
VALOR_IMPLICITO = 0x1401A1358
VALOR_IMPLICITO_PAG = 0x1401A14FC  # el de un control de página
# El mismo valor implícito en los .omd que trae el kit (proyectos): otra compilación del compilador, con la memoria
# estática en otro sitio. 15 usos, todos donde el fuente asigna a un control sin propiedad (`barra = "x"`).
VALOR_IMPLICITO_KIT = 0x14019D1F8
VALORES_IMPLICITOS = (VALOR_IMPLICITO, VALOR_IMPLICITO_PAG, VALOR_IMPLICITO_KIT)
# En 32 bits: 0x4EAD6C con cosmakecon 8.6 x86 (lo compilado aquí: 53 de 53 donde el mismo fuente en 64 lleva uno de
# los de arriba, también el de página), y 0x4AF250, 0x4AF258 y 0x4AF484 en los .omd x86 del kit (20 por versión,
# todos VALOR_IMPLICITO_KIT en 64). Ninguno sale con otro valor en 64.
VALORES_IMPLICITOS_32 = (0x4EAD6C, 0x4AF250, 0x4AF258, 0x4AF484)
# Un smallint escrito, en los .omd del kit, lleva tras su valor 0x14 y ceros (aquí, 0x11) o dos ceros y el relleno
# de MSVC: 44 argumentos de ALMAFAC y prjbmapsdll, todos escritos en su fuente; lo compilado aquí no los da nunca.
ESCRITO_KIT = (bytes([0x14, 0, 0, 0, 0, 0]), bytes([0, 0, 0xCC, 0xCC, 0xCC, 0xCC]))  # 0xCC: RELLENO
# En los de 32 bits, escritos y por defecto llevan lo mismo, 0xCC 0xCC y ceros (327 escritos y 24 por defecto frente a
# los de 64 bits con el mismo fuente). Los que quedan sin decidir por la posición (delante de la llamada) llevan,
# escritos, la variante normal (0xF0 en el byte 1): 123 de 123 en el kit y en lo compilado aquí en 32 bits, según
# el mismo fuente en 64. Un por defecto delante de la llamada solo sale con la variante 0x60 (12 en 64 bits, todos
# en PivotDevExtreme), que no se sabe leer; con otra variante, NoSoportado.
AMBIGUO_32 = bytes([0xCC, 0xCC, 0, 0, 0, 0])
VARIANTE_NORMAL = 0xF0
EVENTOS_FORM = {1: "Open", 2: "Close", 24: "ExMessage", 25: "Timer", 67: "ChangeSize"}  # 24: samples SNDMSG
# Eventos del módulo (PRO de tipo 0x0C): código en +0x28. samples COSMOSJAVA `On Error`, el único visto.
EVENTO_MODULO, EVENTOS_MODULO = 0x0C, {36: "Error"}
# Eventos de tabla (`On Fetch Table x`, PRO de tipo 6): código en +0x28. Batería evtablas.py; el nombre distingue
# mayúsculas. Error, BeginGroup, EndGroup, Eof y Locked no lo son («Unknown table event»).
EVENTOS_TABLA = {13: "Fetch", 15: "Add", 16: "Update", 17: "Delete", 18: "RowChanged", 19: "Edit", 20: "AcceptEdit",
                 21: "CancelEdit", 22: "QueryBegin", 23: "QueryEnd", 35: "ReFetch", 41: "ChangingRow"}

BINARIOS = {1: "=", 2: "**", 3: "*", 4: "/", 5: "%", 6: "*=", 7: "/=", 8: "%=", 9: "+", 10: "-", 11: "+=", 12: "-=",
            16: "and", 17: "xor", 18: "or", 19: "<>", 20: ">", 21: ">=", 22: "<", 23: "<=", 24: "matches", 25: "like",
            31: "=="}
PREFIJOS = {13: "++", 14: "--", 15: "not ", 33: "-"}
BETWEEN, IN, IS_NULL, IS_NOT_NULL, INDICE = 26, 27, 28, 29, 30  # INDICE: a[i] y a[i, j]
# Precedencia: mayor = se aplica antes. `not` va antes que las comparaciones
# (`not a > 1` es `(not a) > 1`).
PREC = {"=": 0, "+=": 0, "-=": 0, "*=": 0, "/=": 0, "%=": 0, "or": 1, "xor": 1, "and": 2, "==": 4, "<>": 4, "<": 4,
        "<=": 4, ">": 4, ">=": 4, "between": 4, "in": 4, "is null": 4, "like": 4, "matches": 4, "+": 5, "-": 5,
        "*": 6, "/": 6, "%": 6, "**": 6.5}
PREC_PREFIJO, PREC_MIEMBRO, PREC_ATOMO = 7, 9, 10
# Literales: tipo de nodo (byte 0 del primer u32 de su registro de REF).
LIT_SMALLINT, LIT_INTEGER, LIT_DECIMAL, LIT_CHAR, LIT_BOOLEAN, LIT_NULL = 0x60, 0x70, 0x80, 0x90, 0xA0, 0xC0
VARTABLE, SIN_IS = 0x08, 0x04  # byte 0 de +0x00 de una FTA: `Vartable` (y sin `is tabla`)
ESCRITA = 0x10  # byte 3 de +0x00 de un FOB de columna: escrita en el fuente (sin él, la añade el compilador)
REQUIRED, NOENTRY, NOUPDATE = 0x400, 0x800, 0x1000  # bits de +0x00 de una columna (FOB) de tabla de formulario
LITERALES = {LIT_SMALLINT, LIT_INTEGER, LIT_DECIMAL, LIT_CHAR, LIT_BOOLEAN, LIT_NULL}
VARIABLE, PROPIEDAD, METODO, ACCESO, LLAMADA, LISTA = 0x10, 0x11, 0x20, 0x21, 0x22, 0xD0
CONSTANTE = 0x50  # byte 1 de un literal que viene de una constante del módulo
EXTERNA = 0x60  # byte 1 de un literal que viene de una constante de un módulo incluido: su nombre, solo en IDE
PREDEFINIDAS = {"3.141592653589793238462643383": "PI"}  # constantes del lenguaje, por su valor (variante CONSTANTE)
TABLA = 0x30  # bytes 0 y 1 de una tabla del formulario usada como objeto (`tabla.Metodo()`): +0x10 → su FTA
CON_CLASE = 0x50  # byte 1 de un método sin receptor llamado con su clase delante
# `objeto.control` (samples dbl: `Miform.milist.AddString("a1")`): nodo 0x01 0x01 con el objeto en +0x10 y, en +0x18,
# el control, un nodo 0x00 con la variante 0x21 (dentro de su formulario es 0x31); +0x10 → su FCT, o su PCT.
MIEMBRO_CONTROL, CONTROL_DE_OBJETO = 0x01, 0x21
# `objeto.opcion` de un menú (samples MENU: `mm.a.Add(…)`): nodo 0xF1 0x00 con el objeto en +0x10 y, en +0x18, la
# opción, un nodo 0xF0 0x20 con +0x10 → su MOP (el nombre, en IDE por su +0x2C, como al escribir el menú).
MIEMBRO_OPCION, OPCION = bytes([0xF1, 0x00]), bytes([0xF0, 0x20])
# Valores de un Enum y de un EnumSet (samples ENUM), con +0x10 → la CLA de su clase: de un Enum, nodo 0xB0 0x50 con el
# índice en +0x18; de un EnumSet, nodo 0x10 0x51 con la máscara (1 << índice) en +0x18.
VALOR_ENUM, VALOR_ENUMSET = bytes([0xB0, 0x50]), bytes([0x10, 0x51])
RELLENO = 0xCC  # memoria sin iniciar de MSVC
# Palabras reservadas: nodo con byte 1 = 0xF1 y su clase en +0x10.
PALABRAS = {"Date": "today", "Time": "now", "DateTime": "current"}  # current: samples GETSYSTEMTYMEUTC
SANGRIA = "    "
BASICOS = {"char", "integer", "smallint", "decimal", "money", "boolean", "date", "time", "datetime", "numeric", "simple"}


# Ficheros de 32 bits: posición en 64 bits → posición en 32 de cada u32, por sección.
# Deducido comparando los módulos que los kits traen compilados en las dos arquitecturas
# (579 pares): en 64 bits los punteros y referencias ocupan huecos de 8 bytes; en 32, de 4.
def _mitad(tam64):
    return {o: o // 2 for o in range(0, tam64, 8)}


MAPA_32 = {
    "REF": _mitad(32), "STM": _mitad(48), "PRO": _mitad(64), "LIB": _mitad(24), "INC": _mitad(24), "ECL": {0: 0}, "EPR": {0: 0},
    # OBJ +0x40: la clase X de un parámetro `a as ArgList of X` (samples ChartRadar; batería clases.py, alp_), como en CLA
    "OBJ": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x28: 0x14, 0x30: 0x18, 0x40: 0x24, 0x48: 0x28},
    "CLA": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x30: 0x18, 0x34: 0x1C, 0x40: 0x24, 0x48: 0x28, 0x50: 0x2C},
    "CTE": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x28: 0x14},
    "FOR": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x28: 0x14, 0x30: 0x18},
    "FOB": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x28: 0x14, 0x30: 0x18, 0x48: 0x28,
            0x50: 0x2C, 0x58: 0x30, 0x60: 0x34, 0x78: 0x40,
            # cadenas (STR) de los valores y de la columna de un lookup: emparejadas por su texto (51/51 y 77/77)
            0x68: 0x38, 0x80: 0x44},
    "FCT": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x24: 0x14, 0x28: 0x18, 0x30: 0x1C,
            0x38: 0x20, 0x3C: 0x24, 0x40: 0x28, 0x44: 0x2C, 0x48: 0x30, 0x50: 0x34, 0x54: 0x38, 0x58: 0x3C,
            0x60: 0x40, 0x68: 0x44, 0x70: 0x48, 0x78: 0x4C, 0x80: 0x50, 0x88: 0x54, 0x90: 0x58, 0x98: 0x5C,
            0xA0: 0x60, 0xA8: 0x64, 0xB0: 0x68, 0xB8: 0x6C},  # +0xB8 CHECKMETHOD (batería formularios.py en 32 bits)
    # Menús (ALMAFAC inicio.omd, 8.2 x86/x64): los u32 sin pareja tienen que ser 0 (ver ESTRICTOS_32).
    "MNU": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C},
    "MOP": {0x00: 0x00, 0x08: 0x04, 0x10: 0x08, 0x18: 0x0C, 0x20: 0x10, 0x28: 0x14, 0x2C: 0x18, 0x30: 0x1C,
            0x40: 0x28, 0x50: 0x30, 0x54: 0x34},
    # Tablas, páginas y controles de página: deducidos con los mismos fuentes compilados aquí en 64 y en 32 bits
    # (samples y baterías, 1339 pares; lab/README.md, «32 bits»). FTA, FJO, FRC y PAG son la mitad exacta (sus
    # referencias a IDE/STR cambian de valor porque IDE y STR se alinean distinto); PCT es como FCT.
    "FTA": _mitad(112), "FJO": _mitad(48), "FRC": _mitad(32), "PAG": _mitad(32), "ECT": {0: 0}, "EFT": {0: 0},
}
MAPA_32["PCT"] = MAPA_32["FCT"]
ESTRICTOS_32 = {"MNU", "MOP"}  # en estas, un u32 de 32 bits que el mapa no lleva y no es 0 → NoSoportado
# Formato 0x3211 (contenedor.VERSION_3211, de un Cosmos más antiguo, solo de 32 bits): FOR, FCT y PCT miden menos
# que en 8.6 de 32 bits, y se pasan a la disposición de 8.6 de 32 bits antes de expandirlos con MAPA_32. Deducido
# comparando campo a campo con los registros de 8.6 de 32 bits (kits x86 y lo compilado aquí): cada campo cuadra en
# todos los registros de los módulos de ese formato que se han visto (punteros dentro de su sección, árbol de
# controles coherente, nombres que existen en IDE, referencias a SVL, FOB, FTA, CLA y ECL válidas). Sin compilador de
# esa versión: nada se ha comprobado con vuelta (AVISO_3211 en toda salida).
# - FOR (28 bytes): los 7 primeros u32 de los 8 de 8.6, en el mismo orden; el último de 8.6 (+0x1C) es siempre 0.
# - FCT y PCT (112 bytes): +0x00 a +0x10 como en 8.6; el u32 de +0x14 junta el u16 bajo del +0x14 de 8.6 (0, o
#   0xFFFF en un MENU) con el número de control de su +0x18 (1..n en el orden de los registros) en el u16 alto; de
#   +0x18 en adelante, el campo de 8.6 cuatro bytes más allá (+0x18 nombre → +0x1C, geometría +0x1C/+0x20 →
#   +0x20/+0x24, … CHECKMETHOD +0x68 → +0x6C); el +0x74 de 8.6 (siempre 0) no está.
AVISO_3211 = "formato 0x3211: sin compilador de esta versión, no comprobado con vuelta"
# u32 del registro 0x3211 que en ese formato han salido siempre a 0: no se sabe si son el campo de 8.6 que les toca;
# con algo, NoSoportado. FCT +0x54/+0x58/+0x5C (8.6 +0x58/+0x5C/+0x60, el FORMAT) y +0x6C; en PCT, de +0x54 al final.
SIN_COMPROBAR_3211 = {"FOR": (), "FCT": (0x54, 0x58, 0x5C, 0x6C), "PCT": (0x54, 0x58, 0x5C, 0x60, 0x64, 0x68, 0x6C)}


def de_3211(et: str, crudo: bytes) -> bytes:
    """Un registro FOR, FCT o PCT del formato 0x3211, con la disposición de 8.6 de 32 bits (32 o 120 bytes)."""
    if len(crudo) != contenedor.TAMANOS_3211[et]:
        raise NoSoportado(f"registro {et} del formato 0x3211 de {len(crudo)} bytes")
    if sueltos := [o for o in SIN_COMPROBAR_3211[et] if crudo[o:o + 4] != bytes(4)]:
        raise NoSoportado(f"registro {et} del formato 0x3211 con datos sin mapa en {[hex(o) for o in sueltos]}")
    if et == "FOR":
        return crudo + bytes(4)
    w = struct.unpack("<28I", crudo)
    if w[5] & 0xFFFF:  # el 0xFFFF de un MENU de 8.6: en 0x3211 no se ha visto ninguno
        raise NoSoportado(f"registro {et} del formato 0x3211 con {w[5] & 0xFFFF:#x} en el u16 bajo de +0x14")
    return struct.pack("<30I", *w[:5], w[5] & 0xFFFF, w[5] >> 16, *w[6:], 0)


TAM_64 = {"LIB": 24, "INC": 24, "MNU": 32, "MOP": 104, "REF": 32, "STM": 48, "PRO": 64, "ECL": 8, "EPR": 8, "OBJ": 80, "CLA": 88, "CTE": 48, "FOR": 64, "FOB": 152, "FCT": 208,
          "FTA": 112, "FJO": 48, "FRC": 32, "PAG": 32, "PCT": 208, "ECT": 8, "EFT": 8}


class NoSoportado(ValueError):
    """El .omd usa algo que el descompilador aún no sabe leer."""


def _ref(w: int):
    """(sección, índice) de una referencia, o None si el u32 no es una referencia."""
    if w == 0 or w & 0xFF:
        return None
    return (w >> 8) & 0xFF, w >> 16


class _Modulo:
    def __init__(self, datos: bytes):
        self.b = datos
        self.omd = contenedor.leer(datos)
        self.bits = self.omd.bits
        self._expandidos: dict = {}
        self.s = {s.etiqueta: s for lista in self.omd.listas for s in lista}
        self.ide = self._flujo("IDE")
        self.str = self._flujo("STR")
        eid = [self.rec("EID", k)[4:].split(b"\0")[0].decode("cp1252") for k in range(self.s["EID"].n)]
        self.ecl = [eid[self.u32("ECL", k, 0) >> 16] for k in range(self.s["ECL"].n)]
        self.declarados = self._declarados()
        self.cadenas_usadas: set[int] = set()  # posiciones de STR que se han escrito como literal
        self.punteros = self._punteros()
        self.por_entrada = self._por_entrada()

    # --- acceso a los registros
    def registros_flujo(self, etiqueta: str) -> dict:
        """Cada registro de IDE, STR o SVL por su posición, la que cuentan las referencias:
        cada bloque cuenta como si ocupara entero su tope (sin empaquetar), aunque guarde
        menos (un registro nunca se parte entre dos bloques)."""
        emp = empaquetado.de_omd(self.b, self.omd, etiqueta)
        inicios, base = [], 0
        for bl in emp.bloques:
            inicios.append((bl.desplazamiento + 4, bl.desplazamiento + 4 + bl.guardado, base))
            base += bl.sin_empaquetar
        salida = {}
        for r in emp.registros:
            ini, _, b0 = next(x for x in inicios if x[0] <= r.desplazamiento < x[1])
            salida[b0 + r.desplazamiento - ini] = r
        return salida

    def _flujo(self, etiqueta: str) -> dict[int, str]:
        return {p: None if r.binario else r.texto() for p, r in self.registros_flujo(etiqueta).items()}

    def rec(self, et: str, k: int) -> bytes:
        s = self.s[et]
        if k is None:
            raise NoSoportado(f"falta una referencia a {et}")
        if not 0 <= k < s.n:
            raise NoSoportado(f"referencia a {et} {k}, que no existe")
        crudo = self.b[s.datos + k * s.tam_registro: s.datos + (k + 1) * s.tam_registro]
        if self.omd.version == contenedor.VERSION_3211 and et in contenedor.TAMANOS_3211:
            crudo = de_3211(et, crudo)
        if self.bits == 64 or et not in MAPA_32:
            if self.bits == 32 and et in contenedor.TAMANOS_POR_BITS and et not in ("EMO",):
                raise NoSoportado(f"registro de {et} en 32 bits, sin mapa")
            return crudo
        # 32 bits: el registro se expande a la disposición de 64, que es la que lee el resto.
        if (et, k) not in self._expandidos:
            if et in ESTRICTOS_32:
                sueltos = [o for o in range(0, len(crudo), 4) if o not in MAPA_32[et].values() and crudo[o:o + 4] != bytes(4)]
                if sueltos:
                    raise NoSoportado(f"registro {et} {k} de 32 bits con datos sin mapa en {[hex(o) for o in sueltos]}")
            salida = bytearray(TAM_64[et])
            for o64, o32 in MAPA_32[et].items():
                if o32 + 4 <= len(crudo):
                    salida[o64:o64 + 4] = crudo[o32:o32 + 4]
            self._expandidos[(et, k)] = bytes(salida)
        return self._expandidos[(et, k)]

    def u32(self, et: str, k: int, off: int) -> int:
        return struct.unpack_from("<I", self.rec(et, k), off)[0]

    def refa(self, et: str, k: int, off: int, seccion: int):
        r = _ref(self.u32(et, k, off))
        return r[1] if r and r[0] == seccion else None

    def texto_ide(self, w: int):
        r = _ref(w)
        return self.ide.get(r[1] * 4) if r and r[0] == IDE else None

    def _declarados(self) -> set[int]:
        """Posiciones de IDE que referencia algún registro fijo con el código 0x01 (declaraciones). La geometría de
        un control (FCT y PCT: x e y en +0x38, ancho y alto en +0x3C; en 32 bits, +0x20 y +0x24 del registro sin
        expandir, y +0x1C y +0x20 en el formato 0x3211) no es una referencia aunque lo parezca: con x o ancho 256 el
        u16 bajo es 0x0100, y y o el alto por 4 pueden caer en el registro de un nombre que no se declara (samples EjDisableAceleradores en 32 bits:
        `POSITION 256 39`, 39 × 4 = 156, el segundo `PutEnv`; batería fct.py geo_ y paginas.py pgeo_)."""
        salida = set()
        for et, s in self.s.items():
            if et in ("IDE", "STR", "SVL") or not s.n:
                continue
            geometria = (0x38, 0x3C) if self.bits == 64 else (0x1C, 0x20) if self.omd.version == contenedor.VERSION_3211 else (0x20, 0x24)
            for k in range(s.n * s.tam_registro // 4):
                if et in ("FCT", "PCT") and 4 * k % s.tam_registro in geometria:
                    continue
                w = struct.unpack_from("<I", self.b, s.datos + 4 * k)[0]
                if w & 0xFFFF == 0x0100 and (w >> 16) * 4 in self.ide:
                    salida.add((w >> 16) * 4)
        return salida

    # --- nombres
    def nombre_obj(self, k: int) -> str:
        return self.texto_ide(self.u32("OBJ", k, 0x10)) or f"obj{k}"

    def nombre_pro(self, k: int) -> str:
        return self.texto_ide(self.u32("PRO", k, 0x28)) or "main"

    def nombre_clase(self, w: int) -> str:
        r = _ref(w)
        if r and r[0] == ECL and r[1] < len(self.ecl):
            return self.ecl[r[1]]
        if r and r[0] == CLA:
            if nombre := self.texto_ide(self.u32("CLA", r[1], 0x10)):
                return nombre
            raise NoSoportado(f"clase CLA {r[1]} sin nombre")  # antes salía un nombre inventado («cla3»)
        raise NoSoportado(f"clase {w:#x} sin interpretar")

    def _por_entrada(self) -> dict[tuple, str]:
        """(EPR o EOB, índice) → el nombre del miembro externo, sacado de los nodos de REF que la usan y cuyo puntero se
        resuelve. Una entrada es un solo miembro: en los 3128 .omd del corpus ninguna da dos nombres (16810 de EPR y
        1540 de EOB). Sirve cuando el puntero de un nodo es una dirección estática del compilador (AGENDA mes:
        `MDY` en 0x14E120 dentro de `myCursor.Open(MDY(…))`) o un puntero dudoso. Si dos nodos dan dos nombres, nada."""
        vistos = defaultdict(set)
        for k in range(self.s["REF"].n):
            r = self.rec("REF", k)
            if r[0] not in (VARIABLE, METODO):
                continue
            p = struct.unpack_from("<Q", r, 0x18)[0]
            if p not in self.punteros:
                continue
            for tabla in (EPR, EOB):
                if (e := self.refa("REF", k, 0x10, tabla)) is not None:
                    vistos[(tabla, e)].add(self.punteros[p])
        return {e: next(iter(ns)) for e, ns in vistos.items() if len(ns) == 1}

    def _punteros(self) -> dict[int, str]:
        """Puntero de memoria → identificador de IDE.

        Cada bloque de IDE estaba en una zona de memoria del compilador, así que la base
        se busca por grupos de punteros cercanos. Una base vale si lleva cada puntero al
        principio de un registro que no es una declaración, y a cada variable a su nombre.
        """
        self.pos_ide: dict[int, int] = {}  # puntero → su posición en IDE (la de su nombre)
        usos = []
        for k in range(self.s["REF"].n):
            r = self.rec("REF", k)
            p = struct.unpack_from("<Q", r, 0x18)[0]
            if r[0] in (VARIABLE, METODO) and p > 0x10000:
                ancla = None
                if r[0] == VARIABLE and (o := self.refa("REF", k, 0x10, OBJ)) is not None:
                    ancla = self.nombre_obj(o)
                if r[0] == METODO and (q := self.refa("REF", k, 0x10, PRO)) is not None:
                    ancla = self.nombre_pro(q)
                usos.append((p, ancla))
        if not usos:
            return {}
        anclas = defaultdict(set)
        for p, a in usos:
            if a:
                anclas[p].add(a.lower())
        libres = {pos for pos in self.ide if pos not in self.declarados}
        ps = sorted({p for p, _ in usos})
        grupos = [[ps[0]]]
        for p in ps[1:]:
            (grupos[-1].append(p) if p - grupos[-1][-1] <= 1300 else grupos.append([p]))
        def vale(b, p):  # la base b lleva p a una posición libre, y a su nombre si es una variable o un método
            return p - b in libres and (not anclas[p] or (self.ide[p - b] or "").lower() in anclas[p])

        elegidos, dudosos = [], set()
        for g in grupos:
            # Un grupo sin ninguna base puede juntar dos bloques de memoria cercanos (prjbmapsdll EjBmapsdll: 86
            # punteros, la mejor base lleva 61): se parte en tramos, cada uno tan largo como le quepa una base.
            tramos, i = [], 0
            while i < len(g):
                candidatas, j = {g[i] - pos for pos in libres if vale(g[i] - pos, g[i])}, i + 1
                while j < len(g) and (siguen := {b for b in candidatas if vale(b, g[j])}):
                    candidatas, j = siguen, j + 1
                tramos.append((g[i:j], candidatas))
                i = j
            # El tramo crece mientras le valga su base, y puede comerse los primeros del siguiente (EjBmapsdll del kit
            # x86: `staticitem1` salía `BMapsLockZoom`; RichText en 32 bits, `RichTextGetProperty` salía `edtMultiline`).
            # Entre dos bloques de memoria hay un solo corte: los últimos del tramo que valen también con la base del
            # siguiente pueden ser de cualquiera de los dos. Si uno de ellos cae, con su base, donde cae uno del
            # siguiente (una aparición en IDE es de un solo puntero), el corte va antes de él. Al revés también: si uno
            # de ellos, con la base del siguiente, cae donde uno seguro del tramo, es del tramo, y con él todos los
            # dudosos de antes (almafac4 lisalba1 del kit x86: `pagina` caería con la base del siguiente en el `acum`
            # de un puntero seguro, a 0x48; `Clear`, delante, también es del tramo). Los demás dudosos se quedan sin
            # nombre.
            for n in range(len(tramos) - 1):
                (t, c), (u, e) = tramos[n], tramos[n + 1]
                if len(c) != 1 or len(e) != 1:
                    continue
                b, b2 = next(iter(c)), next(iter(e))
                i = len(t)
                while i > 1 and vale(b2, t[i - 1]):
                    i -= 1
                del_siguiente = {q - b2 for q in u}
                corte = next((j for j in range(i, len(t)) if t[j] - b in del_siguiente), len(t))
                seguros = {p - b for p in t[:i]}
                ultimo = max((j for j in range(i, corte) if t[j] - b2 in seguros), default=i - 1)
                dudosos.update(t[ultimo + 1:corte])
                tramos[n], tramos[n + 1] = (t[:corte], c), (t[corte:] + u, e)
            if len(tramos) > 1 and not all(len(c) == 1 for _, c in tramos):
                continue  # partido, cada tramo tiene que dar una sola base
            for t, candidatas in tramos:
                if len(candidatas) == 1:
                    b = next(iter(candidatas))
                    elegidos.append((t, b, {p - b for p in t}))
        # Cada aparición en IDE es de un solo puntero: si dos grupos caen en la misma, la base del más pequeño
        # cuadró por casualidad (ActiveX Word: `txtTemplate.Text` salía `txtTemplate.document`) y no vale.
        # Si chocan solo los de un extremo y lo que queda sigue dando una sola base, esos se alargaron con un puntero del
        # otro bloque que cuadraba por casualidad (OutlookActiveX: el último del `On Open`, en el `AttachFile` de un
        # tramo de 39): se quedan sin nombre y el resto vale. Con uno solo que quede, cabe en muchas bases (ActiveX Word).
        def una_base(t):
            return len({b for b in {t[0] - pos for pos in libres} if all(vale(b, p) for p in t)}) == 1

        salida = {}
        for g, base, posiciones in elegidos:
            chocan = {p for p in g if any(p - base in otras and len(otro) >= len(g)
                                          for otro, _, otras in elegidos if otro is not g)}
            if chocan:
                resto = [p for p in g if p not in chocan]
                if not resto or not (chocan == set(g[len(resto):]) or chocan == set(g[:len(chocan)])) or not una_base(resto):
                    continue
                dudosos |= chocan
            salida.update({p: self.ide[p - base] for p in g if p not in dudosos})
            self.pos_ide.update({p: p - base for p in g if p not in dudosos})
        return salida

    # --- literales
    def decimal(self, k: int) -> str:
        d = self.rec("DEC", k)
        exp, pos, nd = struct.unpack_from("<hhh", d, 0)
        if pos == -1:
            return "null"
        valor = sum((Decimal(d[6 + i]) * Decimal(100) ** (exp - 1 - i) for i in range(nd)), Decimal(0))
        texto = format(valor.normalize(), "f")
        return texto if pos else "-" + texto

    def literal(self, r: bytes, clase_ref: int | None = None, con_punto: bool = False) -> str:
        t = r[0]
        if t == LIT_SMALLINT:
            return str(struct.unpack_from("<h", r, 0x18)[0])
        if t == LIT_INTEGER:
            return str(struct.unpack_from("<i", r, 0x18)[0])
        if t == LIT_BOOLEAN:
            return "true" if struct.unpack_from("<I", r, 0x18)[0] else "false"
        if t == LIT_NULL:
            return "null"
        if t == LIT_CHAR:
            ref = _ref(struct.unpack_from("<I", r, 0x18)[0])
            texto = self.str.get(ref[1] * 4) if ref and ref[0] == STR else None
            if texto is None:
                raise NoSoportado("literal char sin cadena en STR")
            self.cadenas_usadas.add(ref[1] * 4)
            if '"' in texto and "'" not in texto:
                return "'" + texto + "'"
            if '"' in texto:
                raise NoSoportado("cadena con comillas simples y dobles")
            return '"' + texto + '"'
        if t == LIT_DECIMAL:
            ref = _ref(struct.unpack_from("<I", r, 0x18)[0])
            if not ref or ref[0] != DEC:
                raise NoSoportado("literal decimal sin registro en DEC")
            texto = self.decimal(ref[1])
            # En una expresión o una constante, con su punto aunque sea entero (CalcALG ScEval `d1 > 0.0`): sin él
            # sería otro literal. En un default, no (`x as Decimal default 0`, el mismo DEC).
            return texto + ".0" if con_punto and texto.lstrip("-").isdigit() else texto
        raise NoSoportado(f"literal {t:#x}")

    def cadenas_apuntadas(self) -> set[int]:
        """Posiciones de STR a las que apunta algún literal char (escrito o no)."""
        salida = set()
        for k in range(self.s["REF"].n):
            r = self.rec("REF", k)
            ref = _ref(struct.unpack_from("<I", r, 0x18)[0])
            if r[0] == LIT_CHAR and ref and ref[0] == STR:
                salida.add(ref[1] * 4)
        for k in range(self.s["CTE"].n):  # el valor de una constante Char (+0x20); el de las demás no es una referencia
            ref = _ref(self.u32("CTE", k, 0x20))
            if ref and ref[0] == STR and self.nombre_clase(self.u32("CTE", k, 0x18)).lower() == "char":
                salida.add(ref[1] * 4)
        for k in range(self.s["CLA"].n):  # los valores de un Enum o EnumSet (+0x40)
            ref = _ref(self.u32("CLA", k, 0x40))
            if ref and ref[0] == STR and self.u32("CLA", k, 0) & 0xFF in (0x08, 0x09):
                salida.add(ref[1] * 4)
        for k in range(self.s["MOP"].n):  # textos de las opciones de menú (+0x18) y su HELP (+0x20)
            for off in (0x18, 0x20):
                ref = _ref(self.u32("MOP", k, off))
                if ref and ref[0] == STR:
                    salida.add(ref[1] * 4)
        for k in range(self.s["FOB"].n):  # columna buscada de un lookup (+0x80)
            ref = _ref(self.u32("FOB", k, 0x80))
            if ref and ref[0] == STR and self.refa("FOB", k, 0x78, 0x15) is not None:
                salida.add(ref[1] * 4)
        for k in range(self.s["FOB"].n):  # boolean values / enumerated de un FOB (+0x68)
            ref = _ref(self.u32("FOB", k, 0x68))
            if ref and ref[0] == STR and self.u32("FOB", k, 0x60):
                salida.add(ref[1] * 4)
        for k in range(self.s["FTA"].n):  # order by de una tabla de formulario (+0x48)
            ref = _ref(self.u32("FTA", k, 0x48))
            if ref and ref[0] == STR:
                salida.add(ref[1] * 4)
        for k in range(self.s["FJO"].n):  # las de las claves externas (columnas que unen)
            for o in (0x20, 0x28):
                ref = _ref(self.u32("FJO", k, o))
                if ref and ref[0] == STR:
                    salida.add(ref[1] * 4)
        for et in ("OBJ", "FOB"):  # default de un Char: la cadena, en +0x28
            for k in range(self.s[et].n):
                r = self.rec(et, k)
                ref = _ref(struct.unpack_from("<I", r, 0x28)[0])
                if r[2] & 0x20 and ref and ref[0] == STR:
                    salida.add(ref[1] * 4)
        for k in range(self.s["PRO"].n):  # nombres de los eventos de control y de las DLL
            r = self.rec("PRO", k)
            ref = _ref(struct.unpack_from("<I", r, 0x30 if r[0] in EXTERNOS else 0x28)[0])
            if r[0] in (5, *EXTERNOS) and ref and ref[0] == STR:
                salida.add(ref[1] * 4)
            control = _ref(struct.unpack_from("<I", r, 0x20)[0])  # `On event X control Y`: Y en STR
            if r[0] == 5 and control and control[0] == STR:
                salida.add(control[1] * 4)
        return salida

    def nombre_fob(self, k: int) -> str:
        """Nombre de una variable de formulario; si es columna de una tabla (+0x50 → FTA), alias.columna."""
        nombre = self.texto_ide(self.u32("FOB", k, 0x10)) or f"fob{k}"
        if (t := self.refa("FOB", k, 0x50, 0x14)) is not None:
            return f"{self.texto_ide(self.u32('FTA', t, 0x10))}.{nombre}"
        return nombre

    def nombre_emo(self, k: int) -> str:
        """Nombre de un módulo externo (librería): en +8 en 64 bits, en +4 en 32."""
        return self.rec("EMO", k)[8 if self.bits == 64 else 4:].split(b"\0")[0].decode("cp1252")

    def librerias(self, etiqueta: str = "LIB") -> list[str]:
        """Las LIBRARIES (o INCLUDES) escritas, en su orden: el registro 0 y siguientes (+0x08),
        cada uno con su nombre en EMO (+0x10). EMO lista además las que estas incluyen."""
        salida, k = [], 0 if self.s[etiqueta].n else None
        while k is not None:
            if self.u32(etiqueta, k, 0x00) != 0x80000000:
                raise NoSoportado(f"{etiqueta} {k} con cabecera {self.u32(etiqueta, k, 0):#x}")
            salida.append(self.nombre_emo(self.refa(etiqueta, k, 0x10, EMO)))
            siguiente = self.u32(etiqueta, k, 0x08)
            k = self.refa(etiqueta, k, 0x08, {"LIB": LIB, "INC": INC}[etiqueta])
            if siguiente and k is None:
                raise NoSoportado(f"{etiqueta}: siguiente {siguiente:#x} sin descifrar")
        return salida

    def constantes(self) -> list[tuple[str, bytes, int]]:
        """(nombre, valor de 8 bytes, clase) de cada constante del módulo."""
        salida = []
        for k in range(self.s["CTE"].n):
            r = self.rec("CTE", k)
            salida.append((self.texto_ide(struct.unpack_from("<I", r, 0x10)[0]), r[0x20:0x28], struct.unpack_from("<I", r, 0x18)[0]))
        return salida


class _Escritor:
    """De los registros a texto COOL."""

    def __init__(self, m: _Modulo, repositorio: str | None = None, catalogo=None):
        self.m = m
        self.repositorio = repositorio
        self.catalogo = catalogo  # repositorio.Catalogo: las columnas, para `x as tabla.columna`
        self.tabla_de_columna: dict[int, str] = {}  # FOB de una columna → su tabla del repositorio
        self.usa_repositorio = False
        self.tablas_elegidas: list[str] = []  # las de los `x as tabla.columna` ya escritos: se prefieren
        self.fobs_de_columna: set[int] = set()  # FOB Money/Decimal escritos `as tabla.columna` por la máscara de LIKEVAR
        self.avisos: list[str] = []
        self.orden_ide: list = []  # (posición en IDE, o None o «?», nodo) de lo escrito del procedimiento (con_externas)
        self.externas: dict[str, bytes] = {}  # constante de un módulo incluido → su valor
        self.metodos_ide: dict[int, str] = {}  # entrada de EPR → el nombre que le dio su hueco en IDE
        self.char_null = self._char_null()  # OBJ → posición en STR de su 'NULL'

    def _char_null(self) -> dict[int, int]:
        """`x as Char default null`: el compilador no lo guarda en el OBJ (igual que sin default) y solo deja la cadena
        'NULL' en STR, sin que la apunte nada, donde se declaró (AGENDA mes, y 4 de samples). STR, IDE y los nodos de
        REF van en el orden del fuente: la cadena cae entre dos literales (nodos de REF), y la variable es una Char sin
        default cuyo nombre (IDE) cae entre los nombres de esos nodos (y de los defaults en STR de otras variables). Si
        hay varias seguidas en el hueco, cualquiera da los mismos bytes: la primera, con aviso."""
        m = self.m
        apuntadas = m.cadenas_apuntadas()
        nulls = sorted(p for p, t in m.str.items() if t == "NULL" and p not in apuntadas)
        if not nulls:
            return {}
        # Un parámetro `x as Char default null` sí lo marca en su OBJ (0x20 de los bytes 0 y 2) y deja también su 'NULL'
        # (mail IncSMTPClient): una por parámetro, en el mismo orden. Si sobran, son de variables sin marca.
        marcados = [k for k in range(m.s["OBJ"].n) if (r := m.rec("OBJ", k))[2] & 0x20 and r[0] & 0x20
                    and m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0]).lower() == "char"]
        if marcados:
            if len(marcados) != len(nulls):
                return {}  # sin saber cuál es de cuál, las cadenas quedan sin usar (NoSoportado)
            return dict(zip(marcados, nulls))
        str_de, ide_de = {}, {}
        for k in range(m.s["REF"].n):
            r = m.rec("REF", k)
            ref = _ref(struct.unpack_from("<I", r, 0x18)[0])
            if r[0] == LIT_CHAR and ref and ref[0] == STR:
                str_de[k] = ref[1] * 4
            if (q := struct.unpack_from("<Q", r, 0x18)[0]) in m.pos_ide:
                ide_de[k] = m.pos_ide[q]
        chars, anclas = [], []  # Char sin default; (IDE, STR) de los defaults char
        for k in range(m.s["OBJ"].n):
            r = m.rec("OBJ", k)
            nombre = _ref(struct.unpack_from("<I", r, 0x10)[0])
            if not nombre or nombre[0] != IDE or m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0]).lower() != "char":
                continue
            ref = _ref(struct.unpack_from("<I", r, 0x28)[0])
            if r[2] & 0x20 and ref and ref[0] == STR:
                anclas.append((nombre[1] * 4, ref[1] * 4))
            elif not r[2] & 0x20 and not r[0] & 0x20 and not any(r[0x28:0x30]):
                chars.append((nombre[1] * 4, k))
        # El orden de REF no es el del fuente entre procedimientos (`main` va detrás), pero dentro de uno sí: cada literal
        # se acota con el nombre del nodo de antes y el de después.
        con_ide = sorted(ide_de)
        antes = {k: ide_de[max((j for j in con_ide if j < k), default=None)] if any(j < k for j in con_ide) else -1
                 for k in str_de}
        despues = {k: ide_de[min(j for j in con_ide if j > k)] if any(j > k for j in con_ide) else 1 << 30
                   for k in str_de}
        salida = {}
        for s0 in nulls:
            lo = max([antes[k] for k, s in str_de.items() if s < s0] + [i for i, s in anclas if s < s0], default=-1)
            hi = min([despues[k] for k, s in str_de.items() if s > s0] + [i for i, s in anclas if s > s0], default=1 << 30)
            # Las del hueco, seguidas o no (entre ellas no se crea ninguna cadena: mail SendModule, con un objeto de
            # otra clase en medio); los parámetros no, que lo marcan en su OBJ.
            ks = [k for i, k in sorted(chars) if lo < i < hi and k not in salida and m.rec("OBJ", k)[0] & 0x0F != 2]
            if not ks:
                continue  # ninguna: la cadena queda sin usar (NoSoportado)
            salida[ks[0]] = s0
            if len(ks) > 1:
                self.avisos.append(f"default null de {m.nombre_obj(ks[0])}: el .omd no lo guarda en la variable; "
                                   f"cabe en {len(ks)} Char del hueco con los mismos bytes")
        return salida

    # --- expresiones: devuelven (texto, precedencia)
    def nodo(self, k: int) -> bytes:
        return self.m.rec("REF", k)

    def hijo(self, k: int, off: int):
        return self.m.refa("REF", k, off, REF)

    def cadena(self, k):
        """Nodos encadenados por +0x08. En una lista (0xD0), +0x08 son sus elementos."""
        salida = []
        while k is not None:
            salida.append(k)
            k = None if self.nodo(k)[0] == LISTA else self.hijo(k, 0x08)
        return salida

    def escritos(self, args, llamada: int):
        """Argumentos de un método con nombre tal como se escribieron. Los que no se
        escribieron los añade el compilador al final, con nodos creados después que el de
        la llamada; los escritos se crean antes. Una lista (0xD0) de argumentos variables
        se escribe suelta."""
        args = list(args)
        variables = []  # la lista de argumentos variables va la última, tras los por defecto
        if args and self.nodo(args[-1])[0] == LISTA:
            lista = self.hijo(args.pop(), 0x08)
            variables = self.cadena(lista) if lista is not None else []
        # Con argumentos variables escritos, los de delante también lo están (no se puede saltar uno y dar los
        # variables). ALMAFAC provee: `Sql.SelectWindow(…, 1, proveedores.provincia)`.
        while args and not variables and self.por_defecto(args[-1], llamada):
            args.pop()
        return args + variables

    def por_defecto(self, k: int, llamada: int) -> bool:
        """Un literal que no se escribió: el compilador lo copia de la declaración, a veces
        después de la llamada y a veces justo antes, y entonces lleva basura (memoria sin
        limpiar) más allá del ancho de su tipo. Un literal escrito lleva ahí ceros o un
        0x11 seguido de ceros."""
        r = self.nodo(k)
        if r[0] not in LITERALES:
            return False
        if k > llamada:
            return True
        # Si la llamada entera la crea el compilador tarde (en `if o.Run then`, para convertir el resultado), el
        # argumento que pone va antes que la llamada pero después de la raíz de la expresión de la sentencia,
        # que se crea la última de las que se escribieron.
        if getattr(self, "raiz", None) is not None and k > self.raiz:
            return True
        if r[0] == LIT_BOOLEAN:  # uno escrito lleva ceros o el relleno de MSVC (0xCC) tras su valor
            resto = r[0x1C:0x20]
            return any(resto) and resto != bytes([RELLENO]) * 4
        resto = {LIT_SMALLINT: r[0x1A:0x20], LIT_INTEGER: r[0x1C:0x20], LIT_NULL: r[0x18:0x20]}.get(r[0], b"")
        if r[0] == LIT_SMALLINT and resto in ESCRITO_KIT:
            return False
        if r[0] == LIT_SMALLINT and self.m.bits == 32 and resto == AMBIGUO_32:
            if r[1] == VARIANTE_NORMAL:
                return False
            raise NoSoportado(f"argumento {self.m.literal(r)} en 32 bits (REF {k}): no se sabe si se escribió")
        return bool(resto) and any(resto) and not (resto[0] == 0x11 and not any(resto[1:]))

    def texto(self, k: int, minimo: int = 0) -> str:
        t, p = self.expr(k)
        return f"({t})" if p < minimo else t

    def lista(self, ks) -> str:
        return ", ".join(self.texto(x, 1) for x in ks)

    def expr(self, k: int):
        r = self.nodo(k)
        t = r[0]
        if r[:2] in (VALOR_ENUM, VALOR_ENUMSET) and (c := self.m.refa("REF", k, 0x10, CLA)) is not None:
            v = struct.unpack_from("<Q", r, 0x18)[0]
            valores = self.valores_enum(c)
            i = v if r[:2] == VALOR_ENUM else v.bit_length() - 1
            if r[:2] == VALOR_ENUMSET and v & (v - 1) or not 0 <= i < len(valores):
                raise NoSoportado(f"valor {v:#x} de la clase CLA {c} en REF {k}")
            return valores[i], PREC_ATOMO
        if t == VARIABLE or t == TABLA or t == 0x00 and r[1] in (0x31, CONTROL_DE_OBJETO):
            self.apunta_ide(k)
        if t == VARIABLE:
            if (o := self.m.refa("REF", k, 0x10, OBJ)) is not None:
                return self.m.nombre_obj(o), PREC_ATOMO
            if (o := self.m.refa("REF", k, 0x10, FOB)) is not None:
                return self.m.nombre_fob(o), PREC_ATOMO
            if (e := self.m.refa("REF", k, 0x10, EOB)) is not None:  # propiedad de una clase externa
                p = struct.unpack_from("<Q", r, 0x18)[0]
                if p in self.m.punteros:
                    return self.m.punteros[p], PREC_ATOMO
                if (EOB, e) in self.m.por_entrada:
                    return self.m.por_entrada[(EOB, e)], PREC_ATOMO
                raise NoSoportado(f"no se sabe el nombre de la propiedad de REF {k}")
            raise NoSoportado(f"variable de la sección {(self.nodo(k)[0x11]):#x} en REF {k}")
        if t == MIEMBRO_CONTROL and r[1] == MIEMBRO_CONTROL:  # `objeto.control`: +0x10 el objeto, +0x18 el control
            if self.nodo(self.hijo(k, 0x18))[:2] != bytes([0x00, CONTROL_DE_OBJETO]):
                raise NoSoportado(f"miembro de REF {k} que no es un control")
            return f"{self.texto(self.hijo(k, 0x10), PREC_MIEMBRO)}.{self.texto(self.hijo(k, 0x18))}", PREC_MIEMBRO
        if r[:2] == MIEMBRO_OPCION:
            o = self.m.refa("REF", self.hijo(k, 0x18), 0x10, MOP)
            if self.nodo(self.hijo(k, 0x18))[:2] != OPCION or o is None or not (w := self.m.u32("MOP", o, 0x2C)) \
                    or (nombre := self.m.ide.get((w - 1) * 4)) is None:
                raise NoSoportado(f"miembro de REF {k} que no es una opción de menú con nombre")
            return f"{self.texto(self.hijo(k, 0x10), PREC_MIEMBRO)}.{nombre}", PREC_MIEMBRO
        if t == 0x00 and r[1] in (0x31, CONTROL_DE_OBJETO):  # control del formulario (0x31) o de un objeto (0x21)
            if (c := self.m.refa("REF", k, 0x10, FCT)) is not None:
                nombre = self.interfaz().nombre(c)
                if nombre:
                    return nombre, PREC_ATOMO
            if (c := self.m.refa("REF", k, 0x10, 0x11)) is not None:  # control de página (PCT)
                nombre = self.pagina().nombre(c)
                if nombre:
                    return nombre, PREC_ATOMO
            raise NoSoportado(f"control sin nombre en REF {k}")
        if r[1] == 0xF1:
            w = struct.unpack_from("<I", r, 0x10)[0]
            clase = self.m.nombre_clase(w)
            if clase not in PALABRAS:
                raise NoSoportado(f"palabra reservada de clase {clase} en REF {k}")
            return PALABRAS[clase], PREC_ATOMO
        if t == LIT_SMALLINT and r[1] == 0x31:  # `self` dentro de una clase (+0x10 → su CLA)
            if self.m.refa("REF", k, 0x10, CLA) is None:
                raise NoSoportado(f"self sin clase en REF {k}")
            return "self", PREC_ATOMO
        if t in LITERALES and r[1] == EXTERNA:  # el nombre se pone al acabar el procedimiento (con_externas)
            self.orden_ide.append((None, k))
            return f"\0{k}\0", PREC_ATOMO
        if t in LITERALES:
            if r[1] not in (0xF0, CONSTANTE):
                raise NoSoportado(f"literal {t:#x} con variante {r[1]:#x} en REF {k}")
            if r[1] == CONSTANTE:
                for nombre, valor, _ in self.m.constantes():
                    if valor == r[0x18:0x20]:
                        return nombre, PREC_ATOMO
                # Sin constante del módulo: una predefinida (`PI`, que el compilador cambia por su valor; escrito el
                # valor, la variante es 0xF0: batería clases.py, CalcALG calcu3 `PI.Char()`)
                nombre = PREDEFINIDAS.get(self.m.literal(r)) if t == LIT_DECIMAL else None
                if nombre is None:
                    raise NoSoportado(f"constante sin nombre en REF {k}")
                return nombre, PREC_ATOMO
            texto = self.m.literal(r, con_punto=True)
            return texto, (PREC_PREFIJO if texto.startswith("-") else PREC_ATOMO)
        if t == LISTA:
            return "(" + self.lista(self.cadena(self.hijo(k, 0x08))) + ")", PREC_ATOMO
        if t == LLAMADA:
            return self.llamada(k)
        if t == ACCESO:
            return self.acceso(k, [])
        if t == PROPIEDAD:
            campo = self.nodo(self.hijo(k, 0x18))
            if campo[0] == VARIABLE and struct.unpack_from("<Q", campo, 0x18)[0] in (
                    VALORES_IMPLICITOS_32 if self.m.bits == 32 else VALORES_IMPLICITOS):
                return self.texto(self.hijo(k, 0x10), PREC_MIEMBRO), PREC_MIEMBRO  # `medit = "x"`: el valor
            obj = self.nodo(self.hijo(k, 0x10))
            if obj[0] == TABLA and campo[0] == VARIABLE and (f := self.m.refa("REF", self.hijo(k, 0x18), 0x10, FOB)) is not None:
                if self.m.refa("FOB", f, 0x50, FTA) != self.m.refa("REF", self.hijo(k, 0x10), 0x10, FTA):
                    raise NoSoportado(f"columna de otra tabla en REF {k}")
                return self.m.nombre_fob(f), PREC_MIEMBRO  # `tabla.columna`: el nombre ya lleva la tabla
            return f"{self.texto(self.hijo(k, 0x10), PREC_MIEMBRO)}.{self.texto(self.hijo(k, 0x18))}", PREC_MIEMBRO
        if t == METODO:
            return self.nombre_metodo(k), PREC_ATOMO
        if t == TABLA and r[1] == TABLA and (f := self.m.refa("REF", k, 0x10, FTA)) is not None:
            if r[2] not in (0x00, 0x05) or r[3] != 0x07 or any(r[0x14:0x18]) or len(r) > 0x20 and any(r[0x20:]):
                raise NoSoportado(f"tabla en REF {k} con bits sin descifrar")
            return self.m.texto_ide(self.m.u32("FTA", f, 0x10)), PREC_ATOMO  # +0x18: puntero de memoria
        raise NoSoportado(f"nodo {t:#04x} {r[1]:#04x} en REF {k}")

    def valores_enum(self, c: int) -> list[str]:
        """Los valores de un Enum o EnumSet (CLA c): su cadena de STR (+0x40), con un `|` detrás de cada uno."""
        r = _ref(self.m.u32("CLA", c, 0x40))
        texto = self.m.str.get(r[1] * 4) if r and r[0] == STR and self.m.u32("CLA", c, 0) & 0xFF in (0x08, 0x09) else None
        valores = texto.split("|") if texto else []
        if not valores or valores[-1] or len(valores) - 1 != self.m.u32("CLA", c, 0x30) \
                or not all(v.isidentifier() for v in valores[:-1]):
            raise NoSoportado(f"Enum CLA {c} con valores {texto!r}")
        return valores[:-1]

    def clase_metodo(self, k: int) -> str:
        if (e := self.m.refa("REF", k, 0x10, EPR)) is not None:
            clase = self.m.u32("EPR", e, 0) & 0xFFFF
            if clase < len(self.m.ecl):
                return self.m.ecl[clase]
        raise NoSoportado(f"clase del método de REF {k}")

    def apunta_ide(self, k: int):
        """Anota, en el orden en que se escribe, la posición en IDE del nombre de un nodo (la de su puntero), o «?» si no
        se sabe (un control, una tabla, un puntero sin resolver, un método)."""
        q = struct.unpack_from("<Q", self.nodo(k), 0x18)[0]
        self.orden_ide.append((self.m.pos_ide.get(q, "?"), k))

    def _nombre_nodo(self, k: int):
        """El nombre con que sale un nodo, sin anotar nada en orden_ide."""
        guardado, self.orden_ide = self.orden_ide, []
        try:
            return self.nombre_metodo(k) if self.nodo(k)[0] == METODO else self.expr(k)[0]
        except NoSoportado:
            return None
        finally:
            self.orden_ide = guardado

    def con_externas(self, pro: int, lineas: list[str]) -> list[str]:
        """Las constantes de un módulo incluido (literal de variante EXTERNA) y los métodos de EPR sin nombre no lo
        guardan en su nodo, pero está en IDE, que lleva los identificadores en el orden del fuente: el texto se escribe
        en ese orden, y cada uno va en el hueco entre el nombre anterior y el siguiente cuya posición se sabe (Nif_1:
        `valor[1, LONGITUD_NIF - 1]`). Solo acotan las posiciones que van creciendo: un puntero puede ir a otra
        aparición del mismo nombre (INC_OUTLOOK: los de `Invoke` y los de `i`), y entonces cuenta como un nombre
        sin posición. En el hueco se recorren a la vez sus nombres libres (ni declaraciones ni de un puntero) y lo
        escrito: un nombre sin posición se come el libre que toca si se llama igual (puede no tenerlo), y cada
        constante o método, el que toca. Tienen que acabarse a la vez; si no, NoSoportado."""
        if not any(e[0] is None or e[0] == CONVERSION for e in self.orden_ide):
            return lineas
        usadas = self.m.declarados | set(self.m.pos_ide.values())
        nombres_pro = sorted(self.m.u32("PRO", j, 0x28) >> 16 << 2 for j in range(self.m.s["PRO"].n)
                             if (x := _ref(self.m.u32("PRO", j, 0x28))) and x[0] == IDE)
        orden, ultima = [], -1
        for p, k in self.orden_ide:
            if isinstance(p, int) and p <= ultima:  # fuera de orden: un nombre sin posición
                orden.append(("?", k, self.m.ide[p]))
            elif p == "?":
                orden.append(("?", k, self._nombre_nodo(k)))
            elif p == CONVERSION:
                orden.append((p, k, None))
            else:
                orden.append((p, k, None))
                ultima = p if isinstance(p, int) else ultima
        nombres, lo, tramo = {}, -1, []
        for p, k, nombre in orden + [(-2, None, None)]:
            if not isinstance(p, int):
                tramo.append((p, k, nombre))
                continue
            if any(x is None or x == CONVERSION for x, _, _ in tramo):
                hi = p if p >= 0 else min((q for q in nombres_pro if q > lo), default=1 << 30)
                libres = [q for q in sorted(self.m.ide) if lo < q < hi and q not in usadas]
                j = 0
                for i, (x, kk, nombre_x) in enumerate(tramo):
                    if x == CONVERSION:  # escrita si le toca un nombre libre (el de su entrada, si ya se sabe)
                        e = self.m.refa("REF", kk, 0x10, EPR)
                        quedan = sum(y is None for y, _, _ in tramo[i + 1:])
                        libre = (self.m.ide[libres[j]] or "").lower() if j < len(libres) else None
                        # una conversión se llama como una clase (samples ejactivexopenofficecalc: `(fila + 1)` no es
                        # `(fila + 1).fila`)
                        if libre and len(libres) - j > quedan and libre in BASICOS | {c.lower() for c in self.m.ecl} \
                                and self.metodos_ide.get(e, libre) == libre:
                            nombres[kk] = libres[j]
                            j += 1
                        elif libre and i == len(tramo) - 1 and self.metodos_ide.get(e, libre) == libre:
                            # la última del tramo, con un nombre libre detrás que no es de una clase (si lo fuera, ya
                            # lo habría tomado la regla de arriba) ni otro que el de su entrada: es el método escrito
                            # sin paréntesis (samples ListasArbolEventoClick_Check en 32 bits: `Miform.Run;`, con el
                            # puntero de Run en otro bloque de memoria). Si fuera una conversión, ese nombre sobraría
                            # y el tramo no cuadraría; si queda más de uno, tampoco cuadra (NoSoportado). Ablación en
                            # el corpus (quitar el puntero, su posición y su entrada a cada método de EPR que lo tiene):
                            # 3131 nombres recuperados, todos el del puntero, y ninguno distinto.
                            nombres[kk] = libres[j]
                            j += 1
                        else:
                            nombres[kk] = None
                    elif x is None:
                        if j >= len(libres):
                            break
                        nombres[kk] = libres[j]
                        j += 1
                    elif j < len(libres) and nombre_x and (self.m.ide[libres[j]] or "").lower() == nombre_x.lower():
                        j += 1
                sin = [kk for x, kk, _ in tramo if x is None and nombres.get(kk) is None]
                if sin or j != len(libres):
                    raise NoSoportado(f"nombre sin hueco en IDE en REF {sin[0] if sin else tramo[0][1]}")
            lo, tramo = p, []
        texto = "\n".join(lineas)
        for k, q in nombres.items():
            if q is None:  # conversión implícita: no se escribió
                texto = texto.replace(f"\1{k}\1", "")
                continue
            texto = texto.replace(f"\1{k}\1", f".\0{k}\0")
            nombre, valor = self.m.ide[q], self.nodo(k)[0x18:0x20]
            if self.nodo(k)[0] == METODO:  # un método de EPR: la misma entrada, el mismo nombre
                e = self.m.refa("REF", k, 0x10, EPR)
                if self.metodos_ide.setdefault(e, nombre.lower()) != nombre.lower():
                    raise NoSoportado(f"entrada EPR {e} con dos nombres en IDE")
            elif self.externas.setdefault(nombre.lower(), valor) != valor:
                raise NoSoportado(f"constante incluida {nombre} con dos valores")
            texto = texto.replace(f"\0{k}\0", nombre)
        return texto.split("\n")

    def nombre_metodo(self, k: int) -> str:
        p = struct.unpack_from("<Q", self.nodo(k), 0x18)[0]
        e = self.m.refa("REF", k, 0x10, EPR)
        if self.m.refa("REF", k, 0x10, PRO) is None and p not in self.m.punteros and e is not None \
                and (EPR, e) not in self.m.por_entrada:
            # Sin puntero que dé el nombre ni otro nodo de su entrada (INC_OUTLOOK `0.integer`: una dirección estática
            # del compilador 7.42): su nombre en IDE, como el de una constante incluida (con_externas)
            self.orden_ide.append((None, k))
            return f"\0{k}\0"
        if (q := self.m.refa("REF", k, 0x10, PRO)) is not None:
            return self.m.nombre_pro(q)
        if p in self.m.punteros:
            return self.m.punteros[p]
        if e is not None and (EPR, e) in self.m.por_entrada:
            return self.m.por_entrada[(EPR, e)]
        raise NoSoportado(f"no se sabe el nombre del método de REF {k}")

    def llamada(self, k: int):
        callee = self.hijo(k, 0x10)
        a = self.hijo(k, 0x18)
        args = self.cadena(a) if a is not None else []
        tc = self.nodo(callee)[0]
        if tc == ACCESO:
            return self.acceso(callee, args, k)
        if tc == METODO:
            args = self.escritos(args, k)
            nombre = self.nombre_metodo(callee)
            if self.nodo(callee)[1] == CON_CLASE:  # «Module.PutEnv(…)»: la clase, escrita
                # Un procedimiento del módulo llamado desde una clase lleva la variante con o sin `module.` escrito
                # (samples MODU `module.Clear` desde una página; Cosregexpdll, sin nada): sale con él, que vale siempre
                clase = "Module" if self.m.refa("REF", callee, 0x10, PRO) is not None else self.clase_metodo(callee)
                if clase.lower() != "module":  # samples activexexcel: `Module.Name` es de Object, y `Object.Name` no
                    raise NoSoportado(f"método de {clase} con la clase escrita en REF {callee}")  # compila
                nombre = f"{clase}.{nombre}"
            elif self.nodo(callee)[1] == 0x40:  # `parent.metodo`: el de la clase base
                nombre = f"parent.{nombre}"
            parentesis = bool(args) or callee == k - 1
            return (f"{nombre}({self.lista(args)})" if parentesis else nombre), PREC_MIEMBRO
        raise NoSoportado(f"llamada a un nodo {tc:#x}")

    def acceso(self, k: int, args, llamada: int | None = None):
        obj, met = self.hijo(k, 0x10), self.hijo(k, 0x18)
        cod = struct.unpack_from("<Q", self.nodo(met), 0x18)[0]
        tok = cod if cod < 0x10000 else None
        if tok == 0 and not args:  # conversión implícita: no se escribió
            return self.expr(obj)
        if tok in BINARIOS and len(args) == 1:
            op = BINARIOS[tok]
            p = PREC[op]
            if p == 0:  # las asignaciones van de derecha a izquierda: a = b = c es a = (b = c)
                return f"{self.texto(obj, p + 1)} {op} {self.texto(args[0], p)}", p
            return f"{self.texto(obj, p)} {op} {self.texto(args[0], p + 1)}", p
        if tok in PREFIJOS and not args:
            return f"{PREFIJOS[tok]}{self.texto(obj, PREC_PREFIJO)}", PREC_PREFIJO
        if tok == BETWEEN and len(args) == 2:
            return f"{self.texto(obj, 5)} between {self.texto(args[0], 5)} and {self.texto(args[1], 5)}", 4
        if tok == IN and len(args) == 1:
            return f"{self.texto(obj, 5)} in {self.texto(args[0])}", 4
        if tok == IS_NULL and not args:
            return f"{self.texto(obj, 5)} is null", 4
        if tok == IS_NOT_NULL and not args:
            return f"{self.texto(obj, 5)} is not null", 4
        if tok == INDICE and args:  # `c[i]` de un Char: la longitud (1) la añade el compilador, como un argumento por defecto
            return f"{self.texto(obj, PREC_MIEMBRO)}[{self.lista(self.escritos(args, k))}]", PREC_MIEMBRO
        if tok is not None:
            raise NoSoportado(f"operador {tok} con {len(args)} argumentos")
        parentesis = False
        if llamada is not None:
            args = self.escritos(args, llamada)
            # Con paréntesis, aunque vayan vacíos, el compilador crea el acceso justo antes
            # que la llamada; sin ellos, en otro momento.
            # Si la llamada se crea tarde (su resultado lleva conversión), el acceso con paréntesis
            # sigue yendo justo detrás de su método.
            parentesis = bool(args) or k == llamada - 1 or k == met + 1
        objeto = self.texto(obj, PREC_MIEMBRO)
        nombre = self.nombre_metodo(met)
        if nombre == f"\0{met}\0" and not args and not parentesis:
            # `x.integer` sin nombre (INC_OUTLOOK, del compilador 7.42): escrito, deja el suyo en IDE; la conversión
            # que añade el compilador, no (`GetWord("|", i)`). Se decide en con_externas.
            self.orden_ide[-1] = (CONVERSION, met)
            return f"{objeto}\1{met}\1", PREC_MIEMBRO
        texto = f"{objeto}.{nombre}"
        return (texto + f"({self.lista(args)})" if parentesis else texto), PREC_MIEMBRO

    # --- sentencias
    def stm(self, k: int) -> tuple:
        return struct.unpack_from("<12I", self.m.rec("STM", k))

    def sig(self, k: int):
        return self.m.refa("STM", k, 0x08, STM)

    def en(self, w: int, seccion: int):
        r = _ref(w)
        return r[1] if r and r[0] == seccion else None

    def e(self, w: int) -> str:
        k = self.en(w, REF)
        if k is None:
            raise NoSoportado(f"expresión {w:#x}")
        antes, self.raiz = getattr(self, "raiz", None), k
        try:
            return self.texto(k)
        finally:
            self.raiz = antes

    def lista_stm(self, k, n: int) -> list[str]:
        salida = []
        while k is not None:
            salida += self.sentencia(k, n)
            k = self.sig(k)
        return salida

    def cuerpo(self, w: int, n: int) -> list[str]:
        """Cuerpo de un if/while/for: un bloque va al mismo nivel; una sentencia sola, un nivel más."""
        k = self.en(w, STM)
        if k is None:
            raise NoSoportado("cuerpo sin sentencia")
        return self.sentencia(k, n if self.stm(k)[0] & 0xFF == 0 else n + 1)

    def sentencia(self, k: int, n: int) -> list[str]:
        w = self.stm(k)
        t = w[0] & 0xFF
        s = SANGRIA * n
        if t == 0x00:
            return [s + "begin", *self.lista_stm(self.en(w[6], STM), n + 1), s + "end"]
        if t == 0x02:
            return [s + self.e(w[8]) + ";"]
        if t == 0x03:
            return [s + (f"return {self.e(w[8])};" if w[8] else "return;")]
        if t == 0x01:
            salida = [s + f"if {self.e(w[4])} then", *self.cuerpo(w[6], n)]
            if w[10]:
                otro = self.en(w[10], STM)
                if self.stm(otro)[0] & 0xFF == 0x01:
                    sub = self.sentencia(otro, n)
                    salida += [s + "else " + sub[0].lstrip(), *sub[1:]]
                else:
                    salida += [s + "else", *self.cuerpo(w[10], n)]
            return salida
        if t in (0x04, 0x24):
            paso = f" step {self.e(w[8])}" if w[8] else ""
            sentido = "down to" if t == 0x24 else "to"
            return [s + f"for {self.e(w[4])} {sentido} {self.e(w[6])}{paso} do", *self.cuerpo(w[10], n)]
        if t == 0x11:
            return [s + f"for {self.e(w[4])} as {self.lista(self.cadena(self.en(w[6], REF)))} do", *self.cuerpo(w[10], n)]
        if t == 0x05:
            return [s + f"while {self.e(w[4])} do", *self.cuerpo(w[10], n)]
        if t == 0x07:
            return [s + "repeat", *self.lista_stm(self.en(w[10], STM), n + 1), s + f"until {self.e(w[4])};"]
        if t == 0x06:
            return [s + "forever", *self.cuerpo(w[10], n)]
        if t == 0x08:
            return [s + "break;"]
        if t == 0x09:
            if any(w[2:]):
                raise NoSoportado(f"continue con campos (STM {k})")
            return [s + "continue;"]
        if t == 0x10:  # do … while cond;: condición en +0x10, cuerpo en +0x28
            return [s + "do", *self.cuerpo(w[10], n), s + f"while {self.e(w[4])};"]
        if t == 0x0F:  # sentencia vacía: `;`
            if any(w[4:]):  # solo cabecera y siguiente (+0x08)
                raise NoSoportado(f"sentencia vacía con campos (STM {k})")
            return [s + ";"]
        if t in (0x0A, 0x0B):
            salida = [s + (f"switch {self.e(w[8])} begin" if t == 0x0A else "switch begin")]
            c = self.en(w[6], STM)
            while c is not None:
                wc = self.stm(c)
                cond = self.en(wc[4], REF)
                if wc[0] & 0xFF == 0x0D:  # case de valor: la condición es «valor == x» o «valor between a and b»
                    args = self.cadena(self.hijo(cond, 0x18))
                    acceso = self.hijo(cond, 0x10)
                    met = self.hijo(acceso, 0x18) if acceso is not None and self.nodo(acceso)[0] == ACCESO else None
                    tok = struct.unpack_from("<Q", self.nodo(met), 0x18)[0] if met is not None else None
                    valores = self.cadena(cond)  # `case "=", "Enter":` una condición «valor == x» por valor, por +0x08
                    if len(valores) > 1:
                        args = [a for v in valores for a in self.valor_de_case(v, c)]
                    if tok == 31:
                        etiqueta = self.lista(args)
                    elif tok == BETWEEN and len(args) == 2:
                        etiqueta = f"between {self.texto(args[0], 5)} and {self.texto(args[1], 5)}"
                    elif tok == IN and len(args) == 1 and self.nodo(args[0])[0] == LISTA:  # case in (a, b)
                        etiqueta = f"in {self.texto(args[0])}"
                    else:
                        raise NoSoportado(f"case de valor con el operador {tok} (STM {c})")
                else:
                    etiqueta = self.texto(cond)
                salida += [s + SANGRIA + f"case {etiqueta}:", *self.lista_stm(self.en(wc[10], STM), n + 2)]
                c = self.sig(c)
            if w[10]:
                d = self.stm(self.en(w[10], STM))
                salida += [s + SANGRIA + "default:", *self.lista_stm(self.en(d[10], STM), n + 2)]
            return salida + [s + "end"]
        raise NoSoportado(f"sentencia de tipo {t:#x} (STM {k})")

    def valor_de_case(self, v: int, c: int) -> list[int]:
        """El valor x de una de las condiciones «valor == x» de un case de varios valores (CalcALG calcu3)."""
        acceso = self.hijo(v, 0x10)
        met = self.hijo(acceso, 0x18) if acceso is not None and self.nodo(acceso)[0] == ACCESO else None
        args = self.cadena(self.hijo(v, 0x18))
        if self.nodo(v)[0] != LLAMADA or met is None or struct.unpack_from("<Q", self.nodo(met), 0x18)[0] != 31 or len(args) != 1:
            raise NoSoportado(f"case de varios valores con una condición que no es «==» (STM {c})")
        return args

    # --- declaraciones y procedimientos
    def objetos(self, k):
        salida = []
        while k is not None:
            salida.append(k)
            k = self.m.refa("OBJ", k, 0x08, OBJ)
        return salida

    def mascaras_likevar(self) -> dict[int, set[int]]:
        """FOB → las máscaras (nibble alto del u16 alto de +0x20) que `LIKEVAR` copió de él en un TEXT de formulario o
        un VAR de página: las de una columna del repositorio (escrita a mano, la variable no lleva; batería
        `likevar.py`). Son los dos controles que la miran en interfaz.py (`mascara_de_columna`)."""
        if not hasattr(self, "_mascaras_likevar"):
            from .interfaz import LIKEVAR, TIPOS, TIPOS_PAG
            self._mascaras_likevar = defaultdict(set)
            for seccion, tipos, tipo in (("FCT", TIPOS, "TEXT"), ("PCT", TIPOS_PAG, "VAR")):
                for k in range(self.m.s[seccion].n if seccion in self.m.s else 0):
                    tipo_dato, v = self.m.u32(seccion, k, 0x20), self.m.u32(seccion, k, 0x78)
                    if (tipos.get(tipo_dato & 0xFFFF) == tipo and self.m.u32(seccion, k, 0) & LIKEVAR and v
                            and not v & 0xFF and (v >> 8) & 0xFF == FOB):
                        self._mascaras_likevar[v >> 16].add(tipo_dato >> 20)
        return self._mascaras_likevar

    def upshifts_likevar(self) -> dict[int, set[bool]]:
        """FOB → si `LIKEVAR` copió de él el UPSHIFT (0x40000 de +0x00) en un TEXT o EDIT de formulario o un VAR de
        página: el de la columna del repositorio (+0x24 del registro del .crf; escrito, UPSHIFT no compila en TEXT ni
        VAR y en EDIT no cuenta: batería `tablas.py`, `up_`). STOCKMDI cust_rep: `surname1 as customers.surname` y
        `company1 as customers.company` son Char(25) con la misma máscara, y solo company es UPSHIFT."""
        if not hasattr(self, "_upshifts_likevar"):
            from .interfaz import LIKEVAR, TIPOS, TIPOS_PAG, UPSHIFT
            self._upshifts_likevar = defaultdict(set)
            for seccion, tipos, de_tipo in (("FCT", TIPOS, ("TEXT", "EDIT")), ("PCT", TIPOS_PAG, ("VAR",))):
                for k in range(self.m.s[seccion].n if seccion in self.m.s else 0):
                    b0, tipo_dato, v = self.m.u32(seccion, k, 0), self.m.u32(seccion, k, 0x20), self.m.u32(seccion, k, 0x78)
                    if (tipos.get(tipo_dato & 0xFFFF) in de_tipo and b0 & LIKEVAR and v
                            and not v & 0xFF and (v >> 8) & 0xFF == FOB):
                        self._upshifts_likevar[v >> 16].add(bool(b0 & UPSHIFT))
        return self._upshifts_likevar

    def upshift_de_fob(self, k: int, nombre: str) -> bool | None:
        """Si un LIKEVAR copió de la variable FOB k el UPSHIFT (None si ninguno la mira)."""
        upshifts = self.upshifts_likevar().get(k)
        if not upshifts:
            return None
        if len(upshifts) > 1:  # una columna lo es o no lo es
            raise NoSoportado(f"{nombre}: LIKEVAR con UPSHIFT y sin él en distintos controles")
        return next(iter(upshifts))

    def mascara_de_fob(self, k: int, nombre: str) -> int | None:
        """La máscara que copió de la variable FOB k un LIKEVAR (None si ninguno lo hizo)."""
        mascaras = self.mascaras_likevar().get(k)
        if not mascaras:
            return None
        if len(mascaras) > 1:  # una columna tiene una sola
            raise NoSoportado(f"{nombre}: LIKEVAR con las máscaras {sorted(mascaras)} en distintos controles")
        return next(iter(mascaras))

    def tipo(self, r: bytes, nombre: str | None = None, mascara: int | None = None, upshift: bool | None = None) -> str:
        """Clase de un OBJ con sus parámetros: +0x30 = longitud (Char) o precisión y escala. `mascara` y `upshift`: lo
        que copió de la variable un LIKEVAR (mascara_de_fob, upshift_de_fob)."""
        clase = self.m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0])
        if clase.lower() == "arglist":  # `ArgList of X`: X en +0x40, y su precisión en +0x30
            elemento = struct.unpack_from("<I", r, 0x40)[0]
            if not elemento:
                return clase
            return f"{clase} of " + self.tipo(r[:0x18] + r[0x40:0x48] + r[0x20:])
        largo, escala = struct.unpack_from("<Hh", r, 0x30)
        if (largo or escala) and clase.lower() not in BASICOS:  # de una clase `X is Decimal (32,2)`: los de la clase
            if not self.parametros_de_clase(struct.unpack_from("<I", r, 0x18)[0], r[0x30:0x34]):  # (`x as X (10,2)`
                raise NoSoportado(f"{nombre} as {clase} con +0x30 = {largo:#x},{escala}")  # no compila)
            return clase
        if escala == -1 and clase.lower() in ("char", "smallint", "integer", "date"):
            return self.tipo_de_columna(clase, largo, nombre, mascara, upshift=upshift)
        if mascara and clase.lower() in ("decimal", "money"):  # una máscara copiada: era una columna (likevar.py)
            return self.tipo_de_columna(clase, largo, nombre, mascara, escala)
        if clase.lower() in ("decimal", "money"):
            defecto = (16, -1) if clase.lower() == "decimal" else (16, 2)
            if (largo, escala) != defecto:
                return f"{clase}({largo},{escala})"
        elif clase.lower() == "char" and largo:
            return f"{clase}({largo})"
        elif clase.lower() != "char" and (largo or escala):
            raise NoSoportado(f"{clase} con +0x30 = {largo:#x},{escala}")
        return clase

    def parametros_de_clase(self, w: int, parametros: bytes) -> bool:
        """Si los parámetros (+0x30) de un OBJ o una clase de la clase w son los de w. Una del módulo los guarda en su
        CLA; una de un módulo incluido, no: solo pueden ser los suyos (escribirlos no compila; batería clases.py)."""
        r = _ref(w)
        return not (r and r[0] == CLA) or self.m.rec("CLA", r[1])[0x30:0x34] == parametros

    def struct_de_tabla(self, miembros: list[int]) -> str | None:
        """`X is Struct as tabla` da los mismos bytes que sus columnas escritas a mano (batería clases.py, `sa_`): el
        .omd no guarda la tabla. Se escribe así si los miembros son, en su orden, las columnas de una sola tabla del
        repositorio, y los de tipo de columna lo son (escala −1 en +0x30; escritos a mano, 0)."""
        if self.catalogo is None or not miembros:
            return None
        for o in miembros:
            r = self.m.rec("OBJ", o)
            clase = self.m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0]).lower()
            if clase in ("char", "smallint", "integer", "date", "time", "datetime") and struct.unpack_from("<h", r, 0x32)[0] != -1:
                return None
        nombres = [self.m.nombre_obj(o).lower() for o in miembros]
        tablas = [t for t in dict.fromkeys(c.tabla for c in self.catalogo.columnas)
                  if [c.nombre.lower() for c in self.catalogo.columnas if c.tabla == t] == nombres]
        if len(tablas) != 1:
            return None
        self.usa_repositorio = True
        return tablas[0]

    def tipo_de_columna(self, clase: str, largo: int, nombre: str | None, mascara: int | None = None,
                        escala: int = -1, upshift: bool | None = None) -> str:
        """`x as tabla.columna`: el .omd solo guarda el tipo resuelto (escala -1 en +0x30; a mano es 0), no la
        tabla. Se escribe una columna del repositorio que compila igual: la del mismo nombre si la hay.

        Con `mascara` (la que copió un LIKEVAR de la variable), solo una columna con esa máscara en el .crf: otra
        compilaría distinto. Un Money de columna (escala ≠ -1) no deja otra huella que esa máscara; sin el .crf no se
        sabe qué columna la tiene. Sin .crf, los de escala -1 siguen eligiéndose sin mirarla (como antes).
        Con `upshift` (si el LIKEVAR copió el bit), lo mismo con el UPSHIFT del .crf (cust_rep: surname y company
        son Char(25) con la misma máscara y solo company es UPSHIFT); sin .crf, un bit exigido no se puede saber."""
        if self.catalogo is None:
            raise NoSoportado(f"{nombre} es del tipo de una columna ({clase}) y el .omd no dice cuál: "
                              "hace falta el repositorio (--repositorio y su carpeta .dbs)")
        de_money = escala != -1
        if de_money and self.catalogo.mascaras is None:
            raise NoSoportado(f"{nombre}: LIKEVAR con la máscara {mascara} de una columna {clase}({largo},{escala}) y "
                              "sin el .crf del repositorio no se sabe cuál")
        if upshift and self.catalogo.upshifts is None:
            raise NoSoportado(f"{nombre}: LIKEVAR con UPSHIFT de una columna {clase}({largo}) y sin el .crf del "
                              "repositorio no se sabe cuál lo es")
        filtro = mascara if self.catalogo.mascaras is not None else None
        filtro_upshift = upshift if self.catalogo.upshifts is not None else None
        if not self.tablas_elegidas:  # las tablas que nombra el módulo en sus textos (las SELECT…): se prefieren
            palabras = {w.lower() for t in self.m.str.values() if t for w in re.findall(r"\w+", t)}
            self.tablas_elegidas = [t for t in dict.fromkeys(c.tabla for c in self.catalogo.columnas)
                                    if t.lower() in palabras]
        # Money: solo una con esa máscara en el .crf. Los de escala -1 ya se elegían sin mirarla: ahora se descarta la
        # que la tiene distinta, y la que no se sabe (columnas de un tipo compuesto, herencias de dos saltos) sigue valiendo.
        c, n = self.catalogo.buscar(clase, largo, escala, nombre, tuple(self.tablas_elegidas), filtro, estricta=de_money,
                                    upshift=filtro_upshift)
        if c is None:
            raise NoSoportado(f"{nombre}: ninguna columna del repositorio es {clase}"
                              + (f"({largo},{escala})" if de_money else f"({largo})" if largo else "")
                              + (" con " + " y ".join(([f"la máscara {filtro}"] if filtro is not None else [])
                                                      + (["UPSHIFT"] if filtro_upshift else [])) + " en el .crf"
                                 if filtro is not None or filtro_upshift else ""))
        self.usa_repositorio = True
        if n > 1:
            self.avisos.append(f"{nombre} as {c.tabla}.{c.nombre}: una de {n} columnas del mismo tipo "
                               + (f"y la máscara {filtro} " if de_money else "") + ("y UPSHIFT " if filtro_upshift else "")
                               + "(el .omd no guarda cuál era; todas compilan igual)")
        if filtro_upshift is False and clase.lower() == "char" and self.catalogo.upshift(c) is None:
            self.avisos.append(f"{nombre} as {c.tabla}.{c.nombre}: el LIKEVAR no lleva UPSHIFT y el .crf no dice si "
                               "esa columna lo es (si lo fuera, compilaría distinto)")
        if upshift is False and filtro_upshift is None and clase.lower() == "char" and n > 1:  # sin .crf
            candidatas = [f"{x.tabla}.{x.nombre}" for x in self.catalogo.ultimas]
            self.avisos.append(f"{nombre} as {c.tabla}.{c.nombre}: el LIKEVAR no lleva UPSHIFT y sin el .crf no se sabe "
                               f"qué columnas lo son; candidatas: {', '.join(candidatas[:8])}"
                               + (f" y {len(candidatas) - 8} más" if len(candidatas) > 8 else ""))
        if c.tabla not in self.tablas_elegidas:
            self.tablas_elegidas.append(c.tabla)
        return f"{c.tabla}.{c.nombre}"

    def decl(self, k: int, seccion: str = "OBJ") -> str:
        """Declaración de un OBJ, o de un FOB (variable de formulario), que empieza igual."""
        r = self.m.rec(seccion, k)
        nombre = self.m.nombre_obj(k) if seccion == "OBJ" else self.m.texto_ide(self.m.u32("FOB", k, 0x10)) or f"fob{k}"
        # 0x40: por referencia. En los objetos de una clase compuesta (0x20 del byte 0 de su CLA: Struct, Array,
        # ArgList…) lo pone el compilador solo, y escribir VAR no compila o da los mismos bytes. Una clase del módulo
        # de un tipo simple (`sm is Smallint`, byte 0 = 0x02) es como un básico: sin VAR no lo lleva (batería
        # clases.py, sc_param_var_clase; antes se perdía el VAR). Con otro tipo simple no se ha visto: NoSoportado.
        clase = struct.unpack_from("<I", r, 0x18)[0]
        basico = self.m.nombre_clase(clase).lower() in BASICOS
        if r[0] & 0x40 and not basico and (ref := _ref(clase)) and ref[0] == CLA and not self.m.rec("CLA", ref[1])[0] & 0x20:
            if self.m.rec("CLA", ref[1])[0] != 0x02:
                raise NoSoportado(f"{nombre}: VAR de una clase {self.m.rec('CLA', ref[1])[0]:#x}")
            basico = True
        if seccion != "OBJ" and self.m.bits != 64 and self.m.nombre_clase(clase).lower() == "arglist":
            raise NoSoportado(f"{nombre}: ArgList de un {seccion} en 32 bits (sin mapa para +0x40)")  # no visto
        mascara = self.mascara_de_fob(k, nombre) if seccion == "FOB" else None
        upshift = self.upshift_de_fob(k, nombre) if seccion == "FOB" else None
        texto = f"{'VAR ' if r[0] & 0x40 and basico else ''}{nombre} as {self.tipo(r, nombre, mascara, upshift)}"
        if mascara and struct.unpack_from("<h", r, 0x32)[0] != -1:  # Money de columna (tipo() ya la ha escrito así)
            self.fobs_de_columna.add(k)
        if seccion == "OBJ":  # visibilidad: la de los objetos del módulo (tipo 0) y los miembros (3); los demás, private
            vis = r[3] >> 4 & 3
            if r[0] & 0x0F in (0, 3) and vis in VISIBILIDAD:
                texto = f"{VISIBILIDAD[vis].upper()} {texto}" if vis != 1 else texto
            elif vis != 3:
                raise NoSoportado(f"{nombre}: visibilidad {vis} en un OBJ de tipo {r[0] & 0x0F}")
        if seccion == "OBJ" and k in self.char_null:  # Char default null: solo la cadena 'NULL' (_char_null)
            texto += " default null"
            self.m.cadenas_usadas.add(self.char_null[k])
        elif r[2] & 0x20 and r[0] & 0x20:  # default null: bit 0x20 del byte 0, y +0x28 (el valor) y +0x2C a 0
            if any(r[0x28:0x30]):
                raise NoSoportado(f"default null de {nombre} con valor {r[0x28:0x30].hex()}")
            texto += " default null"
        elif r[2] & 0x20:  # tiene default: el valor va en +0x28, como el de un literal en +0x18
            texto += f" default {self.valor_default(r)}"
        if seccion == "FOB":
            texto += self.valores(k, r, nombre)
        return texto

    def valor_default(self, r: bytes) -> str:
        """El default de un OBJ o un FOB (variable o columna): +0x28, como el valor de un literal en +0x18, de la clase
        de +0x18. TODAY: bit 0x40 del byte 2 (+0x28, memoria sin limpiar). Fecha: días desde el 31/12/1899, mm/dd/aaaa."""
        nombre = self.m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0]).lower()
        if r[2] & 0x40:  # en un Time, NOW (batería clases.py)
            if nombre not in ("date", "time"):
                raise NoSoportado(f"default TODAY de un {nombre}")
            return "TODAY" if nombre == "date" else "NOW"
        if nombre == "time":  # segundos en +0x28 y 1 en +0x2C (`default 1` es una hora; `default 3600` no compila); en
            segundos, hay = struct.unpack_from("<II", r, 0x28)  # 32 bits solo los segundos (mail IncViews)
            if self.m.bits == 64 and hay != 1 or segundos >= 86400:
                raise NoSoportado(f"default de hora {r[0x28:0x30].hex()}")
            return f'"{segundos // 3600:02d}:{segundos // 60 % 60:02d}:{segundos % 60:02d}"' if segundos else "0"
        if nombre == "date":
            dias, hay = struct.unpack_from("<II", r, 0x28)
            if hay != 1 or not dias:
                raise NoSoportado(f"default de fecha {r[0x28:0x30].hex()}")
            f = datetime.date(1899, 12, 31) + datetime.timedelta(days=dias)
            return f'"{f.month:02d}/{f.day:02d}/{f.year}"'
        tipo = {"integer": LIT_INTEGER, "smallint": LIT_SMALLINT, "boolean": LIT_BOOLEAN, "char": LIT_CHAR,
                "decimal": LIT_DECIMAL, "money": LIT_DECIMAL}.get(nombre)
        if tipo is None:
            raise NoSoportado(f"default de un {nombre}")
        return self.m.literal(bytes([tipo]) + bytes(0x17) + r[0x28:0x30])

    def default_del_repositorio(self, k: int, r: bytes) -> bool:
        """En 32 bits, el default smallint de una columna que no se escribió (el del repositorio) lleva tras su valor
        memoria sin limpiar (50 00 aquí, 4C 00 en el kit: 16 y 16 columnas, ninguna con default en el fuente), y el
        escrito, el relleno de MSVC (CC CC: triple de ALMAFAC con default 0, 1, 2 y 7). En 64 bits los dos llevan lo
        mismo, y se escribe siempre (compila igual)."""
        if self.m.bits != 32 or self.m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0]).lower() != "smallint":
            return False
        resto = r[0x2A:0x2C]
        if resto == bytes([RELLENO]) * 2:
            return False
        if not any(resto):
            raise NoSoportado(f"default smallint del FOB {k} en 32 bits: no se sabe si se escribió")
        return True

    def valores(self, k: int, r: bytes, nombre: str) -> str:
        """`boolean values "a|b"` (2 valores) o `enumerated n values "…"` (más de 2) de un FOB: n en +0x60 y la cadena
        en +0x68 (STR)."""
        n, w = struct.unpack_from("<I", r, 0x60)[0], struct.unpack_from("<I", r, 0x68)[0]
        if not n and not w:
            return ""
        ref = _ref(w)
        texto = self.m.str.get(ref[1] * 4) if ref and ref[0] == STR else None
        if texto is None or '"' in texto or n < 2 or texto.count("|") + 1 != n:
            raise NoSoportado(f"valores del FOB {k} ({nombre}): {n} y {w:#x}")
        self.m.cadenas_usadas.add(ref[1] * 4)
        if nombre == "columna" and self.catalogo is not None and self.catalogo.tiene_valores(texto):
            return ""  # los del repositorio (.crf): el compilador los copia (en 7.4.2, escritos en la columna no compilan)
        return "\n\t\t\t\t" + (f'boolean values "{texto}"' if n == 2 else f'enumerated {n} values "{texto}"')

    def dec_del_default(self, k: int):
        """El registro del default de un OBJ decimal (su DEC) o Char (su cadena en STR), como (sección, índice), o None."""
        r = self.m.rec("OBJ", k)
        clase = self.m.nombre_clase(struct.unpack_from("<I", r, 0x18)[0]).lower()
        if not r[2] & 0x20 or r[0] & 0x20 or clase not in ("decimal", "char"):
            return None
        ref = _ref(struct.unpack_from("<I", r, 0x28)[0])
        return ref if ref and ref[0] == {"decimal": DEC, "char": STR}[clase] else None

    def decls(self, ks) -> list[str]:
        """Declaraciones de OBJ, una por línea, salvo las seguidas que comparten el DEC de su default: salen de una
        sola `a b c as Decimal default 0` (cada línea crea su propio DEC). Lo mismo con la cadena del default de un
        Char (CalcALG AbsAriEval: `str1 str2 str3 as char default ""`, una sola cadena en STR)."""
        salida, ks, i = [], list(ks), 0
        while i < len(ks):
            j, dec = i + 1, self.dec_del_default(ks[i])
            while dec is not None and j < len(ks) and self.dec_del_default(ks[j]) == dec:
                j += 1
            primera = self.decl(ks[i])
            if j > i + 1:
                resto = [self.decl(x) for x in ks[i + 1:j]]
                cola = primera[len(self.m.nombre_obj(ks[i])):]
                if primera.split(" ")[0] in ("VAR", "PROTECTED", "PRIVATE") or any(d[len(self.m.nombre_obj(x)):] != cola for d, x in zip(resto, ks[i + 1:j])):
                    raise NoSoportado(f"OBJ {ks[i]}..{ks[j - 1]} comparten el DEC de su default sin ser del mismo tipo")
                primera = " ".join(self.m.nombre_obj(x) for x in ks[i:j]) + cola
            salida.append(primera)
            i = j
        return salida

    def procedimiento(self, k: int) -> list[str]:
        w = struct.unpack_from("<16I", self.m.rec("PRO", k))
        nombre = self.m.nombre_pro(k)
        tipo = w[0] & 0xFF
        params = self.objetos(self.m.refa("PRO", k, 0x10, OBJ))
        decls = [self.decl(x) for x in params]
        if tipo == 5 and len(decls) in (3, 4):  # Dragover y Dragdrop: su firma exige `var result` (el último), que no
            r = _ref(w[10])  # deja rastro en el OBJ (getdragcolumngetdropcolumn; con 3, el Dragover de un control: drag1)
            if r and r[0] == STR and (self.m.str.get(r[1] * 4) or "").lower() in ("dragover", "dragdrop"):
                if not decls[-1].startswith("VAR "):
                    decls[-1] = "VAR " + decls[-1]
        lista = f" ({', '.join(decls)})" if params else ""
        if tipo == 4:  # evento del formulario: código en +0x28
            if w[10] not in EVENTOS_FORM:
                raise NoSoportado(f"evento de formulario {w[10]} en PRO {k}")
            cabecera = f"On {EVENTOS_FORM[w[10]]}{lista}"
        elif tipo == 5:  # evento de control: nombre del evento en STR (+0x28), control en IDE (+0x20)
            r = _ref(w[10])
            evento = self.m.str.get(r[1] * 4) if r and r[0] == STR else None
            if (w[0] >> 8) & 0x80:  # `On event X [control Y] (e as event)`: el control, también en STR
                rc = _ref(w[8])
                control = "" if not w[8] else self.m.str.get(rc[1] * 4) if rc and rc[0] == STR else None
                if not w[10] and control and (w[0] >> 16) & 0xFF == 1:
                    # `On Control x [(e as Event)]` (Events.smd): sin evento (+0x28 = 0), de todos los del control. Con
                    # el control entre comillas, los mismos bytes (batería controles.py, onc_)
                    self.m.cadenas_usadas.add(rc[1] * 4)
                    cabecera = f"On Control {control}{lista}"
                elif not evento or control is None or (w[0] >> 16) & 0xFF != 1:
                    raise NoSoportado(f"On event sin nombre en PRO {k}")
                else:
                    self.m.cadenas_usadas.add(r[1] * 4)
                    if control:
                        self.m.cadenas_usadas.add(rc[1] * 4)
                    if control and self.es_activex(control):
                        # el compilador no conoce los eventos de un ACTIVEX: sin comillas, «Unknown control event
                        # AfterUpdate»; entre comillas, los mismos bytes que sin ellas (Events: "Click" y Click)
                        cabecera = f'On event "{evento}" control "{control}"' + lista
                    else:
                        cabecera = f"On event {evento}" + (f" control {control}" if control else "") + lista
            else:
                # +0x20 = 0: de cualquier control (`On Click (sender as char)`, el nombre llega como parámetro)
                control = self.m.ide.get((w[8] - 1) * 4) if w[8] else ""  # posición en IDE / 4, más 1
                if not evento or control is None or not control and not params or (w[0] >> 16) & 0xFF:
                    raise NoSoportado(f"evento de control sin nombre en PRO {k}")
                self.m.cadenas_usadas.add(r[1] * 4)
                cabecera = f"On {evento} {control}{lista}" if control else f"On {evento}{lista}"
        elif tipo == EVENTO_MODULO:
            if w[10] not in EVENTOS_MODULO or params or w[8]:
                raise NoSoportado(f"evento del módulo {w[10]} en PRO {k}")
            cabecera = f"On {EVENTOS_MODULO[w[10]]}"
        elif tipo == 6:  # evento de tabla: código en +0x28, la tabla (FTA) en +0x20
            # +0x20 = 0: de cualquier tabla (`On Edit Table (tab as char)`, el nombre llega como parámetro)
            tabla = self.m.refa("PRO", k, 0x20, FTA)
            forma = not params if tabla is not None else not w[8] and bool(params)  # las dos formas vistas
            if w[10] not in EVENTOS_TABLA or not forma or w[0] != 0x05000506:
                raise NoSoportado(f"evento de tabla {w[10]} ({w[0]:#x}) en PRO {k}")
            alias = f" {self.m.texto_ide(self.m.u32('FTA', tabla, 0x10))}" if tabla is not None else ""
            cabecera = f"On {EVENTOS_TABLA[w[10]]} Table{alias}{lista}"
        elif tipo == 7:  # On Command: número de comando en +0x28; 0, el de cualquiera (`On Command (cmd as Char)`: el
            if w[10] == 0:  # nombre llega como parámetro; sin él no compila)
                if not params:
                    raise NoSoportado(f"On Command sin comando ni parámetro en PRO {k}")
                cabecera = f"On Command{lista}"
            else:
                cabecera = f"On Command {self.interfaz().comando(w[10] & 0xFFFF)}{lista}"
        elif tipo in EXTERNOS:  # dll o javaclass: la DLL o la clase Java en STR (+0x30), sin cuerpo
            r = _ref(w[12])
            if not (r and r[0] == STR and r[1] * 4 in self.m.str):
                raise NoSoportado(f"{EXTERNOS[tipo]} sin nombre en PRO {k}")
            bits = (w[0] >> 8) & 0xFF
            if bits & ~BITS_EXTERNO or not bits & 0x01 or (w[0] >> 16) & 0xFF or (w[0] >> 24) & 0xCF != 0x05:
                raise NoSoportado(f"{EXTERNOS[tipo]} con {w[0]:#x} en PRO {k}")
            self.m.cadenas_usadas.add(r[1] * 4)
            vis = self.visibilidad_pro(k, w[0]) + (" self" if bits & SELF_EXTERNO else "")  # `self public dll` no compila
            ret = "" if bits & SIN_RETURN else f" return {self.m.nombre_clase(w[8])}"
            return [f'{vis} {EXTERNOS[tipo]} "{self.m.str[r[1] * 4]}" {nombre}({", ".join(self.decl(x) for x in params)}){ret}']
        elif tipo == OPERADOR:  # `operator = (c as Char)`: el operador en +0x28, con el código de los de REF
            if w[10] not in BINARIOS or not params:
                raise NoSoportado(f"operator {w[10]} en PRO {k}")
            ret = "" if (w[0] >> 8) & SIN_RETURN else f" return {self.m.nombre_clase(w[8])}"
            cabecera = f"{self.visibilidad_pro(k, w[0])} operator {BINARIOS[w[10]]} ({', '.join(self.decl(x) for x in params)}){ret}"
        elif tipo == CONVERSOR:  # `conversor Char`: sin nombre ni parámetros; la clase, la que devuelve (+0x20)
            if w[10] or params or (w[0] >> 8) & SIN_RETURN:
                raise NoSoportado(f"conversor con {w[10]:#x} en PRO {k}")
            cabecera = f"{self.visibilidad_pro(k, w[0])} conversor {self.m.nombre_clase(w[8])}"
        elif tipo not in (0, 1):
            raise NoSoportado(f"procedimiento de tipo {tipo} en PRO {k}")
        elif tipo == 0:  # con parámetros, entre paréntesis (samples Auxiliar: `main(doRun as boolean default TRUE)`). Sus OBJ
            # llevan siempre el 0x40 (VAR): escrito o no, los mismos bytes (batería llamadas.py); no se escribe
            cabecera = f"main({', '.join(x.removeprefix('VAR ') for x in decls)})" if params else "main"
        else:
            vis = self.visibilidad_pro(k, w[0])
            r = _ref(w[8])
            ret = "" if (w[0] >> 8) & SIN_RETURN else f" return {self.m.nombre_clase(w[8])}"
            cabecera = f"{vis} {nombre}({', '.join(self.decl(x) for x in params)}){ret}"
        salida = [cabecera]
        locales = self.objetos(self.m.refa("PRO", k, 0x30, OBJ))
        if locales:
            salida += ["objects begin", *(SANGRIA + d for d in self.decls(locales)), "end"]
        # En IDE, el nombre del procedimiento, sus parámetros y sus variables van delante del cuerpo
        self.orden_ide = [(x[1] * 4, None) for w in [self.m.u32("PRO", k, 0x28)] + [self.m.u32("OBJ", o, 0x10) for o in params + locales]
                          if (x := _ref(w)) and x[0] == IDE]
        return self.con_externas(k, salida + self.sentencia(self.m.refa("PRO", k, 0x38, STM), 0))

    def visibilidad_pro(self, k: int, w0: int) -> str:
        vis = VISIBILIDAD.get(w0 >> 28 & 3)
        if vis is None:
            raise NoSoportado(f"PRO {k} sin visibilidad ({w0:#x})")
        return vis

    def constante(self, nombre: str, valor: bytes, clase: int) -> str:
        """+0x20: el valor como el de un literal (+0x18); el de un Char, su cadena en STR; el de un Decimal, su DEC."""
        tipo = {"integer": LIT_INTEGER, "smallint": LIT_SMALLINT, "char": LIT_CHAR, "decimal": LIT_DECIMAL,
                "boolean": LIT_BOOLEAN}.get(self.m.nombre_clase(clase).lower())
        if tipo is None:
            raise NoSoportado(f"constante {nombre} de clase {self.m.nombre_clase(clase)}")
        return f"{SANGRIA}{nombre} = {self.m.literal(bytes([tipo]) + bytes(0x17) + valor, con_punto=True)}"

    def es_activex(self, nombre: str) -> bool:
        """Si el control `nombre` del módulo es un ACTIVEX (tipo 0x1A de FCT)."""
        i = self.interfaz()
        return any(self.m.u32("FCT", k, 0x20) & 0xFFFF == 0x1A and i.nombre(k).lower() == nombre.lower()
                   for k in range(self.m.s["FCT"].n)) if "FCT" in self.m.s else False

    def interfaz(self):
        from .interfaz import Interfaz
        if not hasattr(self, "_interfaz"):
            self._interfaz = Interfaz(self.m, NoSoportado)
            self._interfaz.fobs_de_columna = self.fobs_de_columna
        return self._interfaz

    def pagina(self):
        from .interfaz import Pagina
        if not hasattr(self, "_pagina"):
            self._pagina = Pagina(self.m, NoSoportado)
            self._pagina.fobs_de_columna = self.fobs_de_columna
        return self._pagina

    def procs_de(self, clase: int) -> list[int]:
        salida, k = [], self.m.refa("CLA", clase, 0x50, PRO)
        while k is not None:
            salida.append(k)
            k = self.m.refa("PRO", k, 0x08, PRO)
        return salida

    def fobs(self, formulario: int) -> list[int]:
        salida, k = [], self.m.refa("FOR", formulario, 0x20, FOB)
        while k is not None:
            salida.append(k)
            k = self.m.refa("FOB", k, 0x08, FOB)
        return salida

    # --- menús
    def es_menu_implicito(self, k: int) -> bool:
        return self.m.u32("CLA", k, 0x00) == 0x83000022

    def opciones(self, k, n: int) -> list[str]:
        """Las opciones de un menú (MOP encadenados por +0x08 desde k), con su sangría n."""
        s, salida = "\t" * n, []
        while k is not None:
            w = struct.unpack_from("<26I", self.m.rec("MOP", k))
            # byte 1: 0x01 CHECKED, 0x02 SEPARATOR, 0x20 DISABLED, 0x40 submenú. Un submenú lleva además la cabecera
            # de un menú (byte 0, +0x50, +0x54): ver cabecera_menu.
            submenu = (w[0] >> 8) & 0x40
            if w[0] & 0xFFFF00F9 != 0x89000000 or w[0] & 0x00009C00 or w[0] & 0x06 and not submenu \
                    or not submenu and (w[0x50 // 4] != 0xFFFF0000 or w[0x54 // 4] != 0xFFFFFFFF) \
                    or any(w[i] for i in (1, 3, 5, 7, 9, 0x24 // 4, 0x34 // 4, 0x38 // 4, 0x3C // 4)) \
                    or any(w[0x58 // 4:]):
                raise NoSoportado(f"opción de menú MOP {k} sin descifrar ({w[0]:#x})")
            r = _ref(w[6])
            if not r or r[0] != STR or r[1] * 4 not in self.m.str:
                raise NoSoportado(f"opción de menú MOP {k} sin texto")
            nombre = self.m.ide.get((w[0x2C // 4] - 1) * 4) if w[0x2C // 4] else ""
            if nombre is None:
                raise NoSoportado(f"opción de menú MOP {k} con nombre {w[0x2C // 4]:#x}")
            salida.append(s + ("MENU" if submenu else "OPTION") + (f" {nombre}" if nombre else ""))
            salida.append(s + "\t" + self.interfaz().cadena(self.m.str[r[1] * 4]))
            # Detrás del texto, en el orden en que los escribe el compilador. SEPARATOR va dentro de la opción
            # que lleva la marca (escrito suelto detrás de ella da lo mismo, pero detrás de la última no compila).
            if (w[0] >> 8) & 0x02:
                salida.append(s + "\tSEPARATOR")
            if (w[0] >> 8) & 0x20:
                salida.append(s + "\tDISABLED")
            if (w[0] >> 8) & 0x01:
                salida.append(s + "\tCHECKED")
            if (icono := w[0x30 // 4] >> 16) != 0xFFFF:  # ICON n: guarda n - 1
                salida.append(s + f"\tICON {icono + 1}")
            if w[8]:  # HELP "x": +0x20 → STR
                ayuda = _ref(w[8])
                if not ayuda or ayuda[0] != STR or ayuda[1] * 4 not in self.m.str:
                    raise NoSoportado(f"opción de menú MOP {k} con HELP sin texto")
                salida.append(s + "\tHELP " + self.interfaz().cadena(self.m.str[ayuda[1] * 4]))
            if cmd := w[0x30 // 4] & 0xFFFF:
                salida.append(s + f"\tCOMMAND {self.interfaz().comando(cmd)}")
            if submenu:
                salida += [s + "\t" + c for c in self.cabecera_menu(w, k, 0xFFFF)]
                salida += [s + "\tBEGIN", *self.opciones(self.m.refa("MOP", k, 0x40, MOP), n + 2), s + "\tEND"]
            elif w[0x40 // 4]:
                raise NoSoportado(f"opción de menú MOP {k} con hijos")
            k = self.m.refa("MOP", k, 0x08, MOP)
        return salida

    def menu(self, mnu: int, n: int) -> list[str]:
        """El PULLDOWN de un menú: la raíz (MOP, +0x10 del MNU) y sus opciones."""
        raiz = self.m.refa("MNU", mnu, 0x10, MOP)
        w = struct.unpack_from("<26I", self.m.rec("MOP", raiz))
        # 0x40 PULLDOWN, 0x400 NOLABEL, 0x01 NOWAIT: la línea del tipo, cada una opcional (sin ninguna, no hay línea:
        # `menu x BEGIN … END`, STOCKMDI frmtmpl); la cabecera, en cabecera_menu. +0x18 → STR: su título (`menu x "t"`,
        # delante de la cabecera: detrás no compila)
        titulo = _ref(w[6])
        if (w[0] & ~0x447 != 0x89084000 or w[0x30 // 4] != 0xFFFF0000 or w[2] or w[0x2C // 4]
                or w[6] and (not titulo or titulo[0] != STR or titulo[1] * 4 not in self.m.str)):
            raise NoSoportado(f"menú MNU {mnu}: raíz {w[0]:#x} sin descifrar")
        s = "\t" * n
        cabeza = [self.interfaz().cadena(self.m.str[titulo[1] * 4])] if w[6] else []  # (+0x18 de MOP: cadena apuntada)
        tipo = " ".join(x for bit, x in ((0x40, "PULLDOWN"), (0x400, "NOLABEL"), (0x01, "NOWAIT")) if w[0] & bit)
        return [*(s + "\t" + c for c in cabeza + self.cabecera_menu(w, raiz, 0)), *([s + tipo] if tipo else []), s + "\tBEGIN",
                *self.opciones(self.m.refa("MOP", raiz, 0x40, MOP), n + 2), s + "\tEND"]

    def cabecera_menu(self, w, k: int, alto: int) -> list[str]:
        """ICONFILE, DEFAULT ICON, ALLOWICON y ALLOWCHECK de un menú (su raíz) o de un submenú (MOP k), en el orden
        del compilador. Byte 0: 0x02 ALLOWICON, 0x04 ALLOWCHECK. +0x50: ICONFILE (índice en ICO en los 16 bits altos;
        0xFFFF0000 = ninguno). +0x54: DEFAULT ICON n en los 16 bajos (0xFFFF = ninguno); los altos, `alto`
        (0 en la raíz, 0xFFFF en un submenú)."""
        fichero, defecto = w[0x50 // 4], w[0x54 // 4]
        if fichero & 0xFFFF or defecto >> 16 != alto or fichero != 0xFFFF0000 and fichero >> 16 >= self.m.s["ICO"].n:
            raise NoSoportado(f"cabecera de menú en MOP {k} sin descifrar ({fichero:#x}, {defecto:#x})")
        cab = []
        if fichero != 0xFFFF0000:
            cab.append(f'ICONFILE "{self.m.rec("ICO", fichero >> 16)[2:].split(b"\0")[0].decode("cp1252")}"')
        if defecto & 0xFFFF != 0xFFFF:
            cab.append(f"DEFAULT ICON {defecto & 0xFFFF}")
        return cab + [p for bit, p in ((0x02, "ALLOWICON"), (0x04, "ALLOWCHECK")) if w[0] & bit]

    def menus_de(self, formulario: int) -> list[str]:
        """Los menús de un formulario: FOB encadenados desde FOR+0x28, con su clase implícita."""
        salida, f = [], self.m.refa("FOR", formulario, 0x28, FOB)
        while f is not None:
            clase = self.m.refa("FOB", f, 0x18, CLA)
            if clase is None or not self.es_menu_implicito(clase):
                raise NoSoportado(f"menú FOB {f} sin su clase")
            salida += [f"\t\tmenu {self.m.texto_ide(self.m.u32('FOB', f, 0x10))}", *self.menu(self.m.refa("CLA", clase, 0x40, MNU), 2)]
            f = self.m.refa("FOB", f, 0x08, FOB)
        return salida

    def clase(self, k: int) -> list[str]:
        """La declaración de una clase, con su visibilidad delante (PROTECTED o PRIVATE; public no se escribe)."""
        lineas = self._clase(k)
        vis = self.m.u32("CLA", k, 0) >> 28 & 3
        if vis not in VISIBILIDAD:
            raise NoSoportado(f"clase CLA {k} sin visibilidad")
        if vis != 1:
            lineas[0] = f"\t{VISIBILIDAD[vis].upper()} " + lineas[0][1:]
        return lineas

    def _clase(self, k: int) -> list[str]:
        nombre = self.m.texto_ide(self.m.u32("CLA", k, 0x10))
        if not nombre:  # antes salía «None is …»
            raise NoSoportado(f"clase CLA {k} sin nombre")
        base = self.m.nombre_clase(self.m.u32("CLA", k, 0x18))
        formulario = self.m.refa("CLA", k, 0x40, FOR)
        if (pag := self.m.refa("CLA", k, 0x40, PAG)) is not None:  # `X is Page`: PAG hace de FOR
            w = struct.unpack_from("<8I", self.m.rec("PAG", pag))
            if w[0] != 0x80000000 or any(w[i] for i in (1, 3, 5, 7)):
                raise NoSoportado(f"página PAG {pag} sin descifrar")
            objetos, f = [], self.m.refa("PAG", pag, 0x18, FOB)
            while f is not None:
                objetos.append(f"\t\t\t{self.decl(f, 'FOB')}")
                f = self.m.refa("FOB", f, 0x08, FOB)
            return [f"\t{nombre} is {base} begin", "\t\tobjects begin", *objetos, "\t\tend",
                    *self.pagina().raiz(self.m.refa("PAG", pag, 0x10, 0x11), 2), "\tend"]
        if formulario is None:
            # Clase derivada simple (`A is Smallint`, `B is A`): nada más que nombre, base y la
            # lista de procedimientos. Byte 0 = el tipo de la base; 0x10 del byte 3 = escrita.
            w = struct.unpack_from("<22I", self.m.rec("CLA", k))
            if w[0] & 0xFF == 0x24 and base.lower() == "array":  # `X is Array [n] of Y`: n en +0x34, Y en +0x40
                # +0x30: los parámetros del elemento (`of Char (8)`: mail IncEncoders), como en un OBJ
                otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in (0x00, 0x08, 0x10, 0x18, 0x20, 0x30, 0x34, 0x40, 0x48, 0x50)]
                if otros or w[0] & 0x00FFFF00 or not w[0x34 // 4] or not w[0x40 // 4]:
                    raise NoSoportado(f"Array {nombre} con {otros}")
                r = self.m.rec("CLA", k)
                return [f"\t{nombre} is Array [{w[0x34 // 4]}] of {self.tipo(r[:0x18] + r[0x40:0x48] + r[0x20:])}"]
            if w[0] & 0xFF == 0x29 and base.lower() == "arglist":  # `X is ArgList of Y` (samples ARG): Y en +0x40
                # y los parámetros de Y en +0x30, como en un Array
                otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in (0x00, 0x08, 0x10, 0x18, 0x20, 0x30, 0x40, 0x48, 0x50)]
                if otros or w[0] & 0x00FFFF00 or not w[0x40 // 4]:
                    raise NoSoportado(f"ArgList {nombre} con {otros}")
                r = self.m.rec("CLA", k)
                return [f"\t{nombre} is ArgList of {self.tipo(r[:0x18] + r[0x40:0x48] + r[0x20:])}"]
            if w[0] & 0xFF in (0x08, 0x09) and base.lower() in ("enum", "enumset"):
                # `X is Enum of [a b c]` (byte 0 = 0x08; EnumSet, 0x09; samples ENUM): los valores, en una cadena de
                # STR (+0x40) con un `|` detrás de cada uno, y cuántos son en +0x30
                otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in (0x00, 0x08, 0x10, 0x18, 0x20, 0x30, 0x40, 0x48, 0x50)]
                if otros or w[0] & 0x00FFFF00:
                    raise NoSoportado(f"{base} {nombre} con {otros}")
                valores = self.valores_enum(k)
                return [f"\t{nombre} is {base} of [{' '.join(valores)}]"]
            if w[0] == 0x93000022 and base.lower() == "menu":  # `X is Menu PULLDOWN …`: +0x40 → su MNU
                otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in (0x00, 0x08, 0x10, 0x18, 0x20, 0x40, 0x48, 0x50)]
                if otros or self.m.refa("CLA", k, 0x40, MNU) is None:
                    raise NoSoportado(f"Menu {nombre} con {otros}")
                return [f"\t{nombre} is Menu", *self.menu(self.m.refa("CLA", k, 0x40, MNU), 1)]
            rb = _ref(w[6])
            base_abstracta = rb and rb[0] == CLA and self.m.u32("CLA", rb[1], 0) & 0x80
            if w[0] & 0xFF == 0x20 and (w[0x40 // 4] or base.lower() == "struct" or base_abstracta):
                # Un Struct, o una clase derivada de otra del usuario (`B is A begin … end`, solo si A es abstracta;
                # si no, no compila): sus miembros, OBJ de tipo 3 desde +0x40. Sin miembros, `A is Struct begin end`
                # y `B is A begin end`: sin el begin no compilan. `B is A` sin miembros, si A los tiene: en +0x40 un puntero
                # de memoria del compilador (cambia de una compilación a otra: CalcALG ScEval, 0x2fc6960 en el kit y
                # 0x1c734b8 aquí), que no se escribe.
                otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in (0x00, 0x08, 0x10, 0x18, 0x20, 0x40, 0x48, 0x50)]
                miembros = self.objetos(self.m.refa("CLA", k, 0x40, OBJ))
                puntero = w[0x40 // 4] and not miembros
                if otros or w[0] & 0x00FFFF00 or any(self.m.rec("OBJ", o)[0] != 3 for o in miembros) \
                        or puntero and (base.lower() == "struct" or w[0x40 // 4] <= 0x10000 or self.m.bits == 64 and w[0x44 // 4]):
                    raise NoSoportado(f"Struct {nombre} con {otros}")
                if puntero:
                    return [f"\t{nombre} is {base}"]
                if base.lower() == "struct" and (tabla := self.struct_de_tabla(miembros)):
                    return [f"\t{nombre} is Struct as {tabla}"]
                return [f"\t{nombre} is {base} begin", *(f"\t\t{x}" for x in self.decls(miembros)), "\tend"]
            if w[0] & 0xFF == 0x20:  # `B is A`, sin miembros ni puntero, de una base que no se ha visto
                raise NoSoportado(f"clase {nombre} is {base} sin miembros")
            otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in (0x00, 0x08, 0x10, 0x18, 0x20, 0x30, 0x48, 0x50)]
            if otros or w[0] & 0x00FFFF00:
                raise NoSoportado(f"clase {nombre} que no es un formulario ({w[0]:#x}, {otros})")
            # `X is Decimal (32,2)`, `X is Char (10)`: la precisión y la escala (o la longitud) en +0x30, como en un OBJ
            tipo = self.tipo(self.m.rec("CLA", k)) if base.lower() in ("decimal", "money", "char") else base
            if w[0x30 // 4] and base.lower() not in ("decimal", "money", "char") and (
                    base.lower() in BASICOS or not self.parametros_de_clase(w[6], self.m.rec("CLA", k)[0x30:0x34])):
                raise NoSoportado(f"clase {nombre} is {base} con +0x30 = {w[0x30 // 4]:#x}")
            return [f"\t{nombre} is {'abstract ' if w[0] & 0x80 else ''}{tipo}"]  # 0x80 del byte 0: abstract
        objetos = [f"\t\t\t{self.decl(o, 'FOB')}" for o in self.fobs(formulario)]
        raiz = self.m.refa("FOR", formulario, 0x10, FCT)
        defecto = self.m.refa("FOR", formulario, 0x30, FOB)  # default menu
        cabeza = [f"\t\tdefault menu {self.m.texto_ide(self.m.u32('FOB', defecto, 0x10))}"] if defecto is not None else []
        return [f"\t{nombre} is {base} begin", *cabeza, "\t\tobjects begin", *objetos, "\t\tend",
                *self.tablas_de(formulario), *self.menus_de(formulario), *self.interfaz().formulario(raiz, 2), "\tend"]

    def tablas_de(self, formulario: int) -> list[str]:
        """`Table alias is tabla begin … end` del formulario: FTA desde FOR+0x18, encadenadas por
        +0x08; sus columnas, FOB desde +0x20. Las de la tabla salen `as column`; las calculadas,
        con su tipo. (FRC, sus columnas clave, sale del repositorio y no se escribe.)"""
        salida, t, vistas = [], self.m.refa("FOR", formulario, 0x18, FTA), {}
        while t is not None:
            w = struct.unpack_from("<28I", self.m.rec("FTA", t))
            # +0x50 → las claves externas (FJO): salen del repositorio y no se escriben
            otros = [i * 4 for i, v in enumerate(w) if v and i * 4 not in
                     (0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x40, 0x48, 0x50, 0x58, 0x60, 0x68)]
            control = self.m.refa("FTA", t, 0x28, FCT)  # el control con `TABLE x`, que apunta aquí (+0x78)
            if w[0x28 // 4] and (control is None or self.m.refa("FCT", control, 0x78, FTA) != t):
                raise NoSoportado(f"tabla FTA {t}: control {w[0x28 // 4]:#x}")
            if w[0] & ~(VARTABLE | SIN_IS) != 0x9A000000 or w[0] & SIN_IS and not w[0] & VARTABLE or otros:
                raise NoSoportado(f"tabla FTA {t} con {otros} (joins…: aún sin descifrar)")
            # +0x68: la casilla de la tabla en la numeración del compilador (FOB +0x48), justo antes de sus columnas
            primera = self.m.refa("FTA", t, 0x20, FOB)
            if primera is None or w[0x68 // 4] + 1 != self.m.u32("FOB", primera, 0x48):
                raise NoSoportado(f"tabla FTA {t}: +0x68 = {w[0x68 // 4]}")
            alias = self.m.texto_ide(w[4])
            tabla = self.m.texto_ide(w[6]) if w[6] else alias
            salida.append(f"\t\t{'Vartable' if w[0] & VARTABLE else 'Table'} {alias}" + ("" if w[0] & SIN_IS else f" is {tabla}"))
            if w[0x30 // 4] or w[0x38 // 4]:  # delante de order by (detrás no compila)
                salida.append(f"\t\t\t{self.depend_on(t, vistas)}")
            vistas[t] = (alias, tabla)
            if w[0x48 // 4]:  # order by (a, b): la cadena «a|b»
                ref = _ref(w[0x48 // 4])
                orden = self.m.str.get(ref[1] * 4) if ref and ref[0] == STR else None
                if not orden:
                    raise NoSoportado(f"tabla FTA {t}: order by {w[0x48 // 4]:#x}")
                self.m.cadenas_usadas.add(ref[1] * 4)
                salida.append(f"\t\t\torder by ({', '.join(orden.split('|'))})")
            salida.append("\t\tbegin")
            f = self.m.refa("FTA", t, 0x20, FOB)
            while f is not None:
                if not (self.m.u32("FOB", f, 0) >> 24) & ESCRITA:  # la clave que añade el compilador: no se escribe
                    f = self.m.refa("FOB", f, 0x08, FOB)
                    continue
                self.tabla_de_columna[f] = tabla
                salida.append("\t\t\t" + self.columna(f))
                f = self.m.refa("FOB", f, 0x08, FOB)
            salida.append("\t\tend")
            t = self.m.refa("FTA", t, 0x08, FTA)
        return salida

    def depend_on(self, t: int, vistas: dict) -> str:
        """`depend on padre join clave`: +0x30 → la FTA padre (una de antes en el formulario); +0x38 → las FRC
        de la unión (columnas de la clave en el padre, cada una con su FOB). El nombre de la clave no se guarda:
        es la única FJO de la tabla (desde +0x50) que apunta al padre, y sus columnas, las de esas FRC."""
        padre = self.m.refa("FTA", t, 0x30, FTA)
        if padre not in vistas:
            raise NoSoportado(f"tabla FTA {t}: depend on {self.m.u32('FTA', t, 0x30):#x}")
        alias, tabla = vistas[padre]
        if alias.lower() != tabla.lower():  # con alias no se ha visto compilar (la hija con alias no compila)
            raise NoSoportado(f"tabla FTA {t}: depend on {alias} is {tabla}")
        claves, j = [], self.m.refa("FTA", t, 0x50, 0x15)
        while j is not None:
            if (self.m.texto_ide(self.m.u32("FJO", j, 0x18)) or "").lower() == tabla.lower():
                claves.append(j)
            j = self.m.refa("FJO", j, 0x08, 0x15)
        unen, r = [], self.m.refa("FTA", t, 0x38, 0x16)
        while r is not None:
            f = self.m.refa("FRC", r, 0x18, FOB)
            if f is None or self.m.refa("FOB", f, 0x50, FTA) != padre:
                raise NoSoportado(f"tabla FTA {t}: depend on con la FRC {r} fuera del padre")
            unen.append(self.m.texto_ide(self.m.u32("FRC", r, 0x10)))
            r = self.m.refa("FRC", r, 0x08, 0x16)
        ref = _ref(self.m.u32("FJO", claves[0], 0x28)) if len(claves) == 1 else None
        if not ref or ref[0] != STR or self.m.str.get(ref[1] * 4, "").split("|") != unen:
            raise NoSoportado(f"tabla FTA {t}: depend on {alias} sin una clave que lo explique")
        return f"depend on {alias} join {self.m.texto_ide(self.m.u32('FJO', claves[0], 0x10))}"

    def columna(self, k: int) -> str:
        r = self.m.rec("FOB", k)
        largo, alto = struct.unpack_from("<HH", r, 0x30)
        if not r[1] & 0x01:  # sin la marca de columna de la tabla (bit 0x01 del byte 1)
            if alto == 0xFFFF and struct.unpack_from("<2I", r, 0x78) == (0, 0) and not r[2] & 0x20:
                return self.decl(k, "FOB")  # `x as tabla.columna` sin join: el tipo resuelto, como un OBJ
            if alto == 0xFFFF:  # `x as tabla.columna` + `join clave lookup "columna"`: +0x78 → la clave (FJO)
                fjo = self.m.refa("FOB", k, 0x78, 0x15)
                buscada = _ref(struct.unpack_from("<I", r, 0x80)[0])
                if fjo is None or not buscada or buscada[0] != STR or r[2] & 0x20:
                    raise NoSoportado(f"columna FOB {k} de otra tabla sin descifrar")
                self.m.cadenas_usadas.add(buscada[1] * 4)
                columna = self.m.str[buscada[1] * 4]
                clave, tabla = (self.m.texto_ide(self.m.u32("FJO", fjo, o)) for o in (0x10, 0x18))
                return (f"{self.m.texto_ide(self.m.u32('FOB', k, 0x10))} as {tabla}.{columna}\n\t\t\t\t"
                        f'join {clave} lookup "{columna}"')
            return self.decl(k, "FOB")  # calculada: con su tipo, como una variable
        texto = f"{self.m.texto_ide(self.m.u32('FOB', k, 0x10))} as column"
        if r[2] & 0x20 and self.default_del_repositorio(k, r):
            pass  # lo copia el compilador del repositorio: no se escribe
        elif r[2] & 0x20:  # default, como el de un OBJ (el tipo, el de la columna en el repositorio)
            texto += f" default {self.valor_default(r)}"
        elif struct.unpack_from("<I", r, 0x28)[0] and not struct.unpack_from("<I", r, 0x2C)[0]:
            texto += " default null"  # sin el bit de default, +0x28 con lo que deja el compilador (sin default: 0)
        # required 0x400 (también si la columna es NOT NULL en el repositorio: entonces no hace falta escribirlo),
        # noentry 0x800, noupdate 0x1000; en este orden, detrás del default
        b = struct.unpack_from("<I", r, 0)[0]
        if b & REQUIRED and not self.no_nula(k):
            texto += " required"
        texto += (" noentry" if b & NOENTRY else "") + (" noupdate" if b & NOUPDATE else "")
        return texto + self.valores(k, r, "columna")

    def no_nula(self, k: int) -> bool:
        """Si la columna del FOB k es NOT NULL en el repositorio (hace falta el catálogo; sin él, no se sabe)."""
        if self.catalogo is None:
            return False
        tabla = self.tabla_de_columna.get(k)
        nombre = self.m.texto_ide(self.m.u32("FOB", k, 0x10))
        return any(c.no_nula for c in self.catalogo.columnas if c.tabla == tabla and c.nombre == nombre)

    def modulo(self) -> str:
        ctes = [self.constante(*c) for c in self.m.constantes()]
        # Los menús de un formulario son clases implícitas (byte 3 sin 0x10): van dentro del formulario.
        # Implícitas (no se escriben): las de los menús y las de las tablas de un formulario.
        clases = [c for c in range(1, self.m.s["CLA"].n) if not self.es_menu_implicito(c)
                  and self.m.u32("CLA", c, 0) != 0x8300002D]
        definiciones = [self.clase(c) for c in clases]
        # Procedimientos en el orden del fuente: los de cada clase (CODE CLASS), luego los del módulo.
        secciones = [(c, self.procs_de(c)) for c in clases] + [(0, self.procs_de(0))]
        procs, usos, de_seccion = [], [], []
        for c, ks in secciones:
            for k in ks:
                self.m.cadenas_usadas = set()
                procs.append(self.procedimiento(k))
                usos.append(self.m.cadenas_usadas)
                de_seccion.append(c)
        # Lo que queda en STR sin que lo apunte ningún literal (salvo la ruta del fuente, la
        # primera) son los comentarios de documentación {* … *}, en el orden del fuente: se
        # guarda lo que va entre «{*» y «}», con el «*» final. Su sitio no se guarda: solo su orden entre las cadenas.
        # Cada uno va tras el último procedimiento que tiene una cadena antes que él; si entre ese y el primero con una
        # cadena detrás hay otros (sin cadenas), o una frontera de sección, cabe en varios sitios con los mismos bytes:
        # se avisa.
        todas = self.m.cadenas_apuntadas()
        bloques = [[] for _ in range(len(procs) + 1)]
        orden = [c for c, _ in secciones]
        registros = self.m.registros_flujo("STR")
        for pos, texto in sorted(self.m.str.items()):
            if pos == 0 or pos in todas or texto is None or pos in self.char_null.values():
                continue
            if not texto.endswith("*"):
                raise NoSoportado(f"cadena de STR sin usar que no es un comentario: {texto[:30]!r}")
            texto = _con_global(texto, registros[pos].datos[4:], self.avisos)
            tras = max((i + 1 for i, u in enumerate(usos) if u and min(u) < pos), default=0)
            hasta = min((i for i, u in enumerate(usos) if u and min(u) > pos), default=len(procs))
            antes = de_seccion[tras - 1] if tras else orden[0]  # las secciones entre las que cae
            despues = de_seccion[tras] if tras < len(procs) else orden[-1]
            if hasta > tras or antes != despues:
                primera = texto.replace("\r", "").strip("\n *").split("\n")[0]
                self.avisos.append(f"comentario {{* {primera[:40]} … }}: su sitio no se guarda; va en el primero posible")
            bloques[tras].append("{*" + texto.replace("\r", "") + "}")
        # Los de antes del primer procedimiento van al principio de su sección (CODE CLASS o CODE).
        partes = {c: [] for c, _ in secciones}
        if bloques[0]:
            partes[de_seccion[0] if procs else 0].append("\n".join(bloques[0]))
        for i, p in enumerate(procs):
            partes[de_seccion[i]].append("\n".join(p))
            if bloques[i + 1]:
                partes[de_seccion[i]].append("\n".join(bloques[i + 1]))
        codigo = "\n\n".join(partes[0])
        codigo_clases = "".join(
            f"CODE CLASS {self.m.texto_ide(self.m.u32('CLA', c, 0x10))} BEGIN\n//{{{{CODEBEGIN\n"
            + ("\n\n".join(partes[c]) + "\n" if partes[c] else "") + "//{{CODEEND\nEND\n"
            for c in clases)
        seccion_clases = ("CLASSES BEGIN\n" + "".join("\n".join(d) + "\n" for d in definiciones) + "END\n") if clases else ""
        # Objetos globales del módulo (sección OBJECTS): OBJ de tipo 0, de la clase del módulo.
        globales = [k for k in range(self.m.s["OBJ"].n)
                    if self.m.rec("OBJ", k)[0] & 0x0F == 0 and self.m.refa("OBJ", k, 0x20, CLA) == 0]
        objetos = ("OBJECTS BEGIN\n" + "".join(SANGRIA + d + "\n" for d in self.decls(globales)) + "END\n") if globales else ""
        libs = self.m.librerias()
        librerias = ("LIBRARIES BEGIN\n" + "".join(SANGRIA + x + "\n" for x in libs) + "END\n") if libs else ""
        incs = self.m.librerias("INC")
        if incs:
            librerias += "INCLUDES BEGIN\n" + "".join(SANGRIA + x + "\n" for x in incs) + "END\n"
        # Fichero de mensajes: la cabecera guarda en +0x30 la posición de su nombre en IDE / 4.
        mensajes = struct.unpack_from("<I", self.m.b, 0x30)[0]
        if mensajes != 0xFFFFFFFF:
            if mensajes * 4 not in self.m.ide:
                raise NoSoportado(f"MESSAGES con un nombre que no está en IDE ({mensajes:#x})")
            librerias = f"MESSAGES {self.m.ide[mensajes * 4]}\n" + librerias
        if self.m.s["FTA"].n or self.usa_repositorio:  # el .omd no guarda el REPOSITORY: hay que darlo de fuera
            if not self.repositorio:
                raise NoSoportado("el módulo usa tablas y el .omd no guarda su REPOSITORY: dalo con --repositorio")
            librerias = f"REPOSITORY {self.repositorio}\n" + librerias
        return (librerias + "CONSTANTS  begin\n" + "".join(c + "\n" for c in ctes) + "end\n" + seccion_clases + objetos
                + codigo_clases + "CODE BEGIN\n//{{CODEBEGIN\n" + codigo + "\n//{{CODEEND\nEND\n")


GLOBAL = "@global"


def _con_global(texto: str, cuerpo: bytes, avisos: list) -> str:
    """El compilador quita `@global` de un comentario corriendo el resto del texto, y deja detrás del 0 la cola del
    texto viejo (los 6 bytes que sobran: 7 menos el 0). Ese resto dice que lo había y, con la cola, dónde: va al
    principio o tras un espacio, con un espacio, un salto o el final detrás, y vuelto a poner da esa cola. Si caben
    varios (lejos del final, la cola es la misma), va justo tras « * » si se puede (o en el primero), y se avisa: en
    CalcALG, `{*@global` sale ` * @global` (mismos bytes). Sin ninguno, NoSoportado."""
    fin = cuerpo.index(b"\0")
    resto = cuerpo[fin + 1:].split(b"\0")[0]
    if not resto:
        return texto
    s = cuerpo[:fin].decode("cp1252")
    sitios = [p for p in range(len(s) + 1) if (p == 0 or s[p - 1] == " ") and (p == len(s) or s[p] in " \r")
              and (s[:p] + GLOBAL + s[p:])[len(s) + 1:len(s) + len(GLOBAL)] == resto.decode("cp1252")]
    if not sitios:  # (la cola tiene que medir 6: lo que mide @global menos el 0)
        raise NoSoportado(f"comentario sin sitio para {GLOBAL} (le quitaron {len(resto) + 1} bytes)")
    # el preferido: justo tras « * » o tras «{* » (la forma de casi todos los del kit); si no, el primero
    p = next((p for p in sitios if s[p - 2:p] == "* " or p == 1 and s[0] == " "), sitios[0])
    if len(sitios) > 1:
        primera = s.replace("\r", "").strip("\n *").split("\n")[0]
        avisos.append(f"comentario {{* {primera[:40]} … }}: {GLOBAL} cabe en {len(sitios)} sitios con los mismos bytes")
    return s[:p] + GLOBAL + s[p:]


def descompilar(datos: bytes, repositorio: str | None = None, catalogo=None, avisos: list | None = None) -> str:
    """Fuente COOL (.SMD) del módulo; NoSoportado si usa algo que aún no se sabe leer. `catalogo`
    (repositorio.Catalogo) hace falta para los objetos `x as tabla.columna`; en `avisos` van las elecciones
    que no salen del .omd."""
    m = _Modulo(datos)
    e = _Escritor(m, repositorio, catalogo)
    if m.omd.version == contenedor.VERSION_3211:
        e.avisos.insert(0, AVISO_3211)  # el primero
    fuente = e.modulo()
    if avisos is not None:
        avisos.extend(e.avisos)
    return fuente

# Formato `.omd`: lo observado

Material: kits de evaluación de Base 100 (Cosmos 8.2, 8.4 y 8.6, x86 y x64), en `kits/` (fuera de git).
Todo lo de aquí se ha comprobado con `hubble` sobre esos ficheros, salvo lo marcado como **hipótesis**.

## 2026-10-27 — primera pasada (fase 1)

Corpus: 199 `.omd` en el kit 8.6 x64 (195 en los demás). Tamaño mínimo 2024 bytes, mediana 22 812, máximo 2 612 674.

- **Sin compresión ni cifrado.** Entropía global por fichero entre 1,30 y 3,46 bits/byte (mediana 2,23); ningún fichero tiene más del 80 % de sus bytes en bloques de 256 bytes con entropía ≥ 7,5.
- **Cabecera fija de 36 bytes**, idéntica en los 1174 `.omd` de los seis kits:
  ```
  43 4f 4d 44  01 00 00 00  30 72 00 00  14 00 00 00
  14 00 00 00  46 46 46 46  56 56 56 56  38 00 00 00
  4c 00 00 00
  ```
  `COMD` al principio; en 0x14 y 0x18, `FFFF` y `VVVV` en ASCII.
  **Hipótesis:** `01 00 00 00` versión del formato; 0x7230 no es un tamaño (es igual en ficheros de tamaños muy distintos).
- **Después varía:** en 0x24 y 0x28 hay sendos u32 little-endian que en todos los ficheros apuntan dentro del propio fichero (`hubble cabeceras`). **Hipótesis:** desplazamientos o longitudes de secciones.
- **Texto en claro**, en un byte por carácter: nombres de módulo, fuentes (`MS Sans Serif`, `Verdana`), nombres de tablas y formularios. En `triple.omd`, nombres de módulo a intervalos fijos de 0x24 bytes desde 0x3a8 (`Articulos`, `Clientes`, `Proveedores`…). **Hipótesis:** registros de 36 bytes.
- Hay rachas de bytes `0xCC` (en cp850 salen como `╠`). **Hipótesis:** relleno de memoria sin inicializar del compilador de Microsoft, que se ha escrito tal cual al fichero.
- No hay ningún tabulador entre texto en los 199 ficheros.
- **Entre versiones y arquitecturas** (comparando por nombre de fichero, 100 nombres en común con 8.6 x64):
  - x64: 99 de 100 idénticos byte a byte entre 8.2, 8.4 y 8.6. El formato no ha cambiado en esas versiones.
  - x86 frente a x64: solo 1 de 100 idéntico, con la misma cabecera de 36 bytes. El cuerpo depende de la arquitectura. **Hipótesis:** campos del ancho de un puntero.

## 2026-10-27 — el contenedor (comprobado en los 1174 `.omd`)

Lo lee `hubble.contenedor` (`hubble secciones fichero.omd`) y lo vigila `tests/test_corpus.py`: los 1174 ficheros quedan cubiertos byte a byte, sin huecos ni solapes.

```
0x00  cabecera (0x4C bytes)
        0x00 «COMD» … (36 bytes fijos, ver arriba)
        0x20 u32 → primera entrada de la lista A (siempre 0x4C: fin de la cabecera)
        0x24 u32 → primera entrada de la lista B
        0x28 u32 → primera entrada de la lista C
        0x2C 32 bytes sin interpretar (69 combinaciones distintas en el corpus)
      lista A: 6 entradas de 32 bytes, y detrás sus datos, seguidos
      lista B: 24 entradas, y detrás sus datos
      lista C: 7 entradas, y detrás sus datos hasta el final del fichero
```

Entrada de sección (32 bytes, u32 LE):

| desp. | campo | valores vistos |
|---|---|---|
| 0x00 | marca | 2, o 0 solo en secciones vacías (**hipótesis:** «presente») |
| 0x04 | ? | siempre 0 |
| 0x08 | tamaño de la entrada | siempre 32 |
| 0x0C | siguiente entrada | 0xFFFFFFFF en la última |
| 0x10 | desplazamiento de los datos | |
| 0x14 | etiqueta | 3 letras ASCII + NUL |
| 0x18 | número de registros | |
| 0x1C | tamaño de registro | depende de la etiqueta y de la arquitectura (ver abajo) |

Etiquetas, siempre las mismas y en el mismo orden:

- **A:** `LIB INC EMO ICO FON CMD`
- **B:** `CTE CLA OBJ MOP MNU PAG FOR FOB FTA FCT FJO FRC PCT DEC DTT ITV PRO STM REF DPR DST DRE IDE STR`
- **C:** `EOB EPR EFT ECT ECL EID SVL`

**Arquitectura.** Muchas etiquetas tienen dos tamaños de registro, el de 64 bits casi el doble que el de 32 (`STM` 24/48, `PRO` 32/64, `REF` 16/32, `CLA` 48/88…; tabla completa en `contenedor.TAMANOS_POR_BITS`). Cada fichero usa o todos los de 32 o todos los de 64, nunca mezclados: los 585 de los kits x86 son de 32; de los 589 de los kits x64, 580 son de 64 y 9 de 32 (entre ellos `converprjx64/main.omd`). Así sale la arquitectura de un `.omd` sin ejecutar nada (`hubble secciones` la muestra). Excepciones: `FOB` mide 76 en 32 bits y 144 o 152 en 64 (152 en 33 ficheros; sin explicar), y `DPR`/`DST`/`DRE` a veces declaran 0. `ICO`, `FON`, `CMD`, `DEC`, `DTT`, `ITV`, `IDE`, `STR`, `EOB`, `EID` y `SVL` miden lo mismo en las dos.

Todas ocupan exactamente n × tamaño de registro **salvo `IDE`, `STR` y `SVL`**, que ocupan otra cosa (casi siempre menos: en `Configuration.omd`, `IDE` tiene 2196 registros de 40 bytes en 41 722 bytes, no en 87 840). Las tres empiezan, en los 1174 ficheros, con un u32 igual a su número de registros; en `test1.omd` siguen 10 bytes y texto: `IDE` los identificadores del fuente, `STR` la ruta con la que se compiló el `.smd` y los literales de cadena. **Hipótesis:** registros de tamaño fijo empaquetados (sin los ceros de relleno).

En `test1.omd` (4 sentencias en `main`), `INC` = 2 (los dos `INCLUDES` del fuente) y `STM` = 5. **Hipótesis:** `STM` = sentencias (las 4 más el cierre), `PRO` = procedimientos, `CTE` = constantes, `CLA` = clases, `OBJ` = objetos, `FOR` = formularios, `MNU` = menús, `REF` = referencias, `IDE` = identificadores, `STR` = cadenas, `EID` = identificadores externos (`Module`, `Nif1`, `Char`, `BaseNif`, `TEST`). Los nombres salen de las etiquetas y de lo que contienen, sin comprobar.

Los `.omd` guardan la ruta de compilación: `test1.omd` del kit 8.6 se compiló en `C:\CosmosVersiones\cosmos742_x64\projects\NIF\test1.SMD`, una carpeta de Cosmos 7.4.2.

## 2026-10-27 — `IDE` y `STR` (comprobado en los 1174 `.omd`)

Lo lee `hubble.empaquetado` (`hubble textos fichero.omd [--seccion IDE] [--sql]`). En los 1174 ficheros se leen exactamente los n registros declarados y los bloques acaban justo donde la sección.

```
u32 n (= número de registros de la entrada)   u16 número de bloques
bloque: u16 tamaño sin empaquetar (32 × tamaño de registro: 1280 en IDE, 8448 en STR)
        u16 bytes guardados
        registros seguidos (ninguno se parte entre dos bloques)
```

- **Registro:** un u32 y un texto terminado en NUL; se guarda sin los ceros del final y se corta en el primer límite cuyo último byte es 0. El primer límite está a 8 bytes; después, de 4 en 4 en los ficheros de 32 bits y de 8 en 8 en los de 64. `IDE` mide 40 = 4 + 36 y `STR` 264 = 4 + 260 (`MAX_PATH`).
- **El u32** vale 0 en todos: los 294 676 registros de `IDE` y los 49 847 de `STR` del corpus. **Hipótesis:** un campo que se rellena al cargar el módulo (un puntero o un índice), y que en el fichero va siempre a cero.
- **`IDE`** guarda cada aparición de un identificador, en el orden del fuente: en `security.omd`, `SECURITY authenticate username password domain retStr retStatus retStatus STATUS_OK SetExecStatus retStatus retStr`, que es el orden exacto en que aparecen en `security.smd`.
- **`STR`** guarda la ruta de compilación del `.smd`, los literales de cadena y los comentarios de documentación `{* … *}`. Los SQL concatenados en el fuente salen en trozos.
- **Texto en Windows-1252** (`Condición` = `Condici\xf3n`; en cp850 la ó sería 0xA2).
- **Restos de memoria:** el compilador quita las etiquetas `@global` de los comentarios y deja detrás del NUL lo que había (`al\r\n *`). Si el NUL cae justo al final de una unidad, el resto empieza en la unidad siguiente y parece otro registro. No lo es: un registro de texto real empieza siempre por un u32 a 0, y el resto no (`or\r\n` = 0x0A0D726F). El lector lo junta con el registro anterior. Pasa en `auxiliar.omd` (6 kits, al final de `STR`) y `abseval.omd` (3 kits x86, **en medio** de `STR`). La primera versión del lector contaba el resto de `abseval` como uno de los n registros y dejaba fuera el último de verdad; salió al leer `SVL` con la regla general.

## 2026-10-27 — `SVL` (comprobado en los 1174 `.omd`)

Misma estructura de bloques que `IDE` y `STR`, con registros de dos tipos. En los 1174 ficheros se leen exactamente los n registros, los bloques acaban justo donde la sección y no sobra nada (19 906 de texto y 1298 binarios).

- **De texto** (u32 = 0): como en `IDE` y `STR`.
- **Binario** (u32 ≠ 0): 16 bits bajos = longitud en bytes contando el u32; 16 bits altos = tipo (del 0 al 13 menos el 12, y 65535; los más frecuentes, 1: 373, 2: 322 y 0: 189). Ocupa la longitud redondeada a la unidad (8 en 64 bits, 4 en 32): un binario de 36 bytes ocupa 40 en 64 bits.
- **El tope de los bloques** (primer u16) no es siempre 32 × 10: hay 320, 328, 360, 392… En todos los bloques es mayor o igual que su registro más largo; sin explicar.
- **Qué guarda:** los textos de las declaraciones `INTERFACE` de los formularios, en el orden del fuente. En `dbmanager/configuration.omd`: `Configuración` (el `LABEL` del formulario), `List` (el de su control `LIST`), un binario de tipo 1 y 168 bytes, `General`, `Mostar Conexiones ODBC en la lista de Conexiones` (sic), `Fichero ini`, `Seleccionar fichero` y `Editar fichero` (los `COMMENT` de dos botones)… hasta `Aceptar` y `Cancelar`. **Hipótesis:** el binario son las propiedades del control `LIST` que lo precede (`COLUMNS`, `CURSORTYPE`…).

`hubble textos --seccion SVL` los saca, con los binarios marcados.

## 2026-10-27 — el código: primeras observaciones en `test1.omd` (hipótesis)

**Todo esto sale de un solo fichero (`projects/NIF/test1.omd`, 64 bits) y está sin
comprobar en el corpus.** Fuente:

```
main objects begin nif as Nif1 end
begin
    nif = "12345678Z";
    Testea(nif);
    nif = "12345678S";
    Testea(nif);
end
```

- **Primer u32 de cada registro:** su byte alto parece el tipo de sección (`PRO` 0x05, `STM` 0x06, `REF` 0x07).
- **Referencias de 32 bits** entre secciones: byte 1 = sección, 16 bits altos = índice. `0x0e` = `STM`, `0x0f` = `REF` (`0x20e00` = STM 2, `0x40f00` = REF 4). También aparecen `0x07`, `0x08`, `0x19`, `0x1b`, sin identificar.
- **`PRO`** (1 registro, `main`): en +0x38, `0x0e00` = STM 0.
- **`STM`** (5 registros): lista enlazada por el campo de +0x08 (STM 1 → 2 → 3 → 4 → 0 = fin; STM 0 apunta a STM 1 en +0x18). Son las 4 sentencias más una cabecera. En +0x20 cada sentencia apunta a su nodo de `REF`: 4, 7, 12 y 15.
- **`REF`** (16 registros): árbol de expresiones; los nodos apuntan a otros nodos (REF 4 → REF 3 y REF 1; REF 3 → REF 0 y REF 2).
- **Los identificadores van como direcciones de memoria del compilador** (u64 en +0x18 de algunos nodos: `0x307412c`, `0x3074134`, `0x3074144`…). Sus diferencias (8, 16, 8, 8, 16) son las distancias entre los textos empaquetados de `IDE` 2 a 7, así que salen `nif`, `Testea`, `nif`, `nif`, `Testea`, `nif`: el orden exacto del fuente. El compilador escribe punteros tal cual, como las direcciones del binario de `SVL`.
- `DPR`, `DST`, `DRE` vacías aquí.

## 2026-10-27 — compilación diferencial: primeros resultados (batería, 64 bits)

Son 91 programas mínimos, cada uno a un solo cambio del base `main objects begin a as
integer end begin a = 1; end`. Se compilaron con `hubble-lab:3`; el detalle está en
`lab/bateria/README.md`. Todo lo de esta sección **sale de la batería (8.6 x64) y está
sin comprobar en el resto del corpus**.

- **La compilación es determinista.** Los programas con el mismo código en otro hueco
  (`coment_linea`, `espacios`) solo difieren en `IDE` y `STR` (nombre y ruta del módulo) y
  en el u32 de `REF[0]+0x18`. Los comentarios y los espacios no dejan rastro en el código.
- **Literales:** un nodo de `REF` por literal. Su tipo está en el byte bajo del primer
  u32, y el valor en +0x18.

  | Fuente | Primer u32 | Valor en +0x18 |
  |---|---|---|
  | `1`, `0`, `255`, `256` | `0x0700f060` | el número, en 16 bits (`-1` → `0xffff`, `-2` → `0xfffe`) |
  | `65535`, `65536`, `2147483647` | `0x0704f070` | el número, en 32 bits |
  | `1.5` (decimal) | `0x0704f080` | `0x0300` (la sección `DEC` pasa de 0 a 1 registro) |
  | `"x"` (char) | `0x0704f090` | `0x0e0200` |
  | `true` | `0x0704f0a0` | `1`, y después `cccccccc`: el relleno de memoria sin iniciar de MSVC |
  | `null` | `0x0704f0c0` | `0` |

  Con `a` de tipo integer, los literales que caben en 16 bits salen con 8 nodos de `REF`;
  los que no caben y `null` salen con 5, igual que `1` asignado a un smallint.
  [hipótesis] Los 3 de más son la conversión de smallint a integer.
- **Cuánto añade cada construcción**, en registros, frente a las 2 `STM` y los 8 `REF`
  del base:
  - otra asignación: +1 `STM` y +8 `REF`;
  - un `if` simple: +1 `STM` y +5 `REF`;
  - `if … else`: +2 `STM`;
  - `while`, `repeat` y cada `for`: +1 `STM`;
  - `switch` con 2 `case`: +4 `STM`;
  - cada función: +1 `PRO`.

  La tabla completa sale de `python lab/bateria/difer.py kits/compilados/bateria-86x64`.
- El «número de sección» de las referencias (0x0e = `STM`, 0x0f = `REF`) **no** es la
  posición de la sección en el fichero: `STM` es la 0x17 del orden global y la 0x11 de la
  lista B. Sigue sin saberse qué numeración es.

## 2026-10-27 — el código (64 bits), comprobado con la vuelta completa

Lo lee `hubble.descompilador` (`hubble descompila f.omd`). **La comprobación** es la vuelta
completa (`lab/bateria/vuelta_todo.sh`): descompilar, recompilar el fuente obtenido en el
laboratorio y comparar con el fuente original compilado igual (mismo script, misma
carpeta y ruta). Resultado: la batería, 91 de 91 idénticos byte a byte; `samples`, 94 de
94 de los que ya se descompilan (el resto, 321 de 415, da `NoSoportado`: clases,
formularios, eventos, librerías…).
Todo lo de esta sección es de ficheros de 64 bits.

**El contexto cambia el `.omd`.** El mismo fuente compilado con `-all` (proyecto entero) y
con `-smd` (módulo suelto) da ficheros distintos: `BET.SMD` sale con 3602 o con 3090 bytes
(cambian `ICO` y `FON`, los recursos que el proyecto declara en `samples.ini`). Por eso
la vuelta compara contra el original recompilado en las mismas condiciones.

### Referencias
u32: byte 0 = 0, byte 1 = número de sección, 16 bits altos = índice. La numeración no
es la posición de la sección en el fichero. En todo el corpus, cada código queda
acotado por el número de registros de una sola sección:

| código | sección | código | sección |
|---|---|---|---|
| 0x01 | `IDE` (posición en el flujo / 4) | 0x0F | `REF` |
| 0x02 | `STR` (posición en el flujo / 4) | 0x10 | `FCT` (controles de formulario) |
| 0x03 | `DEC` | 0x18 | `EMO` |
| 0x07 | `CLA` | 0x19 | `ECL` (clases externas → `EID`, sus nombres) |
| 0x08 | `OBJ` | 0x1B | `EPR` (métodos externos: u16 clase en `ECL`, u16 número de método) |
| 0x0B | `PRO` | 0x0E | `STM` |

El «flujo» de `IDE`/`STR` es la secuencia de registros empaquetados uno tras otro,
sin las cabeceras de bloque: la posición de un registro es la suma de lo que ocupan los
anteriores.

### `PRO` (64 bytes)
Cabecera: byte 0 = tipo (0 `main`, 1 función, 4 eventos y notificaciones: aún sin
descifrar); byte 3: 0x15 `public`, 0x35 `private` (bit 0x20), 0x05 `main`.
+0x08 siguiente `PRO`, +0x10 primer parámetro (`OBJ`), +0x18 clase propietaria (`CLA`),
+0x20 clase devuelta (`ECL`; `CLA` si no devuelve nada), +0x28 nombre (`IDE`),
+0x30 primer local (`OBJ`), +0x38 cuerpo (`STM`).

### `OBJ` (80 bytes)
Cabecera byte 0: 0 global del módulo (sección `OBJECTS`), 1 local, 2 parámetro, más
0x40 si es `VAR` (por referencia); bit 0x20 del byte 2: tiene `default`, con el
valor en +0x28 (como el de un literal). +0x08 siguiente, +0x10 nombre, +0x18 clase,
+0x20 procedimiento, +0x30: longitud (`Char(n)`) o u16 precisión y s16 escala
(`Decimal`, por defecto 16,-1; `Money`, por defecto 16,2).

### `STM` (48 bytes)
Byte 0 = tipo; +0x08 = siguiente sentencia.

| tipo | sentencia | campos |
|---|---|---|
| 0x00 | `begin … end` | +0x18 primera |
| 0x01 | `if` | +0x10 condición, +0x18 `then`, +0x28 `else` |
| 0x02 | expresión | +0x20 |
| 0x03 | `return` | +0x20 (opcional) |
| 0x04 / 0x24 | `for … to` / `down to` | +0x10 inicio, +0x18 límite, +0x20 `step`, +0x28 cuerpo |
| 0x05 | `while` | +0x10, +0x28 |
| 0x06 | `forever` | +0x28 |
| 0x07 | `repeat … until` | +0x10 condición, +0x28 cuerpo |
| 0x08 | `break` | |
| 0x0A / 0x0B | `switch valor` / `switch` de condiciones | +0x20 valor, +0x18 primer `case`, +0x28 `default` |
| 0x0D / 0x0C / 0x0E | `case` de valor / de condición / `default` | +0x10 condición, +0x28 cuerpo |
| 0x11 | `for … as lista` | +0x10 variable, +0x18 lista, +0x28 cuerpo |

0x09 = `continue;` (sin campos), 0x0F = sentencia vacía, 0x10 = `do … while cond;` (+0x10 condición, +0x28 cuerpo): descifrados el 2026-10-28 con `samples`.

### `REF` (32 bytes): nodos de expresión
Byte 0 = tipo de nodo, byte 1 = variante; +0x08 = siguiente (argumentos, elementos).

- **0x10 variable**: +0x10 → `OBJ`; +0x18 puntero a su aparición en `IDE`.
- **0x20 método** (byte 1: 0x20 de un objeto, 0x30 sin receptor, 0x50 sin receptor pero
  con la clase escrita delante, `Module.PutEnv(…)`): +0x10 → `EPR` o `PRO`;
  +0x18 = **código de operador** (`=` 1, `*` 3, `/` 4, `%` 5, `+` 9, `-` 10, `+=` 11,
  `-=` 12, `++` 13, `--` 14, `not` 15, `and` 16, `or` 18, `<>` 19, `>` 20, `>=` 21, `<` 22,
  `<=` 23, `between` 26, `in` 27, `is null` 28, `==` 31, `-` unario 33; 0 = conversión
  implícita) o, si tiene nombre, puntero de memoria a su identificador en `IDE`.
- **0x21 acceso** `obj.método`: +0x10 objeto, +0x18 método. **0x22 llamada**: +0x10 lo
  llamado, +0x18 primer argumento. Los operadores son llamadas: `a = a + 2` es
  `a.=( (a.+(2)).<conversión> )`.
- **Literales**: 0x60 smallint (16 bits en +0x18), 0x70 integer, 0x80 decimal (+0x18 →
  `DEC`), 0x90 char (+0x18 → `STR`), 0xA0 boolean, 0xC0 null. Byte 1 = 0x50: viene de
  una constante (`CTE`, mismo valor en +0x20).
- **0xD0 lista** (`in (…)` y argumentos variables): +0x08 primer elemento.
- **0xE0**: el valor del `switch` en la condición de cada `case`.
- **Palabras reservadas** (byte 1 = 0xF1, clase en +0x10): `today` (Date), `now` (Time).
- **0x00 / 0x31**: control de formulario (+0x10 → `FCT`).

`DEC` (22 bytes) es el `dec_t` de Informix: s16 exponente, s16 signo (1 +, 0 −, −1 null),
s16 número de dígitos y los dígitos en base 100 (1.5 = exp 1, dígitos 1 y 50).

**Lo que el `.omd` guarda sin querer, y el descompilador aprovecha:**
- Los paréntesis vacíos de `a.Trace()` cambian el orden de creación de los nodos: con
  paréntesis, el acceso es justo el nodo anterior a la llamada; sin ellos, se crea en
  otro momento.
- Los argumentos por defecto los añade el compilador después de la llamada (índices
  mayores que el suyo; siempre literales). La lista de argumentos variables (0xD0), aunque
  vaya vacía, es el último eslabón, detrás de los por defecto.
- Los comentarios de documentación `{* … *}` van en `STR` entre las cadenas, en el orden
  del fuente, guardando lo que hay entre `{*` y `}` (con el `*` final). Una cadena de
  `STR` a la que no apunta ningún literal es un comentario; las que añade el compilador
  como argumento por defecto sí tienen literal.
- Los punteros a `IDE` son direcciones de memoria del compilador, y cada bloque de `IDE`
  estaba en una zona distinta. La base de cada grupo de punteros se deduce con los nombres
  de las variables como ancla.

## 2026-10-28 — formularios y clases (64 bits), comprobado con la vuelta completa

Lo descifra la batería de formularios (`lab/bateria/formularios.py`: un atributo, control o
evento por programa) y lo escribe `hubble.interfaz`. Vuelta completa: la batería, 92 de 92
idénticos byte a byte; `samples`, 103 de 103 equivalentes (84 idénticos y 19 salvo punteros).

**Contexto de compilación.** `FON` (fuentes) y `CMD` (comandos) acumulan entradas de los
otros módulos de la misma tanda de `-smd`: la referencia de la vuelta se compila en las
mismas tandas.

- **`CLA`** (88 bytes): +0x10 nombre (`IDE`), +0x18 clase base (`ECL`: `Form`…), +0x40
  formulario (`FOR`), +0x50 primer procedimiento (encadenados por `PRO`+0x08). `CLA 0` es
  el propio módulo.
- **`FOR`**: +0x10 control raíz (`FCT`), +0x20 primera variable del formulario (`FOB`).
- **`FOB`**: variables del formulario (las de su `objects`): +0x08 siguiente, +0x10
  nombre, +0x18 clase, +0x20 clase propietaria, +0x58 control asociado. Los nodos de
  variable de `REF` apuntan a ellas con el código 0x12.
- **`FCT`** (208 bytes; el formulario es `FCT 0`): +0x08 siguiente hermano, +0x10 primer
  hijo, +0x18 padre; +0x20 u16 tipo de control (BUTTON 1, RADIO 2, CHECK 3, DROPLIST 4,
  DROPEDIT 5, EDIT 6, TEXT 7, BOX 8, PERCENT 0x0A, LIST 0x0D, BITMAP 0x0F, PANEL 0x11,
  GRID 0x15, SPIN 0x17, SLIDER 0x18) y u16 `DATATYPE` (CHAR 0, SMALLINT 1, INTEGER 2,
  DECIMAL 3, DATE 5); +0x28 número de control; +0x30 nombre (posición en `IDE` / 4, **más
  1**; 0 = sin nombre); +0x38 u16 x, y y +0x3C u16 ancho, alto (`POSITION`); +0x40
  `NUMBER`, `CHAR(n)`, el comando de un botón o, en el u16 alto, 1 + la fuente en `FON`;
  +0x48 `LABEL`, +0x58 `TAGS` (unidos con `|`) y +0x80 `COMMENT` (código 0x21 = `SVL`);
  +0x50 `BACKGROUND` y +0x54 `FOREGROUND` (COLORREF, BGR; 0x80000000 = sin color);
  +0x58 del formulario: el control con `FOCUS`; +0x78 `VARIABLE` (→ `FOB`).
  - Bits de +0x00: DOUBLE 0x04, ETCHED 0x08, DOWN 0x20, NOBORDER 0x40, DEFPUSH 0x400,
    NOLABEL 0x800, MULTILINE 0x1000, LIKEVAR 0x4000, AUTOSIZE 0x8000, PASSWORD 0x20000,
    UPSHIFT 0x40000, DOWNSHIFT 0x80000, DISABLED 0x100000, BOLD 0x800000, LABEL 0x10000000,
    TAGS 0x20000000, COMMENT 0x40000000; siempre 0x80000000. En el formulario: SYSMENU
    0x100, RESIZING 0x200, MAXIMIZE 0x1000, MINIMIZE 0x2000, y 0x04 si no es `NOBORDER`.
  - Bits de +0x44: ATTACH TOP 0x1000, BOTTOM 0x2000, LEFT 0x4000, RIGHT 0x8000 (BOTTOM
    [hipótesis]: deducido de ALL = 0xF000); NOTABSTOP 0x200000, ALIGNMENT CENTER 0x400000
    y RIGHT 0x800000, BUTTON 0x1000000, WRAP 0x4000000, DATETIMEPICKER 0x10000000;
    0x20000 lo ponen solos DROPLIST y DROPEDIT.
- **`FON`** (40 bytes): u16 0xFFFF, u16 tamaño, u16 juego de caracteres, u16 (0 =
  `CHARSET Ansi` escrito, 1 = sin él), nombre en +8.
- **Eventos** (`PRO` según su tipo): 4 = del formulario, código en +0x28 (Open 1, Close
  2, Timer 25, ChangeSize 67); 5 = de un control: +0x28 → nombre del evento **como cadena
  de `STR`** («Click», «Exit»…), +0x20 = el control (posición en `IDE` / 4, más 1);
  6 = de tabla o lista (Fetch 13, Edit 19, AcceptEdit 20, CancelEdit 21, QueryEnd 23,
  ChangingRow 41: sin descompilar aún); 7 = `On Command`, +0x28 = número de comando
  (los del usuario, 1 + su índice en `CMD`; los predefinidos, del final del rango:
  Close 0xFFEF, AcceptEdit 0xFFF0, CancelEdit 0xFFF1, EditUpdate 0xFFF3, EditNew 0xFFF4,
  Update 0xFFF9, Delete 0xFFFA, ResetFilters 0xFFDC, FilterByColumn 0xFFDD).
- **Listas** (batería `lab/bateria/listas.py`, 32/32 idénticos byte a byte): +0xA8 bits
  `LISTTYPE LISTCOLS` 0x1, `SELECTTYPE SIMPLE` 0x10 y `MULTIPLE` 0x30 (los desplegables
  traen SIMPLE de serie), `ICON FILE` 0x100 (el índice en `ICO` va en el binario de `SVL`
  de la lista: **corregido** en la sección siguiente; la regla de +0x70 era errónea),
  `SORTONCLICK` 0x400; +0xB0 u16 nº de columnas (`LISTCOLS n`, `COLUMNS n`) y u16
  `CURSORTYPE` (FILE 1, SQL 2, ninguno 4, TREEVIEW 5); +0x60 u16 alto = `SHOW n LINES`;
  en +0x00, `SCROLL` HORIZONTAL 0x100 y VERTICAL 0x200. **El registro binario de `SVL`
  de cada lista (sus columnas: 168 bytes más 32 por columna) lo calcula el compilador**
  con estos atributos y el tamaño del control (lleva punteros y anchos calculados): no
  hace falta escribirlo.
- **Argumentos por defecto, regla completa:** un literal al final de los argumentos es
  por defecto si se creó después de la llamada, o si lleva basura más allá del ancho de
  su tipo. Un literal escrito lleva ahí ceros, o un 0x11 seguido de ceros.
- **El orden de los atributos importa** al compilar: `DATATYPE` va después de los de
  aspecto, `VARIABLE` y `BUTTON` antes de `DATATYPE`, `DATETIMEPICKER` después, y `BORDER`
  junto a `NOBORDER`. Sin descifrar aún: GRID, páginas (`PAG`), menús (`MNU`), librerías (`LIB`),
  includes (`INC`) y clases que no son formularios (las de tablas, `is customers`).

## 2026-10-28 — 32 bits, y la posición en el flujo de IDE/STR

- **Posición en el flujo** (lo que cuentan las referencias 0x01/0x02 y los punteros): cada
  bloque cuenta como si ocupara entero su tope (1280 en `IDE`, 8448 en `STR`), aunque
  guarde menos (un registro nunca se parte). En 64 bits los bloques de `IDE` suelen salir
  llenos y no se notaba; en 32 bits no (`msgconstants.omd`: 1268 de 1280).
- **32 bits**: los registros con punteros se leen expandiéndolos a la disposición de 64 bits
  (`descompilador.MAPA_32`): en 64, las referencias van en huecos de 8 bytes; en 32, de 4.
  `REF`, `STM` y `PRO` son la mitad exacta; `OBJ`, `CLA`, `CTE`, `FOR`, `FOB`, `FCT`,
  `EPR` y `ECL` tienen su tabla, deducida comparando los 579 módulos que los kits traen
  compilados en las dos arquitecturas. Comprobación: los 12 de esos pares que ya se
  descompilan dan **el mismo fuente** en 32 y en 64 bits (test
  `test_32_bits_da_lo_mismo_que_64`). Sin vuelta completa en 32 bits: el laboratorio solo
  tiene Wine de 64 (haría falta instalar los paquetes i386 de Wine). (resuelto el 2026-10-29: «32 bits con el compilador del laboratorio»)

## 2026-10-28 — librerías, DLL, propiedades e iconos de lista (64 bits), con la vuelta completa

Sale de `samples` (sin batería nueva): se descompilan 143 de 415, y los 143 vuelven a
dar su `.omd` (122 idénticos byte a byte; 21 salvo punteros de memoria).

- **`LIBRARIES`**: `LIB` (24 bytes) +0x08 siguiente (código 0x04 = `LIB`), +0x10 nombre
  en `EMO` (código 0x18). `EMO` (40 bytes) lleva el nombre en +8 (en 32 bits, en +4 [sin
  vuelta completa]) y en mayúsculas: el fuente original puede decir `LibChart`. `EMO`
  lista además las librerías que incluyen las escritas (`LIBPRNPAG` trae `LIBCON`), que no
  se escriben. Las funciones de una librería se llaman como métodos de su clase externa
  (`EPR`/`ECL`, que apunta al nombre en `EID`).
- **`dll` y `javaclass`**: `PRO` de tipo 0x09 y 0x0D, sin cuerpo; +0x30 = la DLL o la
  clase Java como cadena de `STR`; el resto como una función (+0x10 parámetros, +0x20
  clase devuelta, bit 0x20 del byte 3 = `private`).
- **`MESSAGES nombre`**: cabecera +0x30 = posición del nombre en `IDE` / 4 (0xFFFFFFFF sin él).
- **Propiedades** (`bmp.Bitmap = …`): nodo 0x11 de `REF`, +0x10 el objeto y +0x18 la
  propiedad: un nodo 0x10 que apunta a `EOB` (código 0x1A) y cuyo nombre sale del puntero
  de +0x18, como el de los métodos. Byte 1: 0x00 si se escribe, 0x04 si se lee [hipótesis].
- **`REPOSITORY x`** no deja rastro en el `.omd` cuando no se usan sus tablas
  (`showaggsincompactmode`): el descompilado sin él da los mismos bytes.
- **Icono de una LIST**: **no** va en +0x70 (siempre 0 en una LIST; 0xFFFFFFFF en
  DROPLIST y DROPEDIT), sino en su registro binario de `SVL` (FCT+0x68): u16 en +0x18 =
  índice en `ICO`, 0xFFFF sin icono; u16 en +0x1A = 0xFFFF. Comprobado en las 129 listas
  con icono de `samples`. La regla anterior (+0x70) salía bien en la batería porque allí
  `ICO` solo tenía una entrada.
- **Posición en el flujo de `SVL`**: igual que en `IDE`/`STR`, cada bloque cuenta su tope
  entero; antes se sumaban los registros y las referencias del segundo bloque fallaban.
- **`COLOR transparent`** = 0xC0000000 en +0x50/+0x54.
- **Icono de los demás controles** (`ICON n FILE "x"` en BUTTON, BOX, EDIT, CHECK, TAB…):
  +0x70 = (n − 1) << 16 | índice en `ICO`, y bit 0x2000 de +0x00 [observado en `samples`,
  sin batería]. Sin icono, +0x70 = 0xFFFFFFFF en BUTTON, BOX y EDIT y 0 en los demás.
  Aún sin escribir: da `NoSoportado` (antes se perdía en silencio).
- **Contexto de compilación**: `ICO` también se acumula en la tanda. Un icono mal leído
  en un módulo cambia el `ICO` de los que se compilan detrás.
- **Tipos de control** vistos en `samples` (por el nombre del control en el fuente):
  TAB 0x0B, BUTTONGROUP 0x0C, BOXGROUP 0x0E, BAR 0x10, USER 0x13, MDICLIENT 0x1B.

## 2026-10-28 — controles: iconos, bordes y atributos por tipo (batería `controles.py`)

Batería `lab/bateria/controles.py`: 109 programas, un cambio cada uno sobre la base de su tipo.
Compilan 87; de los que no, se aprende el orden. Los 72 que se descompilan dan **exactamente
su fuente**, y la vuelta completa da 72/72 byte a byte. `samples`: 157 de 415, y los 157
equivalentes (141 byte a byte, 16 salvo punteros).

- **Un bit de +0x00 significa una cosa u otra según el tipo de control:**

  | bit | BUTTON / BOX / EDIT | EDIT sin icono, listas | CHECK, RADIO | BITMAP | SLIDER | SPIN |
  |---|---|---|---|---|---|---|
  | 0x100 | con ICON: sin `CENTER` | `SCROLL HORIZONTAL` | `LABELLEFT` | `STRETCH` | | `COMMAND` |
  | 0x200 | con ICON: `VERTICAL` | `SCROLL VERTICAL` | | | `POINT TOPLEFT` | |
  | 0x400 | `DEFPUSH` (BUTTON) | | | | `TICKMARKS` | |
  | 0x1000 | `MULTILINE` (EDIT, TEXT) | | | | | `VERTICAL` |
  | 0x2000 | `ICON` | | | `AUTOFIT` | | |

  En un EDIT con icono y `SCROLL HORIZONTAL` el 0x100 es ambiguo; las dos lecturas dan los
  mismos bytes.
- **Comunes:** `BORDER` = DOUBLE 0x04, ETCHED 0x08, DOWN 0x20, FRAME 0x80 y `EXTRA n` en
  los 2 bits bajos (`BORDER ETCHED EXTRA 3` = 0x0B); `INVISIBLE` 0x400000; BOX `SCROLL`
  HORIZONTAL 0x1000000 y VERTICAL 0x2000000.
- **+0x44:** `CURSOR` 0x8000000, `STORE DESIGN` 0x100000 (+ `STATUS` 0x80000),
  `READONLY` 0x40000000 (EDIT), `SPIN BUTTON` = 0x2000000 + el bit de `BUTTON`, en una LIST
  `ALLOWDRAG` 0x300 y `ALLOWDROP` 0x10000 (en un EDIT no compilan).
- **Icono** (`ICON n FILE "x" [CENTER] [VERTICAL]`, BUTTON/BOX/EDIT): +0x70 = (n − 1) << 16 |
  índice en `ICO`. En un CHECK, `ICON n` sin `FILE` (con `FILE` no compila; el BUTTON lo
  exige): +0x70 = (n − 1) << 16. Se escribe **detrás de `BORDER`/`NOBORDER`**: delante no compila (y en un CHECK,
  además, detrás de AUTOSIZE y de VARIABLE: sección del 2026-11-02).
- **+0x60:** u16 bajo = `PAGE n` − 1 (la página de un TAB donde va el control; `PAGE 0` =
  0xFFFF); u16 alto = `CURRENT PAGE n` − 1 en BOX y TAB (en DROPLIST/DROPEDIT, `SHOW n LINES`).
- **SLIDER** `RANGE a b`: +0x68 = a | b << 16. **SPIN** +0x40: 2 de serie, 4 `QUADRUPLE`.
  **BAR** `BARTYPE`: u16 alto de +0x20 (MENU 1, STATUS 2). **BITMAP** `BITMAP FILE "x"`:
  el bit de TAGS y la cadena en +0x58, como unos TAGS.
- **Variables del formulario (`FOB`)**: empiezan como `OBJ` (bit de `default` en el byte 2,
  valor en +0x28, longitud o precisión en +0x30). Antes se escribían sin tipo ni `default`.
- **Orden al compilar** (lo que no compila en la otra variante): `READONLY` y `SCROLL`
  detrás de `DATATYPE`; `SPIN BUTTON`, `STORE`, `ICON`, `INVISIBLE` y `CURSOR` delante;
  `LABELLEFT` y `CURSOR` de un RADIO delante de `NUMBER … TAGS`. `PAGE`/`CURRENT PAGE` van
  tras `POSITION` en los fuentes del kit.
- **Guarda:** un campo de FCT que el descompilador no lee tiene que estar a 0 (y +0x88 ser
  la clase `SimpleFormControl`); si no, `NoSoportado`. Ya ha destapado campos que se
  perdían en silencio: `RANGE`, `QUADRUPLE`, `PAGE`, PANELTYPE (u16 alto de +0x20 de un
  PANEL) y +0xA0 de un TEXT.
- ~~**Pendiente:** TAB (0x0B), BUTTONGROUP (0x0C) y BOXGROUP (0x0E)~~ (hechos: TAB en la sección del TAB, los
  grupos en la del 2026-10-29); tipo `VAR`; PANELTYPE.

## 2026-10-28 — tipos de dato, eventos y defaults (batería `datos.py`)

Batería `lab/bateria/datos.py` (45 programas; compilan 40). Los 37 que se descompilan con
su fuente propio lo dan exacto.

- **`DATATYPE` de EDIT y DROPEDIT**: u16 alto de +0x20 = tipo (nibble bajo) | `MASK n`
  << 4 (`INTEGER MASK 2` = 0x22). +0x40: `CHAR(n)` = n; `DECIMAL(p,s)` = p | s << 8
  (`DECIMAL` a secas = 0xFF00; `DECIMAL(9,2)` = 0x209; la escala negativa no compila).
  **Antes se perdía el (p,s).** Con `LIKEVAR` el tipo sale de la variable y no se escribe.
- **u16 alto de +0x20** en otros controles: `PANELTYPE` de un PANEL (COMMENT 1, EDITMODE 3;
  DATE y TIME no compilan); `BORDER HILIGHT` 0x0C y `BORDER BLACK` 0x10 de un BUTTON.
- **Eventos de control** (`PRO` tipo 5), dos formas:
  - clásica (byte 1 = 0x45): `On Click c`, con +0x20 = posición del control en `IDE`/4 + 1;
    con +0x20 = 0, `On Click (sender as char)` (de cualquier control: el nombre llega
    como parámetro);
  - `On event X [control Y] (e as event)` (bit 0x80 del byte 1 y 0x01 en el byte 2):
    el evento **y el control** son cadenas de `STR` (+0x28 y +0x20).
- **`default` de un Char**: bit 0x20 del byte 2 del `OBJ`/`FOB` y +0x28 → la cadena en
  `STR`. **`Char default null` no marca el default**: deja una cadena «NULL» suelta en
  `STR` y nada más, así que no se sabe de qué variable es (`NoSoportado`). `Integer default
  null` da los mismos bytes que sin default.
- **Operadores** que faltaban: `**` 2, `*=` 6, `/=` 7, `%=` 8, `xor` 17, `matches` 24, `like`
  25, `is not null` 29 y **30 = índice**: `a[i]` y la subcadena `a[i, j]`. Las asignaciones
  son asociativas por la derecha: `a = b = 1` sin paréntesis (con ellos cambia el árbol).
- **`case between a and b:`** en un `switch` de valor: la condición es `valor between a and b`.
- **Paréntesis vacíos**, regla completa: con paréntesis, el acceso va justo antes de la
  llamada **o justo detrás de su método**; esto último es lo que queda cuando la llamada se
  crea tarde porque su resultado lleva conversión (`a = s.Min()` con `a` Smallint).
- **Booleano por defecto:** como los demás literales, lleva basura tras el valor (+0x1C) si
  no se escribió; uno escrito lleva ceros o el relleno de MSVC (0xCC). (Primera versión:
  «sin 0xCC = por defecto», errónea: quitaba `DrawListLines(false)`.)
- **`VAR`**: el bit 0x40 del `OBJ` lo pone el compilador solo en los parámetros de clase
  (objetos: `SimpleFormControl`, `Event`…), y ahí escribir `VAR` no compila. En los eventos
  `Dragover` y `Dragdrop`, la firma exige `var result` y eso no deja rastro en el `OBJ`
  (observado en `getdragcolumngetdropcolumn`).
- **`ArgList of X`**: +0x40 del `OBJ` = la clase de los elementos (`ECL`), +0x30 su
  precisión. En 32 bits no se sabe dónde va (`NoSoportado`).
- **`FON`** (corrección): +2 tamaño, +4 **estilo** (ITALIC 1, BOLD 2), +6 **juego** (1 =
  DEFAULT_CHARSET, sin `CHARSET` escrito; 0 Ansi, 161 Greek, 162 Turkish, 204 Russian).
  `BOLD` del control se escribe **delante** de `FONT`: detrás, el compilador lo aplica a la fuente.
- **Formulario** +0x44: 0x400 = `ALLOWDROP`; +0x68 = su `CLA`. Guarda también en FCT 0.
- **Ruido del compilador:** al unir literales de cadena adyacentes largos, a veces mete
  memoria sin iniciar en la cadena de `STR` (`ÍÍÍÍ…ýýýý`, relleno del montón de depuración
  de MSVC): `groupby` sale así en una compilación y limpio en otra, con el mismo fuente.

## 2026-10-28 — clases que no son formulario (64 bits), con la vuelta completa

`samples`: 241 de 415, los **241 equivalentes** (183 byte a byte).

- **`CLA`** byte 0 = tipo de la base: Struct 0x20, Form 0x21, Menu 0x22, Page 0x23, Array
  0x24, ArgList 0x29, Enum 0x08, EnumSet 0x09, y el del tipo básico en las derivadas
  (Smallint 2, Integer 3, JSON 0x10…); +0x80 = `abstract`. Byte 3: 0x10 = escrita en el
  fuente (sin él, la crea el compilador: las clases de tabla `states`, `customers`… que salen
  de usar la tabla). +0x08 siguiente clase, +0x20 → `EMO`, +0x48 sin descifrar.
- **Derivada simple** (`A is Smallint`, `B is A`, `cJson is JSON`): nada más.
  **`X is Array [n] of Y`**: n en +0x34, Y en +0x40. **`X is Struct begin … end`**: +0x40 →
  primer miembro (`OBJ` de tipo 3, encadenados como los demás).
- **`Struct as tabla`**: los miembros salen de las columnas y llevan +0x30 = 0xFFFF0000 aunque
  sean Integer o Date. **Antes ese +0x30 no se miraba** en los tipos sin parámetros: ahora,
  si no es 0, `NoSoportado`.
- **`self`**: nodo literal 0x60 con variante 0x31 y +0x10 → la clase. **Se escribía como el
  número 0**: ahora un literal tiene que llevar variante 0xF0 (o 0x50, constante).
  **`parent.metodo`**: método con variante 0x40.
- **`return`**: lo dice el bit 0x04 del byte 1 de `PRO` (sin return). +0x20 apunta a la
  clase devuelta, o a la propia clase si no devuelve nada (por eso `return sm` en una
  clase `sm` y un método sin return dan la misma +0x20).

## 2026-10-28 — `INCLUDES`, y contexto de compilación igual en los dos lados

- **`INCLUDES`**: `INC` (24 bytes) igual que `LIB`: cabecera 0x80000000, +0x08 siguiente
  (código 0x05 [hipótesis: no hay ningún módulo con dos]), +0x10 → nombre en `EMO`. En el
  fuente va detrás de `LIBRARIES`.
- **La vuelta, más justa:** el compilador se cae en una tanda por un fuente concreto (el
  `GROUPBY` original, el de la memoria sin iniciar): solo salen los 2 primeros y el resto se
  compila uno a uno, sin acumular `ICO`/`FON`/`CMD`. Ahora `compila_lote.sh` recibe el
  informe de la referencia y compila solos, también en la vuelta, los que allí salieron
  `ok-solo`. `samples`: 247 de 415, 246 equivalentes y `groupby` (el ruido del compilador).

## 2026-10-28 — sentencia vacía y valor implícito de un control

- **STM 0x0F** = sentencia vacía (`;`): solo cabecera y siguiente.
- **Propiedad implícita:** `medit = "x"` o `x = txtHora` (el valor de un control) es un nodo
  0x11 cuya propiedad (nodo 0x10 → `EOB`) no apunta a `IDE` sino a la memoria estática del
  compilador: 0x1401A1358 en cosmakecon 8.6 x64 (38 apariciones en `samples`, todas iguales).
  En las páginas (`PAG`) sale otra, 0x1401A14FC. Con otro compilador, otra dirección:
  `NoSoportado`.
- `samples`: 262 de 415, los **262 equivalentes** (185 byte a byte).

## 2026-10-28 — el control TAB (batería `tabs.py`)

Batería `lab/bateria/tabs.py` (26 programas; compilan 25, todos con la vuelta byte a byte).
`samples`: 285 de 415, los **285 equivalentes** (169 byte a byte).

- **TAB** (tipo 0x0B): +0x40 = `NUMBER` (u16 alto, la fuente); las etiquetas, unidas con
  `|`, en el texto de `SVL` de +0x48 (con el bit de LABEL); +0x68 → binario con 3 u32 de
  cabecera y 3 por página: ancho (calculado), icono (u16 alto = n − 1 de `TAB LABEL "x" ICON n`,
  0xFFFE sin él; el bajo, calculado: 2 en un TAB pequeño [hipótesis]) y un tercero calculado.
- Bits de +0x00: `FIXED WIDTH` 0x100, `LOWTAB` 0x400, `VERTICAL` 0x1000, `ICON FILE` 0x2000 con
  +0x70 = índice en `ICO`. **No se guardan:** la n de `FIXED WIDTH` (1, 2, 3 y 5 dan los
  mismos bytes; sale `FIXED WIDTH 1`) ni el `CENTER` del `ICON FILE`. `FIXED` a secas no compila.
- `CURRENT PAGE n`: u16 alto de +0x60 (n − 1), como en un BOX.
- **Orden:** `BORDER`, `VERTICAL`, `LOWTAB`, `FIXED WIDTH`, `ICON FILE`, `NUMBER n`, las `TAB LABEL`;
  un TAB necesita algún atributo antes de `NUMBER` y lleva siempre `BEGIN … END`. `PAGE` y
  `CURRENT PAGE` van detrás de `ATTACH` (delante de `FONT` o de `ATTACH`, no compilan).
- Arreglo: el `NUMBER` de un RADIO usaba el u32 entero de +0x40, con la fuente dentro.

## 2026-10-28 — menús (batería `menus.py`)

Batería `lab/bateria/menus.py` (18 programas; compilan 17, 17/17 con la vuelta byte a byte).
`samples`: 290 de 415, los **290 equivalentes** (161 byte a byte).

- **`MNU`** (32 bytes): +0x10 → raíz en `MOP` (código 0x0A); +0x18 → la clase del menú (`CLA`,
  código 0x07) en los menús de un formulario. Código de `MNU`: 0x09.
- **`MOP`** (104 bytes), árbol: +0x08 siguiente, +0x10 padre (`MNU` en la raíz), +0x18 texto
  (`STR`), +0x28 número correlativo (lo pone el compilador), +0x2C nombre (posición en `IDE`/4
  + 1, como los controles), +0x30 = 0xFFFF0000 | `COMMAND` (mismo número que un botón), +0x40
  primer hijo. Cabecera: raíz (`PULLDOWN`) 0x89084040; opción 0x89000000 con byte 1 = 0x40
  `MENU` (submenú), 0x01 `CHECKED` y 0x02 «detrás va un `SEPARATOR`» (no tiene nodo propio).
  `POPUP` no compila.
- **Menú de un formulario** (`menu x PULLDOWN BEGIN … END`, entre su `objects` y su
  `INTERFACE`): una variable `FOB` (encadenadas desde FOR+0x28) cuya clase es una implícita de
  menú (`CLA` 0x83000022, +0x40 → `MNU`); esas clases no se escriben en `CLASSES`.
  **`default menu x`**: FOR+0x30 → su `FOB`, y el bit 0x40000 de +0x00 del formulario.
- **Clase `X is Menu PULLDOWN …`**: `CLA` 0x93000022, +0x40 → `MNU`.
- **Control MENU** (tipo 0x14) de una barra: `MENU x`, con +0x68 → la raíz del menú; +0x24 =
  0xFFFF y +0x40 = 1 siempre [sin descifrar].
- `self.SetMenu(m)` dentro del formulario sale `SetMenu(m)`: mismos bytes.

## 2026-10-28 — páginas (`X is Page`, batería `paginas.py`)

Batería `lab/bateria/paginas.py` (31 programas; compilan 29, 29/29 con la vuelta byte a byte).
`samples`: 303 de 415, 302 equivalentes (199 byte a byte) más `groupby` (ruido del compilador).

- **`PAG`** (32 bytes, código 0x0C) hace de `FOR`: +0x08 siguiente página, +0x10 raíz en
  **`PCT`** (código 0x11, controles de 208 bytes como los de `FCT`), +0x18 primera variable
  (`FOB`). La clase (`CLA` 0x93000023) apunta a su `PAG` en +0x40.
- **Raíz de la página:** `SIZE w h` en +0x3C; `MARGIN a b c d` en +0x80, un byte por margen en
  **unidades de 3** y al revés (d en el byte 0: `MARGIN 12 24 15 48` = 0x04080510; un margen que
  no es múltiplo de 3 da los mismos bytes que el de debajo); `USEPRINTMARGINS` = 0x100.
- **Controles de página**, otros tipos que en un formulario: TEXT 7, BOX 8, SEPARATOR 9, VAR
  0x11, GROUP 0x15; clase `SimplePageControl`; +0x44 vale 0x80000000 de serie (0xC0000000 en un
  GROUP). `BORDER ALL` = 0xF0; SEPARATOR: `VERTICAL` 0x1000, `THICKLINE` 0x04; GROUP: `AS LINES`
  0x200, `GRID VERTICAL HORIZONTAL` 0x6000, `REPEAT n` en +0x40; VAR: `DATATYPE` como un EDIT.
  En una TEXT de página no compilan `NOBORDER` ni `DATATYPE`.
- El valor implícito de un control de página es el puntero estático 0x1401A14FC.
- **Pendiente:** los demás tipos de página (CHECK, BOXGROUP, BITMAP, 0x19), BORDER parcial,
  GRID de una sola dirección y lo que la guarda ya señala en `samples` (9 módulos).

## 2026-10-28 — tablas de formulario (batería `tablas.py`, repositorio `stock`)

Batería `lab/bateria/tablas.py` (13 programas; compilan 12, 12/12 con la vuelta byte a byte;
se compila con el proyecto `samples`, que tiene el repositorio).

- **`REPOSITORY x` no se guarda** en el `.omd` (ni en la cabecera ni en ninguna sección). Lo
  lista el `.prj`. Hay que darlo de fuera: `hubble descompila --repositorio x`; sin él, un
  módulo con tablas da `NoSoportado`. La vuelta lo toma del fuente original (contexto de
  compilación, como el `.prj`).
- **`FTA`** (112 bytes, código 0x14), `Table alias is tabla begin … end`: FOR+0x18 → la primera;
  +0x08 siguiente, +0x10 alias, +0x18 la tabla si se llama distinto, +0x20 primera columna
  (`FOB`), +0x28 el control con `TABLE alias` (que apunta a la tabla en su +0x78, el campo de
  la variable), +0x40 → `FRC` (las columnas clave: salen del repositorio y no se escriben),
  +0x50 → `FJO` (todas las claves externas de la tabla, sacadas del repositorio: no se escriben)
  y +0x68 (`depend on`) [sin descifrar], +0x58 la clase de la tabla
  (implícita, `CLA` 0x8300002D, con un puntero de memoria en +0x28), +0x60 el formulario.
- **Columnas**: `FOB` con +0x50 → su `FTA` y +0x48 el orden. Bit 0x01 del byte 1 = columna de la
  tabla (`x as column`); el resto de ese byte lo pone el repositorio (`UPSHIFT`…). +0x30 lleva el
  tipo de la columna (0xFFFF | largo, o la precisión de un Decimal). Sin el bit, una calculada
  (`x as Char (10)`), o con 0xFFFF en +0x30, una de otra tabla (`x as t.c` + `join … lookup`).
  `default` como en los demás `FOB`. `required` en la clave no deja rastro.
- **Controles**: `VARIABLE alias.columna`; con `LIKEVAR`, el tipo, `UPSHIFT` y `ALIGNMENT` los
  copia el compilador del repositorio (no se escriben).
- **`x as tabla.columna` + `join clave lookup "columna"`**: `FOB` sin el bit de columna, con +0x78 →
  su clave en `FJO` (+0x10 nombre de la clave, +0x18 la tabla, +0x20/+0x28 las columnas que unen) y
  +0x80 → la columna buscada en `STR`. **`FJO`** (48 bytes, código 0x15): +0x08 siguiente.
- Un `default` que viene del repositorio (`customers.state` = «CA») queda en el `FOB` igual que uno
  escrito: sale escrito, con los mismos bytes.

## 2026-10-28 — GRID y comandos predefinidos

`samples` (con `--repositorio stock`): 315 de 415, los **315 equivalentes** (188 byte a byte).

- **GRID** (tipo 0x15): `PARENTGRID` = 0x10000 de +0x00 (en todos los del kit), `SCROLL` en
  0x100/0x200 como en las listas, `AUTOSORT` = el bit de `BUTTON` de +0x44, `TABLE x` en +0x78 (→
  `FTA`); sus columnas son los controles hijos. El binario de `SVL` de +0x68 lo calcula el
  compilador (no se escribe) y +0xA8 es un puntero de memoria (la vuelta lo enmascara). Un GRID
  sin `PARENTGRID` (`c_grid` de la batería) sigue en `NoSoportado`.
- **Comandos predefinidos** (batería `lab/bateria/comandos.py`, 32/32): QueryByForm 0xFFEB, Query
  0xFFED, EditQueryLike 0xFFF2, New 0xFFF7, Add 0xFFF8, Next 0xFFFD, First 0xFFFF, Last 0xFFFC,
  AscendingSort 0xFFE0, DescendingSort 0xFFDF, HideColumn 0xFFE2, ShowAllColumns 0xFFE1 (y los
  que ya estaban). `Previous`, `Print`, `Export`, `Find`, `Help`, `Ok`, `Cancel`, `Insert`,
  `Remove`, `Save` no lo son: van a `CMD` como los del usuario.

## 2026-10-28 — Cobertura del lenguaje y módulos de 7.4.2

Hubble se guía por el **lenguaje**, no por las aplicaciones: las aplicaciones son la prueba.

- **Lista del lenguaje**: `cosmakecon.exe` lleva las cadenas de formato con que escribe el fuente
  (`FONT "%s" %d%s%s`, ` PARENTGRID`, ` depend on `…), juntas entre `GRAMMAR %s` y `PROJECT_UNKNOWN`:
  245 palabras. `lab/lenguaje/cobertura.py` dice cuáles escribe Hubble (178) y cuáles faltan (67).
  Es aproximado: una palabra cubierta no asegura todas sus variantes; la prueba de verdad es la vuelta.
- **Prueba con aplicaciones**: `lab/lenguaje/proyectos.py` descompila los proyectos del kit
  (`projects/`: ALMAFAC 1–4, STOCKMDI, NIF…, todos con fuentes) y agrupa los motivos de parada;
  `lab/lenguaje/compila_proyecto.sh` los compila enteros con el 8.6 del laboratorio.
- **Varias versiones del compilador**: los `.omd` de `projects/` se compilaron con 7.4.2 (ruta
  `C:\CosmosVersiones\cosmos742_x64\…` en `STR`). Del mismo fuente, 7.4.2 pone en el estilo de `FON`
  0x10 (MS Sans Serif) o 0x20 (Verdana, Arial, Times…) y 8.6 pone 0; el fuente no lo dice
  (`FONT "Verdana" 10`). [hipótesis] El tipo de fuente de la máquina que compiló (0x10 de mapa de bits,
  0x20 TrueType). Hubble los acepta (uno u otro, no los dos) y no escribe nada.
- **`x as tabla.columna`** (objetos de página): el `.omd` solo guarda el tipo ya resuelto en +0x30
  (Char(25) = 0x19,-1; Smallint/Integer = 0,-1; Decimal(12,2) = 12,2) y **no** la tabla ni la columna
  (ni en `IDE` ni en `STR`); +0x58 es el control de página (`PCT`) que la muestra. Cualquier columna del
  mismo tipo compila igual: escribirlo exige leer el repositorio (`.dbs`). Hecho (ver abajo).

## 2026-10-28 — El repositorio (`.dbs`) y `x as tabla.columna`

- El `REPOSITORY x` de un módulo es la base de datos `x.dbs` (carpeta junto al proyecto: `samples/stock.dbs`,
  `projects/ALMAFAC/almafac.dbs`). Su catálogo es el de Informix: `systables.dat` y `syscolumns.dat`, filas de
  longitud fija, enteros big-endian, cada una acabada en `\n` (las borradas no; en el kit son ceros).
  `syscolumns` (29 bytes: colname char(18), tabid integer, colno, coltype, collength smallint) se describe a
  sí misma; `systables` empieza por tabname char(18), owner char(8), dirpath char(64), tabid integer, y su
  longitud de fila sale de sus columnas (tabid 1). coltype: 0 CHAR, 1 SMALLINT, 2 INTEGER, 5 DECIMAL,
  6 SERIAL, 7 DATE, 8 MONEY; +0x100 = NOT NULL; DECIMAL y MONEY: collength = precisión × 256 + escala.
  Los nombres pueden venir en mayúsculas (`SYSCOLUMNS.DAT`) o cortos de 8 letras (`syscolum.dat`).
  Lector: `src/hubble/repositorio.py`; los 11 catálogos del kit se leen.
- Lo que deja en +0x30 un objeto `x as tabla.columna` (8.6, ALMAFAC, 131 objetos cruzados por nombre):
  CHAR(n) → Char (n, -1); SMALLINT → Smallint (0, -1); INTEGER y SERIAL → Integer (0, -1); DATE → Date
  (0, -1); MONEY(p,s) → Money (p, s). Declarados a mano (más de 4000 en la batería y samples) la escala es
  **0**: el -1 distingue sin dudas. Antes un Char de columna salía como `Char(n)`, que compila con escala 0
  (distinto, y sin aviso); ahora sin catálogo es `NoSoportado`.
- Qué columna se escribe: una cualquiera del mismo tipo compila igual (comprobado: el original
  `empresa AS proveedores.empresa` y `clientes.empresa` dan los mismos bytes). Se prefiere la del mismo
  nombre y, entre ellas, la de una tabla que el módulo nombra en sus textos (las SELECT); así PROVPROV y
  PROVCLI salen como su fuente. Cada elección con más de una candidata va a `avisos` (la CLI los escribe).
- CLI: `hubble descompila --repositorio NOMBRE [--dbs DIR]`; sin `--dbs` busca `NOMBRE.dbs` junto al
  módulo o encima. La vuelta (`vuelta.py`) toma el catálogo de junto a los fuentes originales;
  `vuelta_todo.sh` tiene la entrada `alma` (proyecto entero, con `ALMAFAC.PRJ`, su `.dbs` y los módulos que
  aún no se descompilan como dependencias con su fuente original en los dos lados).
- `Struct as tabla` (cone15: `custom is Struct as customers`) sale con los miembros uno a uno, cada uno
  `x as customers.x`: mismos bytes. `Time` de una columna (coltype sin identificar) sigue en `NoSoportado`.
- Vuelta con el catálogo: samples **316/316** (144 byte a byte; antes 188: la vuelta copia ahora `stock.dbs` a la
  carpeta de trabajo y cambian punteros de memoria, que se enmascaran) · tablas 16/16 · ALMAFAC 3/3.

## 2026-10-28 — Menús: iconos, cabecera y atributos de opción

Todas las palabras de menú del compilador (`"%s" SEPARATOR DISABLED CHECKED ICON %d HELP "%s" COMMAND %s
ICONFILE "%s" DEFAULT ICON %d ALLOWICON ALLOWCHECK PULLDOWN NOLABEL NOWAIT`), una variante por palabra en
`lab/bateria/menus.py` (42 programas, 41 compilan: `POPUP` no es del lenguaje).

- **Raíz** (`MOP` de `MNU`+0x10): byte 0 0x01 `NOWAIT`, 0x02 `ALLOWICON`, 0x04 `ALLOWCHECK`; 0x400 `NOLABEL`.
  `NOLABEL` y `NOWAIT` se escriben en la línea del `PULLDOWN` (`PULLDOWN NOLABEL NOWAIT`): en la cabecera o en
  una opción son error de sintaxis.
- **Cabecera** (raíz y submenú, entre `menu x` y el `PULLDOWN`, o detrás de los atributos de un `MENU`):
  +0x50 `ICONFILE "x"` (índice en `ICO` en los 16 bits altos; 0xFFFF0000 = ninguno); +0x54 `DEFAULT ICON n`
  en los 16 bajos (0xFFFF = ninguno; los altos 0 en la raíz y 0xFFFF en un submenú); `ALLOWICON` 0x02 y
  `ALLOWCHECK` 0x04 del byte 0. Orden: `ICONFILE`, `DEFAULT ICON`, `ALLOWICON`, `ALLOWCHECK`.
- **Opción**: byte 1 0x01 `CHECKED`, 0x02 `SEPARATOR`, 0x20 `DISABLED`, 0x40 submenú; `ICON n` = 16 bits altos
  de +0x30, guarda n − 1 (los bajos, `COMMAND`); `HELP "x"` = +0x20 → `STR`. Orden del compilador: texto,
  `SEPARATOR`, `DISABLED`, `CHECKED`, `ICON`, `HELP`, `COMMAND` y, en un submenú, su cabecera.
- `SEPARATOR` marca la opción donde se escribe; escrito suelto detrás de ella da la misma marca, pero detrás de
  la última opción no compila (lo cazó la vuelta): Hubble lo escribe dentro.
- **32 bits** (par `ALMAFAC/inicio.omd` de 8.2): `MNU` 0x00/0x08/0x10/0x18 → 0x00/0x04/0x08/0x0C; `MOP`
  0x00 0x08 0x10 0x18 0x20 0x28 0x2C 0x30 0x40 0x50 0x54 → 0x00 0x04 0x08 0x0C 0x10 0x14 0x18 0x1C 0x28 0x30
  0x34. Expansión **estricta** en las dos: un u32 de 32 bits sin pareja y distinto de 0 da `NoSoportado`.

## 2026-10-28 — Bits de FCT por tipo de control (batería `fct.py`)

70 programas, 57 compilan (los que no: `TICKS n`, `FRAMEAUTOSIZE`, `POINT` en PERCENT, `BORDER HILIGHT` sin
`BUTTON` delante, y las parejas que se excluyen). Vuelta 57/57 byte a byte.

| bit de +0x00 | TEXT | PERCENT | SLIDER | BITMAP | control MENU |
|---|---|---|---|---|---|
| 0x100 | `ETCHEDIN` | | `POINT BOTTOMRIGHT` | (`STRETCH`) | sin `CENTER` (con ICON) |
| 0x200 | `ETCHEDOUT` | | (`POINT TOPLEFT`) | `PALIND` | `VERTICAL` del icono |
| 0x400 | | `TICKMARKS` | (`TICKMARKS`) | `GRAYSCALE` | |
| 0x1000 | (`MULTILINE`) | `VERTICAL` | `VERTICAL` | | `VERTICAL` |
| 0x2000 | | | | (`AUTOFIT`) | `ICON` (sin número ni fichero; +0x70 a 0) |

- Juntos no compilan: `ETCHEDIN`+`ETCHEDOUT`, `PALIND`+`GRAYSCALE`, `POINT TOPLEFT BOTTOMRIGHT`. Hubble da
  `NoSoportado` si los encuentra a la vez.
- **PERCENT** `RANGE a b`: +0x68, como el SLIDER.
- **Control MENU** +0x40: número de opciones de la raíz del menú (un submenú cuenta una); lo calcula el
  compilador y se comprueba.
- `BORDER HILIGHT|BLACK` (u16 alto de +0x20: 0x0C, 0x10) también en **MENU** y **SPIN**, detrás de `BUTTON`, que
  solo no deja huella. Admite además un `BORDER` normal. En BUTTON va delante del icono; en MENU detrás; en SPIN,
  al final.
- **TEXT** lleva `DATATYPE` como EDIT (+0x20 alto, +0x40 bajo el largo). `DATATYPE CHAR` a secas = sin DATATYPE.
  Con `VARIABLE tabla.col`, `LIKEVAR` va delante de `TAGS`.

## 2026-10-28 — Argumentos por defecto y declaraciones de varios nombres (batería `llamadas.py`)

- **`default null`** de un OBJ: bit 0x20 del byte 0, con +0x28 y +0x2C a 0 (un `default 0` lleva +0x2C = 1).
- **Argumento que pone el compilador**: además de crearse después de la llamada, puede ir antes de ella si la
  llamada entera se crea tarde (`if o.Run then`: para convertir el resultado). La referencia es la raíz de la
  expresión de la sentencia, que es lo último que se crea de lo escrito: un literal posterior no se escribió.
- **`x y z as Decimal default 0`**: los nombres de una línea comparten el registro DEC del default; una línea
  por nombre crea uno cada una. Hubble junta los OBJ seguidos que apuntan al mismo DEC. Los enteros no tienen
  DEC: una línea por nombre da los mismos bytes.
- Dan los mismos bytes (vuelta): `!=` / `<>`, `public f` / `public f()`, `Ok(…)` / `Module.Ok(…)`.

## 2026-10-28 — Controles de página: bordes, BOX, GROUP, BANDGROUP, VAR (batería `paginas.py` ampliada)

109 programas, 103 compilan. No compilan: `NOBORDER` y `DATATYPE` en un TEXT de página, una sombra con `DOUBLE`,
`UPSHIFT` en un VAR, `DATE(n)` y `PAGE` en un hijo de GROUP AS LINES.

- **Borde de página** (byte bajo de +0x00; TEXT, BOX, GROUP, BANDGROUP):
  `BORDER [UPSHADOW|DOWNSHADOW] [DOUBLE] [ALL | TOP BOTTOM LEFT RIGHT]`.
  - `UPSHADOW` 0x01, `DOWNSHADOW` 0x02, `DOUBLE` 0x04.
  - `LEFT` 0x10, `RIGHT` 0x20, `TOP` 0x40, `BOTTOM` 0x80; `ALL` = 0xF0.
- **SEPARATOR:** `THICKLINE` 0x04, `DOUBLELINE` 0x100, `SOLID` 0x200, `VERTICAL` 0x1000.
- **TEXT:** `MULTILINE` 0x1000.
- **Controles de página en general:**
  - `PAGE n` en +0x60 (n − 1).
  - +0x08 es el hermano siguiente: antes ningún control tenía más de un hijo.
- **BOX:** `NOLABEL` 0x800. `ICON n FILE "x" [CENTER] [VERTICAL]` va como en un formulario (+0x70; 0x2000, 0x100, 0x200).
  El `BEGIN END` vacío no deja huella.
- **GROUP:**
  - `AS LINES` 0x200 o `BYCOLS` 0x400; con ninguno de los dos queda `REPEAT n` a secas.
  - `GRID VERTICAL` 0x4000, `GRID HORIZONTAL` 0x2000.
- **BANDGROUP** (tipo 0x19): contenedor con `AUTOSIZE` 0x8000. La posición de sus hijos la recalcula el compilador,
  como en GROUP: con borde, el hijo pierde 2 de ancho.
- **VAR:**
  - `LIKEVAR` 0x4000 copia de la variable el tipo (+0x20, +0x40), la alineación y, si es una columna en
    mayúsculas, `UPSHIFT` (0x40000); nada de eso se escribe.
  - `NOLABEL` va delante de `LABEL`.
- **`DATATYPE`** (EDIT, TEXT, VAR): `SMALLINT(n)` e `INTEGER(n)` llevan el ancho en +0x40, como `CHAR(n)`.
- `BACKGROUND COLOR default` no deja huella.

## 2026-10-28 — Variables y tablas de formulario (batería `variables.py`, repositorio `stock`)

52 programas. No compilan:
- `enumerated` con 2 valores (hacen falta más de 2), o en una columna;
- `boolean values` en una columna;
- `order by` sin paréntesis;
- fechas en `dd/mm`;
- `default NOW` en una fecha;
- `references`/`joining` en la cabecera de la tabla y el `lookup … references … joining` del manual, que no
  compila en un formulario de 8.6.

**Variable de formulario (FOB):**
- +0x60 es el número de valores y +0x68 apunta a la cadena `"a|b|…"` en STR.
- Con 2 valores se escribe `boolean values "a|b"`; con más, `enumerated n values "…"`.

**Columna (FOB +0x00):**
- `required` 0x400, `noentry` 0x800, `noupdate` 0x1000, en ese orden y detrás del default.
- El compilador pone `required` también en una columna `NOT NULL` del repositorio (coltype 0x100). Hubble lo omite
  solo si el catálogo lo demuestra; sin catálogo lo escribe, y da los mismos bytes.
- Una columna sin el 0x10 del byte 3 la añade el compilador (la clave de enlace) y no se escribe.

**Default** (OBJ, FOB o columna), de la clase de +0x18:
- número en +0x28 (SMALLINT en 16 bits);
- DECIMAL y MONEY → registro DEC;
- fecha: días desde el 31/12/1899 (`01/01/1900` = 1) y +0x2C = 1, escrita `"mm/dd/aaaa"`;
- `TODAY`: bit 0x40 del byte 2; en +0x28 queda memoria sin limpiar.
- `default null` en una columna da los mismos bytes que no poner default.

**Tabla (FTA):**
- `Vartable` es el 0x08 de +0x00; con 0x04 además, va sin `is tabla`.
- `order by (a, b)`: +0x48 apunta a la cadena `"a|b"`.
- `depend on tabla join clave` y el +0x68: ver la sección siguiente.
- `default null` de una columna: no lleva el bit de default, pero +0x28 ≠ 0 (lo que deja el compilador; sin
  default, 0). Se distingue y se escribe.
- `VAR x as Simple`: el `VAR` se escribe, como en los tipos básicos (sin él, el compilador no pone el 0x40).

**Orden en los controles de página** (lo cazó la vuelta de ALMAFAC; cualquier otro orden no compila):
`NOLABEL`, `ATTACH`, `PAGE` y `LABEL`.

**Guarda: `LIKEVAR` con máscara.** `LIKEVAR` copia de la variable su tipo y, si es una columna, la máscara del
repositorio (en el u16 alto de +0x20). Una variable MONEY o DECIMAL de columna se lee como el tipo a secas (el
`.omd` no la nombra). Si el control trae una máscara y la variable no sale escrita `as tabla.columna`, la
columna se ha perdido y da `NoSoportado`. Caso de ALMAFAC LPROART: `pr_cost as articulos.pr_cost`.
(2026-10-31: resuelto con la máscara del `.crf`; ver la sección de ese día.)

**Referencia que la vuelta da por distinta:** samples `groupby`. Al compilar el original, el compilador mete
memoria sin limpiar en la cadena que forma juntando literales seguidos (`"…" "…"`). El descompilado es el correcto.

## 2026-10-28 — `depend on` y la casilla de una tabla (batería `variables.py`, cuarta tanda)

**FTA +0x68: la casilla de la tabla.** El compilador numera en FOB +0x48 los objetos del formulario y las columnas,
y reserva una casilla para cada tabla justo antes de sus columnas. +0x68 es esa casilla: la de la primera columna
(FTA +0x20 → FOB, su +0x48) menos uno. La primera tabla de un formulario sin objetos tiene la 0; por eso solo se
veía en la segunda (3, detrás de dos columnas y la casilla 0) o en un formulario con variables (AGENDA `mes`: 4,
detrás de cuatro variables). No se escribe; si no cuadra, `NoSoportado`.

**`depend on padre join clave`** (en la hija, delante de `order by`; detrás no compila):
- +0x30 → la FTA del padre, que va antes en el formulario.
- +0x38 → las FRC de la unión: el nombre de cada columna de la clave en el padre y su FOB (una columna del padre).
- +0x40 (la clave primaria de la hija, FRC) pasa a usar el FOB del padre para las columnas que hereda, y la
  columna que el compilador añade para unir (FOB sin el 0x10 del byte 3) ya no aparece.
- El nombre de la clave no se guarda en la FTA: es la única FJO de la hija (cadena desde +0x50) cuya tabla
  (+0x18) es la del padre. Sus columnas (cadena de +0x28, `"a|b"`) tienen que ser las de las FRC de +0x38.
- Guardas: padre que no va antes, FRC con un FOB fuera del padre, ninguna o varias FJO que lo expliquen, y padre
  con alias (`Table cab is orders`: no se ha visto compilar; con la hija con alias, el compilador dice «Unknown
  depend join fk2_lines for table lin»).

Vuelta: variables 49/49 (los 7 programas nuevos: tres tablas encadenadas, padre `customers`, la hija con su
columna de unión escrita, más columnas, variables delante; 5 compilan). Los 12 módulos de proyectos que se
paraban aquí pasan la tabla y se paran más adelante: 7 en un procedimiento de tipo 6 en PRO, 3 en la raíz de menú
0x89084002, uno en el control 0xC y otro en el 0xE.

## 2026-10-28 — La tabla del formulario en el código (batería `codtablas.py`, repositorio `stock`)

- **`tabla.Metodo(…)`** (`proveedores.DisableCommand("QueryProvincias", disable)` en ALMAFAC): la tabla es un nodo
  de REF con los bytes 0 y 1 a 0x30 y +0x10 → su FTA; +0x18 es un puntero de memoria (la vuelta lo pone a cero,
  como los de variable y método: sin eso, samples `exit` y `ejexportxxx` salían distintos). Se escribe con el alias.
- **Valores de columna del repositorio.** El `.crf` junto al `.dbs` (cabecera `CRMMAGIC`) guarda los valores de
  las columnas (ALMAFAC: `sexo` «V|M», `ecivil` «S|C|V|D»), y el compilador los copia al FOB (+0x60/+0x68). No se
  escriben; en 7.4.2, `boolean values` en una columna ni siquiera compila («Expecting identifier»). [hipótesis] Del
  `.crf` solo se lee cada cadena tras 00 10 00 80; la vuelta de ALMAFAC (12/12) lo da por bueno.
- **`tabla.columna`** en el código: PROPIEDAD con ese nodo de tabla en +0x10 y, en +0x18, la variable (0x10, byte 1
  = 0x20) con el FOB de la columna. El nombre del FOB ya lleva la tabla, así que no se repite. Una columna de otra
  tabla da `NoSoportado`.
- La columna a secas (`x = order_nbr`) no compila: «Unknown identifier order_nbr in scope».
- **Argumentos delante de los variables.** Con una lista de argumentos variables escrita (0xD0 con elementos), los
  argumentos de delante también se escribieron: no se puede saltar uno y dar los variables. ALMAFAC `provee`
  (`Sql.SelectWindow(…, 1, proveedores.provincia)`) perdía el 1, que tenía bytes de literal copiado.
- **Los bytes no distinguen un literal escrito de uno copiado.** Probado en todo el corpus: los 22 literales que se
  quitan solo por sus bytes (resto `14 00…`, delante de la llamada) son ESCRITOS (`Exit(1)` de ALMAFAC `comun`,
  `ErrorLevel(0)` de demorestcosmos, `SetListAllRowsHeight(30)`). Al menos en ALMAFAC `comun`, recompilado sin él
  da los mismos bytes: por eso la vuelta no lo ve. Y tomar el relleno 0xCC por «escrito» rompe samples `exit` y `ejexportxxx`, donde sí era
  copiado. Queda pendiente: saberlo por la declaración (el valor por defecto del parámetro), no por los bytes.

## 2026-10-29 — Eventos de tabla (PRO de tipo 6, batería `evtablas.py`)

`On Evento Table x` es un PRO de tipo 6: +0x00 = 0x05000506, +0x18 → la clase, +0x20 → la FTA y +0x28 el evento.
Con +0x20 = 0 es el de cualquier tabla, que lleva el nombre como parámetro: `On Edit Table (tab as Char)`.

| Código | Evento | Código | Evento | Código | Evento |
|---|---|---|---|---|---|
| 13 | Fetch | 18 | RowChanged | 22 | QueryBegin |
| 15 | Add | 19 | Edit | 23 | QueryEnd |
| 16 | Update | 20 | AcceptEdit | 35 | ReFetch |
| 17 | Delete | 21 | CancelEdit | 41 | ChangingRow |

- Los nombres salen de la lista de eventos de cosmakecon (de Fetch a Locked). Error, BeginGroup, EndGroup, Eof y
  Locked no compilan como evento de tabla («Unknown table event»). El 14 no sale con ningún nombre de la lista.
- El nombre del evento distingue mayúsculas (`on fetch table` no compila); `table`, no.
- Sin tabla hace falta el parámetro (`On Edit Table` a secas no compila). Con tabla y parámetro no se ha visto:
  `NoSoportado`.

Proyectos del kit: 55 → 68 de 121 (ALMAFAC `albaran`, `triple`, `clientes`…, STOCKMDI `triple`).

## 2026-10-29 — BUTTONGROUP (0x0C) y BOXGROUP (0x0E) (batería `grupos.py`)

Como el TAB: las etiquetas de los elementos, unidas con `|`, en el texto de SVL de +0x48 (el bit LABEL; un
`LABEL` propio no compila); `NUMBER n` en +0x40, y un binario de SVL en +0x68:

| Desplazamiento | Qué |
|---|---|
| +0x00 u16 | tamaño: 14 + 4·n (BUTTONGROUP) o 16 + 8·n (BOXGROUP) |
| +0x02 u16 | índice en ICO de su `ICON FILE` (0xFFFF sin él); el mismo va en FCT +0x70 |
| +0x04 | ancho y alto del control (los de POSITION) |
| +0x08 | ancho y alto de un elemento (los calcula el compilador) |
| +0x0C u16 | m de `ROWS m` / `COLUMNS m` (BOXGROUP: y un u16 a 0) |
| por elemento | u16 icono n − 1 (0xFFFE sin él), u16 a 0; en BOXGROUP, u32 BACKGROUND (0x80000000 sin él) |

Bits de +0x00: `CLICKTYPE RADIO` 0x80000, `MANUAL` 0x40000 (CHECK es el de serie: no deja huella), `COLUMNS` 0x1000
(sin él, ROWS), `ICON` 0x2000, sin `CENTER` 0x100 (también puesto sin icono), `VERTICAL` 0x200. `BORDER HILIGHT`:
u16 alto de +0x20 = 0x0C, como en un BUTTON (en un BOXGROUP no compila; tampoco `BORDER ALL`). `ALLOWDRAG` en un
BOXGROUP: 0x300 de +0x44, como en una lista.

Orden: `ICON FILE` tras los bordes; `CLICKTYPE`, `NUMBER`, `BORDER HILIGHT` y los elementos, los últimos (VARIABLE o
AUTOSIZE detrás de NUMBER no compilan: samples SELEC). Líneas por elemento: `BUTTON LABEL "x" ICON n`, `BUTTON LABEL ""` (un botón sin nada), `BOX`, `BOX LABEL "x" ICON n`,
`BOX LABEL "x" BACKGROUND RGB r g b`. Icono y color juntos en una caja no se ha visto: `NoSoportado`.

**Sin descifrar:** el u16 alto de +0x20 = 0x40 de ALMAFAC3/almafac4 `inicio` (`c_query`: ICON FILE sin CENTER,
CLICKTYPE MANUAL, BACKGROUND transparente, BOLD, PAGE 3) y ActiveX `demo`; ninguna de las combinaciones de la batería
lo reproduce (y ALMAFAC compila con 7.4.2). Da `NoSoportado`.

De paso: en un GRID, `AUTOSIZE` va delante de `PARENTGRID` (detrás no compila; lo cazó la vuelta de samples
`loadCustomFonts` en cuanto sus grupos se descompilaron).

## 2026-10-29 — Comentarios de documentación en módulos con clases (batería `comentarios.py`)

El sitio de un `{* … *}` no se guarda: ni PRO ni CLA lo apuntan, y solo queda su orden entre las cadenas de STR
(comprobado comparando variantes con y sin comentario: cambian STR y los punteros de memoria, nada más).
- Va tras el último procedimiento con una cadena antes que él; el de antes del primero, al principio de la sección
  (CODE CLASS o CODE) de ese primer procedimiento.
- Si entre ese y el primero con una cadena detrás hay procedimientos sin cadenas, o una frontera de sección, cabe en
  varios sitios con los mismos bytes. Va en el primero posible y `descompilar` lo dice en `avisos` (antes, en un módulo
  con clases, daba `NoSoportado`).
- `@global` (7.4.2 y 8.6): el compilador lo quita corriendo el resto del texto, pero deja detrás del 0 la cola del
  texto viejo (6 bytes: los 7 de `@global` menos el 0). Es lo único que deja restos en todo el corpus (17 comentarios,
  siempre 7). Con esa cola vuelve a su sitio: al principio o tras un espacio, con espacio, salto o final detrás, y
  que dé la misma cola. Lejos del final caben varios con los mismos bytes: va tras « * » (o tras «{* »), la forma de
  casi todos, y se avisa. 13 de los 16 del kit salen exactos; los 3 de CalcALG (`{*@global`) quedan en ` * @global`.
  Sin restaurarlo, los bytes no salen iguales (lo cazó la vuelta de la batería).

Los 8 módulos de STOCKMDI y almafac4 que se paraban aquí salen; solo `invoice` lleva avisos (sus procedimientos no
tienen cadenas). Proyectos del kit: 70 → 78 de 121.

## 2026-10-29 — Menú sin PULLDOWN y con título (batería `menus.py`, quinta tanda)

La raíz (MOP) de un menú: 0x89084000 más `PULLDOWN` 0x40, `NOLABEL` 0x400 y `NOWAIT` 0x01, cada uno opcional, que van
en la línea del tipo; sin ninguno no hay línea (`menu x` `ICONFILE …` `ALLOWICON` `BEGIN … END`: STOCKMDI frmtmpl,
ALMAFAC3 y almafac4 albaran). `NOLABEL` sin `PULLDOWN` compila. 0x02 ALLOWICON y 0x04 ALLOWCHECK, como siempre.
- **Título:** `menu x "Open"` (TryThisOneFirst Menu_examples): +0x18 de la raíz → STR, como el texto de una opción.
  Va el primero de la cabecera (detrás de ICONFILE no compila).
- `POPUP` no compila en un menú de formulario (8.6).

Proyectos del kit: 78 → 81 de 121; ya no queda ningún motivo de menú.

## 2026-10-29 — `On Command (cmd as Char)` (batería `comandos.py`, segunda tanda)

PRO de tipo 7 con +0x28 = 0: el de cualquier comando, que recibe su nombre como parámetro (ALMAFAC auxiliar, STOCKMDI
assistant), como el evento de cualquier tabla o de cualquier control. `On Command` a secas no compila («Expecting '(',
identifier, table»); sin parámetro, `NoSoportado`. Proyectos del kit: 81 → 86 de 121.

De paso: en un GRID, `AUTOSIZE` va tras los bordes y delante de `SCROLL`, `TABLE` y `PARENTGRID` (no solo delante de
PARENTGRID; lo cazó la vuelta de ALMAFAC `auxiliar`, que se descompila desde ahora).

Y `main` con parámetros (samples Auxiliar: `main(doRun as boolean default TRUE)`): se escriben entre paréntesis.
Sus OBJ llevan siempre el 0x40 de VAR; escrito o no, los mismos bytes (batería `llamadas.py`): no se escribe.

## 2026-10-29 — `case in (a, b):` (batería `genera.py`, al final)

En un `switch` de valor, `case in (a, b):` es la condición `valor in (a, b)`: el acceso lleva el operador 27 y un solo
argumento, la lista (nodo 0xD0, sus elementos por +0x08), igual que `x in (…)` en una expresión. Con un solo elemento
(`case in (1):`) también lleva la lista. Si el argumento no es una lista, `NoSoportado`. Batería: 5 programas
(enteros, uno solo, cadenas, expresiones y con `default`), los 5 exactos. Los 5 módulos que se paraban aquí (ALMAFAC
`albaran` en sus cuatro copias, STOCKMDI `orders`) se paran ahora en el nombre de una propiedad de REF.

## 2026-10-29 — El valor implícito en los `.omd` del kit, y punteros que chocan

**Valor implícito en otra dirección.** En los `.omd` que trae el kit (proyectos), la propiedad implícita de un
control (`barra = "x"`, `ctrNif = null`) no va en 0x1401A1358 sino en **0x14019D1F8**. Va en un VARIABLE con el byte 1
a 0x20 y +0x10 → EOB, como en lo que compilamos aquí. 15 usos en 8 proyectos, todos donde el fuente asigna a un control
sin propiedad. Lo que compilamos con 8.6 pone 0x1401A1358 en los mismos sitios: ALMAFAC 3 y 3, NIF 2 y 2. [hipótesis:
los `.omd` del kit salieron de otra compilación de cosmakecon, con la memoria estática en otro sitio]. Proyectos del
kit: 86 → 91 de 121.

En los `.omd` de 32 bits del kit, el mismo valor implícito va en 0x4AF250 (NIF `sample01`) y en 0x4AF258
(ActiveX `Word`): una dirección por módulo y un solo uso de cada una. Sin descifrar: `NoSoportado`. (resuelto el 2026-10-29: «32 bits con el compilador del laboratorio»)

**Punteros que caen en la misma posición.** `_punteros` agrupa los punteros cercanos (≤ 1300 bytes) y busca para cada
grupo la única base que los lleva a posiciones libres de IDE y cuadra con las anclas. En un grupo pequeño eso puede
cuadrar por casualidad. En ActiveX `Word`, 0x14E470 y 0x14E500 (2 punteros, 1 ancla, 55 bases posibles sin anclas)
caían en «document» y «saveFileName», justo donde caen dos punteros del grupo de 32. Así, `txtTemplate.Text` salía
`txtTemplate.document`. Cada aparición en IDE es de un solo puntero, así que cuando dos grupos caen en la misma
posición se descarta el más pequeño (los dos si son iguales) y sus nombres dan `NoSoportado`. En el kit y samples,
el choque sale solo en Word y `LPROART` (que no se descompila por otro motivo).

Descartado: exigir que la posición en IDE crezca con el orden de los REF (321 de 520 módulos tienen inversiones,
los procedimientos no van en orden) y no resolver los grupos pequeños ambiguos (ALMAFAC `auxiliar` e INDODIC
`Search1` los tienen y sus nombres coinciden con el fuente).

## 2026-10-29 — Borde de los elementos de un grupo (batería `grupos.py`, cuarta tanda)

Tras `NUMBER`, un BUTTONGROUP admite el borde de sus botones en el u16 alto de +0x20: 0x0C `BORDER HILIGHT`, 0x10
`BORDER BLACK`, 0x40 `NOBORDER` (ALMAFAC3/almafac4 `inicio`, ActiveX `demo`). Cualquier otro BORDER ahí no compila
(«Expecting black, hilight»: DOUBLE, ETCHED, DOWN, FRAME, DOUBLE DOWN, ni HILIGHT BLACK). En un BOXGROUP solo compila
`NOBORDER` (0x40); `BORDER HILIGHT` tampoco. Lo demás da `NoSoportado`. El `NOBORDER` del propio control (bit 0x40
de +0x00) va delante, con los atributos; el de los elementos, detrás de NUMBER. Batería: 10 programas más al final
(4 compilan, los 4 equivalentes). Proyectos del kit: 91 → 94 de 121.

De paso, `CURSOR` en un grupo va detrás de los colores, `BOLD` y `FONT`. Delante de cualquiera de ellos no compila
(«Expecting number»), y en los demás controles sí (no: tampoco, ver el 2026-11-02). Lo cazó samples `URLText` (`FOREGROUND COLOR blue` / `CURSOR` en un
BOXGROUP), que se descompila desde aquí. Batería: 12 programas (los dos órdenes con FOREGROUND, BACKGROUND y BOLD en
los dos grupos); compilan los 6 con CURSOR detrás.

Y la vuelta ya no da por bueno un módulo cuyo descompilado no compila: si su original compila, cuenta como
`DISTINTO … el descompilado no compila`. Antes, URLText salía «0 distintos», porque solo se comparaban los que
compilaban en los dos lados.

## 2026-10-29 — `BORDER BLACK` (bit 0x10 de +0x00, batería `controles.py`, segunda tanda)

En BOX, BITMAP y TEXT, `BORDER BLACK` es el bit 0x10 de +0x00 y va el primero: `BORDER BLACK DOWN` (STOCKMDI `menu`,
TryThisOneFirst `Menu_examples`), `BORDER BLACK` (CalcRPN `calcu3`, un BITMAP). Compila solo, con `DOWN`, con `FRAME` y
con `EXTRA 1`. No compila detrás (`BORDER DOWN BLACK`), con DOUBLE ni con ETCHED, ni en un EDIT. En un BUTTON va en
el u16 alto de +0x20 (`BORDES_BOTON`, ya descifrado). Para lo demás, `NoSoportado`. Batería: 15 programas al final
(8 compilan, los 8 exactos). Proyectos del kit: 94 → 97 de 121.

STOCKMDI `menu`, que se descompila desde aquí en 64 bits, en 32 bits no resuelve ningún puntero (0 de 117). Allí los
saltos entre punteros (28, 16, 12, 12…) no son los de las posiciones de IDE (en 64 bits, 32, 16, 16, 16…). [hipótesis:
otra granularidad de la memoria del compilador de 32 bits]. Pendiente; el test de 32 frente a 64 bits lo deja aparte. (resuelto el 2026-10-29: «32 bits con el compilador del laboratorio»)

## 2026-10-29 — Atributos de lista en DROPLIST y DROPEDIT (batería `listas.py`, segunda tanda)

Los desplegables guardan sus atributos de lista igual que una LIST:

| Atributo | Dónde va |
|---|---|
| `LISTTYPE LISTCOLS n` | bit 0x01 de +0xA8, y n en el u16 bajo de +0xB0 (con `COLUMNS n` detrás, los mismos bytes) |
| `CURSORTYPE SQL`, `FILE`, `TREEVIEW` | u16 alto de +0xB0: 2, 1 y 5 (4 = ninguno) |
| `SELECTTYPE MULTIPLE` | +0xA8 = 0x30; `SIMPLE` (0x10) es el de serie |
| `SORTONCLICK` | 0x400 de +0xA8 |
| `SCROLL VERTICAL` / `HORIZONTAL` | 0x200 y 0x100 de +0x00 |

Se escriben en el orden de los fuentes del kit: SHOW, LISTTYPE o COLUMNS, CURSORTYPE, SELECTTYPE y SCROLL.
`CURSORTYPE FILE` con TAGS da `NoSoportado`, porque no se sabe si TAGS es el fichero o la lista, y también sin
SIMPLE. Batería: 28 programas al final; compilan todos, 22 exactos y 6 equivalentes. Proyectos del kit: 97 → 100 de
121 (STOCKMDI `customers`, `items`, `suppliers`). prjbmapsdll `EjBmapsdll` se para ahora en el nombre de una propiedad.

## 2026-10-29 — Grupos de punteros que juntan dos bloques, y los literales escritos del kit

**Grupos partidos.** En prjbmapsdll `EjBmapsdll` (y AGENDA `mes`, OutlookActiveX), un grupo de punteros cercanos (≤ 1300
bytes) junta dos bloques de memoria distintos: ninguna base vale para todos (en uno de 86, la mejor lleva 61). El grupo
se parte en tramos, cada uno tan largo como le quepa alguna base. Si algún tramo queda con más de una base, el grupo
entero no vale; si no, se quedaría con nombres de punteros sueltos de la zona baja (0x14E500 en ALMAFAC `eticli`), que
es la del falso `document` de Word. En todo el corpus: 1127 punteros más resueltos, ninguno de antes cambia.

**Literales escritos en los `.omd` del kit.** Un smallint escrito como argumento lleva tras su valor 0x11 y ceros al
compilarlo aquí. En los `.omd` del kit lleva **0x14 y ceros** o **dos ceros y el relleno 0xCC**. La regla de
`por_defecto` lo tomaba por basura y lo quitaba en silencio: `UpDownZoom(1)` salía `UpDownZoom`. Se vio comparando el
texto del `.omd` del kit con el del mismo fuente compilado aquí (cuya vuelta sale byte a byte): 13 de 29 módulos
emparejados (ALMAFAC, NIF, prjbmapsdll) eran distintos. Con los dos patrones quedan 3, y solo cambian el tamaño de
controles con AUTOSIZE, que el compilador calcula con las fuentes. Lo compilado aquí no da esos patrones en ningún
argumento (miles de casos). [hipótesis: el kit se compiló con otra build, quizá de depuración, como apuntan el relleno
0xCC y las otras direcciones estáticas]. En un integer no se ha visto: si sale, se tratará igual que ahora.

**En 32 bits no se puede decidir.** En los `.omd` de 32 bits del kit, un smallint escrito y uno por defecto llevan lo
mismo tras su valor, `CC CC` y ceros. Frente a los de 64 bits con el mismo fuente: 327 escritos y 24 por defecto, y
ninguno se decide por su posición. Antes se quitaban los dos y el texto salía mal en silencio (el test de 32 frente a
64 bits pasaba porque 64 bits también los quitaba). Ahora da `NoSoportado` («no se sabe si se escribió»): 15 módulos
por versión, y el test lo exige. (resuelto el 2026-10-29: «32 bits con el compilador del laboratorio»)

Y la vuelta tiene una entrada nueva, `bmaps` (prjbmapsdll entero, 3 módulos), y un test que exige que kit y compilado
aquí den el mismo texto.

## 2026-10-29 — La tabla del formulario como argumento (batería `codtablas.py`, segunda tanda)

El nodo de una tabla usada en el código (0x30 0x30, +0x10 → FTA) lleva 0x05 en el byte 2 cuando es un argumento
(`EditingTable.IsMe(orders)`; ALMAFAC2 `albaran`: `DisableCommand(cmd, not EditingTable.IsMe(albaranes))`), como
cualquier argumento (una variable pasada a una llamada también lleva 0x05). Como objeto (`orders.IsMe(…)`), 0. Otro
valor, `NoSoportado`. Batería: 4 programas al final, los 4 exactos. Proyectos del kit: 101 → 102 de 121.

## 2026-10-29 — DATATYPE TIME y DATETIME (batería `datos.py`, segunda tanda)

En el u16 alto de +0x20, el tipo de dato 4 es `TIME` y el 6 es `DATETIME`; con `MASK n` en el nibble alto, como los
demás (AGENDA `mes`: `TIME MASK 3` = 0x34; OutlookActiveX: `TIME` = 0x4). En un control, el compilador solo admite
char, date, datetime, decimal, integer, smallint y time: MONEY, BOOLEAN y FLOAT no compilan, ni tampoco `TIME(8)`.
El 7 y siguientes dan `NoSoportado`. Batería: 10 programas al final (6 compilan, los 6 exactos; también en DROPEDIT y
TEXT). Los dos módulos del kit se paran ahora en otra cosa: el nombre de un método de REF y un control de tipo 0x16.

## 2026-10-29 — 32 bits con el compilador del laboratorio (vuelta completa en 32 bits)

Xabier dio permiso para el Wine de 32 bits: `hubble-lab:32a` (Debian trixie + `wine32:i386`, prefijo `win32`, la
misma activación) compila con el `cosmakecon.exe` del kit 8.6 x86 (`lab/README.md`, «32 bits»). El `.prj` depende de
la arquitectura (cabecera «01.64.02» / «01.00.02»): el de 64 no lo abre el compilador de 32. Con él, la vuelta
completa en 32 bits (`ARQ=32 vuelta_todo.sh`): los mismos fuentes compilados en 32 bits, descompilados y recompilados.

- **Mapas de 32 bits** que faltaban, deducidos con los mismos fuentes compilados aquí en las dos arquitecturas (1339
  pares): `FTA`, `FJO`, `FRC` y `PAG`, la mitad exacta (sus referencias a IDE/STR cambian de valor, porque IDE y STR se
  alinean distinto, y no casan por valor); `PCT`, como `FCT`; `ECT` y `EFT`, {0: 0}. En `FOB`, +0x68 → +0x38 (la cadena
  de los valores) y +0x80 → +0x44 (la columna de un lookup), emparejadas por el texto al que apuntan (51/51 y 77/77).
- **Valor implícito en 32 bits** (`VALORES_IMPLICITOS_32`): 0x4EAD6C con 8.6 x86 (53 de 53 casos donde el mismo fuente
  en 64 lleva uno de los tres de 64, también el de página), y 0x4AF250, 0x4AF258 y 0x4AF484 en los `.omd` x86 del kit
  (compilados con 7.2.3: `\\winprod-pc\masterCosmos\cosmos7.2.3\cdrom32\…`; 20 por versión).
- **El smallint ambiguo se decide.** En 32 bits, escrito y por defecto llevan lo mismo tras su valor (`CC CC` y
  ceros). Los que la posición no decide (delante de la llamada) llevan, escritos, la variante normal (0xF0 en el byte
  1): 123 de 123, en el kit y en lo compilado aquí, frente al mismo fuente en 64. Un por defecto delante de la llamada
  solo sale con la variante 0x60 (12 en 64 bits, todos en PivotDevExtreme, que no se sabe leer). Con otra variante,
  `NoSoportado`.
- **El default de columna copiado del repositorio**, en 32 bits, deja memoria sin limpiar tras un smallint (50 00 aquí,
  4C 00 en el kit: 16 y 16 columnas, ninguna con default en el fuente); el escrito, el relleno `CC CC` (triple de
  ALMAFAC compilado con `default` 0, 1, 2 y 7). El copiado no se escribe; con ceros, `NoSoportado`. En 64 bits los dos
  llevan lo mismo y se escribe siempre (compila igual). Lo cazó la vuelta: el descompilado escribía `default 1`.
- **Punteros dudosos entre dos tramos.** El tramo de `_punteros` crece mientras le vale su base y se comía los primeros
  del siguiente: EjBmapsdll del kit x86 (`staticitem1` salía `BMapsLockZoom`), RichText y ChartBarrasyLineas en 32
  bits, y otros dos de samples, todos con otro nombre que el del mismo fuente en 64. Entre dos bloques de memoria hay
  un solo corte: los últimos del tramo que valen también con la base del siguiente son dudosos; si uno cae, con su
  base, donde uno del siguiente, el corte va antes de él; los demás dudosos se quedan sin nombre. Comparando REF a REF
  todos los pares 32/64 del corpus (1960): 88229 nombres iguales y 42 distintos antes; ahora 87796 y 0. En 64 bits
  solo se pierde un nombre (OutlookActiveX, que ya da `NoSoportado` por otra cosa).
- **La vuelta en 32 bits** enmascara los mismos punteros de memoria que en 64, con su sitio de 32: REF +0x0C (4 bytes),
  la basura de los literales tras su ancho, GRID en FCT +0x64, clases de tabla en CLA +0x14 y los binarios de SVL de 4
  en 4.

Resultado: la vuelta completa en 32 bits, las 20 entradas, 0 distintos (samples: 345 de 415 se descompilan; en 64, 354). Los
módulos de los kits con el mismo fuente en 32 y 64 bits dan el mismo texto en 138 casos (antes 87, y 45 ambiguos),
sin ninguno que solo salga en 64 (también STOCKMDI `menu` y NIF `sample01`). Proyectos del kit x86: 19 → 100 de 121;
compilados aquí en 32 bits, 101 de 120 (en 64, 102 de 121). Kit x86 frente a compilado aquí: 88 de 100 con el mismo
texto, y los otros 12 solo cambian en la POSITION de AUTOSIZE (las medidas de 7.2.3 no son las de 8.6).

## 2026-10-29 — Nombre por su entrada de EPR/EOB, y `Char default null`

**El nombre de un miembro externo por su entrada.** Un nodo de método (0x20) o de propiedad externa (0x10 con EOB)
apunta en +0x10 a su entrada de EPR o de EOB, y en +0x18 lleva el puntero a su nombre. A veces ese puntero es una
dirección estática del compilador (AGENDA `mes`: el `MDY` de `myCursor.Open(MDY(…))` va en 0x14E120, y los
`mydate.Month`/`Year` de dentro en 0x14DE40) o un puntero que la regla de choques descarta (ActiveX `Word`,
`txtTemplate.Text`). Entonces el nombre sale de los otros nodos con la misma entrada: en los 3128 `.omd` del corpus
ninguna entrada da dos nombres (16810 de EPR y 1540 de EOB, todas con un nombre, también en mayúsculas y minúsculas).
Si dos nodos de la misma entrada dieran dos nombres, la entrada no sirve (`NoSoportado`). Proyectos: AGENDA y ActiveX
`Word` salen enteros.

**`x as Char default null`.** El compilador no lo guarda en el OBJ (queda igual que sin default: ni el bit 0x20 ni
valor) y solo deja la cadena `NULL`, en mayúsculas aunque el fuente diga `null`, en STR donde se declaró, sin que la
apunte nada (AGENDA `mes` y 4 de samples: `coscompressextract`, `coscompressextractpw`, `fnto_char_number`,
`loadjvm`). STR, IDE y los nodos de REF van en el orden del fuente, pero el orden de REF no lo es entre
procedimientos (en loadjvm, `main` va detrás de `Carga01`); dentro de uno, sí. Así que cada literal se acota con el
nombre (posición de IDE, por su puntero) del nodo de antes y del de después: la variable es una Char sin default cuyo
nombre cae entre el de antes del último literal anterior a `NULL` y el de después del primero posterior (y entre los
defaults en STR de otras Char). Si quedan varias seguidas (en un mismo `objects`), cualquiera da los mismos bytes: la
primera, con aviso (`coscompressextract`: en el fuente es la segunda de tres). Si no queda ninguna, o no son seguidas,
la cadena sigue sin usar (`NoSoportado`).

La vuelta tiene dos entradas nuevas, `agen` (AGENDA) y `actx` (ActiveX), y si los `.omd` de partida de una entrada
no están, los compila (en 64 bits también).

Con las dos entradas nuevas y los 8 samples que ahora salen, la vuelta cazó tres cosas:
- **`c[i]` de un Char:** el operador INDICE lleva siempre dos argumentos; si el fuente solo escribe el primero, el
  segundo (la longitud, 1) lo crea el compilador detrás del operador, como un argumento por defecto (samples
  `utilshtml`: `colorStr.Trim[1]` salía `colorStr.Trim[1, 1]`, y el `.omd` tenía 21 nodos más). Se quitan con la misma
  regla que los argumentos por defecto; escritos (`s[-5, 5]`, `today.Char[1, 5]`), se quedan.
- **LIKEVAR en un EDIT con SCROLL** va delante de SCROLL; detrás, el compilador dice «Actual likevar(LIKEVAR).
  Expecting control, end» (AGENDA `mes`).
- **AUTOSIZE en un BITMAP** va delante de BITMAP FILE; detrás, «Actual autosize(AUTOSIZE). Expecting control, end»
  (samples `almacen`), como en un GRID delante de SCROLL.

## 2026-10-29 — TAB con las páginas en el LABEL, bordes con EXTRA n y VAR de página con borde

- **TAB con `LABEL "a|b"`** (sin NUMBER ni TAB LABEL; ALMAFAC2 FRMTMPL): el FCT es el mismo que con `NUMBER 2` y
  `TAB LABEL`; solo cambia el binario de +0x68, que lleva 0xFFFF en el u16 alto del icono de cada página (0xFFFE, sin
  icono, con TAB LABEL). Todas 0xFFFF → `LABEL "…"`; mezcladas, `NoSoportado`. Batería `tabs.py`, 6 al final. Con las
  páginas en el LABEL no se guarda el ICON FILE (ni el bit ni ICO), y con TAB LABEL además del LABEL mandan las
  páginas. [hipótesis, fuera de la batería] `LABEL "a|b"` con `NUMBER 2` compila, pero el ancho que calcula el
  compilador es el de una página sin texto (42 frente a 49 con «a»); el .omd no dice que hubiera NUMBER y sale sin él.
- **EXTRA n** (2 bits de +0x00) va solo o con DOUBLE, DOWN, FRAME o ETCHED, con n de 1 a 3: batería `controles.py`,
  8 al final, todos compilan (CalcALG calcu3: `BORDER ETCHED EXTRA 2` = 0xA). Con BLACK, solo EXTRA 1 probado; lo demás,
  `NoSoportado`.
- **VAR de página con BORDER** (`BORDER DOUBLE TOP BOTTOM`, `BORDER TOP BOTTOM`: STOCKMDI item_rep1): los mismos bits
  que en un TEXT de página (BORDE_PAG), detrás de LABEL. Batería `paginas.py`, 6 al final.

## 2026-10-30 — Clases que no son formulario (batería `clases.py`; NIF y CalcALG)

- **Visibilidad:** campo 0x30 del byte 3 de CLA, PRO y OBJ: 1 public (la de por defecto; escrita o no, los mismos
  bytes), 2 protected, 3 private; 0 en las clases implícitas, `main` y los eventos. Las variables locales y los
  parámetros llevan siempre 3. Antes, un PRO protected (0x25) salía `private` (se miraba solo el bit 0x20) y en las
  clases, los miembros y los objetos del módulo no se leía: `PRIVATE A is Struct` salía sin PRIVATE. No había ningún
  módulo del corpus que lo diera (todos se paraban antes).
- **Herencia:** `B is A begin … end` (byte 0 = 0x20, miembros desde +0x40) solo compila si A es abstracta (si no,
  «Actual begin(begin). Expecting identifier»), y `A is Struct` o `B is A` sin el `begin end`, tampoco. `B is A` sin
  miembros, con A con miembros: +0x40 lleva un puntero de memoria del compilador (CalcALG ScEval 0x2fc6960 en el kit,
  0x1c734b8 compilado aquí, 0x28a22e0 en el kit x86), que no se escribe; la vuelta lo pone a cero (`_puntero_de_clase`).
  `B is A` sin miembros ni puntero de otra base: `NoSoportado`. Abstracta con miembros no compila.
- **`X is Decimal (32,2)`**, `Money`, `Char (10)`: la precisión y la escala (o la longitud) en +0x30, como en un OBJ.
  Un objeto de esa clase lleva los mismos en su +0x30 (`x as X (10,2)` no compila): con una clase del módulo se
  comprueba que son los suyos; con una incluida, solo pueden serlo. `B is X` los copia igual.
- **Constantes Char** (+0x20 → su cadena en STR; se cuenta como apuntada solo si la constante es Char: un entero 512
  sería 0x200), **Decimal** (su DEC) y **Boolean** (1 o 0). `K = null` deja byte 0 = 0x02, clase 0 y un valor que
  parece basura: `NoSoportado`.
- **`operator` y `conversor`:** PRO de tipo 2 (el operador en +0x28, con los códigos de los binarios de REF: 1 `=`,
  9 `+`, 3 `*`, 11 `+=`) y de tipo 3 (la clase en +0x20, sin nombre ni parámetros). `operator ==`, `<` y `<>` no
  compilan.
- **Constante de un módulo incluido** (variante 0x60 del literal; NIF Nif_1 `LONGITUD_NIF`, CalcALG ScEval
  `TOKEN_IS_UKN`): el nodo no guarda su nombre, pero IDE lleva cada identificador en el orden del fuente, también los
  usos. El texto se escribe en ese orden: mientras se escribe un procedimiento se anotan las posiciones en IDE de lo
  que la tiene (su nombre, parámetros, variables y los nodos con puntero resuelto), y cada constante va en el hueco
  entre la anterior y la siguiente, que no puede tener un nombre de posición desconocida (un control, una tabla, un
  puntero sin resolver) y tiene que dejar un nombre libre por constante (`con_externas`). El orden de REF no sirve:
  no es el del fuente ni dentro de un procedimiento (en ScEval, el nodo de `GetError` se crea después que el de
  `type`).
- **`PI`**: el compilador lo cambia por su valor (3.141592653589793238462643383) con la variante de constante (0x50);
  escrito el valor, la variante es 0xF0. Antes, una variante 0x50 sin constante del módulo salía como literal; ahora
  es `PI` si vale eso y `NoSoportado` si no.
- **Lo que cazó la vuelta de CalcALG** (fallos de antes, no de las clases):
  - `case "=", "Enter":`: una condición «valor == x» por valor, encadenadas por +0x08 de la primera; salía solo la
    primera, sin aviso (calcu3).
  - Un decimal entero (`d1 > 0.0`, `d = 1.0`) salía sin punto y se volvía a compilar como entero (ScEval: DEC 3 → 0).
    En las expresiones y las constantes, con `.0`; en los defaults no hace falta (`default 0`, el mismo DEC).
  - `str1 str2 str3 as char default ""` comparte una sola cadena en STR (tres líneas crean tres), como el DEC de los
    decimales (AbsAriEval).

## 2026-10-30 — OutlookActiveX y mail

- **Método sin nombre por su hueco en IDE.** INC_OUTLOOK (compilado con la 7.42) lleva en `0.integer` (Numeric,
  miembro 0x11) la dirección estática 0x140156AC0, que no está en el compilador 8.6 ni la tiene otro nodo: el nombre
  sale de IDE como el de una constante incluida (`con_externas`). En EPR, cada (clase predefinida, miembro) da un solo
  nombre en todo el corpus (958 entradas; la única doble, de una clase del usuario).
- **Conversión del compilador.** La misma dirección va en la conversión que añade el compilador (`GetWord("|", i)`,
  un Smallint a Integer): no deja nombre en IDE. Un acceso sin argumentos ni paréntesis cuyo método no tiene nombre se
  escribe si en su hueco le toca un nombre libre (y es el que ya tiene esa entrada de EPR); si no, era implícita.
- **El hueco, más estricto:** solo acotan las posiciones que van creciendo (un puntero de método puede ir a otra
  aparición del mismo nombre: el `Invoke` de CreateItemAppointment cae en el del procedimiento de antes; y los de `i`,
  fuera del procedimiento), y lo de posición desconocida (controles, tablas, punteros sin resolver) se empareja por
  su nombre con los libres del hueco: se come el que toca si se llama igual. Tienen que acabarse a la vez.
- **Tramos de punteros recortados.** OutlookActiveX: un tramo de 21 punteros (el `On Open`) se alargó con uno que
  cuadraba por casualidad y caía en la misma posición de IDE que uno de un tramo de 39 (`AttachFile`); la regla de «una
  aparición, un puntero» tiraba el tramo entero (22 y 45 punteros sin nombre). Si chocan solo los de un extremo y lo
  que queda sigue dando una sola base, se quitan esos (sin nombre de puntero; lo toman de su entrada) y el resto vale.
  El tramo falso de ActiveX Word (2 punteros) choca entero y se sigue descartando; uno solo cabe en muchas bases.
- **SPLIT** (tipo 0x16): los bits de siempre (bordes, ATTACH en +0x44, INVISIBLE, DISABLED) y VERTICAL = 0x1000,
  detrás de BORDER (delante no compila). LABEL y NOLABEL no compilan. Batería `controles.py`, 15 al final (12 compilan).
- **`Array [256] of Char (8)`**: los parámetros del elemento en +0x30 del CLA (mail IncEncoders).
- **Time default:** segundos en +0x28 y 1 en +0x2C (en 32 bits, solo los segundos). `default 1` es una hora (3600) y
  `default 3600` no compila («Conversion of 3600 from class Char to class Time is dynamic»); `"10:30:00"` = 37800.
  Sale `0` o `"hh:mm:ss"`; `default NOW`, el bit 0x40 del byte 2, como TODAY; `default null` no se guarda.
- **`x as Char default null` de un parámetro** sí lo marca en su OBJ (0x20 de los bytes 0 y 2) y deja también su
  'NULL' en STR (mail IncSMTPClient): una por parámetro, en orden. En un local sin marca, vale cualquier Char sin
  default del hueco aunque no sean seguidas (mail SendModule, con un objeto de otra clase en medio): entre ellas no se
  crea ninguna cadena.
- **Proyectos con subcarpetas** (mail: Includes, PROBES, PROGRAMS): `vuelta_arbol.sh` compila el árbol con `-all`.
- **samples demorestcosmos customers:** en los tres kits x64 (8.2, 8.4, 8.6) el `.omd` se compiló de otra versión del
  fuente (`" supplier = "` en STR donde el `.smd` y el `.omd` x86 dicen `" customer = "`); no cuenta para 32 = 64.

## 2026-10-30 — Controles y opciones de un objeto, y los atributos que faltaban (samples, 395 → 400)

- **`objeto.control`** (samples DBL `Miform.milist.AddString("a1")`, y 12 más): nodo 0x01 0x01 con el objeto en +0x10
  y el control en +0x18, un nodo 0x00 de variante **0x21** (dentro de su formulario es 0x31) con +0x10 → su FCT, o su
  PCT si es de una página. Su +0x18 es un puntero de memoria, como el de 0x31: la vuelta lo pone a cero.
- **`objeto.opcion`** de un menú (samples MENU `mm.a.Add(…)`): nodo 0xF1 0x00 con la opción en un nodo 0xF0 0x20
  (+0x10 → su MOP); el nombre, en IDE por el +0x2C del MOP, como al escribir el menú.
- **Procedimiento del módulo desde una clase** (variante 0x50 con +0x10 → PRO): MODU escribe `module.Clear` desde una
  página y Cosregexpdll llama a sus dll sin nada; los mismos bytes. Sale con `Module.`, que vale siempre (dentro de la
  clase, `Clear` a secas podría ser un método suyo).
- **Eventos:** `On ExMessage` del formulario es el 24 (SNDMSG); `On Error` del módulo es un PRO de tipo 0x0C con 36
  en +0x28 (COSMOSJAVA, el único visto). `current` es la palabra reservada de DateTime (GETSYSTEMTYMEUTC).
- **DISABLED** va justo tras POSITION: detrás de cualquier otro atributo (FOREGROUND, INVISIBLE, CURSOR, NOTABSTOP,
  ATTACH…) no compila (batería `controles.py`; los 60 del kit van así). Lo cazó la vuelta de CosHttpDllPostCommand.
- **NOBORDER de un BUTTON** no va en los bits de siempre: es 0x40 en el u16 alto de +0x20, el campo de BORDER
  HILIGHT/BLACK; delante del icono. **DEFPUSH**, con uno de esos tres, va detrás (NewLook: `BORDER HILIGHT DEFPUSH`).
- **BAR sin BARTYPE**: 0 (Transparent, IgnoreCustomColors, CosmosVisualModeV2). **PANELTYPE MESSAGE** = 2 (TREE1).
- **NOLABEL del formulario** = 0x800, tras LABEL y delante de SYSMENU (RichText). **RICHTEXTEDIT** de un EDIT = 0x400,
  detrás de BORDER, LABEL y MULTILINE y delante de WRAP, PASSWORD y DATATYPE (RichTextPrintEx).
- Batería `controles.py`: 50 al final (`dis_`, `bnb_`, `bt0_`, `fnl_`, `rte_`, `bdp_`); compilan 30, todas exactas.

## 2026-10-30 — ArgList, Enum y EnumSet (samples ARG y ENUM; batería `clases.py`)

- **`X is ArgList of Y`**: CLA con 0x29 en el byte 0; Y en +0x40 y sus parámetros en +0x30, como un Array. `VAR` en el
  parámetro de un ArgList da los mismos bytes (ARG lo escribe).
- **`X is Enum of [a b c]`** (byte 0 = 0x08) y **`X is EnumSet of [a b c]`** (0x09): los valores en una cadena de STR
  (+0x40) con un `|` detrás de cada uno (`red|yellow|green|`), y cuántos son en +0x30.
- **Valores en el código**, con +0x10 → la CLA de su clase: de un Enum, nodo 0xB0 0x50 con el índice en +0x18; de un
  EnumSet, nodo 0x10 0x51 con la máscara `1 << índice` en +0x18. Su nombre está en IDE (una vez por uso), sin puntero.
- No compilan: `==` entre valores de un Enum («undefined operator == for class color») y `-` de un EnumSet.
- Sin resolver: `red.Trace;` con el método sin puntero (sin paréntesis se lee como una conversión implícita, y `Trace`
  no es una clase): NoSoportado.
- Batería `clases.py`: 20 al final (`en_`, `al_`); compilan 17, 16 exactas (la otra, NoSoportado).

## 2026-10-30 — Controles de página que faltaban (batería `paginas.py`, sexta y séptima tanda)

- **CHECK** (tipo 3) y **BITMAP** (tipo 0x0F) de página: NOLABEL delante del borde; en un BITMAP, STRETCH = 0x100
  detrás del borde. El CHECK puede llevar VARIABLE (+0x78 → FOB).
- **GROUP:** AUTOSIZE = 0x8000, delante de AS LINES y REPEAT; **FIXED** es que falte el 0x40000000 de +0x44 (que hasta
  ahora se daba por obligatorio), detrás de REPEAT; FIXED con BYCOLS no compila. BOLD vale también en un GROUP.
- **TEXT:** WRAP = 0x4000000 de +0x44, entre MULTILINE y TAGS; VERTICALTEXTLEFT = 0x20000 y VERTICALTEXTRIGHT =
  0x10000, detrás de TAGS (samples EjReportProv).
- **BOX:** `CURRENT PAGE n` = n − 1 en el u16 alto de +0x60 (el bajo es el PAGE de los hijos), tras NOLABEL y delante
  del borde. El PAGE de página se lee ahora del u16 bajo (antes, del u32 entero).
- **`CHARSET Gb2312`** = 134 (Impresionpdfmulticharset). `CHARSET Gb` compila pero no deja huella.
- Batería: 47 al final (`pga_`, `ptw_`, `pck_`, `pbm_`, `pbx_`, `pvt_`, `pgb_`); compilan 36.

## 2026-10-30 — BOXGROUP de página (batería `paginas.py`, octava tanda; samples LISTADOCAJA)

- Tipo 0x0E en PCT, con los mismos campos que el de formulario: NUMBER en +0x40, las etiquetas unidas con `|` en +0x48
  (con el bit LABEL), COLUMNS = 0x1000 de +0x00, el binario de grupo en +0x68 (cabecera de 16 bytes y 8 por elemento,
  con su BACKGROUND).
- **Dos bordes.** El `BORDER` de delante de NUMBER es el del control (byte bajo de +0x00, como en cualquier control de
  página); el de detrás, el de los elementos, en el u16 alto de +0x20 con los bits del borde de página (0xF0 ALL, 0xF2
  DOWNSHADOW ALL, 0xC0 TOP BOTTOM). En un formulario, `BORDER ALL` ahí no compila.
- Un `BOX` solo y sin etiqueta no deja ni el bit LABEL ni texto en +0x48. Con dos (`BOX` y `BOX`) sí: LABEL y «|».
  Sin LABEL y con más de uno no se ha visto: NoSoportado.
- `BOX LABEL ""` y `BOX` a secas dan los mismos bytes; `BACKGROUND COLOR red` sale como `RGB 255 0 0`.
- No compilan en página: NOBORDER, CLICKTYPE y LABEL del control. VARIABLE no se ha probado: NoSoportado.
- Batería: 19 al final (`pxg_`); compilan 16, 14 exactas y 2 equivalentes.

## 2026-10-30 — ICON FILE de los desplegables, FORMAT, columnas sin join y `Struct as tabla` (samples)

- **ICON FILE en DROPLIST y DROPEDIT** (SetBoxIcoFile): como en un LIST, el bit 0x10 de +0xA8 y el índice en ICO en el
  u16 de +0x18 de su binario de SVL. Va delante de DATATYPE (en un DROPEDIT, detrás no compila) y detrás de AUTOSIZE.
- **`DATATYPE CHAR FORMAT "x"`** de TEXT y EDIT (drag1): +0xA0 → el texto en SVL, también con `FORMAT ""`. Con
  SMALLINT, DATE o DECIMAL no compila: NoSoportado.
- **`x as tabla.columna` sin join** en una tabla de formulario (EjLookupColumns): un FOB sin la marca de columna, con
  escala −1 en +0x30 y +0x78 y +0x80 a 0. Es el tipo resuelto, como un OBJ: se escribe una columna del repositorio
  del mismo tipo (la del mismo nombre, si la hay), con aviso cuando hay varias.
- **`X is Struct as tabla`** da los mismos bytes que sus columnas escritas a mano (`state as states.state`…): el .omd no
  guarda la tabla. Se escribe `Struct as tabla` si los miembros son, en su orden, las columnas de una sola tabla del
  repositorio y los de tipo de columna tienen escala −1. EjInitializeWithDefault usa una tabla (`tempdefaults`) que crea
  el propio programa y no está en `stock.dbs`: sus miembros Time y DateTime no tienen columna con la que escribirse, y
  sigue en NoSoportado.
- Baterías: `listas.py` 13 al final (`d3_`, compilan 10), `controles.py` 11 (`fmt_`, 7), `tablas.py` 5 (`jx_`, 5),
  `clases.py` 6 (`sa_`, 6). La entrada `cla` de la vuelta pasa al proyecto samples (repositorio stock).

## 2026-10-31 — Ventana: THINFRAME, THINCAPTION, CHECKMETHOD y FRAMEAUTOSIZE (baterías `formularios.py`, `controles.py`, `paginas.py`)

Las cuatro palabras salen de las cadenas de formato de `docdll.dll` del kit (el documentador del fabricante), que dio
las hipótesis; todo lo de abajo está comprobado con las baterías compiladas en x-server, en 64 y en 32 bits.

- **El borde del formulario** (FCT 0, +0x00). El de serie lleva DOUBLE (0x04): `0x80000004`. NOBORDER = 0x40 sin
  0x04; RESIZING = 0x200 con 0x04; **THINFRAME = ninguno de los tres** (`0x80000000`). Antes, un formulario sin 0x04
  salía NOBORDER aunque no tuviera el 0x40: un THINFRAME se escribía como NOBORDER, que recompila a otros bytes y sin
  NoSoportado. THINFRAME o NOBORDER con RESIZING y THINFRAME con NOBORDER no compilan (en ningún orden); cualquier
  otra combinación de esos tres bits no se ha visto: NoSoportado.
- **THINCAPTION** = 0x1 de +0x00 del formulario (en un control, 0x3 es EXTRA n, y THINCAPTION no compila).
- **Orden del formulario** (lo que no, no compila): LABEL, NOLABEL, el borde (NOBORDER, THINFRAME o RESIZING), MAXIMIZE,
  MINIMIZE, THINCAPTION, SYSMENU, ALLOWDROP. **NOBORDER detrás de SYSMENU, MAXIMIZE, MINIMIZE, ALLOWDROP o THINCAPTION
  no compila**: Hubble lo escribía al final, así que un formulario con NOBORDER y cualquiera de esos daba un fuente que
  no compilaba (no había ninguno en el corpus). Ahora va en el sitio del borde.
- **CHECKMETHOD x** de EDIT y DROPEDIT: +0xB8 → el nombre en SVL, tal cual (en 32 bits, +0x6C, comprobado con la
  batería compilada en 32 bits: los 42 programas dan el mismo texto). Es un nombre y no una referencia: compila sin el
  método, y con dos EDIT cada uno lleva su texto. Con comillas no compila. Va el último: detrás de DATATYPE, READONLY,
  LIKEVAR, DATETIMEPICKER y de los atributos de lista (SHOW n LINES, SORTONCLICK); delante, no compila. En un TEXT no
  compila (+0xB8 sigue sin leerse). Con TAGS no compiló en ningún orden de los probados, y con LIKEVAR de una columna
  del repositorio el compilador podría copiarlo de la columna (`docdll` no lo escribe si la columna lleva 0x100100):
  los dos, NoSoportado. Un texto que no es un nombre, NoSoportado. De paso: **READONLY de DROPEDIT** (0x40000000 de
  +0x44, como en EDIT; detrás de DATATYPE).
- **FRAMEAUTOSIZE** = 0x10000 de +0x00 de BUTTONGROUP y BOXGROUP (en BOX, BITMAP o EDIT no compila: por eso no compiló
  en la batería `fct.py`). En el formulario, el orden es COMMENT, NOLABEL, AUTOSIZE, ICON FILE, FRAMEAUTOSIZE,
  VARIABLE, ALLOWDRAG, CLICKTYPE y NUMBER: con FRAMEAUTOSIZE, AUTOSIZE pasa delante del icono (ICON FILE, AUTOSIZE,
  FRAMEAUTOSIZE no compila) y ALLOWDRAG detrás. En un BOXGROUP de página: NOLABEL, ATTACH, PAGE, el borde del control,
  AUTOSIZE y FRAMEAUTOSIZE; AUTOSIZE (0x8000) y BOLD de un BOXGROUP de página también son de esta tanda. AUTOSIZE con
  ATTACH, PAGE o el borde, en página, no se ha visto: NoSoportado.
- Baterías: `formularios.py` 75 al final (`vw_`, `vw2_`; compilan 42, 40 exactas), `controles.py` 28 (`vw_`, `vw2_`;
  compilan 18), `paginas.py` 13 (`pvw_`, `pvw2_`; compilan 9, exactas). La batería de formularios usa los huecos desde
  el 92 (como la instalada).

## 2026-10-31 — Rejilla: NOROWNUM, NOARROW, NOALLOWADD y SORT (baterías `tablas.py` y `fct.py`)

Ninguna de las cuatro sale en un fuente del kit (ni en el manual, salvo en la lista de palabras reservadas): todo lo
de abajo sale de las baterías compiladas en x-server. El orden de las cadenas del compilador (`PARENTGRID`, `COLUMNS
%d`, `NOROWNUM`, `NOARROW`, `NOALLOWADD`, `AUTOSORT`; ` SORT`, ` SORTONCLICK`) dio las hipótesis.

- **NOROWNUM, NOARROW y NOALLOWADD** de un GRID: bits 0x40000, 0x20000 y 0x80000 de +0x00, los mismos que UPSHIFT,
  PASSWORD y DOWNSHIFT en los demás controles. Se suman (los siete casos, `0x800f0000` con los tres) y no cambian el
  binario de SVL de +0x68 ni nada más del .omd (con la misma geometría). PASSWORD, UPSHIFT y DOWNSHIFT en un GRID no
  compilan, ni delante ni detrás de PARENTGRID, así que los bits no son ambiguos. **Antes, Hubble escribía PASSWORD,
  UPSHIFT y DOWNSHIFT** en su lugar, sin NoSoportado, y el fuente no compilaba.
- **Orden:** detrás de PARENTGRID, en el orden NOROWNUM, NOARROW, NOALLOWADD, y delante de AUTOSORT. Cualquier otro
  orden entre ellos, delante de PARENTGRID o delante de TABLE, no compila. Con SCROLL y AUTOSIZE delante, compila.
- Sin PARENTGRID, NOROWNUM compila (0x40000 sin 0x10000), y cambia el alto del hijo: un GRID sin PARENTGRID sigue en
  NoSoportado. **`COLUMNS 1` en un GRID no compila** en los sitios probados (detrás de PARENTGRID, y delante y detrás de
  NOROWNUM): la cadena del compilador será de otro control.
- **SORT** de LIST, DROPLIST y DROPEDIT: 0x200 de +0xA8 (con SIMPLE 0x10, MULTIPLE 0x30, LISTCOLS 0x1, ICON FILE 0x100 y
  SORTONCLICK 0x400 se suma). En un LIST va detrás de ICON FILE, ALLOWDRAG y ALLOWDROP y delante de SORTONCLICK y de
  LISTTYPE (detrás de cualquiera de ellos, no compila). En DROPLIST y DROPEDIT, detrás de ICON FILE y de DATATYPE y
  delante de TAGS, SORTONCLICK y SHOW n LINES. Con READONLY o LIKEVAR no se ha probado: NoSoportado.
- **De paso: SORTONCLICK va delante de SHOW n LINES** en un desplegable; detrás no compila, y Hubble lo escribía detrás
  (ningún fuente del corpus junta los dos).
- Baterías: `tablas.py` 31 al final (`rj_`, `rj2_`; compilan 13, 11 exactas, 1 equivalente con AUTOSIZE y 1
  NoSoportado sin PARENTGRID), `fct.py` 53 (`so_`, `so2_`, `so3_`; compilan 33, todas exactas). En `fct.py` y no en
  `listas.py` porque a `listas.py` no le quedan huecos (usa del 200 al 273).

## 2026-10-31 — Código: SELF, OPERATION, TICKS, references y joining (baterías `clases.py`, `datos.py`, `fct.py`, `variables.py`)

Ninguna sale en un fuente del kit. Las hipótesis, de las cadenas de `cosmakecon.exe`, del manual (`refer.chm`) y del
editor visual (`Victrpro.drw`); lo de abajo, de las baterías compiladas en x-server.

- **`public self dll "x.dll" F(…)`** (y `self javaclass`): bit 0x20 del byte 1 del PRO externo (`0x15000109` →
  `0x15002109`; sin `return`, `0x15000509` → `0x15002509`). No añade parámetros (el manual dice que el objeto se pasa
  como primer parámetro, pero no deja OBJ) ni cambia nada más; igual en el módulo, en una clase `sm is Smallint` y en
  un Struct. `SELF DLL` en mayúsculas da los mismos bytes. `self public dll` y `self dll` (sin acceso) no compilan
  («Actual identifier(self). Expecting  end»). Antes, Hubble no miraba ningún bit del PRO externo y **perdía el SELF
  sin avisar**; ahora el byte 1 solo puede llevar 0x01 (todos los externos del corpus: 904), 0x04 (sin return) y 0x20,
  el byte 2 tiene que ser 0 y el byte 3, 0x05 más la visibilidad: lo demás, NoSoportado.
- **`selfclass` / `SELFCLASS`** no compilan: `return selfclass`, `f(o as selfclass)` y `dll … return selfclass` dan
  «Unknown class identifier selfclass». Es lo que escribe cosmakecon en lugar del nombre de la propia clase; en 8.6
  se escribe el nombre (`return sm`), como ya hacía Hubble.
- **VAR de un parámetro de una clase simple del módulo** (`sm is Smallint`, byte 0 de su CLA = 0x02): el 0x40 del OBJ
  solo está con VAR, como en un básico. Hubble lo quitaba (solo escribía VAR en los básicos): **se perdía en silencio**.
  En las clases compuestas (0x20 del byte 0 de la CLA: Struct 0x20, Array 0x24, ArgList 0x29, 0xA0, 0xA1…) el 0x40 lo
  pone el compilador siempre (`f(VAR o as A)` y `f(o as A)` con un Struct, los mismos bytes). Con otra clase simple
  (0x01, 0x05, 0x08 en el corpus, siempre sin 0x40) y el 0x40, no se ha visto: NoSoportado.
- **Clase sin nombre:** `nombre_clase()` escribía `cla<n>` si la CLA no tenía nombre en IDE, y la definición de la clase
  salía `None is …`. No pasa en el corpus; ahora es NoSoportado.
- **`function` / `FUNCTION`**, `RETURN`, `OF`, `PUBLIC DLL`: los mismos bytes que sin `function` y que en minúsculas
  (solo cambian las posiciones de los nombres en IDE y el puntero de memoria de REF +0x18). `function f` sin acceso no
  compila. Las palabras reservadas no distinguen mayúsculas (manual, ref00005): Hubble escribe una sola grafía.
- **`PANELTYPE OPERATION`** = 4 en el u16 alto de +0x20 de un PANEL (con MESSAGE = 2 en la misma tanda), también dentro de
  un BAR y con LABEL delante. Es el orden del editor visual (General, Comment, Message, EditMode, Operation).
- **`TICKS n` no compila** en SLIDER ni en PERCENT, en ninguna de las 15 formas (detrás de TICKMARKS en otra línea o en
  la misma, con 0, 1 o 5, sin número, con RANGE, VERTICAL o POINT): «Actual ticks(TICKS). Expecting  control, end».
  Con lo de la batería de 2026-10-28, ninguna forma de TICKS compila en 8.6.
- **`references` / `joining` no compilan** en ninguna de las 16 formas nuevas (más las 4 de 2026-10-28): detrás de la
  cabecera de la tabla, `join …` da «Actual join(join). Expecting  begin» y `lookup …`, «Actual lookup(lookup)»; dentro
  del `begin … end`, «Unknown join mio» (con el `join mio lookup` de una columna) o «Expecting  identifier»; en la
  cabecera, «Expecting  begin»; detrás de `depend on orders join mio`, «Unknown depend join mio for table orderlines».
  Un join propio del formulario no se puede escribir en 8.6 (los FJO de una tabla salen todos del repositorio).
- Baterías: `clases.py` 36 al final (`sd_`, `sj_`, `sc_`, `fn_`, `gr_`; compilan 29, todas exactas o con los mismos
  bytes), `datos.py` 4 (`pop_`, exactas), `fct.py` 15 (`tks_`, `tkp_`; ninguna compila), `variables.py` 16 (`rf_`;
  ninguna compila).

## 2026-10-31 — ActiveX: CLSID, PROPERTY y `On Control` (batería `controles.py`; Events del kit 86x86)

Solo hay un ACTIVEX en todo el kit: `xcalendar` de `projects/ActiveX/Events.smd`, en el kit de 32 bits. Las hipótesis
salen de ese `.omd` y de las cadenas de `cosmakecon.exe` (`CLSID "%s"`, `PROPERTY "%s" "%s"`); lo de abajo, de la
batería compilada en x-server, en 64 y en 32 bits (los mismos campos; solo cambian las posiciones en IDE y SVL).

- **`CONTROL x AS ACTIVEX`** es el tipo 0x1A del u16 bajo de +0x20 (en la tabla de tipos del compilador va delante de
  MDICLIENT, 0x1B). Compila en 64 bits igual que en 32, sin que el CLSID esté registrado en Wine.
- **`CLSID "x"`** va donde el LABEL: +0x48 → el texto en SVL, tal cual (un ProgID como `Word.Application` o el CLSID
  en minúsculas se guardan sin tocar; el compilador no lo comprueba). El bit LABEL (0x10000000 de +0x00) está siempre.
- **`PROPERTY "nombre" "valor"`**: todas juntas en un solo texto de SVL donde los TAGS (+0x58, con el bit TAGS
  0x20000000), `nombre=valor|` por cada una y en el orden del fuente, con las repetidas (`Day=1|Day=2|`). Sin
  PROPERTY, el bit TAGS sigue puesto y +0x58 apunta a un texto vacío. Un valor vacío da `Day=|`.
- **Sin escape:** `PROPERTY "a=b" "c"` da `a=b=c|` y `PROPERTY "Day" "a|b"`, `Day=a|b|`. Hubble parte el texto por `|`
  y exige un solo `=` por trozo, con nombre: así lo que escribe vuelve a dar el mismo texto. Lo demás, NoSoportado.
- **Orden:** CLSID es obligatorio (sin él, «Expecting  clsid») y es el último de los atributos: detrás solo van las
  PROPERTY (LABEL, NOLABEL, TAGS, BORDER, NOBORDER o ATTACH detrás de CLSID dan «Expecting  control, end»; PROPERTY
  delante de CLSID o sin él, «Expecting  clsid»). LABEL, NOLABEL y BACKGROUND no compilan ni delante. Delante compilan,
  y salen exactas, DISABLED, INVISIBLE, FOREGROUND, FONT, ATTACH ALL, NOBORDER, BORDER DOUBLE DOWN y BORDER ETCHED
  EXTRA 2, también todas juntas. CURSOR compila delante, pero no se ha visto su bit (la variante con él llevaba
  BACKGROUND): con CURSOR, BOLD, NOTABSTOP, COMMENT, BORDER FRAME, PAGE, VARIABLE, FOCUS o hijos, NoSoportado.
- **`On Control x (e as Event)`** (Events): un PRO de tipo 5 con el bit 0x80 del byte 1, como `On event X control Y`
  (`0x501c505`), con el control en STR (+0x20) y +0x28 = 0: sin evento. Sin parámetro (`On Control c`) y con el
  control entre comillas (`On Control "c"`, los mismos bytes) también compila. Vale para cualquier control (BUTTON).
- **Eventos de un ACTIVEX, entre comillas.** El compilador no conoce sus eventos: `On event AfterUpdate control
  xcalendar` da «Unknown control event AfterUpdate» (lo cazó la vuelta de Events en 32 bits); Events lo escribe
  `On Event "AfterUpdate" Control "xcalendar"`, y entre comillas o sin ellas los bytes son los mismos (`"Click"` y
  `Click` en el mismo módulo). Hubble pone las comillas cuando el control es un ACTIVEX del módulo, y solo entonces.
- **JavaClass** ya estaba (PRO 0x0D, PR del 2026-10-28): Hubble escribe `javaclass`, como el kit; `cobertura.py` la
  cuenta con la otra grafía.
- Batería `controles.py`: 38 al final (`ax_`, `onc_`); compilan 26, 23 exactas, 1 equivalente (`On Control "c"`) y 2
  NoSoportado (las PROPERTY con `=` o `|` de más). Events (el del kit, el compilado aquí y el de `proy32`) ya se
  descompila, y su vuelta en 32 bits da los mismos bytes; el del kit y el compilado aquí, el mismo texto salvo la
  POSITION de sus cuatro TEXT con AUTOSIZE.

## 2026-10-31 — Dudosos que son del tramo (almafac4 lisalba1 del kit x86)

almafac4 lisalba1 del kit x86 daba NoSoportado («nombre sin hueco en IDE en REF 352»); el mismo fuente compilado aquí
en 32 bits y el `.omd` del kit x64 se descompilaban bien. El recorte de tramos del 2026-10-30 ya estaba y no lo
arreglaba: lo único distinto es dónde dejó el compilador del kit los bloques de memoria.

- **Qué pasa.** Sus 94 punteros de REF forman un solo grupo que se parte en dos tramos: 28 con la base 0x2A35C04 y
  66 con 0x2A35C4C, a 0x48 de la primera. Los dos últimos del primer tramo valen también con la base del segundo:
  REF 352, método `Clear` (0x2A360EC; con la otra base, `Text`), y REF 127, `pagina` (0x2A360F8; con la otra base,
  `acum`). Ninguno cae, con su base, donde uno del segundo tramo (que empieza en la posición 1336 de IDE), así que el
  corte no se movía y los dos se quedaban sin nombre; el método `Clear`, sin nombre ni hueco, daba el NoSoportado.
- **La regla** sale del mismo invariante que el corte (una aparición en IDE es de un solo puntero, y entre dos bloques
  hay un solo corte), al revés: si un dudoso, con la base del siguiente tramo, cae en la posición de un puntero seguro
  del tramo (con la base del tramo), no puede ser del siguiente: es del tramo, y con él todos los dudosos de antes.
  `pagina` con la base del segundo caería en la 1196 (`acum`), la del puntero 0x2A360B0 (REF 350), que es del primero
  sin duda (0x2A360F8 − 0x2A360B0 = 0x48, lo mismo que entre las bases). `Clear`, delante, también es del primero.
- **Solo contra seguros.** Un dudoso que solo caería donde otro dudoso no prueba nada: si los dos fueran del siguiente
  tramo no chocarían. Los `AddFormat` cada 0x10 de los samples TO_CHAR (FnTO_CHARDate, TOCHARCLASEDATE) y uno de
  EjTCAFITTOTALSWIDTH se quedan sin nombre, aunque contando con los dudosos saldrían 76 nombres más (iguales a los de
  64 bits, pero sin prueba).
- **Comprobado en todo el corpus** (4019 `.omd` de `kits/`): la regla da nombre a 36 punteros dudosos en 17 módulos,
  de las dos arquitecturas, y ningún otro nombre cambia ni se pierde. Los 36, comparados REF a REF con el `.omd` de la
  otra arquitectura: 36 iguales, ninguno distinto. No hace falta batería: la distancia entre bloques no depende del
  fuente (el mismo lisalba1 compilado aquí sale con las bases a 0xD48 y sin dudosos).
- **Resultado:** almafac4 lisalba1 del kit x86 da el mismo texto que el kit x64 y que el compilado aquí; el kit x86
  pasa de 115 a 116 de 121 (quedan los 5 LIKEVAR, a propósito). En los otros 16 módulos el texto no cambia (los
  nombres los daba ya su entrada de EPR/EOB, o siguen en NoSoportado por otra cosa).

## 2026-10-31 — Los tres samples que solo fallaban en 32 bits (baterías `clases.py`, `fct.py` y `paginas.py`)

Los samples daban 413/415 en 64 bits y 410/415 en 32. Los tres que solo fallaban en 32 salen ahora con el mismo texto
que en 64 (413/415 en las dos; quedan activexexcel y ejinitializewithdefault, a propósito).

- **ChartRadar: `valores as arglist of decimal` (parámetro).** La clase X de `a as ArgList of X` va en el +0x40 del
  OBJ del parámetro en 64 bits y en el +0x24 en 32, como en CLA (el mapa de OBJ de 32 bits no lo llevaba y había un
  NoSoportado a propósito). Batería `alp_`, compilada en las dos arquitecturas: en los 6 que compilan (Integer,
  Decimal, una clase del módulo `A` → +0x40 = 0x10700, dos parámetros, en minúsculas, con una llamada), el +0x24 de 32
  es el +0x40 de 64, y el texto es el mismo. No compilan `ArgList of Char(10)`, `ArgList of Decimal(10,2)` («Expecting
  ')'»), `ArgList` sin `of` («Expecting of») ni un objeto local `x as ArgList of Integer`. Un FOB de clase ArgList no
  se ha visto: en 32 bits sigue en NoSoportado (su +0x40 no tiene mapa).
- **EjDisableAceleradores: la geometría no es una declaración.** `_declarados` toma por declaración todo u32 con el
  u16 bajo 0x0100 que cae en un registro de IDE. `POSITION 256 39` deja en el FCT el u32 0x00270100 (x = 256, y = 39;
  +0x38 en 64, +0x20 en 32), y 39 × 4 = 156 es en 32 bits el registro del segundo `PutEnv`: se marcaba como declarado,
  ninguna base de punteros valía y ningún nombre de puntero se resolvía («no se sabe el nombre de la propiedad de REF
  1»). En 64 no chocaba por suerte: allí 156 no es el principio de un registro. Ahora la geometría de FCT y PCT (x e y en
  +0x38, ancho y alto en +0x3C; +0x20 y +0x24 en 32) no cuenta. Batería `geo_` (fct.py) y `pgeo_` (paginas.py): x o
  ancho 256 con y o alto por 4 en el registro de `Text`, `PutEnv`, `Run` o `Trace` (calculado para el hueco de cada
  variante, porque el primer registro de IDE es el nombre del módulo), en 32 y en 64 bits, y del propio formulario. Con
  main fallaban todas en la arquitectura de su nombre: las de formulario con NoSoportado y las de página **sin avisar**
  (`"x".t()` en vez de `"x".Trace()`: con `Trace` marcado como declarado, el único puntero se llevaba al único
  registro libre, el del control `t`). Con x = 255 no chocan.
- **ListasArbolEventoClick_Check: `Miform.Run;`, un método sin paréntesis ni puntero.** En 32 bits el puntero de `Run`
  (REF 261) cae en otro bloque de memoria y queda solo en su grupo, sin base. Sin nombre y sin paréntesis, el nodo
  puede ser una conversión implícita (no deja nombre en IDE) o el método escrito (sí lo deja); hasta ahora solo se
  tomaba por escrito si el nombre libre que le toca es el de una clase. Regla nueva: si es el último del tramo y le
  queda un nombre libre que no es de una clase (ni otro que el de su entrada de EPR), es el método escrito; si fuera
  una conversión, ese nombre sobraría y el tramo no cuadraría. Comprobado con una ablación en todo el corpus (los
  `.omd` de `kits/compilados` y de los seis zips, 64 y 32 bits): a cada método de EPR con nombre por puntero (puntero
  y entrada de un solo nodo) se le quitan el puntero, su posición y su entrada, y se descompila. La regla recupera 3131
  nombres, todos el del puntero, y no cambia ningún otro texto. (La versión con «no queda ningún otro sin nombre» en vez
  de «es el último del tramo» escribía `(fila + 1).fila` en ejactivexopenofficecalc: descartada.)
- **De paso, sin arreglar:** la misma ablación da 7 textos distintos que ya daba main (no son de esta regla): un `f.Run;`
  que sale `f;` (cosmosjava) y 6 métodos con argumentos que se quedan el nombre libre de otro. No pasan en ningún `.omd`
  real (todos tienen su puntero), pero muestran que las reglas de huecos de IDE de 2026-10-30 suponen que ningún otro
  nombre falta.

## 2026-10-31 — LIKEVAR con la máscara de una columna: el `.crf` (batería `likevar.py`; ALMAFAC LPROART)

Los 5 módulos que faltaban de los 121 de los proyectos del kit (LPROART de ALMAFAC, ALMAFAC2, ALMAFAC3 y almafac4, y
LProArtB de almafac4) tenían un `pr_cost as articulos.pr_cost` (MONEY(12,2)) y un VAR de página con `LIKEVAR`, que
lleva en el control `DECIMAL MASK 4` (+0x20 = 0x00430011). El FOB da los mismos bytes que `as Money(12,2)`: hasta
ahora, NoSoportado a propósito (la guarda de «`LIKEVAR` con máscara», 2026-10-28). Ahora salen los 5, también en el kit
x86: proyectos del kit **121/121** en x64 y en x86 (antes 116).

- **La máscara sale del `.crf`, no de la clase.** Batería `likevar.py` (16 nombres de módulo de ALMAFAC.PRJ, porque
  el compilador no compila un módulo que no está en el .prj: «Unregistered module»), compilada en el proyecto ALMAFAC:
  - `as articulos.pr_cost`, `clientes.total_factura`, `articulos.pr_vent` y `lineas.precio` con LIKEVAR dan el mismo
    control, con la máscara 4; `as Money(12,2)` y `as Decimal(12,2)`, la 0. `albaranes.fecha_albaran` da la 5
    (0x55), `as Date` la 0. Sin LIKEVAR (con `DATATYPE DECIMAL(12,2)`), la columna y el Money a mano dan el mismo
    control y el mismo FOB: sin LIKEVAR la columna no deja huella.
  - Sin `ALMAFAC.CRF` junto al `.dbs` no compila: «Can not load repository almafac».
  - Con copias del `.crf` con un byte cambiado: la máscara de `precio_tipo` de 4 a 3 → el control da 3; la máscara
    propia de `pr_cost` (que hereda de `precio_tipo`) de 0 a 3 → sigue en 4; la de `articulos.existencias` (no
    hereda) a 3 → 3; la de `articulos.articulo` a 6 → `lineas.articulo`, que hereda de ella, da 6. Con el `.crf` v2 de
    almafac4 (y su `precio_tipo` de 4 a 3): lo mismo.
  - En 32 bits (proyecto ALMAFAC de `trabajo32`, con el `.crf` v2 del kit x86), las mismas máscaras.
- **Formato del `.crf`** (`CRMMAGIC`, u16 de +8 = versión 1 o 2): desde 0x40, tablas de registros seguidas, cada una
  con una cabecera de 0x18 bytes (u32 1, u32 capacidad, u32 cuántos…) y `capacidad` registros. En uso: byte 3 con
  0x80. Las cuatro primeras: nombres (24 bytes en v1, 38 en v2; el nombre en +4), textos (260; nombres de tabla,
  etiquetas, valores «a|b»), tablas (50; +0xC → su nombre en textos) y columnas (94 en las dos versiones). El tamaño
  que trae la cabecera en v2 no es el de disco (40, 260, 52/56, 104): los de disco salen de dónde empieza la tabla
  siguiente en los 24 `.crf` de los kits. Registro de columna: +8 su tabla, +0xC su nombre, +0x14 = 1 si hereda,
  +0x1A el registro del que hereda (de un tipo de `tipos_fijos` o la columna de otra tabla), +0x1E coltype, +0x32 la
  máscara. Si hereda, vale la del registro del que hereda. Lector: `repositorio._mascaras_crf`.
- **Qué no se sabe (y no se usa):** una herencia de dos saltos (proveedores.provincia → tipos_fijos.provincia →
  provincias.provincia) no se ha compilado; las columnas de un tipo compuesto (clientes.apellidos… de `dirpost`) no
  están sueltas en el `.crf`; un registro con otro coltype que el `.dbs` o una columna con dos registros. Todas dan
  «no se sabe».
- **Cómo se escribe.** Antes de declarar los FOB, se juntan las máscaras que copian de cada uno los controles con
  LIKEVAR (TEXT de formulario y VAR de página, los dos que la miran; dos distintas → NoSoportado). Un Money o Decimal
  con máscara ≠ 0 era una columna: se escribe una del repositorio del mismo tipo **y con esa máscara en el `.crf`** (la
  del mismo nombre si la hay, con aviso si hay varias). Sin `.crf` legible, o sin ninguna, sigue en NoSoportado. Los de
  tipo de columna (escala −1) ya se escribían sin mirar la máscara: ahora se descarta la columna que tiene otra, y la
  que no se sabe sigue valiendo (así eticli sigue en `clientes.direccion`, que compila igual). En todo el corpus
  (4063 `.omd`) solo cambian los LPROART y LProArtB del kit (12, x64 y x86). 28 mutaciones del arreglo (lector,
  pasada previa, búsqueda, guarda y TEXT), todas en rojo.
- **TEXT con LIKEVAR de un Money:** el `ALIGNMENT RIGHT` lo copia el compilador de la variable (en la batería sale sin
  escribirlo); escrito detrás de LIKEVAR no compila («Actual alignment(ALIGNMENT). Expecting control, end»). Ya no se
  escribe; otra alineación con LIKEVAR en un TEXT no se ha visto: NoSoportado. (No pasaba en ningún `.omd` del corpus.)
- **Vuelta:** `alma` 17/17 en 64 y 32 bits (LPROART incluido), entrada nueva `lkv` (la batería) 14/14 en las dos.
  almafac4 no tiene entrada: su vuelta entera tropieza con AUXILIAR («Actual font(FONT)») e INICIO («Actual
  background(BACKGROUND)»), que no son de esta tarea; LPROART y LProArtB, compilados con los demás módulos en su fuente
  original, salen igual en 64 y 32 bits.

## 2026-11-01 — La vuelta de los proyectos del kit enteros (entrada `proy`)

Hasta ahora solo ALMAFAC (17 módulos) pasaba la vuelta en su propio proyecto. La entrada `proy` de `vuelta_todo.sh`
(`proy32` con `ARQ=32`) la hace con los 121 módulos de los proyectos del kit x64 (17 proyectos) y x86 (16), cada uno
compilado en su proyecto (su `.prj`, sus librerías y su repositorio). Es una medida: lo de abajo lo cazó la vuelta y
**no está arreglado** (cada punto, un arreglo en `src`). Todo sale igual en 64 y en 32 bits.

- **Cifras.** 64 bits: 120 módulos medibles (`converprjx64` no: su `.prj` es de 32 bits, cabecera «01.00.02», y el
  compilador x64 no lo abre), 119 descompilados y 1 NoSoportado; 54 idénticos byte a byte, 25 salvo punteros, 40
  distintos. 32 bits: 121 medibles, 120 descompilados y 1 NoSoportado; 67 idénticos, 13 salvo punteros, 40 distintos.
  De los 40, 8 no compilan y 1 cambia bytes; los otros 31 son consecuencia de los 8 (abajo).
- **CURSOR de un BUTTON va detrás de FOREGROUND, BACKGROUND, BOLD y FONT** (como en un grupo; arreglado el
  2026-11-02, sección de abajo), no justo tras
  POSITION como lo escribe Hubble: «Actual font(FONT). Expecting control, end» (ALMAFAC3 y almafac4 AUXILIAR, con
  `FONT "Verdana" 10 CHARSET Ansi` y luego `CURSOR`) y «Actual background(BACKGROUND)» (ALMAFAC3 y almafac4 INICIO,
  STOCKMDI menu, TryThisOneFirst menu_examples: `BACKGROUND COLOR transparent`, `BOLD`, `CURSOR`). 6 módulos.
- **AUTOSIZE de un control MENU va delante de `MENU x`**: «Actual autosize(AUTOSIZE)» (ALMAFAC2 frmtmpl; el de
  ALMAFAC no lleva control MENU). Hubble escribe `MENU menuForm` y luego `AUTOSIZE`.
- **ICON de un CHECK va detrás de VARIABLE**: «Actual variable(VARIABLE)» (STOCKMDI triple: `LABEL "Invoiced"`,
  `NOBORDER`, `VARIABLE orders.order_status`, `ICON 6`). Hubble escribe el icono delante del VARIABLE.
- **La columna de `x as tabla.columna` sin join deja huella en un VAR de página con LIKEVAR.** STOCKMDI cust_rep:
  `surname1 as customers.surname` sale `customers.company` (las dos Char(25) con máscara 0 y el nombre no coincide),
  y el PCT 10 de la vuelta lleva el bit 0x40000 de +0x00 (UPSHIFT) que el original no tiene: el compilador lo copia
  de la columna (`company` lo lleva, `surname` no). Elegir la columna por ese bit, o NoSoportado cuando no es única.
- **El nombre del REPOSITORY no es el de la carpeta `.dbs`** en INDODIC (`REPOSITORY indodic`, carpeta
  `INDONESI.DBS`): `repositorio.encontrar` no lo encuentra y UpkeepDict compilado aquí da NoSoportado («spanishWord
  es del tipo de una columna (Char) y el .omd no dice cuál»); el del kit salía porque `proyectos.py` pasa la única
  carpeta `.dbs` del proyecto. Pista: si solo hay una carpeta `.dbs` junto a los fuentes, es esa.
- **Un módulo que no compila arrastra a su tanda:** en ALMAFAC3, almafac4 y STOCKMDI los demás módulos de la tanda
  salen con CMD de 1 o 3 registros menos (`CMD: 17 → 16 registros`), porque el compilador acumula los comandos de la
  tanda y el módulo caído no aporta los suyos. Comprobado volviendo a compilar las dos con el fuente original de los
  caídos (AUXILIAR e INICIO; menu y triple): ALMAFAC3 15/15 y STOCKMDI 17/18 (solo queda cust_rep). Son 31 módulos.
- De paso: ALMAFAC2 trae `PROVEE_.SMD` sin estar en el `.prj` («Unregistered module PROVEE_») y sin `.omd`: no cuenta.

## 2026-11-01 — La vuelta repite la tanda con el fuente original de los que no compilan

Los 31 módulos «consecuencia» de la entrada `proy` (ALMAFAC3 y almafac4 por AUXILIAR e INICIO; STOCKMDI por menu y
triple) no tenían nada que arreglar en `src`: su texto descompilado es el bueno, pero la vuelta los medía en una tanda
coja. `compila_lote.sh` compila en tandas de 20 `-smd`, y el compilador acumula en cada tanda los `CMD` (y `ICO`, `FON`)
de todos sus módulos: si uno no compila, no aporta los suyos y los demás salen con 1 a 3 registros de `CMD` menos que
la referencia (`CMD: 17 → 16 registros`; en STOCKMDI `37 → 34`). Es el mismo contexto de tanda del 2026-10-28
(`ok-solo`), por el otro lado.

- **Arreglo, en la vuelta (no en `src`):** `vuelta_remota.sh` baja el informe de la compilación
  (`<VUELTA_TMP>/informe-<nombre>.tsv`); `vuelta.py caidos` lee los `fallo` que cuentan (solo los descompilados: una
  dependencia que falla por su cuenta, como `PROVEE_`, no), guarda el descompilado en `vuelta-<nombre>/caidos/`, repone
  el fuente original con el nombre del descompilado y escribe `caidos-<nombre>.txt`; `vuelta_de` repite entonces la
  compilación de la vuelta entera (línea «fallo en la tanda: … (se repite con su fuente original…)») y `vuelta.py
  compara` quita los caídos de los recompilados, con lo que **siguen contando como «el descompilado no compila»**: el
  arreglo no esconde ningún fallo, solo deja de culpar a los vecinos.
- La tanda repetida tiene el mismo contexto que la referencia (los mismos fuentes salvo los que Hubble descompiló
  bien), así que los demás se comparan en igualdad: cada módulo falla solo por lo suyo. Lo que quede distinto en
  `proy` tras esto es causa propia (los 8 que no compilan y cust_rep).

## 2026-11-02 — CURSOR detrás de los colores, BOLD y FONT en todos los controles (batería `fct.py`, `cur_`)

Los 6 módulos de la entrada `proy` que no compilaban por el CURSOR (ALMAFAC3 y almafac4 AUXILIAR e INICIO, STOCKMDI
menu, TryThisOneFirst menu_examples) ya vuelven. Hubble escribía el `CURSOR` de un control justo tras POSITION, con
DISABLED e INVISIBLE, y solo en los grupos lo ponía detrás de la fuente (lo del 2026-10-29, «y en los demás controles
sí», no se había comprobado: en los samples ningún control con CURSOR lleva colores ni fuente). La batería lo zanja
en todos los tipos a la vez: para 19 tipos (BUTTON, BOX, EDIT, CHECK, RADIO, TEXT, BITMAP, SLIDER, PERCENT, SPIN, LIST,
DROPLIST, DROPEDIT, USER, BAR, SPLIT, GRID, TAB y PANEL), `FOREGROUND … CURSOR`, `BACKGROUND … BOLD … CURSOR` y
`FONT … CURSOR` compilan y al revés no («Actual foreground(FOREGROUND)», «Actual background(BACKGROUND)», «Actual
font(FONT). Expecting control, end»; en RADIO, «Expecting number»). 57 compilan de 114, sin una sola excepción por
tipo.

- **Sitio exacto**, con las variantes de BUTTON y EDIT: detrás de INVISIBLE (`CURSOR` / `INVISIBLE` no compila) y de
  la fuente, y delante de STORE (`STORE DESIGN` / `CURSOR` no compila: «Actual cursor(CURSOR)»), FOCUS, NOTABSTOP y
  ATTACH (las tres igual). Es el mismo sitio que ya tenían los grupos: `atributos()` escribe ahora un solo CURSOR,
  tras FONT, para cualquier tipo. Los 59 que compilan y se descompilan vuelven a su fuente letra por letra (los 3 de
  GRID compilan pero sin PARENTGRID no se descompilan, como siempre).
- **Lo que no compila y no está en ningún fuente del kit:** la variante con todo (`INVISIBLE`, `FOREGROUND`,
  `BACKGROUND`, `BOLD`, `FONT`, `CURSOR`, `FOCUS`, `NOTABSTOP`, `ATTACH ALL`, `LABEL`) falla en NOTABSTOP («Actual
  notabstop(NOTABSTOP)»): `FOCUS` y luego `NOTABSTOP` no compilan juntos en ese orden, que es el que escribe Hubble.
  Ningún módulo del kit lleva los dos, así que queda como pregunta abierta, sin inventar el orden.
- Batería `fct.py`: 125 variantes al final (prefijo `cur_`), que agotan los huecos de `huecos2.txt` (274): la
  siguiente tanda de `fct.py` necesita huecos nuevos.

## 2026-11-02 — AUTOSIZE del control MENU, delante de `MENU x` (batería `menus.py`, `mau_`)

ALMAFAC2 FRMTMPL (el único módulo de la entrada `proy` que no compilaba por esto; el FRMTMPL de ALMAFAC no lleva
control MENU) ya vuelve. Hubble escribía el AUTOSIZE del control MENU de una barra (bit 0x8000 de +0x00, el de
siempre) en el sitio general, detrás de `MENU menuForm`, y el compilador se paraba («Actual autosize(AUTOSIZE).
Expecting control, end»); el fuente original lo lleva entre `ICON CENTER VERTICAL` y `MENU menuForm`.

- **Sitio exacto** (25 variantes `mau_` al final de `menus.py`, 13 compilan y 12 no, sin una sola excepción):
  AUTOSIZE compila detrás de FOREGROUND, ATTACH, NOBORDER, BORDER ETCHED, VERTICAL, ICON, INVISIBLE y CURSOR, y al
  revés no («Actual foreground(FOREGROUND)», «Actual icon(ICON)», «Actual cursor(CURSOR)»… «Expecting control,
  end»); delante de `BUTTON` / `BORDER HILIGHT` compila y detrás no («Actual autosize(AUTOSIZE)»); detrás de
  `MENU m` no compila (lo que escribía Hubble). Es decir: el AUTOSIZE del control MENU va tras el icono, delante de
  `BUTTON BORDER x` y de `MENU x`. `atributos()` lo escribe ahí y lo excluye del AUTOSIZE general (junto con GRID y
  BITMAP, que ya tenían el suyo). Las 13 que compilan vuelven a su fuente letra por letra.
- Los otros controles MENU del kit (STOCKMDI, samples Orders*, MENU, TryThisOneFirst) no llevan AUTOSIZE: no cambian.

## 2026-11-02 — `ICON n` de un CHECK, detrás de VARIABLE y de AUTOSIZE (baterías `menus.py`, `kic_`, y `tablas.py`, `rk_`)

STOCKMDI TRIPLE (el único módulo de la entrada `proy` que no compilaba por esto; ningún otro fuente del kit lleva
`ICON n` en un CHECK) ya vuelve. Hubble escribía el icono de un CHECK (+0x70 = (n − 1) << 16, lo del 2026-10-28)
en el sitio del icono de los demás controles, tras el borde y delante de VARIABLE, y el compilador se paraba en el
CHECK de su rejilla («Actual variable(VARIABLE). Expecting control, end»); el fuente original lleva `LABEL
"Invoiced"` / `NOBORDER` / `VARIABLE orders.order_status` / `ICON 6`.

- **Sitio exacto** (31 variantes `kic_` y `kic2_` al final de `menus.py`, que `fct.py` no tiene huecos; 7 compilan y
  24 no, sin una sola excepción): `VARIABLE v` / `ICON 6` compila y al revés no; `AUTOSIZE` / `ICON 6` compila y
  `ICON 6` / `AUTOSIZE` no («Actual autosize(AUTOSIZE)»: el orden viejo de Hubble fallaba también sin variable);
  `AUTOSIZE` / `VARIABLE v` / `ICON 6` y `LABELLEFT` / `VARIABLE v` / `ICON 6` compilan (AUTOSIZE o LABELLEFT detrás
  de VARIABLE, no). Es decir: el `ICON n` de un CHECK es lo último que escribe Hubble para ese control, detrás de
  AUTOSIZE y de VARIABLE. `atributos()` lo escribe tras VARIABLE y lo quita del sitio general del icono.
- **Lo que no compila en un CHECK, en ningún orden:** TAGS, LIKEVAR, READONLY y ALIGNMENT («Actual tags(TAGS)»…
  «Expecting control, end», con o sin VARIABLE, delante o detrás del icono). Nada de lo que Hubble escribe detrás de
  VARIABLE puede aparecer en un CHECK, así que no hay más orden que fijar.
- **Los demás controles con icono no cambian:** en un EDIT, `ICON 2 FILE "_MBSTDBMP_"` / `VARIABLE v` compila y
  `VARIABLE v` / `ICON …` no («Actual icon(ICON)»): el icono de BUTTON/BOX/EDIT sigue delante de VARIABLE, como
  siempre. En BUTTON y BOX, VARIABLE no compila (con icono o sin él).
- **En una rejilla, igual** (2 variantes `rk_` al final de `tablas.py`, repositorio stock): un CHECK hijo de un GRID
  con `VARIABLE states.sname` / `ICON 6` compila y al revés no. Las 7 + 1 que compilan vuelven a su fuente letra por
  letra (salvo `Char (1)` → `Char(1)` y, con AUTOSIZE, el tamaño calculado por el compilador).

## 2026-11-02 — El UPSHIFT que LIKEVAR copia de la columna: +0x24 del `.crf` (batería `tablas.py`, `up_`; STOCKMDI cust_rep)

STOCKMDI cust_rep (el último distinto de la entrada `proy`, en 64 y en 32: «PCT: mismos registros, otros bytes») ya
vuelve. `surname1 as customers.surname` salía `surname1 as customers.company`: las dos son Char(25) con máscara 0 en
stock.crf, el nombre `surname1` no coincide con ninguna y `buscar()` cogía la primera. Al recompilar, el VAR de página
con LIKEVAR sobre esa variable llevaba +0x00 = 0x90044800 en vez de 0x90004800: el bit 0x40000 (UPSHIFT), que el
compilador copia de la columna (company lo lleva, surname no).

- **De dónde sale el bit** (18 variantes `up_` al final de `tablas.py`, repositorio stock, 12 compilan y 6 no): con
  LIKEVAR sobre `p as customers.company` (o `states.state`), el VAR de página, el TEXT y el EDIT de formulario llevan
  0x40000 en +0x00; sobre `customers.surname` o `customers.fname`, no. En stock.crf, en el registro de columna
  (94 bytes, el del 2026-10-31), el u16 de +0x24 vale 0x2 en company, payform y state (y states.state…) y 0 en
  surname, fname y las demás; en los 24 `.crf` de los kits solo vale 0 o 2, y solo en columnas Char. Compilando las
  mismas 6 variantes con copias de stock.crf con ese u16 cambiado: company a 0 y surname a 2 → el bit se intercambia
  (surname lo lleva, company no) en VAR, TEXT y EDIT; surname a 1 → sin el bit (el 0x1 no deja huella en +0x00 ni en
  +0x44). Es el UPSHIFT de la columna del repositorio, y solo lo mira LIKEVAR: sin él (`DATATYPE CHAR(25)` sobre
  company), 0x90000000.
- **Escrito, no cuenta.** `UPSHIFT` en un VAR de página con LIKEVAR no compila (ya se sabía) ni en un TEXT con
  LIKEVAR («Actual upshift(UPSHIFT). Expecting control, end», entre LIKEVAR y TAGS, donde lo escribía Hubble); en un
  EDIT con `UPSHIFT` / `LIKEVAR` compila, pero el bit lo decide la columna igual (sobre surname, sin bit; sobre
  company, con él).
  `DATATYPE CHAR(25)` / `UPSHIFT` no compila en un EDIT (UPSHIFT va delante de DATATYPE, como escribe Hubble).
- **Cómo se usa.** El lector del `.crf` (`repositorio._huellas_crf`, antes `_mascaras_crf`) saca de cada columna Char
  la máscara y el UPSHIFT (`Catalogo.upshifts`, `upshift(c)`); en otros tipos, «no se sabe» (no medido). Si la
  columna hereda de otro registro (ALMAFAC: proveedores.apellidos de tipos_fijos.apellidos), el UPSHIFT vale si el
  suyo y el del padre coinciden (en los kits, siempre); si no, «no se sabe». Antes de declarar los FOB, la pasada
  `upshifts_likevar` apunta por cada FOB si los TEXT y EDIT de formulario y los VAR de página con LIKEVAR llevan el
  bit (con y sin él en distintos controles → NoSoportado, como con dos máscaras). `tipo_de_columna` pasa ese bit a
  `Catalogo.buscar`, que solo deja las que lo tienen igual en el `.crf`; con el bit, una con el UPSHIFT sin saber no
  vale (sería elegir a ciegas); sin él, sigue valiendo como antes (ALMAFAC eticli: clientes.direccion, que el `.crf`
  no aclara) y, si es Char, se avisa («el LIKEVAR no lleva UPSHIFT y el .crf no dice si esa columna lo es»); el aviso de «una de n columnas» dice «y UPSHIFT» cuando filtró
  por él. Sin `.crf` legible y con el bit exigido, NoSoportado; sin el bit, se elige como antes y se avisa con las candidatas («sin el .crf no se sabe qué columnas lo son; candidatas: customers.company, customers.surname…»). La vuelta `tb` lo enseñó: `compilados/tablas-86x64` tenía stock.dbs sin stock.crf y las 4 variantes sobre surname salían company; con el stock.crf del kit al lado (el que usa el compilador en samples), 46 de 46 idénticos. En un TEXT con
  LIKEVAR ya no se escribe UPSHIFT (es el de la columna), y un LIKEVAR con el bit sobre una variable que no es de
  columna (+0x32 del FOB ≠ −1) da NoSoportado: no hay de dónde copiarlo ni forma de escribirlo.
- **Lo que no se sabe:** si el UPSHIFT de una columna que hereda es el suyo o el del padre cuando no coinciden
  (ningún `.crf` del kit los tiene distintos); qué significa el 0x1 de +0x24 (no deja huella en el control); si un
  DROPEDIT u otro control con LIKEVAR copia el bit (no se mira: solo TEXT, EDIT y VAR de página).

## 2026-11-02 — La base de datos de un repositorio: +0x14 de la cabecera del `.crf` (INDODIC UpkeepDict)

INDODIC/UpkeepDict dice `REPOSITORY indodic`, pero la carpeta de la base es INDONESI.DBS (junto a INDODIC.CRF):
`repositorio.encontrar` buscaba `indodic.dbs` y el módulo daba NoSoportado («hace falta el repositorio»). El nombre de
`REPOSITORY` es el del `.crf` (el compilador lee el `.crf`: las baterías del 2026-10-31 y de hoy compilan con copias
cambiadas), y el `.crf` dice qué base describe: el u32 de +0x14 de la cabecera es el registro de la tabla de nombres
(la primera, desde 0x40; el registro 0 es el nombre del repositorio) con el nombre de la base. En los 22 `.crf` de los
kits con un `.dbs` al lado, siempre el de esa carpeta: ALMAFAC.CRF → 3 «almafac», stock.crf → 3 «STOCK», agenda.crf →
6 «AGENDA» e INDODIC.CRF → 3 «indonesi» (los dos `columninfo.CRF` de dbmanager, sin `.dbs`, llevan 0xFFFFFFFF: ninguna
base).

- **Cómo se usa.** `encontrar(nombre)` busca primero `<nombre>.dbs`, como antes; si no está, `<nombre>.crf` en las
  mismas carpetas y, a su lado, la carpeta de su base (`base_del_crf`). El `.crf` de una carpeta `.dbs` (`crf_de`, para
  la máscara, el UPSHIFT y las cadenas de valores) es el del mismo nombre o, si no lo hay, el único cuya base es esa
  carpeta (con dos, ninguno).
- **Lo que no se sabe:** qué es el u32 de +0x2C de la cabecera (4 en INDODIC.CRF, «indodic», y en stock.crf, «local»;
  8 en agenda.crf); no se ha compilado un módulo con una carpeta `.dbs` que no sea la del `.crf` (no hace falta: la
  vuelta del módulo compila con los ficheros del proyecto tal cual).

## 2026-11-03 — Formato 0x3211: FOR, FCT y PCT de un Cosmos más antiguo (32 bits)

El u32 de +0x08 de la cabecera es la versión del formato: 0x7230 en todos los `.omd` de los kits 8.2–8.6 (x86 y x64,
extraídos y compilados aquí). Los de versión 0x3211 son de un Cosmos más antiguo, solo de 32 bits: todas sus secciones
miden como en 8.6 de 32 bits salvo `FOR` (28 bytes frente a 32), `FCT` y `PCT` (112 frente a 120). `contenedor` lee la
versión (`Omd.version`) y, en 0x3211, exige esos tres tamaños (`TAMANOS_3211`) y los de 32 bits en lo demás; otra
versión es un error. No hay compilador de esa versión: **no hay vuelta**, y toda salida de un `.omd` 0x3211 lleva el
aviso fijo «formato 0x3211: sin compilador de esta versión, no comprobado con vuelta» (el primero de los avisos).

Los registros se pasan a la disposición de 8.6 de 32 bits (`descompilador.de_3211`) y de ahí se expanden con `MAPA_32`
como siempre. El mapa sale de comparar campo a campo con los registros de 8.6 de 32 bits (kits x86 y lo compilado
aquí); un campo entra solo si cuadra en **todos** los registros de los módulos 0x3211 vistos:

- **`FOR`**: los 7 primeros u32 de 8.6, en el mismo orden (+0x08 control raíz, sin padre; +0x0C la primera `FTA`;
  +0x10 las variables, ningún `FOB` con clase de menú; +0x14 los menús, todos con la clase de menú implícita; +0x18
  el `default menu`, siempre uno de los de +0x14). El +0x1C de 8.6, que falta, es siempre 0 en 8.6.
- **`FCT` y `PCT`**: +0x00 (bits), +0x04 siguiente, +0x08 primer hijo y +0x0C padre (el árbol cuadra: cada hijo tiene
  por padre al que lo apunta) y +0x10 (tipo y `DATATYPE`) como en 8.6. El u32 de +0x14 junta dos campos de 8.6: en el
  u16 bajo, el de +0x14 (0, o 0xFFFF en un `MENU`; en 0x3211 siempre 0) y en el alto el número de control de +0x18
  (1..n en el orden de los registros, en 8.6 y en 0x3211). De +0x18 en adelante, cada u32 es el de 8.6 cuatro bytes
  más allá: +0x18 nombre (posición en `IDE` / 4 más 1, siempre un nombre que existe; en el formulario, como en 8.6,
  la `MOP` de su menú), +0x1C/+0x20 geometría, +0x24 número o comando, +0x28 bits, +0x2C `LABEL` (`SVL`), +0x30 y
  +0x34 colores, +0x38 `TAGS` o `FOCUS`, +0x40 la `CLA` del formulario o el binario de `SVL`, +0x48 `VARIABLE`
  (`FOB` o `FTA`), +0x4C `COMMENT` (en una página, `MARGIN`), +0x50 la `ECL` del control, +0x60/+0x64 bits y columnas
  de las listas, +0x68 `CHECKMETHOD`. El +0x74 de 8.6 (siempre 0) no está.
- **Diferencias vistas:** la raíz de una página (`PCT` sin padre) no lleva `ECL` en +0x50 (en 8.6 sí); la raíz no la
  lee, así que no cambia nada.
- **Sin comprobar (NoSoportado si traen algo):** los u32 que en 0x3211 han salido siempre a 0 (`FCT` +0x54, +0x58,
  +0x5C, donde iría el `FORMAT` de 8.6, y +0x6C; `PCT` de +0x54 al final), el u16 bajo de +0x14 (el 0xFFFF de un
  `MENU`) y cualquier registro de otro largo. Las reglas de 8.6 siguen mandando sobre lo que se lee: bits de estilo
  sin descifrar, colores en la raíz de una página, etc. dan NoSoportado como en 8.6.
- **Geometría:** `_declarados` salta +0x1C y +0x20 del registro 0x3211 sin pasar (en 8.6 de 32 bits, +0x20 y +0x24).
- **Pruebas** (`tests/test_formato_3211.py`, sin datos de módulos 0x3211): registros sintéticos, y los `.omd` de 32
  bits de los kits (formularios, páginas, controles, listas, menús, tablas, grupos y samples) recortados a mano al
  formato 0x3211 (`a_3211`, la inversa): los que no tienen nada en los campos sin comprobar dan el mismo fuente con el
  aviso delante (EjDisableAceleradores, `POSITION 256 39`, vigila la geometría); los demás, NoSoportado.
- **Lo que queda (sin reglas comprobadas en 8.6; NoSoportado):** bits de controles de página que el lector de 8.6 no
  conoce para ese tipo (VAR, BITMAP, BOX, TEXT), `BACKGROUND`/`FOREGROUND` en la raíz de una página, métodos de
  `Object` con la clase escrita (en 8.6 no compila), clases que no son formulario con algo en `CLA` +0x40, constantes
  incluidas con dos valores, nombres sin hueco en `IDE` y propiedades sin nombre (sin investigar), y los módulos que
  necesitan el repositorio (`syscolumns.dat`) para `x as tabla.columna`.

## Preguntas abiertas

- `FOCUS` seguido de `NOTABSTOP` en un control no compila («Actual notabstop(NOTABSTOP). Expecting control, end»,
  batería `fct.py` cur_b_todo); Hubble escribe FOCUS delante. Ningún módulo del kit lleva los dos: comprobar el orden
  bueno con una variante `NOTABSTOP` / `FOCUS` cuando haya huecos.

- Comprobar en todo el corpus lo de las referencias, la lista de `STM` y el árbol de `REF`; qué son los tipos de nodo de `REF` (0x7000010, 0x704f090, 0x7022020, 0x7080021, 0x7040022, 0x7086020, 0x7050010…).
- Qué hay en los registros binarios de `SVL` según su tipo, y qué marca el tope de sus bloques.
- Qué hay en los 32 bytes de 0x2C y qué guarda cada registro de las secciones fijas (sobre todo `STM`, `PRO` y `REF`: ahí debería estar el código).
- Si los `.omd` de otra versión llevan la misma cabecera, y de cuántos bits son: `hubble secciones` lo dice.

# Batería de compilación diferencial

Programas COOL mínimos, cada uno a un solo cambio del programa base (`b_base`):

```
main
objects begin
    a as integer
end
begin
    a = 1;
end
```

Al comparar el `.omd` de cada variante con el del programa base se ve qué codifica ese
cambio. Los programas están en `genera.py`. Si se añaden, conviene ponerlos al final para
que los ya hechos no cambien de hueco.

## Huecos

`cosmakecon` solo compila módulos registrados en el `.prj` (si no, da
`Unregistered module X`), y el `.prj` es binario. Por eso cada programa ocupa un
**hueco**: el nombre de un módulo de `samples.prj` (el proyecto de ejemplos del kit 8.6
x64), en una copia aparte del proyecto.

Sirven como huecos los módulos que cumplen las tres condiciones:
- compilan solos;
- tienen `main`;
- ni incluyen ni son incluidos por otro módulo.

Hay 274. Un hueco que es una librería (`COSMOSJAVA`, `Cosqrdll`) interfiere con el
módulo que la incluye.

`manifiesto.tsv` dice qué programa ocupa cada hueco. El nombre del hueco aparece en el
`.omd`, y eso es todo el ruido que mete: dos programas con el mismo código en huecos
distintos solo difieren en `IDE`, en `STR` y en un u32 de `REF[0]`. En los literales
cambia además `OBJ[0]+0x10`.

## Uso

```sh
# en el Mac: generar
python3 -I lab/bateria/genera.py <salida> <huecos.txt>
# en x-server: compilar lo que no tenga .omd (en tandas de 20; si una falla, uno a uno)
~/hubble-lab/compila_lote.sh ~/hubble-lab/bateria/propia /wine/drive_c/hubble/propia samples.prj
```

`compila_lote.sh` escribe `informe-<dir>.tsv` (`ok`, `ok-solo` o `fallo` con el error).
Un módulo suelto se compila con `-smd NOMBRE`, **sin** extensión: con `.SMD` da
`Unregistered module`.

**32 bits** (2026-10-29): con `LAB_IMAGEN=hubble-lab:32a LAB_COSMOS='~/hubble-lab/cosmos32'` y un `.prj` de 32
bits (el `samples.prj` del kit x86, en `~/hubble-lab/bateria32/propia`). Los huecos de 64 sirven también: los
mismos nombres están en el `samples.prj` x86 (los de samples que solo están en el de 64 dan `Unregistered module`).
La vuelta completa en 32 bits: `ARQ=32 VUELTA_TMP=… HUBBLE_KITS=… lab/bateria/vuelta_todo.sh`; compila primero los
mismos fuentes en 32 bits, en `kits/compilados/<x>-86x86`.

**Los proyectos del kit, enteros** (2026-11-01): la entrada `proy` de `vuelta_todo.sh` (`SOLO=proy`; `proy32` con
`ARQ=32`) hace la vuelta de los 121 módulos de los proyectos del kit x64 (17 proyectos) o x86 (16), cada módulo
compilado en su propio proyecto: su `.prj` (que es de una arquitectura), sus librerías (los módulos que no cuentan van
con su fuente original a los dos lados) y su repositorio (`.dbs` y `.crf`). En x-server, cada proyecto sin fuentes ni
compilados está en `~/hubble-lab/trabajo/<P>` (x64) y `~/hubble-lab/trabajo32/projects/<P>` (x86). Los `.omd` de
partida, los mismos fuentes compilados aquí, en `kits/compilados/proyectos-86x64/<P>` y `proyectos-86x86/<P>`. Un
resumen por proyecto queda en `$VUELTA_TMP/resumen-proy.txt` (o `-proy32`), y al final sale el total. mail (módulos en
subcarpetas) sigue en su entrada `mail` y LookAndFeel7 no tiene módulos.

**La tanda se repite con el fuente original de los que no compilan** (2026-11-01): el compilador acumula en cada
tanda de `-smd` los `CMD` (y `ICO`, `FON`) de sus módulos, así que un descompilado que no compila dejaba a sus vecinos
con registros de menos (`CMD: 17 → 16 registros`) sin ser culpa suya. `vuelta_remota.sh` baja el informe a
`$VUELTA_TMP/informe-<nombre>.tsv`; `vuelta.py caidos` repone el fuente original de los `fallo` que cuentan (el
descompilado queda en `vuelta-<nombre>/caidos/`) y escribe `caidos-<nombre>.txt`; `vuelta_de` vuelve a compilar la
vuelta entera y `vuelta.py compara` quita los caídos, que siguen contando como «el descompilado no compila».

## Resultados (2026-10-27, `hubble-lab:3`, Cosmos 8.6 x64)

- **Batería:** 91 programas, 91 `.omd`.
  - Un error de COOL que salió por el camino: `not` tiene más prioridad que `>`.
    `if not a > 1` da `undefined operator NOT for class Integer`.
- **`samples` del kit:** 447 fuentes, de las que el kit solo trae 4 compiladas. Ahora
  hay 415 `.omd`, es decir, 411 pares fuente/compilado nuevos.
  - Los 32 que faltan no están registrados en `samples.prj`.
  - Con `-all` el compilador se cae a mitad (fallo de página en `cosmakecon+0x6fadb`,
    tras 110 módulos). En tandas con `-smd` compilan todos los registrados. No sé cuál
    de ellos tumbaba el `-all`.
- Todo está en el Mac, fuera de git: `kits/compilados/bateria-86x64/` (fuentes, `.omd` y
  manifiesto) y `kits/compilados/samples-86x64/`.

#!/bin/bash
# Vuelta completa de la batería y de samples. Ejecutar desde la raíz del repo, con
# VUELTA_TMP y HUBBLE_KITS puestos; SOLO=bat|sam|form|list|ctrl|dat|tab|menu|fct|llam|pag|tb|var|ctb|evt|gru|com|cmd|alma|bmaps|agen|actx|cla|nif|calc|outl|lkv|mail|proy
# para hacer solo uno. proy: los 121 módulos de los proyectos del kit, cada uno en su proyecto (al final). lkv: batería likevar.py, compilada en el proyecto ALMAFAC (necesita su .crf: ver likevar.py).
# Referencia justa: el fuente ORIGINAL compilado igual que el descompilado (mismo script,
# misma carpeta, misma ruta), porque el contexto de compilación cambia el .omd.
# ARQ=32: lo mismo en 32 bits (hubble-lab:32a, kit 8.6 x86). Los .omd de partida son los mismos fuentes
# compilados en 32 bits, en <compilados>/<x>-86x86; si no están, se compilan primero.
T=${VUELTA_TMP:?pon VUELTA_TMP (carpeta de trabajo)}
K=${HUBBLE_KITS:?pon HUBBLE_KITS}
R=$(dirname "$0")
if [ "$ARQ" = 32 ]; then
  export LAB_IMAGEN=hubble-lab:32a LAB_COSMOS='~/hubble-lab/cosmos32'  # la ~, en x-server
fi
vuelta_de() {  # <nombre> <dir .omd de partida> <dir fuentes .SMD> <ruta Windows> <proyecto en x-server> [deps]
  local NOMBRE=$1 OMDS=$2 FUENTES=$3 RUTA=$4 PROY=$5 DEPS=$6
  # los .omd de partida: si no están, los mismos fuentes compilados aquí
  [ -d "$OMDS" ] || bash "$R/vuelta_remota.sh" "$FUENTES" "orig$NOMBRE" "$RUTA" "$OMDS" "$PROY"
  echo "######## $NOMBRE"
  rm -rf "$T/vuelta-$NOMBRE" "$T/ref-$NOMBRE-src" "$T/caidos-$NOMBRE.txt" "$T/informe-$NOMBRE.tsv"
  uv run python -I lab/bateria/vuelta.py descompila "$OMDS" "$FUENTES" "$T/vuelta-$NOMBRE"
  # los originales de los mismos módulos
  mkdir -p "$T/ref-$NOMBRE-src"
  uv run python -I -c "
import shutil, sys
from pathlib import Path
d, f, o = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
hechos = {p.name.lower() for p in d.iterdir() if p.suffix.lower() == '.smd'}
for p in f.iterdir():
    if p.name.lower() in hechos: shutil.copy(p, o / p.name)
" "$T/vuelta-$NOMBRE" "$FUENTES" "$T/ref-$NOMBRE-src"
  # Proyecto entero (DEPS): los módulos que no se descompilan van con su fuente original a los dos lados,
  # porque otros los incluyen; solo cuentan los descompilados.
  ls "$T/ref-$NOMBRE-src" | sed 's/\.[^.]*$//' > "$T/cuentan-$NOMBRE.txt"
  if [ -n "$DEPS" ]; then
    uv run python -I -c "
import shutil, sys
from pathlib import Path
f, *ds = map(Path, sys.argv[1:])
hechos = {p.name.lower() for p in ds[0].iterdir()}
for p in f.iterdir():
    if p.suffix.lower() == '.smd' and p.name.lower() not in hechos:
        for d in ds: shutil.copy(p, d / p.name)
" "$FUENTES" "$T/ref-$NOMBRE-src" "$T/vuelta-$NOMBRE"
  fi
  bash "$R/vuelta_remota.sh" "$T/ref-$NOMBRE-src" "ref$NOMBRE" "$RUTA" "$T/ref-$NOMBRE-omd" "$PROY"
  bash "$R/vuelta_remota.sh" "$T/vuelta-$NOMBRE" "$NOMBRE" "$RUTA" "$T/vuelta-$NOMBRE-omd" "$PROY" "~/hubble-lab/vuelta/informe-ref$NOMBRE.tsv"
  # Un descompilado que no compila le quita a su tanda lo que aporta (el compilador acumula CMD, ICO y FON por tanda
  # de -smd; ALMAFAC3: 12 módulos con «CMD: 17 → 16 registros» por AUXILIAR e INICIO): se repite la tanda con su
  # fuente original para medir a los demás con el mismo contexto. El caído sigue contando como «no compila».
  CAIDOS=$(uv run python -I lab/bateria/vuelta.py caidos "$T/informe-$NOMBRE.tsv" "$T/vuelta-$NOMBRE" "$FUENTES" "$T/cuentan-$NOMBRE.txt" "$T/caidos-$NOMBRE.txt")
  if [ -n "$CAIDOS" ]; then
    echo "fallo en la tanda: $CAIDOS (se repite con su fuente original; siguen contando como «no compila»)"
    bash "$R/vuelta_remota.sh" "$T/vuelta-$NOMBRE" "$NOMBRE" "$RUTA" "$T/vuelta-$NOMBRE-omd" "$PROY" "~/hubble-lab/vuelta/informe-ref$NOMBRE.tsv"
  fi
  uv run python -I lab/bateria/vuelta.py compara "$T/ref-$NOMBRE-omd" "$T/vuelta-$NOMBRE-omd" "$T/cuentan-$NOMBRE.txt" "$T/caidos-$NOMBRE.txt"
}
for c in "bat|$K/compilados/bateria-86x64|$K/compilados/bateria-86x64|/wine/drive_c/hubble/propia|~/hubble-lab/bateria/propia" \
         "sam|$K/compilados/samples-86x64|$K/extraido/86x64/Cosmos8.6x64eval/samples|/wine/drive_c/CosmosVersion/Cosmos8.6x64eval/samples|~/hubble-lab/bateria/samples" \
         "form|$K/compilados/formularios-86x64|$K/compilados/formularios-86x64|/wine/drive_c/hubble/formularios|~/hubble-lab/bateria/propia" \
         "list|$K/compilados/listas-86x64|$K/compilados/listas-86x64|/wine/drive_c/hubble/listas|~/hubble-lab/bateria/propia" \
         "ctrl|$K/compilados/controles-86x64|$K/compilados/controles-86x64|/wine/drive_c/hubble/controles|~/hubble-lab/bateria/propia" \
         "dat|$K/compilados/datos-86x64|$K/compilados/datos-86x64|/wine/drive_c/hubble/datos|~/hubble-lab/bateria/propia" \
         "tab|$K/compilados/tabs-86x64|$K/compilados/tabs-86x64|/wine/drive_c/hubble/tabs|~/hubble-lab/bateria/propia" \
         "menu|$K/compilados/menus-86x64|$K/compilados/menus-86x64|/wine/drive_c/hubble/menus|~/hubble-lab/bateria/propia" \
         "fct|$K/compilados/fct-86x64|$K/compilados/fct-86x64|/wine/drive_c/hubble/fct|~/hubble-lab/bateria/propia" \
         "llam|$K/compilados/llamadas-86x64|$K/compilados/llamadas-86x64|/wine/drive_c/hubble/llamadas|~/hubble-lab/bateria/propia" \
         "pag|$K/compilados/paginas-86x64|$K/compilados/paginas-86x64|/wine/drive_c/hubble/paginas|~/hubble-lab/bateria/propia" \
         "tb|$K/compilados/tablas-86x64|$K/compilados/tablas-86x64|/wine/drive_c/CosmosVersion/Cosmos8.6x64eval/samples|~/hubble-lab/bateria/samples" \
         "var|$K/compilados/variables-86x64|$K/compilados/variables-86x64|/wine/drive_c/CosmosVersion/Cosmos8.6x64eval/samples|~/hubble-lab/bateria/samples" \
         "ctb|$K/compilados/codtablas-86x64|$K/compilados/codtablas-86x64|/wine/drive_c/CosmosVersion/Cosmos8.6x64eval/samples|~/hubble-lab/bateria/samples" \
         "evt|$K/compilados/evtablas-86x64|$K/compilados/evtablas-86x64|/wine/drive_c/CosmosVersion/Cosmos8.6x64eval/samples|~/hubble-lab/bateria/samples" \
         "gru|$K/compilados/grupos-86x64|$K/compilados/grupos-86x64|/wine/drive_c/hubble/grupos|~/hubble-lab/bateria/propia" \
         "com|$K/compilados/comentarios-86x64|$K/compilados/comentarios-86x64|/wine/drive_c/hubble/comentarios|~/hubble-lab/bateria/propia" \
         "cmd|$K/compilados/comandos-86x64|$K/compilados/comandos-86x64|/wine/drive_c/hubble/comandos|~/hubble-lab/bateria/propia" \
         "alma|$K/compilados/almafac-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/ALMAFAC|/wine/drive_c/CosmosVersiones/cosmos742_x64/projects/ALMAFAC|~/hubble-lab/trabajo/ALMAFAC|ALMAFAC.PRJ|deps" \
         "bmaps|$K/compilados/bmaps-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/prjbmapsdll|/wine/drive_c/hubble/bmaps|~/hubble-lab/trabajo/prjbmapsdll|PRJBMAPSDLL.PRJ|deps" \
         "agen|$K/compilados/agenda-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/AGENDA|/wine/drive_c/hubble/agenda|~/hubble-lab/trabajo/AGENDA|AGENDA.PRJ|deps" \
         "actx|$K/compilados/activex-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/ActiveX|/wine/drive_c/hubble/activex|~/hubble-lab/trabajo/ActiveX|ActiveX.prj|deps" \
         "cla|$K/compilados/clases-86x64|$K/compilados/clases-86x64|/wine/drive_c/hubble/clases|~/hubble-lab/bateria/samples" \
         "nif|$K/compilados/nif2-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/NIF|/wine/drive_c/hubble/nif|~/hubble-lab/trabajo/NIF|NIF.PRJ|deps" \
         "calc|$K/compilados/calcalg-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/CalcALG|/wine/drive_c/hubble/calcalg|~/hubble-lab/trabajo/CalcALG|CalcALG.prj|deps" \
         "outl|$K/compilados/outlook-86x64|$K/extraido/86x64/Cosmos8.6x64eval/projects/OutlookActiveX|/wine/drive_c/hubble/outlook|~/hubble-lab/trabajo/OutlookActiveX|OutlookActiveX.PRJ|deps" \
         "lkv|$K/compilados/likevar-86x64|$K/compilados/likevar-86x64|/wine/drive_c/CosmosVersiones/cosmos742_x64/projects/ALMAFAC|~/hubble-lab/trabajo/ALMAFAC|ALMAFAC.PRJ"; do
  IFS='|' read -r NOMBRE OMDS FUENTES RUTA PROY PRJ DEPS <<< "$c"
  export VUELTA_PRJ=${PRJ:-samples.prj}
  [ -n "$SOLO" ] && [ "$SOLO" != "$NOMBRE" ] && continue
  if [ "$ARQ" = 32 ]; then
    OMDS=${OMDS/-86x64/-86x86}; FUENTES=${FUENTES/86x64\/Cosmos8.6x64eval/86x86\/Cosmos8.6eval}
    PROY=${PROY/hubble-lab\/bateria\//hubble-lab/bateria32/}; PROY=${PROY/hubble-lab\/trabajo\//hubble-lab/trabajo32/projects/}
    NOMBRE=${NOMBRE}32
  fi
  vuelta_de "$NOMBRE" "$OMDS" "$FUENTES" "$RUTA" "$PROY" "$DEPS"
done
# mail: los módulos van en subcarpetas (Includes, PROBES, PROGRAMS…): se compila el árbol con -all
if [ -z "$SOLO" ] || [ "$SOLO" = mail ]; then
  if [ "$ARQ" = 32 ]; then M=$K/extraido/86x86/Cosmos8.6eval/projects/mail; N=mail32; else M=$K/extraido/86x64/Cosmos8.6x64eval/projects/mail; N=mail; fi
  bash "$R/vuelta_arbol.sh" "$M" "$N" /wine/drive_c/hubble/mail CLIENTS.PRJ "$T"
fi
# proy: los 121 módulos de los proyectos del kit (x64 o x86), cada uno compilado en su propio proyecto (su .prj, sus
# librerías y su repositorio). mail va aparte (subcarpetas) y LookAndFeel7 no tiene módulos. Los .omd de partida, los
# mismos fuentes compilados aquí, en <compilados>/proyectos-86x64/<P> (o -86x86). En x-server, el proyecto (.prj,
# .ini, .dbs, .crf, iconos…) está en ~/hubble-lab/trabajo/<P> (o trabajo32/projects/<P>).
if [ -z "$SOLO" ] || [ "$SOLO" = proy ]; then
  if [ "$ARQ" = 32 ]; then
    E=$K/extraido/86x86/Cosmos8.6eval/projects; N=proy32; TR='~/hubble-lab/trabajo32/projects'; C=$K/compilados/proyectos-86x86
  else
    E=$K/extraido/86x64/Cosmos8.6x64eval/projects; N=proy; TR='~/hubble-lab/trabajo'; C=$K/compilados/proyectos-86x64
  fi
  mkdir -p "$T"; : > "$T/resumen-$N.txt"
  for d in "$E"/*/; do
    d=${d%/}; P=$(basename "$d")
    export VUELTA_PRJ=$(ls "$d" | grep -i '\.prj$' | head -1)
    { [ -n "$VUELTA_PRJ" ] && ls "$d" | grep -qi '\.omd$'; } || continue
    vuelta_de "$N-$P" "$C/$P" "$d" "/wine/drive_c/hubble/proy/$P" "$TR/$P" deps | tee -a "$T/resumen-$N.txt"
  done
  echo "######## $N (todos los proyectos)"
  uv run python -I -c "
import re, sys
a = b = c = n = 0
for m in re.finditer(r'^(\d+) de (\d+) idénticos.*?; (\d+) más.*?; (\d+) distintos', open(sys.argv[1]).read(), re.M):
    a, n, b, c = a + int(m[1]), n + int(m[2]), b + int(m[3]), c + int(m[4])
print(f'{a} de {n} idénticos byte a byte; {b} más idénticos salvo punteros de memoria; {c} distintos')
" "$T/resumen-$N.txt"
fi

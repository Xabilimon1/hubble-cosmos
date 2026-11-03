#!/bin/bash
# Uso: compila_lote.sh <dir proyecto en host> <ruta Windows-montaje en el contenedor> <fichero .prj> [informe]
# Compila en tandas de 20 los .SMD sin .OMD; si una tanda falla, uno a uno. Informe en <dir>/../informe-<nombre>.tsv
# Con [informe] (el de otra compilación), los módulos que allí salieron «ok-solo» se compilan
# solos también aquí: la tanda acumula ICO/FON/CMD, y así las dos compilaciones tienen el
# mismo contexto (el compilador a veces se cae en una tanda por un fuente concreto).
# LAB_IMAGEN y LAB_COSMOS: imagen y kit (por defecto, 64 bits; en 32, hubble-lab:32a y ~/hubble-lab/cosmos32).
P=$1; R=$2; PRJ=$3; OTRO=$4; N=$(basename "$P"); INF=$(dirname "$P")/informe-$N.tsv
corre() { timeout 300 docker run --rm -v "${LAB_COSMOS:-$HOME/hubble-lab/cosmos}":/cosmos:ro -v "$P":"$R" -w "$R" "${LAB_IMAGEN:-hubble-lab:3}" 'Z:\cosmos\bin\cosmakecon.exe' -prj "$PRJ" "$@" -err errores.txt >/dev/null 2>&1; }
pendientes() { for s in "$P"/*.[sS][mM][dD]; do b=$(basename "$s"); b=${b%.*}; ls "$P" | grep -i -q "^$b\.omd$" || echo "$b"; done; }
solo_en_otro() { [ -n "$OTRO" ] && grep -i -q -P "^$1\tok-solo" "$OTRO"; }
mapfile -t L < <(pendientes)
echo "pendientes: ${#L[@]}"
: > "$INF"
for ((i=0; i<${#L[@]}; i+=20)); do
  T=("${L[@]:i:20}"); args=(); for m in "${T[@]}"; do solo_en_otro "$m" || args+=(-smd "$m"); done
  [ ${#args[@]} -gt 0 ] && corre "${args[@]}"
  for m in "${T[@]}"; do
    if ls "$P" | grep -i -q "^$m\.omd$"; then printf "%s\tok\n" "$m" >> "$INF"; continue; fi
    rm -f "$P/errores.txt"; corre -smd "$m"
    if ls "$P" | grep -i -q "^$m\.omd$"; then printf "%s\tok-solo\n" "$m" >> "$INF"
    else printf "%s\tfallo\t%s\n" "$m" "$(tr -d '\r' < "$P/errores.txt" 2>/dev/null | tr '\n' ' ' | cut -c1-200)" >> "$INF"; fi
  done
done
echo "hecho: $(cut -f2 "$INF" | sort | uniq -c | tr '\n' ' ')"

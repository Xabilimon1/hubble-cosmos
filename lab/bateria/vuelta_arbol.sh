#!/bin/bash
# Vuelta de un proyecto con los módulos en subcarpetas (mail: Includes, PROBES, PROGRAMS…), que compila_lote.sh no
# recorre: se compila el árbol entero con `-all`, se descompila cada módulo en su sitio, se vuelve a compilar y se
# comparan módulo a módulo. Los que no se descompilan se quedan con su fuente (son dependencias y no cuentan).
# Uso: vuelta_arbol.sh <árbol local del proyecto> <nombre> <ruta Windows en el contenedor> <fichero .prj> <dir de trabajo>
# LAB_IMAGEN y LAB_COSMOS: imagen y kit (32 bits: hubble-lab:32a y ~/hubble-lab/cosmos32).
set -e
FUENTES=$1; NOMBRE=$2; RUTA=$3; PRJ=$4; T=$5
R=$(dirname "$0")
compila() {  # <dir local con el árbol> <nombre remoto> <dir local de salida de los .omd>
  ssh x-server-vpn "rm -rf ~/hubble-lab/vuelta/$2 && mkdir -p ~/hubble-lab/vuelta/$2"
  ( cd "$1" && COPYFILE_DISABLE=1 tar --no-xattrs -czf - . ) | ssh x-server-vpn "tar -xzf - -C ~/hubble-lab/vuelta/$2"
  ssh x-server-vpn "cd ~/hubble-lab/vuelta/$2 && timeout 900 docker run --rm -v ${LAB_COSMOS:-\$HOME/hubble-lab/cosmos}:/cosmos:ro \
    -v \$PWD:'$RUTA' -w '$RUTA' ${LAB_IMAGEN:-hubble-lab:3} 'Z:\\cosmos\\bin\\cosmakecon.exe' -prj '$PRJ' -all -err errores.txt \
    >/dev/null 2>&1; tr -d '\r' < errores.txt 2>/dev/null | grep -i error | head -5 || true"
  rm -rf "$3"; mkdir -p "$3"
  ssh x-server-vpn "cd ~/hubble-lab/vuelta/$2 && find . -iname '*.omd' | tar -czf - -T -" | tar -xzf - -C "$3"
  ssh x-server-vpn "rm -rf ~/hubble-lab/vuelta/$2"
}
rm -rf "$T/$NOMBRE-a" "$T/$NOMBRE-b"
mkdir -p "$T/$NOMBRE-a"
( cd "$FUENTES" && COPYFILE_DISABLE=1 tar --no-xattrs --exclude='*.OMD' --exclude='*.omd' -cf - . ) | tar -xf - -C "$T/$NOMBRE-a"
cp -R "$T/$NOMBRE-a" "$T/$NOMBRE-b"
compila "$T/$NOMBRE-a" "$NOMBRE-a" "$T/$NOMBRE-a-omd"
uv run python -I -c "
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from hubble.descompilador import descompilar, NoSoportado
omd, b, cuentan = Path(sys.argv[1]), Path(sys.argv[2]), []
for f in sorted(omd.rglob('*')):
    if f.suffix.lower() != '.omd':
        continue
    d = b / f.parent.relative_to(omd)
    smd = next((p for p in d.iterdir() if p.stem.lower() == f.stem.lower() and p.suffix.lower() == '.smd'), None)
    if smd is None:
        continue
    try:
        texto = descompilar(f.read_bytes())
    except NoSoportado as e:
        print('no soportado', f.relative_to(omd), e)
        continue
    smd.write_bytes(texto.replace('\n', '\r\n').encode('cp1252'))
    cuentan.append(f.stem.lower())
Path(sys.argv[3]).write_text(''.join(c + '\n' for c in cuentan))
print(len(cuentan), 'descompilados')
" "$T/$NOMBRE-a-omd" "$T/$NOMBRE-b" "$T/cuentan-$NOMBRE.txt"
compila "$T/$NOMBRE-b" "$NOMBRE-b" "$T/$NOMBRE-b-omd"
for x in a b; do  # planos, para comparar por nombre
  rm -rf "$T/$NOMBRE-$x-plano"; mkdir -p "$T/$NOMBRE-$x-plano"
  find "$T/$NOMBRE-$x-omd" -iname '*.omd' -exec cp {} "$T/$NOMBRE-$x-plano/" \;
done
echo "######## $NOMBRE"
uv run python -I "$R/vuelta.py" compara "$T/$NOMBRE-a-plano" "$T/$NOMBRE-b-plano" "$T/cuentan-$NOMBRE.txt"

#!/bin/bash
# Compila con el compilador del laboratorio (8.6 x64) un proyecto entero del kit y trae los .omd.
# Uso: compila_proyecto.sh <carpeta local del proyecto> <dir local de salida>
# El proyecto se monta en C:\CosmosVersiones\cosmos742_x64\projects\<nombre>, la ruta con la que se compilaron
# los .omd del kit (va en STR), y se borran antes sus .omd para no traer los del kit.
set -e
LOCAL=$1; SALIDA=$2; NOMBRE=$(basename "$LOCAL")
PRJ=$(cd "$LOCAL" && ls | grep -i '\.prj$' | head -1)
DESTINO=/wine/drive_c/CosmosVersiones/cosmos742_x64/projects/$NOMBRE
ssh x-server-vpn "rm -rf ~/hubble-lab/trabajo/$NOMBRE && mkdir -p ~/hubble-lab/trabajo/$NOMBRE"
( cd "$LOCAL" && COPYFILE_DISABLE=1 tar --no-xattrs -czf - . ) | ssh x-server-vpn "tar -xzf - -C ~/hubble-lab/trabajo/$NOMBRE && find ~/hubble-lab/trabajo/$NOMBRE -maxdepth 1 -iname '*.omd' -delete"
ssh x-server-vpn "docker run --rm -v ~/hubble-lab/cosmos:/cosmos:ro -v ~/hubble-lab/trabajo/$NOMBRE:$DESTINO -w $DESTINO \
  hubble-lab:3 'Z:\\cosmos\\bin\\cosmakecon.exe' -prj $PRJ -all -err errores.txt >/dev/null 2>&1; echo salida \$?; \
  head -c 600 ~/hubble-lab/trabajo/$NOMBRE/errores.txt 2>/dev/null || true"
rm -rf "$SALIDA"; mkdir -p "$SALIDA"
ssh x-server-vpn "cd ~/hubble-lab/trabajo/$NOMBRE && tar -czf - \$(ls | grep -i '\.omd$')" | tar -xzf - -C "$SALIDA"
ls "$SALIDA" | wc -l

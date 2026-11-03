#!/bin/bash
# Uso: vuelta_remota.sh <dir local con .SMD> <nombre> <ruta Windows en el contenedor> <dir local de salida .OMD> <proyecto original en x-server>
# Del proyecto original se copia todo salvo fuentes y compilados (.prj, .ini con los recursos…) y su repositorio
# (carpetas .dbs) y sus iconos (carpeta icons: OutlookActiveX). LAB_IMAGEN/LAB_COSMOS: imagen y kit (32 bits: hubble-lab:32a, ~/hubble-lab/cosmos32). VUELTA_PRJ: el .prj (por defecto samples.prj).
set -e
LOCAL=$1; NOMBRE=$2; RUTA=$3; SALIDA=$4; PROYECTO=$5; OTRO=$6  # OTRO: informe cuyos «ok-solo» se compilan solos
ssh x-server-vpn "rm -rf ~/hubble-lab/vuelta/$NOMBRE ~/hubble-lab/vuelta/informe-$NOMBRE.tsv; mkdir -p ~/hubble-lab/vuelta/$NOMBRE; cd $PROYECTO && find . -maxdepth 1 -type f ! -iname '*.smd' ! -iname '*.omd' ! -iname 'errores.txt' -exec cp {} ~/hubble-lab/vuelta/$NOMBRE/ \\; ; find . -maxdepth 1 -type d \\( -iname '*.dbs' -o -iname icons \\) -exec cp -r {} ~/hubble-lab/vuelta/$NOMBRE/ \\;"
( cd "$LOCAL" && COPYFILE_DISABLE=1 tar --no-xattrs -czf - ./*.SMD ./*.smd 2>/dev/null ) | ssh x-server-vpn "tar -xzf - -C ~/hubble-lab/vuelta/$NOMBRE"
ssh x-server-vpn "LAB_IMAGEN=${LAB_IMAGEN:-hubble-lab:3} LAB_COSMOS=${LAB_COSMOS:-~/hubble-lab/cosmos} ~/hubble-lab/compila_lote.sh ~/hubble-lab/vuelta/$NOMBRE '$RUTA' ${VUELTA_PRJ:-samples.prj} $OTRO | tail -1; grep -v -P '\tok' ~/hubble-lab/vuelta/informe-$NOMBRE.tsv | head -20 || true"
# el informe, al lado de la salida (quién compiló, quién solo y quién falló): la vuelta repite la tanda con los caídos
ssh x-server-vpn "cat ~/hubble-lab/vuelta/informe-$NOMBRE.tsv" > "$(dirname "$SALIDA")/informe-$NOMBRE.tsv"
rm -rf "$SALIDA"; mkdir -p "$SALIDA"
ssh x-server-vpn "cd ~/hubble-lab/vuelta/$NOMBRE && tar -czf - \$(ls | grep -i '\.omd$')" | tar -xzf - -C "$SALIDA"
ls "$SALIDA" | wc -l

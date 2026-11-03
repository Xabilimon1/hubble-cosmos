#!/bin/sh
# Dentro del contenedor: pantalla virtual :1, VNC con contraseña en el 5901 y el
# programa de Windows que se pase como argumentos (por defecto, register.exe).
set -eu
: "${VNC_CLAVE:?falta VNC_CLAVE}"
Xvfb :1 -screen 0 1024x768x24 -nolisten tcp &
sleep 1
mkdir -p "$HOME/.vnc"
x11vnc -storepasswd "$VNC_CLAVE" "$HOME/.vnc/clave" >/dev/null
x11vnc -display :1 -rfbport 5901 -rfbauth "$HOME/.vnc/clave" -forever -quiet -bg -o "$HOME/.vnc/x11vnc.log"
export DISPLAY=:1
if [ "$#" -eq 0 ]; then
    set -- 'Z:\cosmos\bin\register.exe'
fi
/usr/lib/wine/wine64 "$@"
/usr/lib/wine/wineserver -w

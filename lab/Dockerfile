# Laboratorio de Hubble: Wine (64 bits) para ejecutar el compilador de Cosmos
# (cosmakecon.exe) sobre programas de prueba. Corre en x-server (x86-64).
# El kit de Base 100 no va en la imagen: se monta en /cosmos (solo lectura).
FROM debian:trixie-slim

ENV WINEPREFIX=/wine WINEARCH=win64 WINEDEBUG=-all

# Todo en una capa: Wine, el prefijo, y enlaces duros entre las DLL que wineboot
# copia al prefijo y las de /usr/lib (son las mismas; si no, la imagen ocupa ~800 MB más)
RUN apt-get update \
 && apt-get install -y --no-install-recommends wine64 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m hubble && mkdir /wine && chown hubble /wine \
 && su hubble -s /bin/sh -c '/usr/lib/wine/wine64 wineboot --init && /usr/lib/wine/wineserver -w' \
 && hardlink --content /usr/lib/x86_64-linux-gnu/wine /wine

USER hubble
WORKDIR /trabajo
ENTRYPOINT ["/usr/lib/wine/wine64"]

# Laboratorio: el compilador de Cosmos con Wine en x-server

Para compilar programas de prueba con `cosmakecon.exe` (Windows x64) y comparar
los `.omd` que salen. Corre en x-server (Debian 13, x86-64) dentro de un contenedor,
para no instalar Wine en el sistema.

**Solo el kit de evaluación de Base 100 y programas de prueba propios.**

## Lo que hay en x-server (2026-10-27)

| | Ocupa |
|---|---|
| Imagen `hubble-lab:2` (Debian trixie-slim + Wine 10.0, `wine64`) | 1,39 GB |
| `~/hubble-lab/cosmos/`: `bin etc msg include drw template licences` del kit 8.6 x64 | 110 MB |
| `~/hubble-lab/trabajo/`: proyectos de prueba | < 1 MB |

La primera versión ocupaba 2,43 GB: `wineboot` copia al prefijo las DLL que ya están
en `/usr/lib`. Con `hardlink --content` en la misma capa se quedan en una sola copia.

## Montarlo

```sh
ssh x-server-vpn 'mkdir -p ~/hubble-lab/cosmos ~/hubble-lab/trabajo'
scp lab/Dockerfile x-server-vpn:hubble-lab/
cd kits/extraido/86x64/Cosmos8.6x64eval
COPYFILE_DISABLE=1 tar --no-xattrs -cf - bin etc msg include drw template licences \
  | ssh x-server-vpn 'tar -C ~/hubble-lab/cosmos -xf -'
ssh x-server-vpn 'cd ~/hubble-lab && docker build -t hubble-lab:2 .'
```

`COPYFILE_DISABLE=1` evita que el `tar` de macOS meta ficheros `._*` (la primera
copia llevó 399).

## Usarlo

`hubble-lab:3` es `hubble-lab:2` con la evaluación activada. Compila un proyecto entero
con `-all`; `-reb` y `-smd` sueltos no generan nada.

```sh
ssh x-server-vpn 'docker run --rm -v ~/hubble-lab/cosmos:/cosmos:ro \
  -v ~/hubble-lab/<proyecto>:/wine/drive_c/CosmosVersiones/cosmos742_x64/projects/NIF \
  -w /wine/drive_c/CosmosVersiones/cosmos742_x64/projects/NIF \
  hubble-lab:3 "Z:\\cosmos\\bin\\cosmakecon.exe" -prj NIF.PRJ -all -err errores.txt'
```

El `.omd` guarda en `STR` la ruta del fuente con la que se compiló. Los del kit se
compilaron en `C:\CosmosVersiones\cosmos742_x64\projects\NIF\`: montar el proyecto en esa
misma ruta (como arriba) deja la ruta igual que en el original.

Sintaxis de `cosmake` (Manual del Usuario p. 93): `[-prj f.prj] [-pf f] [-smd f.smd …] [-all] [-reb] [-com] [-grp etiqueta] [-err f] [-stu | -st]`.

| Opciones | Resultado (2026-10-27) |
|---|---|
| `-prj NIF.PRJ -all` (y con `-com`) | 9 `.omd`, salida 0 |
| `-prj NIF.PRJ -reb` | nada, salida 0 |
| `-prj NIF.PRJ -smd TEST1.SMD -com` | nada; 68 bytes en `errores.txt` |
| `-smd TEST1.SMD` | `Need Project File` |

## Estado

- **Activada el 2026-10-27** por Xabier, en modo «Automático» de `register.exe`
  (Cosmos 8.6 0.0, licencia 201): en línea, sin código ni correo.
- El registro **no toca el kit** (los 390 ficheros, con la misma huella SHA-256 antes y
  después). Escribe una sola clave en el registro de Wine, en `system.reg`:
  `HKLM\Software\Classes\RegUpdate.Registry1\00001IE`, valor binario `Register` (19 bytes).
  El resto de cambios en `system.reg` son del propio Wine (nombre del equipo, fechas).
- `hubble-lab:3` = `hubble-lab:2` + los tres `.reg` del contenedor de registro. Compila
  también con otro nombre de equipo (contenedor sin `--hostname`); `hubble-lab:2` sigue
  respondiendo `Unregistered licence` (salida 1).
- Copia de los `.reg` activados, fuera de git, en el Mac: `kits/registro-licencia/`.
- **Compilación contra el kit** (NIF, 8.6 x64): con el proyecto en la ruta original, los
  6 `.omd` que tienen pareja en el kit salen 82 bytes más cortos. La diferencia es la
  sección `A/ICO` (1 × 82), que el original tiene y el nuestro no.
  [hipótesis] El original se compiló con 7.4.2 (lo dice la ruta) o desde el IDE, y por eso
  lleva icono.
  Los demás bytes distintos aún no están comparados sección a sección. Pueden ser solo
  desplazamientos.
  Los `.omd` compilados están en el Mac, fuera de git: `kits/compilados/nif-86x64/`.

- **Batería de compilación diferencial** y compilación de `samples` (411 pares nuevos):
  `lab/bateria/README.md`.

## Activación de la evaluación (hecha el 2026-10-27)

`register.exe` tiene ventana, así que se usó una pantalla virtual temporal:
`Dockerfile.pantalla` (Xvfb + x11vnc sobre `hubble-lab:2`, unos 300 MB) y `pantalla.sh`.
El VNC tiene contraseña y solo escucha en 127.0.0.1 de x-server; desde el Mac se entra
por un túnel SSH. Para repetirla (por ejemplo, si caduca):

1. `docker build -f Dockerfile.pantalla -t hubble-lab:pantalla .` en `~/hubble-lab`.
2. En x-server:
   ```sh
   docker run -d --name hubble-registro -e VNC_CLAVE=<clave> -p 127.0.0.1:5901:5901 \
     -v ~/hubble-lab/cosmos:/cosmos hubble-lab:pantalla
   ```
3. En el Mac: `ssh -N -L 5901:127.0.0.1:5901 x-server-vpn` y abrir `vnc://localhost:5901`
   con Compartir Pantalla. En el asistente: «Automático» → «Siguiente».
4. Sacar los `.reg` (`docker cp hubble-registro:/wine/system.reg …`, y lo mismo con
   `user.reg` y `userdef.reg`). Copiarlos en un contenedor creado desde `hubble-lab:2` y
   hacer `docker commit … hubble-lab:3`.
5. Borrar el contenedor, la imagen `hubble-lab:pantalla` y el túnel.

Para ver la pantalla sin VNC: un contenedor auxiliar con
`--network container:hubble-registro` (comparte el socket abstracto de Xvfb) y `x11-apps`,
con `xwd -root`.

## 32 bits (2026-10-29)

El mismo laboratorio con el compilador del kit 8.6 de 32 bits (Xabier dio permiso para el Wine de 32 bits).

| | Ocupa |
|---|---|
| Imagen `hubble-lab:32` (Debian trixie-slim + `wine32:i386`, prefijo `win32`; `Dockerfile.32`) | 1,31 GB (340 MB propios) |
| Imagen `hubble-lab:32a` = `:32` + la activación | lo mismo (una capa de unos KB) |
| `~/hubble-lab/cosmos32/`: `bin etc msg include drw template licences` del kit 8.6 x86 | 87 MB |
| `~/hubble-lab/trabajo32/`: `projects` y `samples` del kit x86 (sus `.prj` son de 32 bits) | 26 MB |
| `~/hubble-lab/bateria32/`: `propia` (solo el `samples.prj` de 32 bits) y `samples` (enlace a `trabajo32/samples`) | < 1 MB |

- **El `.prj` depende de la arquitectura** (cabecera «01.64.02» en x64, «01.00.02» en x86). Con el de 64 bits, el
  compilador de 32 responde `Can not open Project File`.
- **Activación:** la misma clave que en 64 bits, importada con `regedit /S` (`HKLM\Software\Classes\RegUpdate.Registry1\00001IE`,
  valor `Register`, sacado de `kits/registro-licencia/system.reg.nuevo`), y `docker commit` a `hubble-lab:32a`
  (con `--change 'ENTRYPOINT ["/usr/lib/wine/wine"]'`). Sin ella: `Unregistered licence`.
- **Montarlo:**
  ```sh
  scp lab/Dockerfile.32 x-server-vpn:hubble-lab/
  cd kits/extraido/86x86/Cosmos8.6eval   # el kit cosmos86x86eval.zip descomprimido
  COPYFILE_DISABLE=1 tar --no-xattrs -cf - bin etc msg include drw template licences \
    | ssh x-server-vpn 'mkdir -p ~/hubble-lab/cosmos32 && tar -C ~/hubble-lab/cosmos32 -xf -'
  COPYFILE_DISABLE=1 tar --no-xattrs -cf - projects samples \
    | ssh x-server-vpn 'mkdir -p ~/hubble-lab/trabajo32 && tar -C ~/hubble-lab/trabajo32 -xf -'
  ssh x-server-vpn 'cd ~/hubble-lab && docker build -f Dockerfile.32 -t hubble-lab:32 .'
  ```
- **Usarlo:** `compila_lote.sh` y `vuelta_remota.sh` toman `LAB_IMAGEN=hubble-lab:32a` y
  `LAB_COSMOS='~/hubble-lab/cosmos32'` (con la `~` entre comillas: se expande en x-server; sin ellas, Docker
  monta una carpeta inexistente del Mac y no compila nada). La vuelta completa en 32 bits: `ARQ=32 vuelta_todo.sh`
  (los `.omd` de partida, los mismos fuentes compilados en 32 bits, quedan en `kits/compilados/<x>-86x86`).
- **Primera prueba:** NIF compilado aquí en 32 bits da el mismo texto que los `.omd` x86 del kit (9/9), aunque
  estos se compilaron con 7.2.3 (`\\winprod-pc\masterCosmos\cosmos7.2.3\cdrom32\…`). Los 16 proyectos del kit x86
  compilados aquí (`kits/compilados/proy32/`): de los 100 módulos que se descompilan en los dos, 88 con el mismo
  texto que el kit; los otros 12 solo cambian en la POSITION de AUTOSIZE (test `test_kit_x86_y_compilado_aqui_en_32_bits`).

## Quitarlo todo

```sh
ssh x-server-vpn 'docker image rm hubble-lab:32a hubble-lab:32 hubble-lab:3 hubble-lab:2; rm -rf ~/hubble-lab'
```

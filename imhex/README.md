# Hubble en ImHex

`omd.hexpat` es un patrón para [ImHex](https://imhex.werwolv.net/) (1.38.1). Abre un `.omd`
y colorea cada sección. El panel «Pattern Data» muestra el árbol de lo que Hubble entiende:
- la cabecera y las 37 entradas de sección;
- los textos de `IDE`, `STR` y `SVL`;
- en los ficheros de 64 bits, las sentencias (`STM`), los nodos de expresión (`REF`) y los
  procedimientos (`PRO`), con los literales descifrados (`literal -1`, `literal 65536`,
  `literal true`…).

Solo describe lo que está en `docs/formato-omd.md`. Lo que no se entiende va **en gris** y
con el comentario «sin descifrar», y lo que es hipótesis lleva `[hipótesis]`. Cuando se
descifre algo nuevo, se añade aquí y se ve.

## Usarlo

1. Abrir el `.omd` en ImHex. El patrón se reconoce solo por la firma `COMD` si está en
   la carpeta de patrones de ImHex; si no, se carga con *File → Import → Pattern File*.
2. `demo.smd` es un programa nuestro (una función, un bucle, un `if`, cadenas) para
   enseñarlo. Su `.omd` compilado está fuera de git, en `kits/compilados/demo/demo.omd`.
   Se compila con el laboratorio, como cualquier módulo de la batería
   (`lab/bateria/README.md`).

## Comprobación

`verifica.py` ejecuta el patrón con la línea de comandos de ImHex (`imhex --pl format`) y
compara sus textos con los de Hubble, byte a byte:

```sh
uv run python imhex/verifica.py /Applications/ImHex.app/Contents/MacOS kits/*.zip
```

Resultado (2026-10-27): **1174 de 1174** `.omd` de los kits iguales, y también los 415 de `samples`, los 91 de la batería y la demo.

`tests/test_imhex.py` hace lo mismo con tres ficheros de muestra (de 64 y de 32 bits),
y con `HUBBLE_IMHEX` apuntando a esa carpeta. Además comprueba que un patrón estropeado
a propósito falla.

## Instalación en macOS

Homebrew tiene el *cask* deshabilitado desde 2026-09-01: ImHex no pasa Gatekeeper, porque
la firma es *ad hoc* y no está notarizado. Se instala desde la página de releases
(`imhex-1.38.1-macOS-arm64.dmg`, SHA-256 `cbe57f8f…47b0ee8`). La primera vez que se abre,
macOS lo bloquea; se autoriza en *System Settings → Privacy & Security → Open Anyway*.

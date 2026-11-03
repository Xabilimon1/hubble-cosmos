# Mutaciones

Un test que no se ha visto fallar no vigila nada. Cada script rompe una regla del
código cada vez (sustitución exacta de texto), pasa los tests y comprueba que algo
se pone en rojo; luego restaura el fichero.

```sh
uv run python dev/mutaciones/mutar.py      "$PWD"   # inventario, cadenas, cabeceras, entropía
uv run python dev/mutaciones/mutar_cli.py  "$PWD"   # cli.py
uv run python dev/mutaciones/mutar_cont.py "$PWD"   # contenedor.py (+ corpus)
uv run python dev/mutaciones/mutar_emp.py  "$PWD"   # empaquetado.py (+ corpus)
```

- **Antes, la suite en verde.** Con la base en rojo y `-x`, toda mutación sale «roja».
- Sin bytecode (`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`): una mutación del
  mismo tamaño restaurada en el mismo segundo deja cargado el `.pyc` mutado.
- `mutar_cont.py` y `mutar_emp.py` lanzan pytest en su propio grupo de procesos y lo
  matan entero si se cuelga (una mutación quita la protección contra bucles).
- Los de contenedor y empaquetado usan los kits de `HUBBLE_KITS` (ruta del Mac de Xabier,
  escrita en el script).
- «NO ENCONTRADO» = la línea cambió: hay que actualizar la mutación, no ignorarla.

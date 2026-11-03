"""Análisis y descompilación de aplicaciones MultiBase Cosmos (Base 100).

Según el manual de Cosmos, los programas se escriben en COOL en ficheros `.smd`,
el compilador `cosmake` los convierte en módulos binarios `.omd` y el runtime
`cosrun` los ejecuta. El formato `.omd` no está documentado.

Fase 1 (este paquete, por ahora): herramientas que no dependen del formato y
sirven para descubrirlo: inventario de la instalación, texto incrustado,
comparación de cabeceras y entropía.
"""

__version__ = "0.1.0"

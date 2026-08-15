"""Lectura de documentos clinicos y adaptadores de modelo.

Sin plantilla ni coordenadas: en el INSN no llega un solo formulario, llegan
documentos de establecimientos distintos con maquetados distintos. En vez de
preguntar "que dice el rectangulo (x, y, w, h)" se pregunta "cual es el DNI del
paciente en este documento".

El `VerificadorExtraccion` del dominio no se entera del cambio: valida VALORES,
no posiciones. Por eso la capa que impide el error silencioso es independiente
del maquetado.
"""

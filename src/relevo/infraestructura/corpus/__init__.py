"""Corpus sintetico de Hojas de Referencia.

El hospital no puede entregarnos formularios llenos: son datos personales y la
negativa es correcta. Sin muestras no se puede construir ni MEDIR un sistema de
digitalizacion, asi que los generamos.

Sale mejor que pedirlos prestados: no hay dato de nadie, se pueden publicar, se
generan mil en vez de cinco, y la verdad viene gratis porque nosotros
escribimos cada campo.

    python -m relevo.interfaz.cli.descargar_fuentes
    python -m relevo.interfaz.cli.generar_corpus --n 200
"""

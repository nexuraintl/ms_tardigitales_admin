from enum import IntEnum

class TipoTarjeta(IntEnum):
    CONTADORES = 1
    SOCIEDADES = 2

class TipoAsociado(IntEnum):
    PRIMERA_VEZ = 1
    DUPLICADO = 2
    SUSTITUCION = 3
    MODIFICACION = 4
    # etc.

class TipoEstadoTarjeta(IntEnum):
    ACTIVA = 1
    EMITIDA = 2
    CANCELADA = 3

TIPO_TARJETA_MAP = {
    "contadores": TipoTarjeta.CONTADORES,
    "sociedades": TipoTarjeta.SOCIEDADES,
}

TIPO_ASOCIADO_MAP = {
    "primeraVez": TipoAsociado.PRIMERA_VEZ,
    "duplicado": TipoAsociado.DUPLICADO,
    "sustitucion": TipoAsociado.SUSTITUCION,
    "modificacion": TipoAsociado.MODIFICACION,
    "Primera vez": TipoAsociado.PRIMERA_VEZ,
    "Duplicado": TipoAsociado.DUPLICADO,
    "Sustitución": TipoAsociado.SUSTITUCION,
    "Sustitucion": TipoAsociado.SUSTITUCION,
}

TIPO_ESTADO_TARJETA_MAP = {
    "Activa" : TipoEstadoTarjeta.ACTIVA,
    "Emitida" : TipoEstadoTarjeta.EMITIDA,
    "Cancelada" : TipoEstadoTarjeta.CANCELADA
}
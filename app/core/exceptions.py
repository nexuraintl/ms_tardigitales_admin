from typing import Optional, Dict, Any
from fastapi import HTTPException, status

STAGE_ERROR_CODES: Dict[str, int] = {
    "TENANT_CLIENT_ID_REQUERIDO": 3801,
    "CONFIGURACION_TENANT_NO_ENCONTRADA": 3802,
    "CONEXION_DB_CENTRAL": 3803,
    "CONSULTA_BDCONEX": 3804,
    "CONEXION_DB_TENANT": 3805,
    "CONSULTA_API_JCC": 3806,
    "CHECK_EXISTENCIA": 3807,
    "TABLA_PRINCIPAL": 3808,
    "TABLA_INTERMEDIA": 3809,
    "REGISTRO_AUDITORIA": 3810,
    "CONFIGURACION_VALIDADOR": 3811,
    "CONFIGURACION_COLUMNAS": 3812,
    "BRANDING_CREDENTIALS": 3813,
    "PARAMETROS_INVALIDOS": 3814,
    "ERROR_DESCONOCIDO_MYSQL": 3899,
}

class PipelineException(HTTPException):
    def __init__(
        self,
        etapa: str,
        mensaje: str,
        codigo_error: Optional[int] = None,
        detalle_tecnico: Optional[str] = None,
        cliente_id: Optional[int] = None,
        tabla_afectada: Optional[str] = None,
        base_datos_cliente: Optional[str] = None,
        contexto: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.etapa = etapa
        self.mensaje = mensaje
        self.codigo_error = codigo_error or STAGE_ERROR_CODES.get(etapa, 3899)
        self.detalle_tecnico = detalle_tecnico
        self.cliente_id = cliente_id
        self.tabla_afectada = tabla_afectada
        self.base_datos_cliente = base_datos_cliente
        self.contexto = contexto
        
        super().__init__(status_code=status_code, detail=mensaje)

    def to_dict(self) -> Dict[str, Any]:
        error_payload: Dict[str, Any] = {
            "codigo_error": self.codigo_error,
            "etapa": self.etapa,
            "mensaje": self.mensaje,
        }
        if self.cliente_id is not None:
            error_payload["cliente_id"] = self.cliente_id
        if self.base_datos_cliente:
            error_payload["base_datos_cliente"] = self.base_datos_cliente
        if self.tabla_afectada:
            error_payload["tabla_afectada"] = self.tabla_afectada
        if self.detalle_tecnico:
            error_payload["detalle_tecnico"] = str(self.detalle_tecnico)
        if self.contexto:
            error_payload["contexto"] = self.contexto

        return {
            "status": "error",
            "code": self.status_code,
            "error": error_payload
        }

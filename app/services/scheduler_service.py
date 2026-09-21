import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.integrations.jcc_client import JccClient
from app.repositories.tarjetas_repository import TarjetasRepository
from app.schemas.tarjetas_schema import EstadoTarjetaEnum

logger = logging.getLogger("scheduler_service")

class SchedulerService:
    def __init__(self):
        self.jcc_client = JccClient()
        self.repository = TarjetasRepository()

    async def ejecutar_emision_recurrente(self, client_id: Optional[int] = None) -> Dict[str, Any]:
        """
        HU-JCC-005 (Página 22): Emisión credencial digital RECURRENTE
        
        1. El sistema consumirá de manera recurrente los servicios expuestos por MYJCC para gestionar la emisión de credenciales digitales de contadores y sociedades, según su tipo.
        2. Una vez generada la credencial digital, el sistema almacenará el registro con la información asociada y asignará como estado inicial de la tarjeta "Emitida".
        3. [TODO HU-JCC-024] Generará un token/hash único asociado al registro en forma de QR.
        4. Adicionalmente, aquellos que vienen de la tarea recurrente deberán consultarse individualmente para obtener la FOTOGRAFÍA (si no vino incluida en la consulta inicial).
        5. [TODO HU-JCC-008] Enviará al SGDEA la información de activación y el branding correspondiente.
        6. No debe permitir registrar datos o credenciales con el mismo número de documento o NIT (Control de duplicados).
        """
        resumen = {
            "fecha_ejecucion": datetime.now().isoformat(),
            "procesados_contadores": 0,
            "procesados_sociedades": 0,
            "creados": 0,
            "omitidos_duplicados": 0,
            "errores": 0,
            "detalles": []
        }

        # Tipos de trámites a consultar según HU-JCC-005
        tipos_contadores = ["primeraVez", "duplicado", "sustitucion"]
        tipos_sociedades = ["primeraVez", "modificacion", "duplicado"]

        cid = client_id
        logger.info(f"[SchedulerService] Iniciando tarea programada de emisión recurrente de credenciales (client_id={cid})...")

        # ---------------------------------------------------------------------
        # PROCESO RECURRENTE DE CONTADORES
        # ---------------------------------------------------------------------
        for tipo in tipos_contadores:
            try:
                # Paso 1: Consultar servicios de MYJCC por tipo de trámite recurrente
                consulta = await self.jcc_client.consultar_registro(documento="", tipo_tarjeta="contadores", tipo=tipo)
                disponibles = consulta.get("disponibles", [])

                if not disponibles or not consulta.get("encontrado"):
                    continue

                for item in disponibles:
                    no_documento = str(item.get("no_documento", "")).strip()
                    if not no_documento:
                        continue

                    resumen["procesados_contadores"] += 1

                    # Paso 6: Control de duplicados por número de documento
                    existe_contador = await self.repository.exists_accountant(no_documento, cid)
                    if existe_contador:
                        resumen["omitidos_duplicados"] += 1
                        resumen["detalles"].append({
                            "tipo": "contador",
                            "documento": no_documento,
                            "resultado": "omitido_duplicado",
                            "mensaje": f"El contador con número documento {no_documento} ya está registrado previamente (MS-3857)."
                        })
                        continue

                    # Paso 4: Consulta individual complementaria para obtener FOTOGRAFÍA si viene ausente
                    foto_b64 = item.get("pdf") or item.get("foto")
                    if not foto_b64:
                        consulta_indiv = await self.jcc_client.consultar_registro(
                            documento=no_documento,
                            tipo_tarjeta="contadores",
                            tipo=tipo
                        )
                        data_indiv = consulta_indiv.get("data") or {}
                        foto_b64 = data_indiv.get("pdf") or data_indiv.get("foto")

                    # Paso 2: Construir estructura y asignar como estado inicial de la tarjeta "Emitida"
                    contador_data = {
                        "no_tarjeta": item.get("no_tarjeta", ""),
                        "nombres": item.get("nombres", ""),
                        "primer_apellido": item.get("primer_apellido", ""),
                        "segundo_apellido": item.get("segundo_apellido", ""),
                        "no_expd": item.get("no_expd", 0),
                        "tipo_documento": item.get("tipo_documento", "CC"),
                        "no_documento": no_documento,
                        "universidad": item.get("universidad", ""),
                        "estado_contador": item.get("estado_contador", "ACTIVO"),
                        "resolucion": item.get("resolucion", ""),
                        "fecha_estado": item.get("fecha_estado"),
                        "fecha_radicacion": item.get("fecha_radicacion"),
                        "fecha_resolucion": item.get("fecha_resolucion"),
                        "acta_jcc": item.get("acta_jcc"),
                        "fecha_grado": item.get("fecha_grado"),
                        "seccional": item.get("seccional", ""),
                        "correo": item.get("correo", ""),
                        "fecha_emision": datetime.now(),
                        "tipo_asociado": tipo,
                        "estado": EstadoTarjetaEnum.EMITIDA.value,
                        "foto": foto_b64
                    }

                    new_id = await self.repository.create_contadores(contador_data, cid)

                    # TODO HU-JCC-024: Generar token/hash único asociado al registro en forma de QR
                    # token_hash = self.generar_token_qr_dinamico(new_id, no_documento)

                    # TODO HU-JCC-008: Enviar al SGDEA la información necesaria para el proceso de activación
                    # await self.notificar_activacion_sgdea(new_id, branding_data, token_hash)

                    resumen["creados"] += 1
                    resumen["detalles"].append({
                        "tipo": "contador",
                        "id": new_id,
                        "documento": no_documento,
                        "resultado": "emitido_exitosamente",
                        "estado_inicial": EstadoTarjetaEnum.EMITIDA.value
                    })

                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"[SchedulerService] Error emitiendo contador tipo {tipo}: {e}")
                resumen["errores"] += 1

        # ---------------------------------------------------------------------
        # PROCESO RECURRENTE DE SOCIEDADES
        # ---------------------------------------------------------------------
        for tipo in tipos_sociedades:
            try:
                # Paso 1: Consultar servicios de MYJCC para sociedades
                consulta = await self.jcc_client.consultar_registro(documento="", tipo_tarjeta="sociedades", tipo=tipo)
                disponibles = consulta.get("disponibles", [])

                if not disponibles or not consulta.get("encontrado"):
                    continue

                for item in disponibles:
                    nit = str(item.get("nit", "")).strip()
                    if not nit:
                        continue

                    resumen["procesados_sociedades"] += 1

                    # Paso 6: Control de duplicados por NIT
                    existe_sociedad = await self.repository.exists_society(nit, cid)
                    if existe_sociedad:
                        resumen["omitidos_duplicados"] += 1
                        resumen["detalles"].append({
                            "tipo": "sociedad",
                            "nit": nit,
                            "resultado": "omitido_duplicado",
                            "mensaje": f"La sociedad con NIT {nit} ya está registrada previamente (MS-3857)."
                        })
                        continue

                    # Paso 4: Consulta individual complementaria para obtener FOTOGRAFÍA si viene ausente
                    foto_b64 = item.get("pdf") or item.get("foto")
                    if not foto_b64:
                        consulta_indiv = await self.jcc_client.consultar_registro(
                            documento=nit,
                            tipo_tarjeta="sociedades",
                            tipo=tipo
                        )
                        data_indiv = consulta_indiv.get("data") or {}
                        foto_b64 = data_indiv.get("pdf") or data_indiv.get("foto")

                    # Paso 2: Asignar estado inicial "Emitida"
                    sociedad_data = {
                        "no_expd": item.get("no_expd", 0),
                        "razon_social": item.get("razon_social", ""),
                        "nit": nit,
                        "tipo_sociedad": item.get("tipo_sociedad", "SOCIEDAD DE CONTADORES"),
                        "inscripcion": item.get("inscripcion"),
                        "fecha_radicacion": item.get("fecha_radicacion"),
                        "estado_sociedad": item.get("estado_sociedad", "ACTIVO"),
                        "resolucion": item.get("resolucion", ""),
                        "fecha_resolucion": item.get("fecha_resolucion"),
                        "acta_jcc": str(item.get("acta_jcc")) if item.get("acta_jcc") is not None else None,
                        "estado_solicitud": item.get("estado_solicitud"),
                        "tipo_solicitud": item.get("tipo_solicitud"),
                        "correo": item.get("correo", ""),
                        "representante_legal": item.get("representante_legal", ""),
                        "fecha_emision": datetime.now(),
                        "tipo_asociado": tipo,
                        "estado": EstadoTarjetaEnum.EMITIDA.value,
                        "foto": foto_b64
                    }

                    new_id = await self.repository.create_sociedades(sociedad_data, cid)

                    # TODO HU-JCC-024: Generar token/hash único asociado al registro en forma de QR
                    # token_hash = self.generar_token_qr_dinamico(new_id, nit)

                    # TODO HU-JCC-008: Enviar al SGDEA la información necesaria para el proceso de activación
                    # await self.notificar_activacion_sgdea(new_id, branding_data, token_hash)

                    resumen["creados"] += 1
                    resumen["detalles"].append({
                        "tipo": "sociedad",
                        "id": new_id,
                        "nit": nit,
                        "resultado": "emitido_exitosamente",
                        "estado_inicial": EstadoTarjetaEnum.EMITIDA.value
                    })

                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"[SchedulerService] Error emitiendo sociedad tipo {tipo}: {e}")
                resumen["errores"] += 1

        logger.info(f"[SchedulerService] Tarea de emisión recurrente finalizada: {resumen['creados']} creadas, {resumen['omitidos_duplicados']} omitidas.")
        return resumen

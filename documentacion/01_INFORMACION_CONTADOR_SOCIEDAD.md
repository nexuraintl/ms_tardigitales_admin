# Endpoint 01: Información Contador / Sociedad (Verificación Pública)

> **Destinatario / Consumo:** Modelos de IA (Claude / LLM) e Ingenieros Backend.  
> **Servicio:** `ms_tardigitales_admin` (`app/api/v1/routes/tarjetas.py`).  
> **Función de Ruta:** `get_tarjeta_by_hash` y `verificar_tarjeta_query`.  
> **Repositorio:** `TarjetasRepository.get_by_hash(hash_sha256, tipo_tarjeta, client_id)`.

---

## 1. Definición del Endpoint HTTP

### Rutas Disponibles en FastAPI:
1. `GET /apig/tardigitales/admin/tarjetas/verificar`
2. `GET /apig/tardigitales/admin/tarjetas/verificar/{hash}`
3. `GET /apig/tardigitales/admin/tarjetas/get-by-hash/{hash}`

### Parámetros de Petición:
| Parámetro | Ubicación | Tipo | Requerido | Descripción |
|---|---|---|:---:|---|
| `hash` | Path | `string` | Condicional | Hash SHA-256 canónico (10 a 64 caracteres hex). |
| `token` | Query | `string` | Condicional | Token/Hash alternativo si se invoca `/verificar?token=...`. |
| `tipo_tarjeta`| Query | `string` | No | Filtro opcional: `'contadores'` o `'sociedades'`. Si se omite, el repositorio busca primero en contadores y luego en sociedades. |
| `client_id` | Query | `int` | No | ID del Tenant. Por defecto toma la variable de entorno `CLIENT_ID` (`20001`). |

---

## 2. Flujo de Ejecución y Reglas de Negocio

1. **Resolución del Hash:** Se sanitiza y valida la existencia del parámetro `token` o `hash`. Si ambos faltan, se lanza `HTTPException(400)`.
2. **Consulta Asíncrona:**
   - Si `tipo_tarjeta == "contadores"`: Consulta `tn_tarjetavirtual_contadores ttc WHERE ttc.hash_sha256 = %s`.
   - Si `tipo_tarjeta == "sociedades"`: Consulta `tn_tarjetavirtual_sociedades tts WHERE tts.hash_sha256 = %s`.
   - Si no se especifica, ejecuta fallback automático: busca en contadores; si no existe registro, busca en sociedades.
3. **Tarjeta No Encontrada:** Si ninguna tabla contiene el hash, lanza `PipelineException(etapa="TABLA_PRINCIPAL", status_code=404)`.
4. **Estado de la Tarjeta (Caso de Fallecimiento o Cancelación):**
   - El modelo retorna el campo canónico `estado_tarjeta` (`Activa`, `Emitida`, `Cancelada`, `Suspendida`, `Vencida`).
   - El endpoint **retorna exitosamente los datos** independientemente de si la tarjeta está cancelada o no; es responsabilidad del cliente visual (App o Web) advertir que la credencial se encuentra cancelada por fallecimiento o sanción legal.

---

## 3. Contrato JSON de Salida (Respuesta HTTP 200)

### Ejemplo Respuesta Contador:
```json
{
  "id": 98,
  "tipo_tarjeta": "contadores",
  "no_tarjeta": "320890-T",
  "nombre_completo": "ARIS PAOLA HERRERA RODRIGUEZ",
  "nombres": "ARIS PAOLA",
  "primer_apellido": "HERRERA",
  "segundo_apellido": "RODRIGUEZ",
  "no_expd": "2024-EXP-0012",
  "tipo_asociado": "Principal",
  "fecha_emision": "2026-10-14 10:30:00",
  "tipo_documento": "CC",
  "no_documento": "1002345678",
  "correo": "titular@correo.com",
  "universidad": "UNIVERSIDAD NACIONAL DE COLOMBIA",
  "estado_tarjeta": "Activa",
  "estado_contador": "Vigente",
  "resolucion": "0292",
  "fecha_resolucion": "2024-03-15",
  "acta_jcc": "2180",
  "fecha_grado": "2023-12-10",
  "seccional": "BOGOTA D.C.",
  "foto": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "hash_sha256": "a5339002552bc8b6411b21e6383ad1dc1ec8789e9d6fc8ccd0251bbbc17074cf"
}
```

---

## 4. Directivas de Código para Claude

- Nunca modificar la consulta de `TarjetasRepository.get_by_hash` para unir `contadores` y `sociedades` con `UNION` pesadas; el patrón actual ejecuta queries individuales indexadas por `hash_sha256`.
- Los campos de fecha deben formatearse siempre en SQL con `DATE_FORMAT(..., '%Y-%m-%d %H:%i:%s')`.

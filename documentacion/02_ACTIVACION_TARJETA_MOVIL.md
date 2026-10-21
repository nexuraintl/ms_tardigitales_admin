# Endpoint 02: Activación de Tarjeta Móvil (HU-JCC-014)

> **Destinatario / Consumo:** Modelos de IA (Claude / LLM) e Ingenieros Backend.  
> **Servicio:** `ms_tardigitales_admin` (`app/api/v1/routes/tarjetas.py`).  
> **Función de Ruta:** `activar_tarjeta_movil`.  
> **Esquema de Entrada:** `ActivacionMovilRequestSchema` (`app/schemas/tarjetas_schema.py`).

---

## 1. Definición del Endpoint HTTP

- **Método:** `POST`
- **Ruta Oficial:** `/apig/tardigitales/admin/tarjetas/activar-movil`
- **Content-Type:** `application/json`
- **Status Code Exitoso:** `200 OK`

---

## 2. Esquema Pydantic de Entrada

```python
class ActivacionMovilRequestSchema(BaseModel):
    token: str = Field(..., min_length=10, max_length=64, description="Hash SHA-256 de la tarjeta")
    fcm_token: Optional[str] = Field(None, description="Token de Firebase Cloud Messaging")
    device_id: Optional[str] = Field(None, description="UUID único del hardware o instalación")
    device_os: Optional[str] = Field(None, description="Sistema operativo ('android' o 'ios')")
    device_modelo: Optional[str] = Field(None, description="Modelo comercial del dispositivo")
    app_version: Optional[str] = Field(None, description="Versión instalada de la App Móvil")
    client_id: Optional[int] = Field(None, description="ID del Tenant/Cliente (default: 20001)")
```

---

## 3. Lógica Transaccional en Base de Datos

El método `service.activar_tarjeta_movil(payload)` ejecuta las siguientes operaciones en orden atómico:

1. **Búsqueda de la Tarjeta:** Invoca `repo.get_by_hash(payload.token, client_id=cid)`. Si no existe, lanza `PipelineException(404, "Tarjeta digital no encontrada.")`.
2. **Validación de Estado Previo:** Si la tarjeta ya está `'Activa'`, actualiza el dispositivo sin generar error (idempotencia para reinstalaciones de la app).
3. **Actualización de Estado en la Tabla Principal:**
   ```sql
   UPDATE tn_tarjetavirtual_contadores 
   SET estado = 'Activa', fecha_estado = NOW() 
   WHERE id = %s;
   ```
4. **Registro de Dispositivo Móvil (`tn_tarjetavirtual_dispositivos`):**
   ```sql
   INSERT INTO tn_tarjetavirtual_dispositivos 
   (tarjeta_id, tipo_tarjeta, device_id, device_os, device_modelo, app_version, fcm_token, fecha_registro, fecha_ultimo_acceso)
   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
   ON DUPLICATE KEY UPDATE 
       fcm_token = VALUES(fcm_token), 
       app_version = VALUES(app_version),
       fecha_ultimo_acceso = NOW();
   ```
5. **Historial de Estados (`tn_tarjetavirtual_estados_historial`):**
   Registra el cambio de estado con el usuario del sistema `'App Móvil'`.
6. **Inyección de Branding:** Recupera el branding publicado de la tarjeta y lo empaqueta en la respuesta junto a los datos del titular para entrega inmediata a la billetera digital.

---

## 4. Contrato JSON de Salida (Respuesta HTTP 200)

```json
{
  "success": true,
  "mensaje": "Credencial digital activada exitosamente en el dispositivo móvil.",
  "data": {
    "tarjeta": {
      "id": 98,
      "tipo_tarjeta": "contadores",
      "no_tarjeta": "320890-T",
      "nombre_completo": "ARIS PAOLA HERRERA RODRIGUEZ",
      "no_documento": "1002345678",
      "estado_tarjeta": "Activa",
      "foto": "data:image/jpeg;base64,...",
      "hash_sha256": "a5339002552bc8b6411b21e6383ad1dc1ec8789e9d6fc8ccd0251bbbc17074cf"
    },
    "branding": {
      "id": 1,
      "color_fondo": "#0284c7",
      "color_letra": "#ffffff",
      "logo": "data:image/svg+xml;base64,...",
      "patron": "data:image/png;base64,...",
      "nombre_director": "DR. CARLOS ALBERTO PEREZ",
      "firma_director": "data:image/png;base64,..."
    }
  }
}
```

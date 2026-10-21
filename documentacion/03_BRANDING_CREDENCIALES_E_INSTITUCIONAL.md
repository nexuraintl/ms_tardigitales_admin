# Endpoint 03: Branding de Credenciales e Institucional

> **Destinatario / Consumo:** Modelos de IA (Claude / LLM) e Ingenieros Backend.  
> **Servicio:** `ms_tardigitales_admin` (`app/api/v1/routes/tarjetas.py`).  
> **Tablas:** `tn_tarjetavirtual_configuracion_branding`, `tn_tarjetavirtual_configuracion_branding_versiones`, `tn_tarjetavirtual_institucional_versiones`.

---

## 1. Definición de Endpoints de Lectura Pública

### A. Branding de Credenciales Publicado (Específico por Tipo)
- **Ruta:** `GET /apig/tardigitales/admin/tarjetas/branding-credentials/info-published/{id}`
- **Parámetro `id`:**
  - `1`: Configuración oficial de Tarjeta Contador.
  - `2`: Configuración oficial de Tarjeta Sociedad.
- **Respuesta:**
  ```json
  {
    "status": "success",
    "data": {
      "id": 1,
      "tipo_id": 1,
      "version_publicada": 3,
      "color_fondo": "#0284c7",
      "color_letra": "#ffffff",
      "color_letra_impresion": "#0f172a",
      "logo": "data:image/svg+xml;base64,...",
      "logo_impresion": "data:image/svg+xml;base64,...",
      "patron": "data:image/png;base64,...",
      "patron_impresion": "data:image/png;base64,..."
    }
  }
  ```

### B. Branding Institucional Publicado (Global JCC - Director General)
- **Rutas:**
  - `GET /apig/tardigitales/admin/tarjetas/branding-credentials/institucional/info-published`
  - `GET /apig/tardigitales/admin/tarjetas/branding-institucional/info-published`
- **Respuesta:**
  ```json
  {
    "status": "success",
    "data": {
      "id": 1,
      "version_publicada": 2,
      "nombre_director": "DR. JOSÉ ORLANDO RAMÍREZ",
      "cargo_director": "Director General UAE JCC",
      "firma_director": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
      "fecha_publicacion": "2026-10-15 14:00:00"
    }
  }
  ```

---

## 2. Lógica de Versionamiento y Publicación

1. **Creación de Borrador (`POST .../branding-credentials/create`):**
   - Incrementa `version_actual` en la tabla cabecera y guarda el registro con `es_publicada = 0` en la tabla de versiones.
2. **Publicación (`PUT .../branding-credentials/update/change-version/{id}`):**
   - Actualiza `version_publicada = %s` en la cabecera.
   - Pone `es_publicada = 1` en la versión seleccionada y desmarca las anteriores (`es_publicada = 0`).
   - El cambio tiene efecto inmediato en la app móvil y en la generación de nuevos PDFs.

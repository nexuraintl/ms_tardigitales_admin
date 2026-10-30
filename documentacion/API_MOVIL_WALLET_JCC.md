# Especificación de Endpoints API - Aplicación Móvil (Wallet JCC)

> **Servicio:** Microservicio Tarjetas Digitales UAE JCC (`ms_tardigitales_admin`).  
> **Base URL Gateway (Local / Preproducción):** `http://local-jcc.nexura.com.co/apig/tardigitales/admin/tarjetas`  
> **Base URL Directa Microservicio (Docker):** `http://<host>:8000/tardigitales/admin/tarjetas`  
> **Headers Globales:**  
> - `Content-Type: application/json`  
> - `Accept: application/json`  
> - `X-Tenant-Id: jcc` *(Opcional en headers)*  
> **Zona Horaria Oficial:** Colombia (`America/Bogota`, UTC-5).  
> **Regla de Multi-tenancy (`client_id`):**  
> Para garantizar la separación de bases de datos por entidad, **todos los endpoints admiten y deben recibir el parámetro `client_id`** (para la UAE JCC es `20001`):  
> - En peticiones **`GET`**: Se envía como parámetro URL (`?client_id=20001`).  
> - En peticiones **`POST`**: Se envía en el cuerpo JSON (`"client_id": 20001`) o como parámetro URL.  
> - *Fallback:* Si el cliente lo omite, el microservicio asume automáticamente el tenant predeterminado (`20001`), pero la buena práctica es enviarlo explícitamente en todas las peticiones.

---

## Tabla Resumen de Endpoints

| # | Endpoint Oficial (Gateway) | Método | Multi-tenant (`client_id`) | Descripción |
|---|---|:---:|:---:|---|
| **01** | `/apig/tardigitales/admin/tarjetas/verificar` <br> `/apig/tardigitales/admin/tarjetas/verificar/{hash}` | `GET` | Query Param (`?client_id=20001`) | Consulta y verifica la información del titular (Contador o Sociedad) mediante el hash del QR. |
| **02** | `/apig/tardigitales/admin/tarjetas/otp/solicitar` | `POST` | Body JSON (`"client_id": 20001`) | Solicita generación y envío del código OTP al correo oficial del titular. |
| **03** | `/apig/tardigitales/admin/tarjetas/otp/validar` | `POST` | Body JSON (`"client_id": 20001`) | Valida el código numérico OTP de 6 dígitos ingresado por el titular. |
| **04** | `/apig/tardigitales/admin/tarjetas/activar-movil` | `POST` | Body JSON (`"client_id": 20001`) | Enrola el dispositivo físico (FCM, SO, modelo) y activa la credencial en el Wallet. |
| **05** | `/apig/tardigitales/admin/tarjetas/branding-credentials/info-published/{tipo_id}` | `GET` | Query Param (`?client_id=20001`) | Retorna versión publicada de colores, logo SVG y patrón Base64 de la tarjeta. |
| **06** | `/apig/tardigitales/admin/tarjetas/branding-institucional/info-published` | `GET` | Query Param (`?client_id=20001`) | Retorna versión publicada del nombre, cargo y firma oficial del Director General. |
| **07** | `/apig/tardigitales/admin/tarjetas/lecturas/registrar` | `POST` | Body JSON (`"client_id": 20001`) | Registra el evento de auditoría tras escanear una credencial digital/física. |
| **08** | `/apig/tardigitales/admin/tarjetas/lecturas/historial` | `GET` | Query Param (`?client_id=20001`) | Consulta historial de lecturas (`me_consultaron` o `mis_consultas`). |

---

## 1. `GET /verificar` y `GET /verificar/{hash}` - Verificación de Credencial por QR

Permite a la aplicación móvil consultar los datos completos de una credencial (Contador Público o Sociedad de Contadores) a partir del token hash SHA-256 extraído tras escanear el código QR.

- **Método HTTP:** `GET`
- **Ruta Gateway (Query Param):** `/apig/tardigitales/admin/tarjetas/verificar?token={hash}&client_id=20001`
- **Ruta Gateway (Path Param):** `/apig/tardigitales/admin/tarjetas/verificar/{hash}?client_id=20001`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/verificar?token={hash}&client_id=20001`
- **Ruta Alternativa Microservicio:** `/tardigitales/admin/tarjetas/get-by-hash/{hash}?client_id=20001`

### Parámetros de Entrada

| Parámetro | Ubicación | Tipo | Requerido | Descripción | Ejemplo |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `hash` | **Path** | `string` | Condicional | Hash SHA-256 canónico de la credencial (10 a 64 caracteres hex). Requerido si se invoca `/verificar/{hash}`. | `fb98bcc7ef3167edae16...` |
| `token` | **Query** | `string` | Condicional | Token o hash SHA-256 de la credencial. Requerido si se invoca `/verificar?token=...`. | `fb98bcc7ef3167edae16...` |
| `client_id` | **Query** | `integer` | No | ID del tenant/entidad (UAE JCC: `20001`). Recomendado enviarlo siempre. | `20001` |
| `tipo_tarjeta` | **Query** | `string` | No | Filtro de entidad: `"contadores"` o `"sociedades"`. Si se omite, el backend busca automáticamente en ambas. | `"contadores"` |
| `sanitizar` | **Query** | `boolean` | No (default: `true`) | Si es `true`, aplica los filtros de privacidad legal aprobados para la UAE JCC. | `true` |

### Respuestas del Servidor

#### `HTTP 200 OK` (Respuesta para Contador Público)
```json
{
  "id": 98,
  "tipo_tarjeta": "contadores",
  "no_tarjeta": "320890-T",
  "nombre_completo": "ARIS PAOLA HERRERA RODRIGUEZ",
  "nombres": "ARIS PAOLA",
  "primer_apellido": "HERRERA",
  "segundo_apellido": "RODRIGUEZ",
  "no_expd": "375883",
  "tipo_asociado": "Principal",
  "fecha_emision": "2026-10-14 10:30:00",
  "tipo_documento": "CC",
  "no_documento": "1002345678",
  "correo": "k***2@hotmail.com",
  "universidad": "UNIVERSIDAD NACIONAL DE COLOMBIA",
  "estado_tarjeta": "Activa",
  "estado_contador": "Vigente",
  "resolucion": "0292",
  "fecha_resolucion": "2024-03-15",
  "acta_jcc": "2180",
  "fecha_grado": "2023-12-10",
  "seccional": "BOGOTA D.C.",
  "foto": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
  "hash_sha256": "fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898"
}
```

#### `HTTP 200 OK` (Respuesta para Sociedad de Contadores)
```json
{
  "id": 45,
  "tipo_tarjeta": "sociedades",
  "no_tarjeta": "S-00452-2024",
  "razon_social": "AUDITORES Y CONSULTORES ASOCIADOS S.A.S.",
  "no_expd": "SOC-2024-012",
  "tipo_asociado": "Principal",
  "fecha_emision": "2026-10-14 11:00:00",
  "tipo_documento": "NIT",
  "no_documento": "901234567",
  "estado_tarjeta": "Activa",
  "estado_sociedad": "Vigente",
  "resolucion": "0185",
  "fecha_resolucion": "2024-02-20",
  "seccional": "MEDELLIN",
  "hash_sha256": "9b12a3d76e43f1ffe663735108db2bad5ff6c741b1ef6898a1b2c3d4e5f60718"
}
```

#### `HTTP 400 Bad Request` (Falta token o hash)
```json
{
  "detail": "Debe suministrar el parámetro 'token' o 'hash' de la tarjeta a verificar."
}
```

#### `HTTP 404 Not Found` (Credencial inexistente)
```json
{
  "detail": "Tarjeta digital no encontrada."
}
```

---

## 2. `POST /otp/solicitar` - Solicitar Código OTP

Genera y envía un código numérico OTP de 6 dígitos al correo electrónico del titular registrado ante la UAE JCC, previa comprobación de coincidencia entre el hash de la tarjeta y su número de expediente.

- **Método HTTP:** `POST`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/otp/solicitar`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/otp/solicitar`
- **Content-Type:** `application/json`

### Parámetros de Entrada (`Request Body`)

```json
{
  "hash": "fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898",
  "expediente": "375883",
  "client_id": 20001
}
```

| Campo | Tipo | Requerido | Descripción |
| :--- | :--- | :---: | :--- |
| `hash` | `string` | **Sí** | Hash SHA-256 canónico de la tarjeta (10 a 64 caracteres) obtenido del QR. |
| `expediente` | `string` | **Sí** | Número de expediente del contador o sociedad (1 a 45 caracteres). |
| `client_id` | `integer` | No | ID de la entidad cliente (UAE JCC: `20001`). Puede enviarse en Body o Query. |

### Respuestas del Servidor

#### `HTTP 200 OK` (Éxito)
```json
{
  "status": "success",
  "message": "Código de verificación generado y despachado.",
  "correo_enmascarado": "k***2@hotmail.com",
  "expira_en_minutos": 5
}
```

#### `HTTP 400 Bad Request` (Discrepancia de datos)
```json
{
  "detail": "El número de expediente no coincide con la tarjeta escaneada."
}
```

#### `HTTP 404 Not Found` (Tarjeta no encontrada)
```json
{
  "detail": "No se encontró ninguna tarjeta activa vinculada al hash suministrado."
}
```

---

## 3. `POST /otp/validar` - Validar Código OTP

Valida si el código de 6 dígitos numéricos ingresado por el usuario coincide con el generado y se encuentra vigente.

- **Método HTTP:** `POST`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/otp/validar`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/otp/validar`
- **Content-Type:** `application/json`

### Parámetros de Entrada (`Request Body`)

```json
{
  "hash": "fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898",
  "token": "573882",
  "expediente": "375883",
  "client_id": 20001
}
```

| Campo | Tipo | Requerido | Descripción |
| :--- | :--- | :---: | :--- |
| `hash` | `string` | **Sí** | Hash SHA-256 de la tarjeta. |
| `token` | `string` | **Sí** | Código numérico OTP de 6 dígitos ingresado por el usuario. |
| `expediente` | `string` | No | Número de expediente (opcional, para verificación cruzada). |
| `client_id` | `integer` | No | ID de la entidad cliente (UAE JCC: `20001`). Puede enviarse en Body o Query. |

### Respuestas del Servidor

#### `HTTP 200 OK` (Validación Exitosa)
```json
{
  "status": "success",
  "validado": true,
  "message": "Código OTP validado correctamente."
}
```

#### `HTTP 400 Bad Request` (Código inválido o expirado)
```json
{
  "detail": "Código OTP inválido o expirado."
}
```

---

## 4. `POST /activar-movil` - Enrolamiento de Dispositivo Móvil

Registra los metadatos del dispositivo físico (SO, hardware, versión de la app, token push FCM) y cambia el estado de la credencial a `'Activa'` si se encontraba pendiente.

- **Método HTTP:** `POST`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/activar-movil`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/activar-movil`
- **Content-Type:** `application/json`

### Parámetros de Entrada (`Request Body`)

```json
{
  "token": "fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898",
  "fcm_token": "fN4-kJq_T9W:APA91bH7...",
  "device_id": "c83b8b98-11da-45d2-bce4-6f0ad7295ef1",
  "device_os": "android",
  "device_modelo": "Samsung Galaxy S23",
  "app_version": "1.0.0",
  "client_id": 20001
}
```

| Campo | Tipo | Requerido | Descripción |
| :--- | :--- | :---: | :--- |
| `token` | `string` | **Sí** | Hash SHA-256 de la credencial digital obtenido del QR. |
| `fcm_token` | `string` | No | Token de registro de Firebase Cloud Messaging para notificaciones push. |
| `device_id` | `string` | No | Identificador único del dispositivo (UUID / IDFV / Android ID). |
| `device_os` | `string` | No | Plataforma (`"android"` o `"ios"`). |
| `device_modelo` | `string` | No | Modelo comercial del dispositivo físico. |
| `app_version` | `string` | No | Versión de la app móvil instalada. |
| `client_id` | `integer` | No | ID del cliente/tenant (UAE JCC: `20001`). Puede enviarse en Body o Query. |

### Respuestas del Servidor

#### `HTTP 200 OK` (Activación Exitosa)
```json
{
  "success": true,
  "mensaje": "Credencial digital activada exitosamente en el dispositivo móvil.",
  "data": {
    "tarjeta": {
      "id": 98,
      "tipo_tarjeta": "contadores",
      "no_tarjeta": "320890-T",
      "nombre_completo": "CARLOS ANDRES OSORIO GOMEZ",
      "no_documento": "1002345678",
      "estado_tarjeta": "Activa",
      "hash_sha256": "fb98bcc7ef3167edae16559c4d04b1ffe663735108db2bad5ff6c741b1ef6898"
    },
    "branding": {
      "id": 1,
      "color_fondo": "#8a0c46",
      "color_letra": "#ffffff",
      "logo": "data:image/svg+xml;base64,...",
      "patron": "data:image/png;base64,...",
      "nombre_director": "SANDRA MILENA BARRIOS PULIDO",
      "firma_director": "data:image/png;base64,..."
    }
  }
}
```

#### `HTTP 404 Not Found` (Tarjeta no encontrada)
```json
{
  "detail": "Tarjeta digital no encontrada."
}
```

---

## 5. `GET /branding-credentials/info-published/{tipo_id}` - Branding Credencial Publicado

Retorna los elementos gráficos y paleta de colores oficialmente aprobados y vigentes para renderizar la tarjeta digital en el Wallet.

- **Método HTTP:** `GET`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/branding-credentials/info-published/{tipo_id}?client_id=20001`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/branding-credentials/info-published/{tipo_id}?client_id=20001`

### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Descripción | Ejemplo |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `tipo_id` | **Path** | `integer` | **Sí** | `1`: Contadores Públicos. <br> `2`: Sociedades de Contadores. | `1` |
| `client_id` | **Query** | `integer` | No | ID del cliente/tenant (UAE JCC: `20001`). Recomendado enviarlo siempre. | `20001` |

### Respuestas del Servidor

#### `HTTP 200 OK` (Éxito)
```json
{
  "tipo_id": 1,
  "version": 3,
  "color_fondo": "#8a0c46",
  "color_letra": "#ffffff",
  "color_letra_impresion": "#164fd4",
  "logo": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTEyIiBoZWlnaHQ9IjMyIiB2aWV3Qm94PSIwIDAgMTEyIDMyIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF...",
  "patron": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABLAAAASwCAYAAADrPX...",
  "logo_impresion": null,
  "patron_impresion": null,
  "nombre_director": "SANDRA MILENA BARRIOS PULIDO",
  "cargo_director": "DIRECTOR GENERAL",
  "firma_director": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIoAAABDCAYAAABDYJ0Y...",
  "observacion": "Aprobación versión oficial de branding para credenciales digitales"
}
```

#### `HTTP 404 Not Found`
```json
{
  "detail": "No existe una versión de branding publicada para el tipo de credencial solicitado."
}
```

---

## 6. `GET /branding-institucional/info-published` - Branding Institucional Publicado

Retorna de manera directa el nombre, cargo y firma facsímil del Director General vigente en la UAE Junta Central de Contadores.

- **Método HTTP:** `GET`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/branding-institucional/info-published?client_id=20001`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/branding-institucional/info-published?client_id=20001`

### Parámetros

| Parámetro | Ubicación | Tipo | Requerido | Descripción | Ejemplo |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `client_id` | **Query** | `integer` | No | ID del cliente/tenant (UAE JCC: `20001`). Recomendado enviarlo siempre. | `20001` |

### Respuestas del Servidor

#### `HTTP 200 OK` (Éxito)
```json
{
  "status": "success",
  "data": {
    "nombre_director": "SANDRA MILENA BARRIOS PULIDO",
    "cargo_director": "DIRECTOR GENERAL",
    "firma_director": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIoAAABDCAYAAABDYJ0Y...",
    "version": 1,
    "publicado": 1,
    "observacion": "Firma oficial autorizada para emisión y wallet digital"
  }
}
```

---

## 7. `POST /lecturas/registrar` - Ingesta de Lectura de Código QR

Registra el evento de auditoría cuando una credencial profesional es escaneada o consultada.

- **Método HTTP:** `POST`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/lecturas/registrar`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/lecturas/registrar`
- **Content-Type:** `application/json`

### Parámetros de Entrada (`Request Body`)

```json
{
  "documento_consultado": "1002345678",
  "documento_consultor": "987654321",
  "tipo_qr": "dinamico",
  "client_id": 20001
}
```

| Campo | Tipo | Requerido | Descripción |
| :--- | :--- | :---: | :--- |
| `documento_consultado` | `string` | **Sí** | Número de documento del titular consultado, o el hash SHA-256 extraído del QR (el backend resuelve automáticamente el documento del titular). |
| `documento_consultor` | `string` | No | Número de documento del usuario autenticado en la App Móvil que ejecuta el escaneo. En lecturas anónimas se omite o es `null`. |
| `tipo_qr` | `string` | No | `"dinamico"` (default, asigna automáticamente `origen = "Dispositivo móvil"`) o `"estatico"` (asigna `origen = "Navegador web"`). |
| `origen` | `string` | No | Permite especificar el origen de forma explícita: `"Dispositivo móvil"` o `"Navegador web"`. |
| `client_id` | `integer` | No | ID de la entidad cliente/tenant (UAE JCC: `20001`). Puede enviarse en Body o Query. |

### Respuestas del Servidor

#### `HTTP 201 Created` (Lectura Registrada)
```json
{
  "success": true,
  "mensaje": "Lectura registrada exitosamente.",
  "data": {
    "id": 142,
    "documento_consultado": "1002345678",
    "documento_consultor": "987654321",
    "origen": "Dispositivo móvil",
    "ip": "186.84.20.15"
  }
}
```

#### `HTTP 400 Bad Request` (Error en datos)
```json
{
  "detail": "El documento_consultado no corresponde a ninguna tarjeta registrada."
}
```

---

## 8. `GET /lecturas/historial` - Consulta de Historial de Lecturas QR

Consulta los eventos de lectura asociados a un usuario para alimentar las vistas de auditoría del titular.

- **Método HTTP:** `GET`
- **Ruta Gateway:** `/apig/tardigitales/admin/tarjetas/lecturas/historial?documento={documento}&filtro=me_consultaron&client_id=20001`
- **Ruta Microservicio:** `/tardigitales/admin/tarjetas/lecturas/historial?documento={documento}&filtro=me_consultaron&client_id=20001`

### Parámetros Query

| Parámetro | Tipo | Requerido | Valor por Defecto | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| `documento` | `string` | **Sí** | - | Documento de identidad del titular consultante. |
| `filtro` | `string` | No | `"me_consultaron"` | `"me_consultaron"` *(quiénes consultaron mi tarjeta)* o `"mis_consultas"` *(tarjetas que he consultado)*. |
| `limit` | `integer` | No | `20` | Cantidad máxima de registros a retornar (máximo `100`). |
| `offset` | `integer` | No | `0` | Desplazamiento para paginación incremental. |
| `client_id` | `integer` | No | `20001` | ID de la entidad cliente/tenant (UAE JCC: `20001`). Recomendado enviarlo siempre. |

### Respuestas del Servidor

#### `HTTP 200 OK` - Ejemplo con `filtro=me_consultaron`
```http
GET /apig/tardigitales/admin/tarjetas/lecturas/historial?documento=1002345678&filtro=me_consultaron&client_id=20001 HTTP/1.1
```

```json
{
  "success": true,
  "filtro": "me_consultaron",
  "total": 2,
  "data": [
    {
      "id": 142,
      "documento_consultado": "1002345678",
      "documento_consultor": "987654321",
      "origen": "Dispositivo móvil",
      "fecha": "2026-10-29 23:41:25",
      "ip": "186.84.20.15"
    },
    {
      "id": 141,
      "documento_consultado": "1002345678",
      "documento_consultor": null,
      "origen": "Navegador web",
      "fecha": "2026-10-29 21:15:02",
      "ip": "190.25.10.88"
    }
  ]
}
```

#### `HTTP 200 OK` - Ejemplo con `filtro=mis_consultas`
```http
GET /apig/tardigitales/admin/tarjetas/lecturas/historial?documento=987654321&filtro=mis_consultas&client_id=20001 HTTP/1.1
```

```json
{
  "success": true,
  "filtro": "mis_consultas",
  "total": 1,
  "data": [
    {
      "id": 142,
      "documento_consultado": "1002345678",
      "documento_consultor": "987654321",
      "origen": "Dispositivo móvil",
      "fecha": "2026-10-29 23:41:25",
      "ip": "186.84.20.15"
    }
  ]
}
```

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `success` | `boolean` | `true` si la consulta fue exitosa. |
| `filtro` | `string` | Filtro aplicado (`"me_consultaron"` o `"mis_consultas"`). |
| `total` | `integer` | Total de registros encontrados según el filtro. |
| `data[].id` | `integer` | ID autoincremental del registro en la tabla de auditoría. |
| `data[].documento_consultado` | `string` | Documento del titular de la credencial que fue escaneada. |
| `data[].documento_consultor` | `string \| null` | Documento del usuario que escaneó (`null` si fue verificación web anónima). |
| `data[].origen` | `string` | `"Dispositivo móvil"` o `"Navegador web"`. |
| `data[].fecha` | `string` | Fecha y hora en formato `YYYY-MM-DD HH:MM:SS` (hora oficial de Colombia UTC-5). |
| `data[].ip` | `string \| null` | Dirección IP capturada durante la consulta. |

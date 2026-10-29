# Microservicio de Tarjetas Digitales y Administración JCC (`ms_tardigitales_admin`)

> **Plataforma:** Junta Central de Contadores (JCC) - República de Colombia  
> **Tecnología:** Python 3.12 | FastAPI | Asynchronous I/O (Asyncio) | aiomysql | Redis 7 | Docker  
> **Host / Puerto Local:** `http://localhost:8000` (Enrutado por Gateway en puerto 80)  
> **Prefijo Global de Rutas:** `/tardigitales/admin`

---

## 1. Descripción del Proyecto

El microservicio **`ms_tardigitales_admin`** es el componente central de backend para la emisión, validación, control gráfico y ciclo de vida de las **Tarjetas de Registro Profesional Digital** de Contadores Públicos y Sociedades de Contadores en Colombia.

Cuenta con integración asíncrona a MariaDB, motor de colas en Redis para emisión masiva en segundo plano con Circuit Breaker, endpoints de auditoría transaccional, y servicios REST dedicados para el Microfrontend Web (`mfe_tardigitales_admin`) y la Aplicación Móvil (**Wallet JCC**).

---

## 2. Documentación Especializada para la App Móvil (Wallet JCC)

Para la integración exclusiva de la aplicación móvil (enrolamiento, activación por QR, notificaciones push FCM y renderizado offline), consulte la guía dedicada:  
👉 **[Guía de Integración API - Aplicación Móvil (Wallet JCC)](./README_APP_MOVIL.md)**

---

## 3. Arquitectura del Proyecto

```
ms_tardigitales_admin/
├── app/
│   ├── api/v1/routes/
│   │   ├── tarjetas.py          # Tarjetas, branding, QR, activación móvil y dashboard
│   │   ├── colas.py             # Telemetría de worker, lotes y sincronización JCC
│   │   ├── notificaciones.py    # Historial y envío de notificaciones
│   │   └── certificados.py      # Certificados digitales y descarga de PDF
│   ├── core/
│   │   ├── config.py            # Settings y variables de entorno
│   │   ├── database.py          # Pool aiomysql y multitenant
│   │   └── exceptions.py        # PipelineException y respuestas de error unificadas
│   ├── integrations/
│   │   └── jcc_client.py        # Cliente HTTP con reintentos para API externa JCC
│   ├── repositories/
│   │   └── tarjetas_repository.py # Capa de acceso a datos MariaDB
│   ├── schemas/
│   │   ├── tarjetas_schema.py   # DTOs y validaciones Pydantic
│   │   └── notificaciones_schema.py # Esquemas de eventos y plantillas
│   ├── services/
│   │   ├── tarjetas_service.py  # Lógica de credenciales, branding y estados
│   │   └── colas_service.py     # Procesamiento asíncrono y workers
│   └── main.py                  # Punto de entrada FastAPI y montaje de prefijos
├── docker-compose.yml           # Despliegue API + Redis 7
├── Dockerfile                   # Imagen ligera de producción (python:3.12-slim)
├── README.md                    # Catálogo y documentación técnica general
└── README_APP_MOVIL.md          # Manual de integración exclusivo App Móvil
```

---

## 4. Catálogo Detallado de Endpoints y Parámetros

Todos los endpoints se encuentran precedidos por el prefijo base del microservicio:  
`http://<host>:<port>/tardigitales/admin`

---

### 4.1. Módulo: Gestión y Emisión de Tarjetas Digitales (`/tarjetas`)

| Método | Endpoint Completo | Parámetros (Path / Query / Body) | Resp. HTTP | Descripción y Propósito |
| :---: | :--- | :--- | :---: | :--- |
| `GET` | `/tardigitales/admin/tarjetas/list` | **Query:**<br>• `tipo_tarjeta`: `"contadores"` o `"sociedades"`<br>• `page`: Número de página (int, default `1`)<br>• `page_size`: Tamaño de página (int, default `10`, max `100`)<br>• `texto`: Búsqueda libre (nombre, cédula o matrícula)<br>• `documento`: Filtro exacto por documento/NIT<br>• `estado`: `"Emitida"`, `"Activa"`, `"Cancelada"`<br>• `fecha_desde` / `fecha_hasta`: Rango `YYYY-MM-DD`<br>• `client_id`: ID de la entidad cliente (int) | `200 OK` | Consulta el listado paginado de credenciales registradas con filtros aplicados. |
| `GET` | `/tardigitales/admin/tarjetas/consult-registry` | **Query:**<br>• `documento` *(Requerido)*: Cédula o NIT.<br>• `tipo_tarjeta`: `"contadores"` o `"sociedades"`<br>• `client_id`: ID de la entidad cliente | `200 OK`<br>`404 Not Found` | Consulta la información oficial del contador/sociedad en JCC o en la base local para previsualizar antes de emitir. |
| `POST` | `/tardigitales/admin/tarjetas/create`<br>*(Alias: `/contador/create`, `/sociedad/create`)* | **Body (JSON):**<br>`{ "documento": "10203040", "nombres": "JUAN", "apellidos": "PEREZ", "matricula": "12345-T", "expediente": "5892", "tipo_tarjeta": "contadores", "correo_electronico": "juan@mail.com" }` | `201 Created`<br>`400 Bad Request` | Genera y emite oficialmente una nueva tarjeta digital, creando su código QR y token criptográfico SHA-256. |
| `GET` | `/tardigitales/admin/tarjetas/get/{id}` | **Path:**<br>• `id` (int): Identificador único de la tarjeta | `200 OK`<br>`404 Not Found` | Obtiene el detalle completo y trazabilidad de una tarjeta virtual por su ID. |
| `GET` | `/tardigitales/admin/tarjetas/verificar/{hash}`<br>*(Alias: `/get-by-hash/{hash}`)* | **Path:**<br>• `hash` (string): Token SHA-256 de la tarjeta | `200 OK`<br>`404 Not Found` | Endpoint público para verificar la autenticidad y vigencia de una tarjeta al escanear su código QR. |
| `GET` | `/tardigitales/admin/tarjetas/verificar/{hash}/pdf`<br>*(Alias: `/pdf/{id}`, `/get/{id}/pdf`)* | **Path:**<br>• `hash` o `id`: Identificador o token | `200 OK` (`application/pdf`) | Descarga en streaming el documento PDF oficial generado con estampados de seguridad y QR. |
| `POST` | `/tardigitales/admin/tarjetas/activar-movil` | **Body (JSON):**<br>`{ "token": "hash_sha256...", "client_id": 20001, "fcm_token": "token_push...", "device_id": "uuid...", "device_os": "android", "device_modelo": "Galaxy S23", "app_version": "1.0" }` | `200 OK`<br>`404 Not Found`<br>`409 Conflict` | Activa la tarjeta en la App Móvil (Wallet JCC), asocia el dispositivo y cambia el estado de `Emitida` a `Activa`. |
| `GET` | `/tardigitales/admin/tarjetas/historial/{id}` | **Path:**<br>• `id` (int): ID de la tarjeta | `200 OK` | Consulta la bitácora histórica de eventos (emisión, activación móvil, cambios de estado). |
| `GET` | `/tardigitales/admin/tarjetas/reportes/dashboard` | **Query:**<br>• `fecha_desde` / `fecha_hasta`: Rango `YYYY-MM-DD`<br>• `segmento`: `"all"`, `"accountants"`, `"companies"`<br>• `tipo_reporte`: `"general"`, `"cards"`<br>• `estado`: Filtro por estado<br>• `client_id`: ID de la entidad | `200 OK` | Entrega métricas analíticas consolidadas separando **estado de tarjeta** (Activa/Emitida/Cancelada) y **estado de registro** (Activo/Cancelada/Fallecido). |

---

### 4.2. Módulo: Configuración del Validador QR (`/tarjetas/validador-qr`)

| Método | Endpoint Completo | Parámetros | Resp. HTTP | Descripción y Propósito |
| :---: | :--- | :--- | :---: | :--- |
| `GET` | `/tardigitales/admin/tarjetas/validador-qr/get-config` | **Query:**<br>• `tipo_tarjeta`: `"contadores"` o `"sociedades"`<br>• `client_id`: ID de la entidad cliente | `200 OK` | Retorna los flags de visibilidad de los campos que deben mostrarse cuando un ciudadano escanea el QR público. |
| `POST` | `/tardigitales/admin/tarjetas/validador-qr/update-config` | **Body (JSON):**<br>`{ "tipo_tarjeta": "contadores", "val_nombres": true, "val_matricula": true, "val_estado": true, ... }` | `200 OK` | Actualiza la configuración de qué datos son públicos o privados en la pantalla de verificación QR. |

---

### 4.3. Módulo: Identidad Visual y Branding Vigente (`/tarjetas/branding-*`)

| Método | Endpoint Completo | Parámetros (Path / Query / Body) | Resp. HTTP | Descripción y Propósito |
| :---: | :--- | :--- | :---: | :--- |
| `GET` | `/tardigitales/admin/tarjetas/branding-credentials/info-published/{id}` | **Path:**<br>• `id` (int): `1` para Contadores, `2` para Sociedades.<br>**Query:**<br>• `client_id`: ID de la entidad cliente | `200 OK`<br>`404 Not Found` | **Retorna la apariencia oficial publicada vigente** de la tarjeta (colores `#hex`, logo SVG, patrón de fondo y firma directiva) libre de metadatos de auditoría interna. |
| `GET` | `/tardigitales/admin/tarjetas/branding-institucional/info-published`<br>*(Alias: `.../branding-credentials/institucional/info-published`)* | **Query:**<br>• `client_id`: ID de la entidad cliente | `200 OK` | **Retorna la firma institucional vigente** de la Directora General de la JCC (`nombre_director`, `cargo_director`, `firma_director` en Base64, versión). |
| `GET` | `/tardigitales/admin/tarjetas/branding-credentials/info/{id}` | **Path:**<br>• `id` (int): `1` (Contadores) o `2` (Sociedades) | `200 OK` | Retorna la versión en edición o borrador para la interfaz administrativa de Branding. |
| `POST` | `/tardigitales/admin/tarjetas/branding-credentials/create` | **Body (JSON):**<br>`{ "tipo_id": 1, "color_fondo": "#0b2240", "color_letra": "#ffffff", "logo": "data:image...", "patron": "data:image...", "observacion": "Ajuste color", "usuario_creacion_id": 1 }` | `201 Created` | Guarda una nueva versión de diseño en el historial sin reemplazar la versión publicada hasta su aprobación. |
| `PUT` | `/tardigitales/admin/tarjetas/branding-credentials/update/change-version/{id}` | **Path:**<br>• `id` (int): ID o tipo.<br>**Body (JSON):**<br>`{ "version_publicada": 3, "observacion": "Aprobación oficial comité" }` | `200 OK` | **Publica formalmente** una versión existente para convertirla en el diseño vigente en producción. |
| `GET` | `/tardigitales/admin/tarjetas/branding-credentials/list-history-versions/{id}` | **Path:**<br>• `id` (int): `1` o `2`.<br>**Query:**<br>• `page` (int, default `1`), `page_size` (int, default `10`) | `200 OK` | Historial completo de versiones registradas con fecha, usuario creador y estado de publicación. |
| `POST` | `/tardigitales/admin/tarjetas/branding-institucional/create` | **Body (JSON):**<br>`{ "nombre_director": "SANDRA MILENA BARRIOS PULIDO", "cargo_director": "DIRECTOR GENERAL", "firma_director": "data:image/png;base64...", "observacion": "Resolución de posesión" }` | `201 Created` | Crea una nueva versión de firma institucional para la entidad. |
| `PUT` | `/tardigitales/admin/tarjetas/branding-institucional/update/change-version/{id}` | **Path:**<br>• `id`: Versión institucional a publicar | `200 OK` | Publica la versión institucional seleccionada como la firma oficial vigente. |

---

### 4.4. Módulo: Procesamiento Asíncrono y Emisión Masiva (`/emision-masiva` y `/colas`)

| Método | Endpoint Completo | Parámetros (Path / Form / Body) | Resp. HTTP | Descripción y Propósito |
| :---: | :--- | :--- | :---: | :--- |
| `POST` | `/tardigitales/admin/tarjetas/emision-masiva` | **Form-Data:**<br>• `file`: Archivo CSV con números de documento/NIT.<br>• `tipo_tarjeta`: `"contadores"` o `"sociedades"`<br>• `client_id`: ID de la entidad cliente | `200 OK` | Recibe el archivo de emisión masiva, valida registros y encola el lote asíncrono en Redis retornando el `lote_id`. |
| `GET` | `/tardigitales/admin/tarjetas/emision-masiva/lote/{lote_id}` | **Path:**<br>• `lote_id` (int): ID del lote en procesamiento | `200 OK`<br>`404 Not Found` | Permite consultar el porcentaje de avance, cantidad de registros procesados, exitosos y fallidos en tiempo real. |
| `GET` | `/tardigitales/admin/colas/metricas` | Ninguno | `200 OK` | Retorna la telemetría del worker en segundo plano, número de tareas pendientes en Redis y estado del Circuit Breaker. |
| `POST` | `/tardigitales/admin/colas/sincronizar-estados` | **Body opcional:** Parámetros de sincronización | `200 OK` | Ejecuta un barrido en segundo plano para verificar y sincronizar el estado de todas las tarjetas con la base oficial de JCC. |

---

### 4.5. Módulo: Historial de Notificaciones (`/notificaciones`)

| Método | Endpoint Completo | Parámetros | Resp. HTTP | Descripción y Propósito |
| :---: | :--- | :--- | :---: | :--- |
| `GET` | `/tardigitales/admin/notificaciones/list` | **Query:**<br>• `page`: Número de página (default `1`)<br>• `page_size`: Tamaño de página (default `10`)<br>• `tipo`: `"email"`, `"push"`, `"sms"`<br>• `estado`: `"Enviado"`, `"Fallido"`, `"Pendiente"` | `200 OK` | Retorna el historial de notificaciones masivas o individuales enviadas por el sistema. |
| `POST` | `/tardigitales/admin/notificaciones/create` | **Body (JSON):**<br>`{ "destinatario": "correo@ejemplo.com", "tipo": "email", "asunto": "Emisión Tarjeta", "mensaje": "..." }` | `201 Created` | Encola el despacho de una notificación por correo o push. |
| `GET` | `/tardigitales/admin/notificaciones/{id}` | **Path:**<br>• `id` (int): ID de la notificación | `200 OK` | Detalle específico y log de auditoría del envío. |

---

### 4.6. Módulo: Certificados Digitales (`/certificados`)

| Método | Endpoint Completo | Parámetros | Resp. HTTP | Descripción y Propósito |
| :---: | :--- | :--- | :---: | :--- |
| `GET` | `/tardigitales/admin/certificados` | **Query:**<br>• `page`, `page_size`, `documento`, `estado` | `200 OK` | Lista de certificados de vigencia y antecedentes expedidos. |
| `GET` | `/tardigitales/admin/certificados/{n_certificado}` | **Path:**<br>• `n_certificado` (string): Número consecutivo | `200 OK` | Consulta el detalle y vigencia legal del certificado. |
| `GET` | `/tardigitales/admin/certificados/{n_certificado}/pdf` | **Path:**<br>• `n_certificado` (string) | `200 OK` (`application/pdf`) | Descarga el PDF oficial del certificado con firma digital y estampilla cronológica. |

---

## 5. Configuración y Variables de Entorno (`.env`)

Cree o ajuste el archivo `.env` en la raíz de `ms_tardigitales_admin`:

```env
# Configuración del Servicio
ENVIRONMENT=production
DEBUG=False
PORT=8080

# Base de Datos MariaDB / MySQL
DB_HOST=host.docker.internal
DB_PORT=3306
DB_USER=root
DB_PASSWORD=secret
DB_NAME=producto9_base
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20

# Redis (Colas Asíncronas y Caché)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Integración Externa JCC
JCC_API_BASE_URL=https://api.jcc.gov.co/v1
JCC_API_TOKEN=your_secure_bearer_token_here
```

---

## 6. Despliegue y Comandos Útiles

### Compilar y levantar contenedores en segundo plano:
```bash
docker compose up -d --build
```

### Consultar registros (logs) en tiempo real:
```bash
docker compose logs -f api
```

### Reiniciar el servicio backend:
```bash
docker compose restart api
```

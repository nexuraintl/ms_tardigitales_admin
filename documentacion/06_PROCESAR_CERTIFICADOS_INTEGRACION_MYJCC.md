# Especificación Técnica: POST /apig/tardigitales/admin/certificados/procesar

Documentación técnica para la integración y consumo del endpoint de procesamiento y descarga de certificados por parte de terceros.

---

## 1. Endpoint y Protocolo

* **Ambiente (Preproducción):** `https://preproduccion9-jcc.nexura.com.co`
* **Ruta:** `/apig/tardigitales/admin/certificados/procesar`
* **Método:** `POST`
* **Autenticación:** `Bearer Token`
* **Headers:**
  * `Authorization: Bearer <access_token>`
  * `Content-Type: application/json`
  * `Accept: application/pdf`
* **Respuesta Exitosa:** `200 OK` (Stream binario del archivo PDF).

---

## 2. Autenticación (Obtención de Token)

Endpoint para generar el token JWT antes de consumir los servicios protegidos.

* **URL:** `POST https://preproduccion9-jcc.nexura.com.co/apig/core/auth/token`
* **Headers:**
  * `Content-Type: application/json`

### Body (raw JSON):
```json
{
  "client_id": "20001",
  "user": "tu_usuario",
  "password": "tu_password"
}
```

### Respuesta (`200 OK`):
```json
{
  "authenticated": true,
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...",
  "token_type": "Bearer"
}
```

El valor de `access_token` debe enviarse en la cabecera HTTP:
```http
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6Ij...
```

---

## 3. Especificación de Parámetros (`/certificados/procesar`)

### Objeto Raíz (JSON)

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `Nuevo` | Boolean | Sí | `true` para primera emisión. `false` para redescarga o reimpresión de certificado existente. |
| `tipo` | String | Sí | Tipo de titular: `"contador"` o `"sociedad"`. |
| `documento` | String | Sí | Número de identificación (Cédula de Ciudadanía o NIT sin dígito de verificación). |
| `N_CERTIFICADO` | String | Sí | Número o consecutivo único del certificado (ej. `"CERT-2026-00458"`). |
| `fechaGeneracion`| String | No | Fecha de emisión en formato `YYYY-MM-DD`. Por defecto toma la fecha actual del sistema. |
| `historia` | String | No | Años de historial de antecedentes a evaluar. Valor por defecto: `"5"`. |
| `dirigido` | String | No | Destinatario del certificado. Valor por defecto: `"A QUIEN INTERESE"`. |
| `Detalles` | Object | Sí | Objeto JSON con los atributos del titular y su historial disciplinario. |

---

### Objeto `Detalles` para Contador (`tipo: "contador"`)

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `CON_NOMBRES` | String | Sí | Nombres del contador. |
| `CON_APELLIDO1` | String | Sí | Primer apellido. |
| `CON_APELLIDO2` | String | No | Segundo apellido. |
| `CON_TIPO_DOCUMENTO` | String | Sí | Tipo de documento (`"CC"`, `"CE"`, `"PAS"`). |
| `CON_NRO_TARJETA` | String | Sí | Número de tarjeta profesional (ej. `"123456-T"`). |
| `CON_TIPO_TARJETA` | String | Sí | Categoría de la tarjeta (`"T"` para Titulado, `"P"` para Práctico). |
| `CON_SEXO` | String | No | `"M"` o `"F"`. |
| `MUNICIPIO_DOCUMENTO` | String | No | Municipio de expedición del documento. |
| `DEPARTAMENTO_DOCUMENTO` | String | No | Departamento de expedición del documento. |
| `CON_FECHA_EXPEDICION` | String | No | Fecha de expedición de la tarjeta (`YYYY-MM-DD`). |
| `ESTADO` | String | Sí | Estado del registro (ej. `"ACTIVO"`). |
| `EMAIL` | String | No | Correo electrónico del contador. |
| `SOLICITANTE` | String | No | Nombre de la entidad o persona que solicita el certificado. |
| `ANTECEDENTES` | Array | Sí | Lista de sanciones registradas (vacía `[]` si no registra antecedentes). |

---

### Objeto `Detalles` para Sociedad (`tipo: "sociedad"`)

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `SOC_RAZON_SOCIAL` | String | Sí | Razón social o denominación de la sociedad de contadores. |
| `SOC_CODIGO` | String | Sí | Código de registro de la sociedad en la JCC. |
| `SOC_REPRESENTANTE_LEGAL`| String | Sí | Nombre completo del representante legal. |
| `SOC_TIPO_DOCUMENTO_REP` | String | No | Tipo de documento del representante legal (`"CC"`, `"CE"`). |
| `SOC_DOCUMENTO_REP` | String | No | Número de identificación del representante legal. |
| `MUNICIPIO` | String | No | Municipio del domicilio de la sociedad. |
| `DEPARTAMENTO` | String | No | Departamento del domicilio de la sociedad. |
| `ESTADO` | String | Sí | Estado del registro (ej. `"ACTIVO"`). |
| `EMAIL` | String | No | Correo electrónico corporativo. |
| `SOLICITANTE` | String | No | Nombre de la entidad o persona solicitante. |
| `ANTECEDENTES` | Array | Sí | Lista de sanciones registradas (vacía `[]` si no registra antecedentes). |

---

### Estructura de Elementos en `ANTECEDENTES`

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :---: | :--- |
| `SAN_TIPO` | String | Sí | Tipo de sanción (`"SUSPENSION"`, `"CANCELACION"`, `"AMONESTACION"`). |
| `SAN_MESES` | Integer/String | No | Duración de la sanción en meses (si aplica). |
| `SAN_RESOLUCION` | String | Sí | Número de la resolución sancionatoria. |
| `SAN_FECHA_RESOLUCION`| String | No | Fecha de expedición de la resolución (`YYYY-MM-DD`). |
| `SAN_FECHA_EJECUTORIA` | String | No | Fecha de ejecutoria del acto administrativo (`YYYY-MM-DD`). |
| `SAN_FECHA_FIN` | String | No | Fecha de culminación de la sanción (`YYYY-MM-DD`). |

---

## 4. Ejemplos de Payload

### Ejemplo 1: Emisión Certificado Contador (Sin Antecedentes)
```json
{
  "Nuevo": true,
  "tipo": "contador",
  "documento": "1018412345",
  "N_CERTIFICADO": "CERT-2026-00458",
  "fechaGeneracion": "2026-10-15",
  "historia": "5",
  "dirigido": "A QUIEN INTERESE",
  "Detalles": {
    "CON_NOMBRES": "CARLOS ANDRES",
    "CON_APELLIDO1": "PEREZ",
    "CON_APELLIDO2": "GOMEZ",
    "CON_TIPO_DOCUMENTO": "CC",
    "CON_NRO_TARJETA": "123456-T",
    "CON_TIPO_TARJETA": "T",
    "CON_SEXO": "M",
    "MUNICIPIO_DOCUMENTO": "BOGOTA D.C.",
    "DEPARTAMENTO_DOCUMENTO": "BOGOTA D.C.",
    "CON_FECHA_EXPEDICION": "2018-05-20",
    "ESTADO": "ACTIVO",
    "EMAIL": "carlos.perez@ejemplo.com",
    "SOLICITANTE": "EMPRESA AUDITORA S.A.S.",
    "ANTECEDENTES": []
  }
}
```

### Ejemplo 2: Emisión Certificado Sociedad (Con Antecedentes)
```json
{
  "Nuevo": true,
  "tipo": "sociedad",
  "documento": "900123456",
  "N_CERTIFICADO": "CERT-SOC-2026-00102",
  "fechaGeneracion": "2026-10-15",
  "historia": "5",
  "dirigido": "A QUIEN INTERESE",
  "Detalles": {
    "SOC_RAZON_SOCIAL": "AUDITORES Y ASESORES CONTABLES S.A.S.",
    "SOC_CODIGO": "SOC-90012",
    "SOC_REPRESENTANTE_LEGAL": "MARIA FERNANDA LOPEZ",
    "SOC_TIPO_DOCUMENTO_REP": "CC",
    "SOC_DOCUMENTO_REP": "52987654",
    "MUNICIPIO": "MEDELLIN",
    "DEPARTAMENTO": "ANTIOQUIA",
    "ESTADO": "ACTIVO",
    "EMAIL": "contacto@auditoresasesores.com",
    "SOLICITANTE": "BANCO DE COMERCIO",
    "ANTECEDENTES": [
      {
        "SAN_TIPO": "SUSPENSION",
        "SAN_MESES": 12,
        "SAN_RESOLUCION": "RES-2024-089",
        "SAN_FECHA_RESOLUCION": "2024-03-10",
        "SAN_FECHA_EJECUTORIA": "2024-04-01",
        "SAN_FECHA_FIN": "2025-04-01"
      }
    ]
  }
}
```

### Ejemplo 3: Redescarga de Certificado Preexistente
```json
{
  "Nuevo": false,
  "tipo": "contador",
  "documento": "1018412345",
  "N_CERTIFICADO": "CERT-2026-00458",
  "fechaGeneracion": "2026-10-15",
  "historia": "5",
  "dirigido": "A QUIEN INTERESE",
  "Detalles": {
    "CON_NOMBRES": "CARLOS ANDRES",
    "CON_APELLIDO1": "PEREZ",
    "CON_APELLIDO2": "GOMEZ",
    "CON_TIPO_DOCUMENTO": "CC",
    "CON_NRO_TARJETA": "123456-T",
    "CON_TIPO_TARJETA": "T",
    "ESTADO": "ACTIVO",
    "ANTECEDENTES": []
  }
}
```

---

## 5. Códigos de Respuesta HTTP

### 200 OK
* **Content-Type:** `application/pdf`
* **Content-Disposition:** `attachment; filename="certificado-CERT-2026-00458.pdf"`
* **Headers:**
  * `X-Numero-Certificado`: Código del certificado emitido/recuperado.
  * `X-Origen-Documento`: `GENERADO` o `REGENERADO`.
* **Body:** Archivo binario en formato PDF.

### 401 Unauthorized
Token de autenticación no suministrado, inválido o expirado.
```json
{
  "detail": "Could not validate credentials"
}
```

### 422 Unprocessable Entity
Error de validación de esquema en la petición. Indica campo faltante o formato incorrecto.
```json
{
  "detail": [
    {
      "loc": ["body", "tipo"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```



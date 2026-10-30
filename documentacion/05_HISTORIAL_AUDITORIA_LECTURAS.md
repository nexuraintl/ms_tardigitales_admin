# Endpoint 05: Gestión de Registro y Consulta de Auditoría (Lecturas QR)

> **Destinatario / Consumo:** Modelos de IA (Claude / LLM), Ingenieros Backend y Desarrollador Móvil (Flutter / Dart).  
> **Servicio:** `ms_tardigitales_admin` (`app/api/v1/routes/tarjetas.py`).  
> **Funciones de Ruta:** `registrar_lectura` y `get_historial_lecturas`.  
> **Esquemas:** `RegistroLecturaRequestSchema`, `ConsultaHistorialLecturasResponseSchema` (`app/schemas/tarjetas_schema.py`).  
> **Tabla Principal:** `tn_tarjetavirtual_lecturas_historial`.

---

## 1. Visión General de la Historia de Usuario

Permite a los profesionales contadores y sociedades registradas contar con trazabilidad transparente sobre quién ha accedido a su información profesional mediante lectura de códigos QR.

### Reglas de Negocio Implementadas:
1. **Clasificación Automática de Origen:**
   - **`Dispositivo móvil`** (17:34): Cuando la lectura proviene del escáner de QR dinámico dentro de la App Móvil institucional (`tipo_qr = "dinamico"`).
   - **`Navegador web`** (17:39): Cuando la consulta proviene de la lectura de QR estático que abre el navegador web, o de la consulta en el portal web público (`tipo_qr = "estatico"`).
3. **Diferenciación de Pestañas en la App Móvil (14:09):**
   - **`me_consultaron`** *(¿Quién vio mi perfil?)*: Filtra por `documento_consultado == mi_documento`.
   - **`mis_consultas`** *(¿A quién he consultado yo?)*: Filtra por `documento_consultor == mi_documento`.
4. **Auto-registro en Portal Web:**
   - Cada vez que un usuario o tercero consulta la URL pública `GET /apig/tardigitales/admin/tarjetas/verificar?token=<hash>`, el microservicio auto-registra el evento en segundo plano como `origen = "Navegador web"`, `quien_consulto = "Público general"` y `etiqueta = "verificación pública exitosa"`.
5. **Compatibilidad con Panel MFE Web:**
   - El endpoint `GET /apig/tardigitales/admin/tarjetas/historial/{id}` consume directamente esta tabla por documento del titular para alimentar la columna *"Historial de lecturas del QR"* de contadores y sociedades.

---

## 2. Definición de Endpoints HTTP

### A. Endpoint de Ingesta (Registro de Lectura)

- **Método:** `POST`
- **Ruta Oficial:** `/apig/tardigitales/admin/tarjetas/lecturas/registrar`
- **Ruta Directa Microservicio:** `/tardigitales/admin/tarjetas/lecturas/registrar`
- **Content-Type:** `application/json`
- **Status Code Exitoso:** `201 Created`

#### Contrato JSON de Entrada (Request Body):
```json
{
  "documento_consultado": "1002345678",
  "documento_consultor": "987654321",
  "tipo_qr": "dinamico"
}
```

| Parámetro | Tipo | Requerido | Descripción |
|---|---|:---:|---|
| `documento_consultado` | `string` | **Sí** | Número de documento (Cédula o NIT) del titular consultado, o token/hash SHA-256 escaneado del QR. |
| `documento_consultor` | `string` | No | Número de documento del profesional autenticado en la App Móvil que realiza el escaneo. En consultas anónimas/públicas se omite o viaja `null`. |
| `tipo_qr` | `string` | No (default: `"dinamico"`) | `"dinamico"` (asigna origen `"Dispositivo móvil"`) o `"estatico"` (asigna origen `"Navegador web"`). |
| `origen` | `string` | No | Permite forzar el origen explícito: `"Dispositivo móvil"` o `"Navegador web"`. |
| `client_id` | `integer` | No | ID del Tenant/Cliente (default: `20001`). |

#### Respuesta Exitosa (`HTTP 201 Created`):
```json
{
  "success": true,
  "mensaje": "Lectura registrada exitosamente.",
  "data": {
    "id": 1,
    "documento_consultado": "1002345678",
    "documento_consultor": "987654321",
    "origen": "Dispositivo móvil",
    "ip": "186.84.20.15"
  }
}
```

---

### B. Endpoint de Visualización (Historial de Consultas App Móvil)

- **Método:** `GET`
- **Ruta Oficial:** `/apig/tardigitales/admin/tarjetas/lecturas/historial`
- **Ruta Directa Microservicio:** `/tardigitales/admin/tarjetas/lecturas/historial`
- **Content-Type:** `application/json`
- **Status Code Exitoso:** `200 OK`

#### Parámetros Query:
| Parámetro | Tipo | Requerido | Descripción | Ejemplo |
|---|---|:---:|---|---|
| `documento` | `string` | **Sí** | Cédula o NIT del usuario que consulta su historial. | `1002345678` |
| `filtro` | `string` | No (default: `"me_consultaron"`) | `"me_consultaron"` (quién vio mi perfil) o `"mis_consultas"` (a quién he consultado). | `me_consultaron` |
| `limit` | `integer` | No (default: `20`) | Cantidad de registros por página (máx. 100). | `20` |
| `offset` | `integer` | No (default: `0`) | Desplazamiento para paginación. | `0` |
| `client_id` | `integer` | No | ID del Tenant/Cliente. | `20001` |

#### Respuesta Exitosa (`HTTP 200 OK` - Pestaña "Me consultaron"):
```json
{
  "success": true,
  "filtro": "me_consultaron",
  "total": 2,
  "data": [
    {
      "id": 2,
      "documento_consultado": "1002345678",
      "documento_consultor": null,
      "origen": "Navegador web",
        "fecha": "2026-10-30 09:12:45",
      "ip": "186.84.20.15"
    },
    {
      "id": 1,
      "documento_consultado": "1002345678",
      "documento_consultor": "987654321",
      "origen": "Dispositivo móvil",
        "fecha": "2026-10-29 17:34:10",
      "ip": "190.25.10.88"
    }
  ]
}
```

#### Respuesta Exitosa (`HTTP 200 OK` - Pestaña "Mis consultas"):
```json
{
  "success": true,
  "filtro": "mis_consultas",
  "total": 1,
  "data": [
    {
      "id": 1,
      "documento_consultado": "1002345678",
      "documento_consultor": "987654321",
      "origen": "Dispositivo móvil",
        "fecha": "2026-10-29 17:34:10",
      "ip": "190.25.10.88"
    }
  ]
}
```

---

## 3. Modelo de Base de Datos (`producto9_base`)

```sql
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_lecturas_historial` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `documento_consultado` VARCHAR(50) NOT NULL,
  `documento_consultor` VARCHAR(50) NULL,
  `origen` ENUM('Dispositivo móvil', 'Navegador web') NOT NULL,
  `ip` VARCHAR(45) NULL,
  `fecha` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_lect_consultado` (`documento_consultado`, `fecha`),
  KEY `idx_lect_consultor` (`documento_consultor`, `fecha`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 4. Ejemplo de Integración en Flutter / Dart (App Móvil)

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class AuditoriaLecturasService {
  static const String baseUrl = 'http://local-jcc.nexura.com.co/apig/tardigitales/admin/tarjetas';

  /// 1. Registrar lectura al escanear QR dinámico de otro profesional
  static Future<bool> registrarLecturaEscaneo({
    required String documentoConsultado,
    required String miDocumento,
  }) async {
    final url = Uri.parse('$baseUrl/lecturas/registrar');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json', 'X-Tenant-Id': 'jcc'},
      body: jsonEncode({
        'documento_consultado': documentoConsultado,
        'documento_consultor': miDocumento,
        'tipo_qr': 'dinamico',
      }),
    );
    return response.statusCode == 201;
  }

  /// 2. Consultar historial ("me_consultaron" o "mis_consultas")
  static Future<Map<String, dynamic>> obtenerHistorial({
    required String miDocumento,
    String filtro = 'me_consultaron', // 'me_consultaron' | 'mis_consultas'
    int limit = 20,
    int offset = 0,
  }) async {
    final url = Uri.parse(
      '$baseUrl/lecturas/historial?documento=$miDocumento&filtro=$filtro&limit=$limit&offset=$offset'
    );
    final response = await http.get(
      url,
      headers: {'Accept': 'application/json', 'X-Tenant-Id': 'jcc'},
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } else {
      throw Exception('Error al consultar historial de lecturas');
    }
  }
}
```


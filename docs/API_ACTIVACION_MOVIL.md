# Guía de Integración para App Móvil: Activación de Tarjeta Digital (HU-JCC-014)

> **Destinatario**: Desarrollador Móvil (Alejo)  
> **Servicio**: Microservicio Tarjetas Digitales (`ms_tardigitales_admin`)  
> **Arquitectura**: FastAPI + MariaDB + Firebase Cloud Messaging (FCM)  

---

## 1. Visión General del Flujo

1. **Lectura del QR**: El usuario titular abre la App Móvil institucional (Flutter / Nativo) y escanea el código QR de su credencial física o PDF de bienvenida.
2. **Extracción del Token**:
   - Si el QR contiene la URL pública de validación (ej. `http://local-jcc.nexura.com.co/admin/tardigitales/verificar?token=<HASH_SHA256>`), la app extrae el parámetro `token`.
   - Si el QR contiene directamente el Hash SHA-256 de 64 caracteres, se toma directamente.
3. **Petición de Activación**: La App Móvil obtiene el token de Firebase Cloud Messaging (`fcm_token`) y los metadatos del dispositivo (`device_id`, `device_os`, `device_modelo`, `app_version`), y realiza un `POST` al endpoint oficial.
4. **Respuesta del Servidor**:
   - El microservicio valida la credencial y su vigencia.
   - Pasa el estado de `"Emitida"` a `"Activa"`.
   - Registra el dispositivo y su token push en `tn_tarjetavirtual_dispositivos`.
   - Guarda el evento en la auditoría/historial (`tn_tarjetavirtual_estados_historial`).
   - Retorna en un solo payload los **datos completos del titular** y la **configuración oficial de Branding publicada** (colores, gradientes, logos en Base64, firma del Director General) para que la app renderice de inmediato la tarjeta en la billetera digital (Wallet).

---

## 2. Especificación Técnica del Endpoint

### **POST** `/apig/tardigitales/admin/tarjetas/activar-movil`

- **URL Base Entorno Local/Preproducción**:
  ```http
  http://local-jcc.nexura.com.co/apig/tardigitales/admin/tarjetas/activar-movil
  ```
- **Content-Type**: `application/json`
- **Headers Obligatorios**:
  - `Content-Type: application/json`
  - `X-Tenant-Id: jcc` *(opcional si se envía `client_id` en el body, default: 20001)*

---

## 3. Contrato de Entrada (Request Body)

| Campo | Tipo | Requerido | Descripción | Ejemplo |
| :--- | :--- | :---: | :--- | :--- |
| `token` | `string` | **Sí** | Hash SHA-256 de 64 caracteres hex escaneado del QR | `"a5339002552bc8b6411b21e6383ad1dc1ec8789e9d6fc8ccd0251bbbc17074cf"` |
| `fcm_token` | `string` | No (Recomendado) | Token de registro FCM obtenido de Firebase Messaging | `"c_qXy... (token de Firebase)"` |
| `device_id` | `string` | No (Recomendado) | UUID único o hardware ID del dispositivo móvil | `"9a1b2c3d-4e5f-6789-abcd-ef0123456789"` |
| `device_os` | `string` | No | Sistema operativo del dispositivo (`android` o `ios`) | `"android"` |
| `device_modelo`| `string`| No | Modelo comercial del dispositivo | `"Samsung Galaxy S23"` o `"iPhone 15 Pro"` |
| `app_version` | `string` | No | Versión instalada de la aplicación móvil | `"1.0.0"` |
| `client_id` | `integer` | No | ID del Tenant/Cliente (default `20001` - JCC) | `20001` |

### Ejemplo JSON de Petición:
```json
{
  "token": "a5339002552bc8b6411b21e6383ad1dc1ec8789e9d6fc8ccd0251bbbc17074cf",
  "fcm_token": "fH9_K8s9Q4A:APA91bF8d...ejemplo_token_firebase",
  "device_id": "4b63897d-6dc8-4179-8438-fb1c86940a02",
  "device_os": "android",
  "device_modelo": "Xiaomi 13 Pro",
  "app_version": "1.0.2",
  "client_id": 20001
}
```

---

## 4. Contrato de Salida (Response)

### Respuesta Exitosa: `HTTP 200 OK`
```json
{
  "success": true,
  "mensaje": "Credencial digital activada exitosamente en el dispositivo móvil.",
  "data": {
    "tarjeta": {
      "id": 98,
      "tipo_tarjeta": "contadores",
      "no_tarjeta": "320890-T",
      "nombres": "ARIS PAOLA",
      "primer_apellido": "HERRERA",
      "segundo_apellido": "RODRIGUEZ",
      "nombre_completo": "ARIS PAOLA HERRERA RODRIGUEZ",
      "tipo_documento": "CC",
      "no_documento": "1002345678",
      "no_expd": "2024-EXP-0012",
      "universidad": "UNIVERSIDAD NACIONAL DE COLOMBIA",
      "resolucion": "0292",
      "fecha_resolucion": "2024-03-15",
      "seccional": "BOGOTA D.C.",
      "fecha_emision": "2026-10-14",
      "correo": "titular@correo.com",
      "estado_tarjeta": "Activa",
      "foto": "data:image/jpeg;base64,...",
      "hash_sha256": "a5339002552bc8b6411b21e6383ad1dc1ec8789e9d6fc8ccd0251bbbc17074cf"
    },
    "branding": {
      "id": 1,
      "tipo_tarjeta": "contadores",
      "background_color_start": "#0f172a",
      "background_color_end": "#1e3a8a",
      "background_angle": 135,
      "color_primary": "#2563eb",
      "color_secondary": "#1d4ed8",
      "text_color": "#ffffff",
      "logo_header": "data:image/png;base64,...",
      "nombre_director": "DR. CARLOS ALBERTO MARTÍNEZ",
      "cargo_director": "DIRECTOR GENERAL UAE JCC",
      "firma_director": "data:image/png;base64,..."
    },
    "dispositivo": {
      "device_id": "4b63897d-6dc8-4179-8438-fb1c86940a02",
      "device_os": "android",
      "fcm_token_registrado": true
    }
  }
}
```

> **Nota de Idempotencia**: Si la tarjeta ya se encontraba en estado `"Activa"` (por ejemplo si el usuario reinstaló la aplicación o cambió de teléfono), el servicio responderá igualmente `HTTP 200 OK` con el mensaje:
> `"Credencial ya se encontraba activa. Dispositivo móvil sincronizado."`
> y actualizará el nuevo `fcm_token` y metadatos del dispositivo en la tabla satélite.

---

## 5. Respuestas de Error y Manejo en la App

| Código HTTP | Motivo | Body de Error | Acción recomendada en App |
| :---: | :--- | :--- | :--- |
| **404 Not Found** | El token QR no existe en la base de datos | `{"detail": "Credencial digital no encontrada con el token proporcionado."}` | Mostrar alerta: *"El código QR escaneado no corresponde a una credencial válida o registrada."* |
| **409 Conflict** | La credencial está suspendida, cancelada o inactiva | `{"detail": "La credencial digital se encuentra en estado 'Cancelada' y no puede ser activada."}` | Mostrar alerta: *"Esta credencial no puede ser activada debido a su estado actual. Comuníquese con la JCC."* |
| **422 Unprocessable Entity** | Faltan campos requeridos en el body (ej. `token`) | `{"detail": [{"loc": ["body", "token"], "msg": "Field required"}]}` | Validar que el token escaneado sea un string no vacío. |
| **500 Internal Error** | Error de conexión de base de datos | `{"status": "error", "message": "..."}` | Reintentar o reportar error temporal de red. |

---

## 6. Ejemplo de Implementación en Flutter / Dart

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'dart:io';

Future<Map<String, dynamic>?> activarTarjetaMovil(String qrTokenScanned) async {
  // 1. Obtener FCM Token de Firebase
  String? fcmToken = await FirebaseMessaging.instance.getToken();

  // 2. Obtener metadatos del dispositivo físico
  final deviceInfo = DeviceInfoPlugin();
  String deviceId = 'unknown';
  String deviceModelo = 'unknown';
  String deviceOs = Platform.isAndroid ? 'android' : (Platform.isIOS ? 'ios' : 'other');

  if (Platform.isAndroid) {
    final androidInfo = await deviceInfo.androidInfo;
    deviceId = androidInfo.id;
    deviceModelo = '${androidInfo.brand} ${androidInfo.model}';
  } else if (Platform.isIOS) {
    final iosInfo = await deviceInfo.iosInfo;
    deviceId = iosInfo.identifierForVendor ?? 'unknown';
    deviceModelo = iosInfo.utsname.machine;
  }

  // 3. Petición POST al Microservicio
  final url = Uri.parse('http://local-jcc.nexura.com.co/apig/tardigitales/admin/tarjetas/activar-movil');
  
  final response = await http.post(
    url,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': 'jcc',
    },
    body: jsonEncode({
      'token': qrTokenScanned,
      'fcm_token': fcmToken,
      'device_id': deviceId,
      'device_os': deviceOs,
      'device_modelo': deviceModelo,
      'app_version': '1.0.0',
    }),
  );

  if (response.statusCode == 200) {
    final body = jsonDecode(utf8.decode(response.bodyBytes));
    print('Activación exitosa: ${body["mensaje"]}');
    return body["data"]; // Contiene {tarjeta, branding, dispositivo}
  } else {
    final error = jsonDecode(utf8.decode(response.bodyBytes));
    throw Exception(error["detail"] ?? "Error al activar tarjeta");
  }
}
```

---

## 7. Buenas Prácticas Recomendadas para Alejo

1. **Almacenamiento Seguro (Keychain / EncryptedSharedPreferences)**:
   - Guardar el `hash_sha256` y los datos del titular usando `flutter_secure_storage` para habilitar acceso offline al Wallet.
2. **Branding Dinámico**:
   - Guardar los colores y logos en caché local para que la tarjeta se dibuje con el branding oficial incluso si el usuario no tiene conexión a internet.
3. **Renovación del Token FCM**:
   - Escuchar `FirebaseMessaging.instance.onTokenRefresh`. Si el token de Firebase cambia, invocar nuevamente el endpoint para mantener el dispositivo sincronizado para las notificaciones push de revocación o renovación.

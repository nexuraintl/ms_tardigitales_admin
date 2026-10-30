# Guía de Integración API - Aplicación Móvil (Wallet JCC)

> **Documento Oficial Unificado:** [`documentacion/API_MOVIL_WALLET_JCC.md`](./documentacion/API_MOVIL_WALLET_JCC.md)  
> **Microservicio:** `ms_tardigitales_admin` (FastAPI + MariaDB)  
> **Host Base (Gateway):** `http://local-jcc.nexura.com.co/apig/tardigitales/admin/tarjetas`  
> **Ruta Directa Microservicio:** `http://<host>:8000/tardigitales/admin/tarjetas`  
> **Versión del Contrato:** 2.0.0 (Octubre 2026)

---

## 1. Catálogo Rápido de Endpoints para la Aplicación Móvil

| Módulo | Endpoint | Método | Descripción |
| :--- | :--- | :---: | :--- |
| **OTP** | `/otp/solicitar` | `POST` | Solicita código OTP al correo oficial del titular (5 min vigencia). |
| **OTP** | `/otp/validar` | `POST` | Valida el código de 6 dígitos ingresado por el usuario. |
| **Branding Publicado** | `/branding-credentials/info-published/{tipo_id}` | `GET` | Retorna colores, logo SVG y patrón en Base64 (`1`: Contadores, `2`: Sociedades). |
| **Branding Publicado** | `/branding-institucional/info-published` | `GET` | Retorna el nombre, cargo y firma PNG transparente del Director General. |
| **Auditoría QR** | `/lecturas/registrar` | `POST` | Registra lectura de QR dinámico (clasifica auto `"Dispositivo móvil"`). |
| **Auditoría QR** | `/lecturas/historial` | `GET` | Consulta historial: `filtro=me_consultaron` o `filtro=mis_consultas`. |
| **Activación** | `/activar-movil` | `POST` | Enrola el dispositivo físico y token push FCM a la tarjeta. |
| **Verificación** | `/verificar?token=<hash>` | `GET` | Consulta datos de tarjeta por token QR (auto-registra lectura web). |

---

## 2. Documentación Detallada y Ejemplos de Código

Para la especificación exhaustiva de cada endpoint, esquemas JSON de entrada/salida, códigos de respuesta HTTP y parámetros de consulta, consulte el documento de referencia oficial:

👉 **[Especificación de Endpoints API Móvil (`documentacion/API_MOVIL_WALLET_JCC.md`)](./documentacion/API_MOVIL_WALLET_JCC.md)**

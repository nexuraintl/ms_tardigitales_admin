# Plan de Ajustes — Backend JCC vs App Móvil

Resumen ejecutivo y propuesta técnica directa para atender cada punto del reporte del equipo móvil.

---

## 1. R6 / S3 — Quitar datos de identidad de `GET /verificar/{hash}`

* **Qué pidieron:** Que `GET /verificar/{hash}` no devuelva `no_expd` (expediente), `no_documento` ni `correo`.
* **Situación actual:** El endpoint está devolviendo toda la fila de la BD (`sanitizar=False`), exponiendo esos 3 campos sensibles en un QR público.
* **Cuidado al aplicarlo:** Si la app móvil hoy lee `no_expd` de esta respuesta para validar al usuario en la pantalla del celular, quitarlo de golpe le rompería la app.
* **Propuesta de solución:**
  1. **Validar en el servidor, no en el celular:** La app debe enviar `{hash, expediente}` a `POST /otp/solicitar`. El backend es quien valida si el expediente coincide y, si es así, envía el correo con el código OTP.
  2. **Coordinación:** 
     * Habilitar `POST /otp/solicitar` en el Gateway.
     * Que la app móvil apunte la validación a ese endpoint.
     * Una vez la app ya no dependa de leer `no_expd`, activar la limpieza en `/verificar/{hash}` dejando esos campos en `null` y el correo enmascarado (`f***@correo.com`).
* **Respuesta final de `/verificar/{hash}`:** Solo datos públicos (Nombre, Matrícula/Tarjeta, Estado, Universidad, Fecha de resolución y Hash). Sin expediente ni documento.

---
*(Siguiente punto a documentar: S1 — Proteger `activar-movil` con token OTP)*

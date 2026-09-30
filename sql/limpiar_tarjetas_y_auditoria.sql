-- =====================================================================
-- Script de Limpieza: Tarjetas, Lotes de Emisión, Historial y Auditoría
-- Base de datos: producto9_base
-- =====================================================================
-- NOTA: Este script preserva intactas las tablas de configuración:
-- - tn_tarjetavirtual_configuracion_branding
-- - tn_tarjetavirtual_config_columnas_filtro_tarjetas
-- - tn_tarjetavirtual_config_validador
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Limpieza de tarjetas e historial de cambios de estado
TRUNCATE TABLE tn_tarjetavirtual_estados_historial;
TRUNCATE TABLE tn_tarjetavirtual_contadores;
TRUNCATE TABLE tn_tarjetavirtual_sociedades;

-- 2. Limpieza de lotes de emisión masiva y sus ítems de cola
TRUNCATE TABLE tn_tarjetavirtual_emision_lote_items;
TRUNCATE TABLE tn_tarjetavirtual_emision_lotes;

-- 3. Limpieza de registros de auditoría y logs de sincronización
TRUNCATE TABLE tn_tarjetavirtual_auditoria_api;
TRUNCATE TABLE tn_tarjetavirtual_sincronizacion_logs;

-- 4. Limpieza de historial de notificaciones
TRUNCATE TABLE tn_tarjetavirtual_notificaciones;

SET FOREIGN_KEY_CHECKS = 1;

-- Verificación de registros restantes (debe dar 0 en todas)
SELECT 'tn_tarjetavirtual_contadores' AS tabla, COUNT(*) AS total FROM tn_tarjetavirtual_contadores
UNION ALL
SELECT 'tn_tarjetavirtual_sociedades', COUNT(*) FROM tn_tarjetavirtual_sociedades
UNION ALL
SELECT 'tn_tarjetavirtual_estados_historial', COUNT(*) FROM tn_tarjetavirtual_estados_historial
UNION ALL
SELECT 'tn_tarjetavirtual_emision_lote_items', COUNT(*) FROM tn_tarjetavirtual_emision_lote_items
UNION ALL
SELECT 'tn_tarjetavirtual_emision_lotes', COUNT(*) FROM tn_tarjetavirtual_emision_lotes
UNION ALL
SELECT 'tn_tarjetavirtual_auditoria_api', COUNT(*) FROM tn_tarjetavirtual_auditoria_api
UNION ALL
SELECT 'tn_tarjetavirtual_sincronizacion_logs', COUNT(*) FROM tn_tarjetavirtual_sincronizacion_logs
UNION ALL
SELECT 'tn_tarjetavirtual_notificaciones', COUNT(*) FROM tn_tarjetavirtual_notificaciones;


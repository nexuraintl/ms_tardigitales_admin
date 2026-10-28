-- =============================================================================
-- BITÁCORA INCREMENTAL DE AJUSTES DE BASE DE DATOS (PREPRODUCCIÓN)
-- Microservicio: Tarjetas Digitales Admin (`ms_tardigitales_admin`)
-- Regla: Cada ajuste debe incluir fecha (YYYY-MM-DD) y breve descripción.
-- =============================================================================

SET NAMES utf8mb4;

-- [2026-10-27] Columnas de vinculación de dispositivo móvil y fecha de activación en Contadores y Sociedades (HU-JCC-014 / Bug 26893)
ALTER TABLE `tn_tarjetavirtual_contadores`
  ADD COLUMN IF NOT EXISTS `fcm_token` VARCHAR(500) NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS `device_id` VARCHAR(255) NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS `device_os` VARCHAR(100) NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS `fecha_activacion` DATETIME NULL DEFAULT NULL;

ALTER TABLE `tn_tarjetavirtual_sociedades`
  ADD COLUMN IF NOT EXISTS `fcm_token` VARCHAR(500) NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS `device_id` VARCHAR(255) NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS `device_os` VARCHAR(100) NULL DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS `fecha_activacion` DATETIME NULL DEFAULT NULL;

-- [2026-10-27] Tabla satélite de dispositivos vinculados para trazabilidad de activación móvil y push notifications (HU-JCC-014 / HU-JCC-023)
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_dispositivos` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `tarjeta_id` INT(11) NOT NULL,
  `tipo_tarjeta` VARCHAR(30) NOT NULL DEFAULT 'contadores',
  `device_id` VARCHAR(255) NOT NULL,
  `device_os` VARCHAR(100) DEFAULT NULL,
  `fcm_token` VARCHAR(500) NOT NULL,
  `activo` TINYINT(1) NOT NULL DEFAULT 1,
  `fecha_vinculacion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tarjeta_tipo` (`tarjeta_id`, `tipo_tarjeta`),
  KEY `idx_device_id` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- [2026-10-28] Configuración de columna "Fecha de activación" en el selector de columnas y filtros de tarjetas (Bug 26893)
INSERT INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  (`tipo_tarjeta`, `key_name`, `label`, `visible_defecto`, `es_filtrable`, `orden`, `tipo_dato`)
SELECT 'contadores', 'fecha_activacion', 'Fecha de activación', 0, 0, 18, 'date'
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  WHERE `tipo_tarjeta` = 'contadores' AND `key_name` = 'fecha_activacion'
);

INSERT INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  (`tipo_tarjeta`, `key_name`, `label`, `visible_defecto`, `es_filtrable`, `orden`, `tipo_dato`)
SELECT 'sociedades', 'fecha_activacion', 'Fecha de activación', 0, 0, 16, 'date'
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  WHERE `tipo_tarjeta` = 'sociedades' AND `key_name` = 'fecha_activacion'
);

-- [2026-10-28] Columna de observación obligatoria al publicar versiones de Branding (Contadores, Sociedades e Institucional)
ALTER TABLE `tn_tarjetavirtual_configuracion_branding`
  ADD COLUMN IF NOT EXISTS `observacion` TEXT NULL DEFAULT NULL;

ALTER TABLE `tn_tarjetavirtual_configuracion_institucional`
  ADD COLUMN IF NOT EXISTS `observacion` TEXT NULL DEFAULT NULL;


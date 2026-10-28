-- =============================================================================
-- BITÁCORA INCREMENTAL DE AJUSTES DE BASE DE DATOS (PREPRODUCCIÓN)
-- Microservicio: Tarjetas Digitales Admin (`ms_tardigitales_admin`)
-- Regla: Cada ajuste debe incluir fecha (YYYY-MM-DD) y breve descripción.
-- =============================================================================

SET NAMES utf8mb4;

-- [2026-10-27] Tabla satélite de dispositivos móviles vinculados para notificaciones push FCM (HU-JCC-014 / HU-JCC-023)
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_dispositivos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL DEFAULT 20001,
  `tarjeta_id` int(11) NOT NULL,
  `tipo_tarjeta` enum('contadores','sociedades') NOT NULL DEFAULT 'contadores',
  `fcm_token` varchar(500) DEFAULT NULL,
  `device_id` varchar(150) DEFAULT NULL,
  `device_os` varchar(50) DEFAULT NULL,
  `device_modelo` varchar(100) DEFAULT NULL,
  `app_version` varchar(50) DEFAULT NULL,
  `estado` enum('activo','inactivo') NOT NULL DEFAULT 'activo',
  `fecha_activacion` datetime NOT NULL DEFAULT current_timestamp(),
  `fecha_ultimo_acceso` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_disp_tarjeta` (`client_id`,`tarjeta_id`,`tipo_tarjeta`),
  KEY `idx_disp_device` (`device_id`),
  KEY `idx_disp_fcm` (`fcm_token`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- [2026-10-28] Configuración de columna "Fecha de activación" en el selector de columnas (consultada desde tn_tarjetavirtual_estados_historial) (Bug 26893)
INSERT INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  (`tipo_tarjeta`, `key_name`, `label`, `visible_defecto`, `es_filtrable`, `orden`, `tipo_dato`)
SELECT 'contadores', 'fecha_activacion', 'Fecha de activación', 1, 1, 8, 'date'
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  WHERE `tipo_tarjeta` = 'contadores' AND `key_name` = 'fecha_activacion'
);

INSERT INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas`
  (`tipo_tarjeta`, `key_name`, `label`, `visible_defecto`, `es_filtrable`, `orden`, `tipo_dato`)
SELECT 'sociedades', 'fecha_activacion', 'Fecha de activación', 1, 1, 8, 'date'
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

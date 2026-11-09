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

-- [2026-10-29] Tabla de historial de lecturas y auditoría QR (HU: Gestión de Registro y Consulta de Auditoría)
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

-- [2026-11-05] Tabla oficial de certificados expedidos estandarizada con prefijo tn_tarjetavirtual
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_certificados_expedidos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL DEFAULT 20001,
  `n_certificado` varchar(100) NOT NULL,
  `tipo` enum('contador','sociedad') NOT NULL,
  `documento` varchar(50) NOT NULL,
  `nombre_titular` varchar(255) NOT NULL,
  `fecha_generacion` date NOT NULL,
  `fecha_firma_onac` datetime DEFAULT NULL,
  `estado` varchar(50) NOT NULL DEFAULT 'ACTIVO',
  `payload_detalles` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Metadata de MyJCC y arreglo de ANTECEDENTES' CHECK (json_valid(`payload_detalles`)),
  `ruta_pdf` varchar(500) DEFAULT NULL,
  `hash_sha256` varchar(64) DEFAULT NULL,
  `origen` varchar(50) NOT NULL DEFAULT 'GENERADO',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_n_certificado` (`n_certificado`),
  KEY `idx_cert_client_tipo` (`client_id`,`tipo`),
  KEY `idx_cert_doc` (`documento`),
  KEY `idx_cert_fecha` (`fecha_generacion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- [2026-11-08] Desacoplamiento de seguridad: Token público de verificación independiente para QR del PDF
ALTER TABLE `tn_tarjetavirtual_contadores`
  ADD COLUMN IF NOT EXISTS `token_verificacion` VARCHAR(64) NULL DEFAULT NULL AFTER `hash_sha256`,
  ADD KEY IF NOT EXISTS `idx_contadores_token_verif` (`token_verificacion`);

ALTER TABLE `tn_tarjetavirtual_sociedades`
  ADD COLUMN IF NOT EXISTS `token_verificacion` VARCHAR(64) NULL DEFAULT NULL AFTER `hash_sha256`,
  ADD KEY IF NOT EXISTS `idx_sociedades_token_verif` (`token_verificacion`);

-- [2026-11-08] Soporte de lecturas QR offline e idempotencia (id_lectura UUID y fecha_sincronizacion)
ALTER TABLE 	n_tarjetavirtual_lecturas_historial
  ADD COLUMN IF NOT EXISTS id_lectura VARCHAR(64) NULL DEFAULT NULL AFTER id,
  ADD COLUMN IF NOT EXISTS echa_sincronizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER echa,
  ADD UNIQUE KEY IF NOT EXISTS uk_lect_id_lectura (id_lectura);

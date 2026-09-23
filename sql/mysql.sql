-- =============================================================================
-- ESQUEMA OFICIAL DE BASE DE DATOS: MICROSERVICIO TARJETAS DIGITALES ADMIN
-- Módulo: Tarjetas Digitales y Notificaciones (tn_tarjetavirtual_*)
-- Versión: Limpia y desacoplada para despliegue en cualquier entorno
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_contadores (Registro de Contadores Públicos)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_contadores`;
CREATE TABLE `tn_tarjetavirtual_contadores` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `no_tarjeta` VARCHAR(50) NOT NULL,
    `nombres` VARCHAR(100) NOT NULL,
    `primer_apellido` VARCHAR(100) NOT NULL,
    `segundo_apellido` VARCHAR(100) DEFAULT NULL,
    `no_expd` INT(11) NOT NULL,
    `tipo_documento` VARCHAR(10) NOT NULL,
    `no_documento` BIGINT(20) NOT NULL,
    `universidad` VARCHAR(255) DEFAULT NULL,
    `estado_contador` VARCHAR(50) DEFAULT 'ACTIVO',
    `resolucion` VARCHAR(100) DEFAULT NULL,
    `fecha_estado` DATETIME DEFAULT NULL,
    `fecha_radicacion` DATETIME DEFAULT NULL,
    `fecha_resolucion` DATE DEFAULT NULL,
    `acta_jcc` VARCHAR(50) DEFAULT NULL,
    `fecha_grado` DATE DEFAULT NULL,
    `seccional` VARCHAR(100) DEFAULT NULL,
    `fecha_emision` DATETIME DEFAULT NULL,
    `correo` VARCHAR(255) DEFAULT NULL,
    `tipo_asociado` VARCHAR(100) DEFAULT 'Contador Público',
    `estado` VARCHAR(50) DEFAULT 'Vigente',
    `foto` LONGTEXT DEFAULT NULL,
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_contadores_no_tarjeta` (`no_tarjeta`),
    UNIQUE KEY `uk_contadores_no_documento` (`no_documento`),
    KEY `idx_contadores_no_expd` (`no_expd`),
    KEY `idx_contadores_estado` (`estado`),
    KEY `idx_contadores_estado_contador` (`estado_contador`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_sociedades (Registro de Sociedades de Contadores)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_sociedades`;
CREATE TABLE `tn_tarjetavirtual_sociedades` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `no_expd` INT(11) NOT NULL,
    `razon_social` VARCHAR(255) NOT NULL,
    `nit` VARCHAR(30) NOT NULL,
    `tipo_sociedad` VARCHAR(100) NOT NULL,
    `inscripcion` VARCHAR(50) DEFAULT NULL,
    `fecha_radicacion` DATETIME DEFAULT NULL,
    `estado_sociedad` VARCHAR(50) DEFAULT 'ACTIVO',
    `resolucion` VARCHAR(100) DEFAULT NULL,
    `fecha_resolucion` DATE DEFAULT NULL,
    `acta_jcc` VARCHAR(50) DEFAULT NULL,
    `estado_solicitud` VARCHAR(100) DEFAULT NULL,
    `tipo_solicitud` VARCHAR(100) DEFAULT NULL,
    `fecha_emision` DATETIME DEFAULT NULL,
    `tipo_asociado` VARCHAR(100) DEFAULT 'Sociedad de Contadores Públicos',
    `estado` VARCHAR(50) DEFAULT 'Vigente',
    `representante_legal` VARCHAR(255) DEFAULT NULL,
    `foto` LONGTEXT DEFAULT NULL,
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    KEY `idx_sociedades_no_expd` (`no_expd`),
    KEY `idx_sociedades_nit` (`nit`),
    KEY `idx_sociedades_estado` (`estado`),
    KEY `idx_sociedades_estado_sociedad` (`estado_sociedad`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_estados_historial (Trazabilidad de Cambios de Estado)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_estados_historial`;
CREATE TABLE `tn_tarjetavirtual_estados_historial` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `tarjeta_id` INT(11) NOT NULL,
    `estado` VARCHAR(50) NOT NULL,
    `descripcion` TEXT DEFAULT NULL,
    `fecha` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    `realizado_por` VARCHAR(100) DEFAULT 'Sistema',
    PRIMARY KEY (`id`),
    KEY `idx_estados_historial_tarjeta` (`tarjeta_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_config_validador (Parámetros del Validador QR Público)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_config_validador`;
CREATE TABLE `tn_tarjetavirtual_config_validador` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `client_id` INT(11) NOT NULL,
    `val_foto` TINYINT(4) NOT NULL DEFAULT 1,
    `val_nombres` TINYINT(4) NOT NULL DEFAULT 1,
    `val_matricula` TINYINT(4) NOT NULL DEFAULT 1,
    `val_numero_identificacion` TINYINT(4) NOT NULL DEFAULT 0,
    `val_codigo_tarjeta` TINYINT(4) NOT NULL DEFAULT 1,
    `val_estado` TINYINT(4) NOT NULL DEFAULT 1,
    `fecha_actualizacion` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_validador_client_id` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `tn_tarjetavirtual_config_validador` (`client_id`, `val_foto`, `val_nombres`, `val_matricula`, `val_numero_identificacion`, `val_codigo_tarjeta`, `val_estado`) 
VALUES (20001, 1, 1, 1, 0, 1, 1);

-- =============================================================================
-- TABLA: tn_tarjetavirtual_config_columnas_filtro_tarjetas (Config Dinámica de Columnas)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_config_columnas_filtro_tarjetas`;
CREATE TABLE `tn_tarjetavirtual_config_columnas_filtro_tarjetas` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `tipo_tarjeta` VARCHAR(20) NOT NULL COMMENT 'contadores, sociedades',
    `key_name` VARCHAR(50) NOT NULL,
    `label` VARCHAR(100) NOT NULL,
    `visible_defecto` TINYINT(1) DEFAULT 1,
    `es_filtrable` TINYINT(1) DEFAULT 1,
    `orden` INT(11) DEFAULT 0,
    `tipo_dato` VARCHAR(20) DEFAULT 'string',
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    KEY `idx_tipo_tarjeta` (`tipo_tarjeta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Columnas oficiales para Contadores
INSERT INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas` (`tipo_tarjeta`, `key_name`, `label`, `orden`, `visible_defecto`, `es_filtrable`, `tipo_dato`) VALUES
('contadores', 'matricula', 'Tarjeta profesional', 1, 1, 1, 'string'),
('contadores', 'solicitante', 'Nombre completo', 2, 1, 1, 'string'),
('contadores', 'expediente', 'Expediente', 3, 1, 1, 'string'),
('contadores', 'tipo_asociado', 'Tipo', 4, 1, 1, 'string'),
('contadores', 'fecha', 'Fecha emisión', 5, 1, 1, 'date'),
('contadores', 'documento', 'Documento', 6, 1, 1, 'string'),
('contadores', 'correo', 'Correo', 7, 1, 0, 'string'),
('contadores', 'universidad', 'Universidad', 8, 0, 0, 'string'),
('contadores', 'tarjeta', 'Estado tarjeta', 9, 1, 1, 'string'),
('contadores', 'estado_contador', 'Estado registro', 10, 1, 1, 'string'),
('contadores', 'resolucion', 'Resolución', 11, 0, 1, 'string'),
('contadores', 'fecha_estado', 'Fecha del estado', 12, 0, 0, 'date'),
('contadores', 'fecha_registro', 'Fecha de registro', 13, 0, 0, 'date'),
('contadores', 'fecha_resolucion', 'Fecha de resolución', 14, 0, 0, 'date'),
('contadores', 'acta_jcc', 'Acta JCC', 15, 0, 1, 'string'),
('contadores', 'fecha_grado', 'Fecha de grado', 16, 0, 0, 'date'),
('contadores', 'seccional', 'Seccional', 17, 0, 0, 'string'),
('contadores', 'no_tarjeta', 'Número de tarjeta', 18, 0, 1, 'string');

-- Columnas oficiales para Sociedades
INSERT INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas` (`tipo_tarjeta`, `key_name`, `label`, `orden`, `visible_defecto`, `es_filtrable`, `tipo_dato`) VALUES
('sociedades', 'no_expd', 'Expediente', 1, 1, 1, 'number'),
('sociedades', 'razon_social', 'Razón social', 2, 1, 1, 'string'),
('sociedades', 'nit', 'Nit', 3, 1, 1, 'string'),
('sociedades', 'tipo_asociado', 'Tipo', 4, 1, 1, 'string'),
('sociedades', 'fecha_emision', 'Fecha emisión', 5, 1, 1, 'string'),
('sociedades', 'tipo_sociedad', 'Tipo de sociedad', 6, 0, 1, 'string'),
('sociedades', 'inscripcion', 'Inscripción', 7, 1, 1, 'string'),
('sociedades', 'fecha_inscripcion', 'Fecha de inscripción', 8, 0, 1, 'string'),
('sociedades', 'estado_tarjeta', 'Estado de la tarjeta', 9, 1, 1, 'string'),
('sociedades', 'estado_sociedad', 'Estado de la sociedad', 10, 1, 1, 'string'),
('sociedades', 'resolucion', 'Resolución', 11, 1, 1, 'string'),
('sociedades', 'fecha_resolucion', 'Fecha de resolución', 12, 0, 1, 'string'),
('sociedades', 'acta_jcc', 'Acta JCC', 13, 0, 1, 'string'),
('sociedades', 'estado_solicitud', 'Estado de la solicitud', 14, 0, 1, 'string'),
('sociedades', 'tipo_solicitud', 'Tipo de solicitud', 15, 0, 1, 'string');

-- =============================================================================
-- TABLA: tn_tarjetavirtual_configuracion_branding (Branding e Identidad Visual)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_configuracion_branding`;
CREATE TABLE `tn_tarjetavirtual_configuracion_branding` (
    `id` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
    `tipo_id` INT(11) NOT NULL COMMENT '1: Contadores, 2: Sociedades',
    `version` INT(10) UNSIGNED NOT NULL DEFAULT 1,
    `publicado` TINYINT(1) NOT NULL DEFAULT 0,
    `logo` LONGTEXT DEFAULT NULL,
    `patron` LONGTEXT DEFAULT NULL,
    `color_fondo` VARCHAR(20) NOT NULL DEFAULT '#14275f',
    `color_letra` VARCHAR(20) NOT NULL DEFAULT '#ffffff',
    `fuente_letra` VARCHAR(100) NOT NULL DEFAULT 'Arial, sans-serif',
    `usuario_creacion_id` INT(11) DEFAULT NULL,
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_branding_tipo_version` (`tipo_id`, `version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Plantillas base por defecto
INSERT INTO `tn_tarjetavirtual_configuracion_branding` (`tipo_id`, `version`, `publicado`, `color_fondo`, `color_letra`, `fuente_letra`) VALUES
(1, 1, 1, '#14275f', '#ffffff', 'Arial, sans-serif'),
(2, 1, 1, '#134567', '#ffffff', 'Arial, sans-serif');

-- =============================================================================
-- TABLA: tn_tarjetavirtual_auditoria_api (Auditoría de Consultas y Validaciones)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_auditoria_api`;
CREATE TABLE `tn_tarjetavirtual_auditoria_api` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `client_id` INT(11) NOT NULL,
    `fecha_creacion` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    `tipo_tarjeta` VARCHAR(50) DEFAULT 'contadores',
    `metodo` VARCHAR(15) NOT NULL,
    `tipo_asociado` VARCHAR(100) DEFAULT NULL,
    `duracion_ms` INT(11) DEFAULT NULL,
    `url` VARCHAR(255) NOT NULL,
    `parametros_peticion` TEXT DEFAULT NULL,
    `cuerpo_respuesta_peticion` LONGTEXT DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_auditoria_fecha` (`fecha_creacion`),
    KEY `idx_auditoria_tipo` (`tipo_tarjeta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_emision_lotes (Historial de Lotes de Emisión)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_emision_lote_items`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_emision_lotes`;
CREATE TABLE `tn_tarjetavirtual_emision_lotes` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `client_id` INT(11) NOT NULL DEFAULT 20001,
    `tipo_tarjeta` VARCHAR(50) NOT NULL COMMENT 'contadores, sociedades',
    `tipo_tramite` VARCHAR(50) DEFAULT 'primeraVez',
    `archivo_nombre` VARCHAR(255) DEFAULT NULL,
    `total_registros` INT(11) NOT NULL DEFAULT 0,
    `procesados` INT(11) NOT NULL DEFAULT 0,
    `exitosos` INT(11) NOT NULL DEFAULT 0,
    `duplicados` INT(11) NOT NULL DEFAULT 0,
    `fallidos` INT(11) NOT NULL DEFAULT 0,
    `estado` VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    `mensaje` VARCHAR(255) DEFAULT NULL,
    `creado_por` VARCHAR(100) DEFAULT NULL,
    `fecha_creacion` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    `fecha_fin` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_lotes_client` (`client_id`),
    KEY `idx_lotes_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_emision_lote_items (Items de Detalle de Lote y Cola)
-- =============================================================================
CREATE TABLE `tn_tarjetavirtual_emision_lote_items` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `lote_id` INT(11) NOT NULL,
    `documento_o_nit` VARCHAR(50) NOT NULL,
    `resultado` VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    `tarjeta_id` INT(11) DEFAULT NULL,
    `mensaje_detalle` TEXT DEFAULT NULL,
    `fecha_proceso` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    KEY `idx_lote_items_lote` (`lote_id`),
    KEY `idx_lote_items_doc` (`documento_o_nit`),
    CONSTRAINT `fk_lote_items_lote` FOREIGN KEY (`lote_id`) REFERENCES `tn_tarjetavirtual_emision_lotes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- TABLA: tn_tarjetavirtual_config_colas (Configuración Centralizada del Motor)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_config_colas`;
CREATE TABLE `tn_tarjetavirtual_config_colas` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `client_id` INT(11) NOT NULL,
    `worker_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `poll_interval_seconds` DECIMAL(5,2) NOT NULL DEFAULT 5.00,
    `batch_size` INT(11) NOT NULL DEFAULT 10,
    `item_delay_seconds` DECIMAL(5,3) NOT NULL DEFAULT 0.050,
    `circuit_breaker_fail_threshold` INT(11) NOT NULL DEFAULT 3,
    `circuit_breaker_cooldown_seconds` INT(11) NOT NULL DEFAULT 60,
    `max_retries_per_item` INT(11) NOT NULL DEFAULT 2,
    `scheduler_enabled` TINYINT(1) NOT NULL DEFAULT 1,
    `scheduler_interval_seconds` INT(11) NOT NULL DEFAULT 3600,
    `scheduler_auto_enqueue` TINYINT(1) NOT NULL DEFAULT 1,
    `updated_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_config_colas_client_id` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `tn_tarjetavirtual_config_colas` (`client_id`, `worker_enabled`, `poll_interval_seconds`, `batch_size`, `item_delay_seconds`, `circuit_breaker_fail_threshold`, `circuit_breaker_cooldown_seconds`, `max_retries_per_item`, `scheduler_enabled`, `scheduler_interval_seconds`, `scheduler_auto_enqueue`)
VALUES (20001, 1, 5.00, 10, 0.050, 3, 60, 2, 1, 3600, 1);

-- =============================================================================
-- TABLA: tn_tarjetavirtual_sincronizacion_logs (Auditoría Persistente de Sincronización)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_sincronizacion_logs`;
CREATE TABLE `tn_tarjetavirtual_sincronizacion_logs` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `origen` VARCHAR(20) NOT NULL DEFAULT 'PROGRAMADO' COMMENT 'PROGRAMADO, MANUAL',
    `fecha_inicio` DATETIME NOT NULL,
    `fecha_fin` DATETIME DEFAULT NULL,
    `duracion_ms` INT(11) DEFAULT 0,
    `estado` VARCHAR(30) NOT NULL COMMENT 'EXITOSO, PARCIAL, FALLIDO',
    `total_encolados` INT(11) NOT NULL DEFAULT 0,
    `contadores_encolados` INT(11) NOT NULL DEFAULT 0,
    `sociedades_encoladas` INT(11) NOT NULL DEFAULT 0,
    `errores_count` INT(11) NOT NULL DEFAULT 0,
    `detalle` VARCHAR(500) DEFAULT NULL,
    `creado_en` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (`id`),
    KEY `idx_sincro_fecha_inicio` (`fecha_inicio`),
    KEY `idx_sincro_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

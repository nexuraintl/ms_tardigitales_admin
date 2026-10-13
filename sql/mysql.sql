-- =============================================================================
-- ESQUEMA OFICIAL DE BASE DE DATOS Y CONFIGURACIONES MAESTRAS
-- Microservicio: Tarjetas Digitales Admin (`ms_tardigitales_admin`)
-- Base de datos: producto9_base (MariaDB 10.4+ / MySQL 8.0+)
-- Entorno de destino: Preproducción (QA / Master)
-- =============================================================================
-- CARACTERÍSTICAS DEL SCRIPT:
-- 1. Idempotente: Utiliza CREATE TABLE IF NOT EXISTS e INSERT IGNORE INTO.
-- 2. Limpio: Sin datos transaccionales de tarjetas (contadores, sociedades e historial vacíos).
-- 3. Listo para producción: Incluye tablas de lotes, colas, logs y configuraciones maestras.
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =============================================================================
-- 0. LIMPIEZA DE ENTORNO (DROP TABLE IF EXISTS)
-- =============================================================================
DROP TABLE IF EXISTS `tn_tarjetavirtual_auditoria_api`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_estados_historial`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_emision_lote_items`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_emision_lotes`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_sincronizacion_logs`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_notificaciones`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_configuracion_branding`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_configuracion_institucional`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_config_validador`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_config_columnas_filtro_tarjetas`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_config_colas`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_sociedades`;
DROP TABLE IF EXISTS `tn_tarjetavirtual_contadores`;


-- =============================================================================
-- 1. CREACIÓN DE ESTRUCTURAS DE TABLAS (13 TABLAS OFICIALES)
-- =============================================================================

CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_contadores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `no_tarjeta` varchar(50) NOT NULL,
  `nombres` varchar(100) NOT NULL,
  `primer_apellido` varchar(100) NOT NULL,
  `segundo_apellido` varchar(100) DEFAULT NULL,
  `no_expd` int(11) NOT NULL,
  `tipo_documento` varchar(10) NOT NULL,
  `no_documento` bigint(20) NOT NULL,
  `universidad` varchar(255) DEFAULT NULL,
  `estado_contador` varchar(50) DEFAULT 'ACTIVO',
  `resolucion` varchar(100) DEFAULT NULL,
  `fecha_estado` datetime DEFAULT NULL,
  `fecha_radicacion` datetime DEFAULT NULL,
  `fecha_resolucion` date DEFAULT NULL,
  `acta_jcc` varchar(50) DEFAULT NULL,
  `fecha_grado` date DEFAULT NULL,
  `seccional` varchar(100) DEFAULT NULL,
  `fecha_emision` datetime DEFAULT NULL,
  `correo` varchar(255) DEFAULT NULL,
  `tipo_asociado` varchar(100) DEFAULT 'Contador Público',
  `estado` varchar(50) DEFAULT 'Vigente',
  `foto` longtext DEFAULT NULL,
  `hash_sha256` varchar(64) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_contadores_no_tarjeta` (`no_tarjeta`),
  UNIQUE KEY `uk_contadores_no_documento` (`no_documento`),
  KEY `idx_contadores_no_expd` (`no_expd`),
  KEY `idx_contadores_estado` (`estado`),
  KEY `idx_contadores_estado_contador` (`estado_contador`),
  KEY `idx_contadores_hash` (`hash_sha256`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_sociedades` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `no_expd` int(11) NOT NULL,
  `razon_social` varchar(255) NOT NULL,
  `nit` varchar(30) NOT NULL,
  `tipo_sociedad` varchar(100) NOT NULL,
  `inscripcion` varchar(50) DEFAULT NULL,
  `correo` varchar(255) DEFAULT NULL,
  `fecha_radicacion` datetime DEFAULT NULL,
  `estado_sociedad` varchar(50) DEFAULT 'ACTIVO',
  `resolucion` varchar(100) DEFAULT NULL,
  `fecha_resolucion` date DEFAULT NULL,
  `acta_jcc` varchar(50) DEFAULT NULL,
  `estado_solicitud` varchar(100) DEFAULT NULL,
  `tipo_solicitud` varchar(100) DEFAULT NULL,
  `fecha_emision` datetime DEFAULT NULL,
  `tipo_asociado` varchar(100) DEFAULT 'Sociedad de Contadores Públicos',
  `estado` varchar(50) DEFAULT 'Vigente',
  `representante_legal` varchar(255) DEFAULT NULL,
  `foto` longtext DEFAULT NULL,
  `hash_sha256` varchar(64) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sociedades_no_expd` (`no_expd`),
  KEY `idx_sociedades_no_expd` (`no_expd`),
  KEY `idx_sociedades_nit` (`nit`),
  KEY `idx_sociedades_estado` (`estado`),
  KEY `idx_sociedades_estado_sociedad` (`estado_sociedad`),
  KEY `idx_sociedades_hash` (`hash_sha256`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_estados_historial` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tarjeta_id` int(11) NOT NULL,
  `estado` varchar(50) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha` timestamp NULL DEFAULT current_timestamp(),
  `realizado_por` varchar(100) DEFAULT 'Sistema',
  PRIMARY KEY (`id`),
  KEY `idx_estados_historial_tarjeta` (`tarjeta_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_auditoria_api` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `fecha_creacion` timestamp NULL DEFAULT current_timestamp(),
  `tipo_tarjeta` varchar(50) DEFAULT 'contadores',
  `metodo` varchar(15) NOT NULL,
  `tipo_asociado` varchar(100) DEFAULT NULL,
  `duracion_ms` int(11) DEFAULT NULL,
  `codigo_http` int(11) NOT NULL DEFAULT 200,
  `url` varchar(255) NOT NULL,
  `parametros_peticion` text DEFAULT NULL,
  `cuerpo_respuesta_peticion` longtext DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_auditoria_fecha` (`fecha_creacion`),
  KEY `idx_auditoria_tipo` (`tipo_tarjeta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_emision_lotes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL DEFAULT 20001,
  `tipo_tarjeta` varchar(50) NOT NULL COMMENT 'contadores, sociedades',
  `tipo_tramite` varchar(50) DEFAULT 'primeraVez',
  `archivo_nombre` varchar(255) DEFAULT NULL,
  `total_registros` int(11) NOT NULL DEFAULT 0,
  `procesados` int(11) NOT NULL DEFAULT 0,
  `exitosos` int(11) NOT NULL DEFAULT 0,
  `duplicados` int(11) NOT NULL DEFAULT 0,
  `fallidos` int(11) NOT NULL DEFAULT 0,
  `estado` varchar(30) NOT NULL DEFAULT 'PENDIENTE',
  `mensaje` varchar(255) DEFAULT NULL,
  `creado_por` varchar(100) DEFAULT NULL,
  `fecha_creacion` timestamp NULL DEFAULT current_timestamp(),
  `fecha_fin` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_lotes_client` (`client_id`),
  KEY `idx_lotes_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_emision_lote_items` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `lote_id` int(11) NOT NULL,
  `documento_o_nit` varchar(50) NOT NULL,
  `resultado` varchar(30) NOT NULL DEFAULT 'PENDIENTE',
  `tarjeta_id` int(11) DEFAULT NULL,
  `mensaje_detalle` text DEFAULT NULL,
  `fecha_proceso` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_lote_items_lote` (`lote_id`),
  KEY `idx_lote_items_doc` (`documento_o_nit`),
  CONSTRAINT `fk_lote_items_lote` FOREIGN KEY (`lote_id`) REFERENCES `tn_tarjetavirtual_emision_lotes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_config_colas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `worker_enabled` tinyint(1) NOT NULL DEFAULT 1,
  `poll_interval_seconds` decimal(5,2) NOT NULL DEFAULT 5.00,
  `batch_size` int(11) NOT NULL DEFAULT 10,
  `item_delay_seconds` decimal(5,3) NOT NULL DEFAULT 0.050,
  `circuit_breaker_fail_threshold` int(11) NOT NULL DEFAULT 3,
  `circuit_breaker_cooldown_seconds` int(11) NOT NULL DEFAULT 60,
  `max_retries_per_item` int(11) NOT NULL DEFAULT 2,
  `scheduler_enabled` tinyint(1) NOT NULL DEFAULT 1,
  `scheduler_interval_seconds` int(11) NOT NULL DEFAULT 3600,
  `scheduler_auto_enqueue` tinyint(1) NOT NULL DEFAULT 1,
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_colas_client_id` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_sincronizacion_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `origen` varchar(20) NOT NULL DEFAULT 'PROGRAMADO' COMMENT 'PROGRAMADO, MANUAL',
  `fecha_inicio` datetime NOT NULL,
  `fecha_fin` datetime DEFAULT NULL,
  `duracion_ms` int(11) DEFAULT 0,
  `estado` varchar(30) NOT NULL COMMENT 'EXITOSO, PARCIAL, FALLIDO',
  `total_encolados` int(11) NOT NULL DEFAULT 0,
  `contadores_encolados` int(11) NOT NULL DEFAULT 0,
  `sociedades_encoladas` int(11) NOT NULL DEFAULT 0,
  `errores_count` int(11) NOT NULL DEFAULT 0,
  `detalle` varchar(500) DEFAULT NULL,
  `creado_en` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_sincro_fecha_inicio` (`fecha_inicio`),
  KEY `idx_sincro_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_config_columnas_filtro_tarjetas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tipo_tarjeta` varchar(20) NOT NULL COMMENT 'contadores, sociedades',
  `key_name` varchar(50) NOT NULL,
  `label` varchar(100) NOT NULL,
  `visible_defecto` tinyint(1) DEFAULT 1,
  `es_filtrable` tinyint(1) DEFAULT 1,
  `orden` int(11) DEFAULT 0,
  `tipo_dato` varchar(20) DEFAULT 'string',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_tipo_tarjeta` (`tipo_tarjeta`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_config_validador` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `val_foto` tinyint(4) NOT NULL DEFAULT 1,
  `val_nombres` tinyint(4) NOT NULL DEFAULT 1,
  `val_matricula` tinyint(4) NOT NULL DEFAULT 1,
  `val_numero_identificacion` tinyint(4) NOT NULL DEFAULT 0,
  `val_codigo_tarjeta` tinyint(4) NOT NULL DEFAULT 1,
  `val_estado` tinyint(4) NOT NULL DEFAULT 1,
  `fecha_actualizacion` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_validador_client_id` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_configuracion_institucional` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `nombre_director` varchar(255) NOT NULL,
  `cargo_director` varchar(100) NOT NULL DEFAULT 'DIRECTOR GENERAL',
  `firma_director` longtext DEFAULT NULL,
  `version` int(10) unsigned NOT NULL DEFAULT 1,
  `publicado` tinyint(1) NOT NULL DEFAULT 1,
  `usuario_creacion_id` int(11) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_configuracion_branding` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `tipo_id` int(11) NOT NULL COMMENT '1: Contadores, 2: Sociedades',
  `version` int(10) unsigned NOT NULL DEFAULT 1,
  `publicado` tinyint(1) NOT NULL DEFAULT 0,
  `logo` longtext DEFAULT NULL,
  `patron` longtext DEFAULT NULL,
  `logo_impresion` longtext DEFAULT NULL,
  `patron_impresion` longtext DEFAULT NULL,
  `color_fondo` varchar(20) NOT NULL DEFAULT '#14275f',
  `color_letra` varchar(20) NOT NULL DEFAULT '#ffffff',
  `color_letra_impresion` varchar(20) NOT NULL DEFAULT '#0f172a',
  `nombre_director` varchar(255) DEFAULT NULL,
  `firma_director` longtext DEFAULT NULL,
  `usuario_creacion_id` int(11) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_branding_tipo_version` (`tipo_id`,`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_notificaciones` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `client_id` int(11) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `mensaje` text NOT NULL,
  `tipo` varchar(50) DEFAULT 'Informativa',
  `canal` varchar(100) NOT NULL,
  `audiencia` varchar(100) NOT NULL,
  `destinatarios` int(11) NOT NULL DEFAULT 0,
  `fecha` varchar(50) DEFAULT NULL,
  `estado` varchar(50) NOT NULL DEFAULT 'Programada',
  `creado_por` varchar(100) DEFAULT 'Administrador',
  `hora_inicio` varchar(10) DEFAULT '07:00',
  `hora_fin` varchar(10) DEFAULT '17:00',
  `max_diario` int(11) DEFAULT 2,
  `recurrencia` varchar(50) DEFAULT 'No repetir',
  `respetar_rango` tinyint(1) DEFAULT 1,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_notif_client` (`client_id`),
  KEY `idx_notif_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- 2. CONFIGURACIONES MAESTRAS DEL SISTEMA (COLAS, FILTROS, BRANDING, INSTITUCIONAL)
-- =============================================================================

INSERT IGNORE INTO `tn_tarjetavirtual_config_colas` VALUES
(1,20001,1,5.00,10,0.050,3,60,2,1,3600,1,'2026-09-23 21:23:02');
INSERT IGNORE INTO `tn_tarjetavirtual_config_validador` VALUES
(1,20001,1,1,1,0,1,1,'2026-09-23 21:23:01');
INSERT IGNORE INTO `tn_tarjetavirtual_config_columnas_filtro_tarjetas` VALUES
(1,'contadores','no_tarjeta','Tarjeta profesional',1,1,1,'string','2026-09-23 21:23:01'),
(2,'contadores','nombre_completo','Nombre completo',1,1,2,'string','2026-09-23 21:23:01'),
(3,'contadores','no_expd','Expediente',1,1,3,'string','2026-09-23 21:23:01'),
(4,'contadores','tipo_asociado','Tipo',1,1,4,'string','2026-09-23 21:23:01'),
(5,'contadores','fecha_emision','Fecha emisiÃ³n',1,1,5,'date','2026-09-23 21:23:01'),
(6,'contadores','no_documento','Documento',1,1,6,'string','2026-09-23 21:23:01'),
(7,'contadores','correo','Correo',1,0,7,'string','2026-09-23 21:23:01'),
(8,'contadores','universidad','Universidad',0,0,8,'string','2026-09-23 21:23:01'),
(9,'contadores','estado_tarjeta','Estado tarjeta',1,1,9,'string','2026-09-23 21:23:01'),
(10,'contadores','estado_contador','Estado registro',1,1,10,'string','2026-09-23 21:23:01'),
(11,'contadores','resolucion','ResoluciÃ³n',0,1,11,'string','2026-09-23 21:23:01'),
(12,'contadores','fecha_estado','Fecha del estado',0,0,12,'date','2026-09-23 21:23:01'),
(13,'contadores','fecha_radicacion','Fecha de radicaciÃ³n',0,0,13,'date','2026-09-23 21:23:01'),
(14,'contadores','fecha_resolucion','Fecha de resoluciÃ³n',0,0,14,'date','2026-09-23 21:23:01'),
(15,'contadores','acta_jcc','Acta JCC',0,1,15,'string','2026-09-23 21:23:01'),
(16,'contadores','fecha_grado','Fecha de grado',0,0,16,'date','2026-09-23 21:23:01'),
(17,'contadores','seccional','Seccional',0,0,17,'string','2026-09-23 21:23:01'),
(19,'sociedades','no_expd','Expediente',1,1,1,'number','2026-09-23 21:23:01'),
(20,'sociedades','razon_social','RazÃ³n social',1,1,2,'string','2026-09-23 21:23:01'),
(21,'sociedades','nit','Nit',1,1,3,'string','2026-09-23 21:23:01'),
(22,'sociedades','tipo_asociado','Tipo',1,1,4,'string','2026-09-23 21:23:01'),
(23,'sociedades','fecha_emision','Fecha emisiÃ³n',1,1,5,'string','2026-09-23 21:23:01'),
(24,'sociedades','tipo_sociedad','Tipo de registro',0,1,6,'string','2026-09-23 21:23:01'),
(25,'sociedades','inscripcion','InscripciÃ³n',1,1,7,'string','2026-09-23 21:23:01'),
(26,'sociedades','fecha_radicacion','Fecha de radicaciÃ³n',0,1,8,'string','2026-09-23 21:23:01'),
(27,'sociedades','estado_tarjeta','Estado de la tarjeta',1,1,9,'string','2026-09-23 21:23:01'),
(28,'sociedades','estado_sociedad','Estado de la sociedad',1,1,10,'string','2026-09-23 21:23:01'),
(29,'sociedades','resolucion','ResoluciÃ³n',1,1,11,'string','2026-09-23 21:23:01'),
(30,'sociedades','fecha_resolucion','Fecha de resoluciÃ³n',0,1,12,'string','2026-09-23 21:23:01'),
(31,'sociedades','acta_jcc','Acta JCC',0,1,13,'string','2026-09-23 21:23:01'),
(32,'sociedades','estado_solicitud','Estado de la solicitud',0,1,14,'string','2026-09-23 21:23:01'),
(33,'sociedades','tipo_solicitud','Tipo de solicitud',0,1,15,'string','2026-09-23 21:23:01'),
(34,'sociedades','correo','Correo',1,0,4,'string','2026-10-13 15:47:48');
INSERT IGNORE INTO `tn_tarjetavirtual_configuracion_institucional` VALUES
(1,'SANDRA MILENA BARRIOS PULIDO','DIRECTOR GENERAL','data:image/png;base64,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',1,1,NULL,'2026-10-04 19:08:03','2026-10-04 20:30:06'),
(2,'SANDRA MILENA BARRIOS PULIDOo','DIRECTOR GENERAL','data:image/png;base64,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',2,0,141,'2026-10-04 19:56:20','2026-10-04 20:30:06');
SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- FIN DEL ESQUEMA OFICIAL
-- =============================================================================

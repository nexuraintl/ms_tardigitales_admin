-- =============================================================================
-- ESQUEMAS Y DATOS DE BASE DE DATOS: ms_tardigitales_notificaciones
-- Entidad Cliente: 20001 (Junta Central de Contadores)
-- Estándar: nxPlatform / Microservicios
-- =============================================================================

-- 2026-07-16
-- Creación de la tabla de notificaciones institucionales
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_notificaciones` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `client_id` INT NOT NULL DEFAULT 20001,
    `titulo` VARCHAR(255) NOT NULL,
    `canal` VARCHAR(100) NOT NULL,
    `audiencia` VARCHAR(100) NOT NULL,
    `destinatarios` INT NOT NULL,
    `fecha` VARCHAR(100) NOT NULL,
    `estado` VARCHAR(50) NOT NULL,
    `creadoPor` VARCHAR(100) NOT NULL,
    `mensaje` TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar registros semilla de notificaciones (Impersonales)
INSERT INTO `tn_tarjetavirtual_notificaciones` (`id`, `client_id`, `titulo`, `canal`, `audiencia`, `destinatarios`, `fecha`, `estado`, `creadoPor`, `mensaje`) VALUES
(1, 20001, 'Jornada de Actualización Normativa 2026', 'Push', 'Todos', 12458, '2026-07-16 07:30:00', 'Entregada', 'Administrador', 'Estimados contadores, les invitamos a participar en la jornada de capacitación sobre estándares internacionales.'),
(2, 20001, 'Nueva versión del portal de trámites', 'Alerta estándar', 'Contadores', 9820, '2026-07-15 16:15:00', 'Entregada', 'Soporte Técnico', 'Se ha liberado la nueva versión del portal con mejoras en la visualización de la tarjeta digital.'),
(3, 20001, 'Actualización anual de datos de sociedades', 'Notificación interna', 'Sociedades', 640, '2026-07-15 10:20:00', 'Entregada', 'Área de Registro', 'Recuerde actualizar los datos de representación legal de su sociedad antes del 31 de julio.'),
(4, 20001, 'Renovación próxima de matrícula', 'Push', 'Contadores', 310, '2026-07-14 08:00:00', 'Programada', 'Área de Registro', 'Su tarjeta profesional está próxima a cumplir ciclo de vigencia. Inicie el trámite en línea.'),
(5, 20001, 'Mantenimiento programado de plataforma', 'Alerta estándar', 'Todos', 12458, '2026-07-13 22:00:00', 'Programada', 'Soporte Técnico', 'La plataforma entrará en mantenimiento preventivo el día sábado entre las 22:00 y las 02:00.')
ON DUPLICATE KEY UPDATE `titulo`=VALUES(`titulo`), `mensaje`=VALUES(`mensaje`);

-- 2026-07-31
-- Creación de la tabla de catálogo de trámites oficiales
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_tramites` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(255) NOT NULL,
    `tipo` VARCHAR(100) NOT NULL,
    `costo` DECIMAL(12,2) NOT NULL,
    `estado` VARCHAR(50) NOT NULL,
    `descripcion` TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar trámites oficiales iniciales
INSERT INTO `tn_tarjetavirtual_tramites` (`id`, `nombre`, `tipo`, `costo`, `estado`, `descripcion`) VALUES
(1, 'Inscripción de Tarjeta Profesional', 'Contador Público', 412000.00, 'Activo', 'Trámite oficial para solicitud de tarjeta profesional por primera vez.'),
(2, 'Duplicado de Tarjeta Profesional', 'Contador Público', 41000.00, 'Activo', 'Reposición de credencial digital por extravío o deterioro.'),
(3, 'Actualización de Datos de Registro', 'Contador Público', 0.00, 'Activo', 'Modificación de información de contacto y domicilio institucional.'),
(4, 'Registro de Sociedad de Contadores', 'Sociedad', 5350000.00, 'Activo', 'Inscripción inicial de personas jurídicas y sociedades de contadores.'),
(5, 'Renovación de Matrícula de Sociedad', 'Sociedad', 680000.00, 'Activo', 'Renovación de vigencia de registro anual de persona jurídica.')
ON DUPLICATE KEY UPDATE `nombre`=VALUES(`nombre`), `costo`=VALUES(`costo`);

-- 2026-08-03
-- Creación de la tabla de tarjetas virtuales (Contadores y Sociedades)
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_tarjetas` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tipo_tarjeta` VARCHAR(50) NOT NULL,
    `codigo` VARCHAR(100) NOT NULL,
    `expediente` INT NOT NULL,
    `solicitante` VARCHAR(255) NOT NULL,
    `documento` VARCHAR(100) NOT NULL,
    `matricula` VARCHAR(100) NOT NULL,
    `correo` VARCHAR(255) DEFAULT NULL,
    `representante` VARCHAR(255) DEFAULT NULL,
    `tarjeta` VARCHAR(50) NOT NULL,
    `fecha` DATE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Precargar registros de prueba impersonales para Contadores y Sociedades
INSERT INTO `tn_tarjetavirtual_tarjetas` (`id`, `tipo_tarjeta`, `codigo`, `expediente`, `solicitante`, `documento`, `matricula`, `correo`, `representante`, `tarjeta`, `fecha`) VALUES
(1, 'contadores', 'TC-DEMO-001', 10001, 'Usuario Demo Contador Uno', 'CC 1000000001', 'MP-10001', 'contador.uno@ejemplo.com', NULL, 'Virtual Activa', '2026-01-15'),
(2, 'contadores', 'TC-DEMO-002', 10002, 'Usuario Demo Contador Dos', 'CC 1000000002', 'MP-10002', 'contador.dos@ejemplo.com', NULL, 'Virtual Activa', '2026-02-20'),
(3, 'contadores', 'TC-DEMO-003', 10003, 'Usuario Demo Contador Tres', 'CC 1000000003', 'MP-10003', 'contador.tres@ejemplo.com', NULL, 'En Trámite', '2026-03-10'),
(4, 'sociedades', 'TS-DEMO-001', 20001, 'Sociedad Auditora Ejemplo S.A.S.', 'NIT 900000001-1', 'MS-20001', 'contacto@sociedadejemplo.com', 'Representante Legal Demo Uno', 'Virtual Activa', '2026-01-25'),
(5, 'sociedades', 'TS-DEMO-002', 20002, 'Consultores Contables Demo Ltda.', 'NIT 900000002-2', 'MS-20002', 'info@consultoresdemo.com', 'Representante Legal Demo Dos', 'Virtual Activa', '2026-02-14')
ON DUPLICATE KEY UPDATE `codigo`=VALUES(`codigo`), `solicitante`=VALUES(`solicitante`);

-- 2026-08-06
-- Creación de la tabla de historial de estados para tarjetas virtuales
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_estados_historial` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tarjeta_id` INT NOT NULL,
    `estado` VARCHAR(50) NOT NULL,
    `descripcion` TEXT DEFAULT NULL,
    `fecha` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `realizado_por` VARCHAR(100) DEFAULT 'Sistema',
    FOREIGN KEY (`tarjeta_id`) REFERENCES `tn_tarjetavirtual_tarjetas`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Creación de la tabla de historial de lecturas / auditoría de código QR
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_lecturas_historial` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `tarjeta_id` INT NOT NULL,
    `fecha` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `endpoint` VARCHAR(255) NOT NULL,
    `metodo` VARCHAR(10) NOT NULL,
    `codigo_http` INT NOT NULL,
    `ip` VARCHAR(45) NOT NULL,
    FOREIGN KEY (`tarjeta_id`) REFERENCES `tn_tarjetavirtual_tarjetas`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar historial de estados inicial
INSERT INTO `tn_tarjetavirtual_estados_historial` (`id`, `tarjeta_id`, `estado`, `descripcion`, `realizado_por`) VALUES
(1, 1, 'Creada', 'Creación y registro inicial en el sistema de prueba.', 'Sistema'),
(2, 1, 'Virtual Activa', 'Aprobación de credencial digital emitida.', 'Administrador'),
(3, 2, 'Creada', 'Creación y registro inicial en el sistema de prueba.', 'Sistema'),
(4, 2, 'Virtual Activa', 'Aprobación de credencial digital emitida.', 'Administrador'),
(5, 4, 'Creada', 'Registro de sociedad de contadores.', 'Sistema'),
(6, 4, 'Virtual Activa', 'Emisión de registro de sociedad completado.', 'Administrador')
ON DUPLICATE KEY UPDATE `estado`=VALUES(`estado`);

-- Insertar historial de lecturas QR inicial
INSERT INTO `tn_tarjetavirtual_lecturas_historial` (`id`, `tarjeta_id`, `endpoint`, `metodo`, `codigo_http`, `ip`) VALUES
(1, 1, '/apig/tardigitales/validador-qr', 'GET', 200, '127.0.0.1'),
(2, 2, '/apig/tardigitales/validador-qr', 'GET', 200, '127.0.0.1'),
(3, 4, '/apig/tardigitales/validador-qr', 'GET', 200, '127.0.0.1')
ON DUPLICATE KEY UPDATE `codigo_http`=VALUES(`codigo_http`);

-- 2026-08-10
-- Creación de la tabla de configuración del validador QR
CREATE TABLE IF NOT EXISTS `tn_tarjetavirtual_validador_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `client_id` INT NOT NULL UNIQUE,
    `val_foto` TINYINT NOT NULL DEFAULT 1,
    `val_nombres` TINYINT NOT NULL DEFAULT 1,
    `val_matricula` TINYINT NOT NULL DEFAULT 1,
    `val_numero_identificacion` TINYINT NOT NULL DEFAULT 0,
    `val_codigo_tarjeta` TINYINT NOT NULL DEFAULT 1,
    `val_estado` TINYINT NOT NULL DEFAULT 1,
    `fecha_actualizacion` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar configuración por defecto para el cliente 20001
INSERT INTO `tn_tarjetavirtual_validador_config` (`client_id`, `val_foto`, `val_nombres`, `val_matricula`, `val_numero_identificacion`, `val_codigo_tarjeta`, `val_estado`) VALUES
(20001, 1, 1, 1, 0, 1, 1)
ON DUPLICATE KEY UPDATE `val_foto`=VALUES(`val_foto`);

-- 2026-08-25
-- Configuración de conexión multitenant en base de datos central
CREATE DATABASE IF NOT EXISTS `pre_gestion_bdconex` 
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `pre_gestion_bdconex`.`tn_gestion_bdconex` (
    `idConexion` INT(11) NOT NULL AUTO_INCREMENT,
    `idCliente` INT(11) NOT NULL,
    `nombreBaseDeDatos` VARCHAR(255) NOT NULL,
    `usuario` VARCHAR(100) NOT NULL,
    `contrasena` VARCHAR(100) DEFAULT '',
    `motor` VARCHAR(50) DEFAULT 'mysql',
    `hosting` VARCHAR(255) NOT NULL DEFAULT 'host.docker.internal',
    `puerto` INT(11) NOT NULL DEFAULT 3306,
    `tipoDeBaseDeDatos` VARCHAR(50) DEFAULT 'mysql',
    `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (`idConexion`),
    KEY `idx_cliente` (`idCliente`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `pre_gestion_bdconex`.`tn_gestion_bdconex` (`idCliente`, `nombreBaseDeDatos`, `usuario`, `contrasena`, `motor`, `hosting`, `puerto`, `tipoDeBaseDeDatos`)
VALUES (20001, 'producto9_base', 'root', '', 'mysql', 'host.docker.internal', 3306, 'mysql')
ON DUPLICATE KEY UPDATE `nombreBaseDeDatos`='producto9_base', `hosting`='host.docker.internal';

-- 2026-09-07
-- Configuración Branding de credenciales (Tabla Única Unificada con Histórico y Estado Publicado)
CREATE TABLE IF NOT EXISTS tn_tarjetavirtual_tipos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO tn_tarjetavirtual_tipos (id, nombre) VALUES 
(1, "Contadores"),
(2, "Sociedades")
ON DUPLICATE KEY UPDATE nombre=VALUES(nombre);

DROP TABLE IF EXISTS tn_tarjetavirtual_configuracion_branding_historico;

CREATE TABLE IF NOT EXISTS tn_tarjetavirtual_configuracion_branding (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tipo_id INT NOT NULL,
    version INT UNSIGNED NOT NULL DEFAULT 1,
    publicado TINYINT(1) NOT NULL DEFAULT 0,
    logo LONGTEXT NULL,
    patron LONGTEXT NULL,
    color_fondo VARCHAR(20) NOT NULL,
    color_letra VARCHAR(20) NOT NULL,
    fuente_letra VARCHAR(100) NOT NULL,
    usuario_creacion_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_configuracion_branding_tipo
        FOREIGN KEY (tipo_id) 
        REFERENCES tn_tarjetavirtual_tipos(id) ON DELETE CASCADE,

    UNIQUE KEY uk_branding_tipo_version (tipo_id, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla para el manejo de los diferentes tipos
CREATE TABLE tn_tarjetavirtual_tipos_asociados (
	id INT AUTO_INCREMENT PRIMARY KEY,
	nombre VARCHAR(60) not null 
);

INSERT INTO tn_tarjetavirtual_tipos_asociados(nombre)
VALUES ('primeraVez'),
('duplicado'),
('sustitucion');

-- Estados tarjetas
CREATE TABLE tn_tarjetavirtual_estados_tarjetas (
	id INT AUTO_INCREMENT PRIMARY KEY,
	nombre VARCHAR(60) not null 
);

INSERT INTO tn_tarjetavirtual_estados_tarjetas(nombre)
VALUES ('Activa'),
('Emitida'),
('Cancelada');

-- Auditoria API
CREATE TABLE tn_tarjetavirtual_auditoria_api (
    id INT PRIMARY KEY AUTO_INCREMENT,
    client_id INT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo_id INT NOT NULL, 
    metodo VARCHAR(15) NOT NULL,
    tipo_asociado_id INT,
    duracion_ms INT,                   
    url VARCHAR(255) NOT NULL,
    parametros_peticion TEXT COMMENT "Parámetros / cuerpo",
    cuerpo_respuesta_peticion LONGTEXT COMMENT "Cuerpo de la respuesta",
    
    INDEX idx_fecha (fecha_creacion),
    INDEX idx_tipo_id (tipo_id),
    
    CONSTRAINT fk_auditoria_api_tipo 
    FOREIGN KEY (tipo_id) 
    REFERENCES tn_tarjetavirtual_tipos(id),
    
    CONSTRAINT fk_auditoria_api_tipo_asociado_id 
    FOREIGN KEY (tipo_asociado_id) 
    REFERENCES tn_tarjetavirtual_tipos_asociados(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sociedades
CREATE TABLE tn_tarjetavirtual_sociedades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    no_expd INT NOT NULL,
    razon_social VARCHAR(255) NOT NULL,
    nit VARCHAR(20) NOT NULL,
    tipo_sociedad VARCHAR(100) NOT NULL,
    inscripcion INT,
    fecha_radicacion DATETIME,
    estado_sociedad VARCHAR(50) DEFAULT 'ACTIVO',
    resolucion VARCHAR(20),
    fecha_resolucion DATE,
    acta_jcc VARCHAR(50),
    estado_solicitud VARCHAR(100),
    tipo_solicitud VARCHAR(100),
    fecha_emision DATETIME,
    tipo_asociado_id INT NOT NULL COMMENT 'primeraVez, duplicado',
    estado_tarjeta_id INT NOT NULL COMMENT 'Activa, Emitida y Cancelada',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_sociedades_estado_tarjeta_id
    FOREIGN KEY (estado_tarjeta_id)
    REFERENCES tn_tarjetavirtual_estados_tarjetas(id),

    CONSTRAINT fk_sociedades_tipo_asociado_id
    FOREIGN KEY (tipo_asociado_id)
    REFERENCES tn_tarjetavirtual_tipos_asociados(id),

    INDEX idx_no_expd (no_expd),
    INDEX idx_nit (nit),
    INDEX idx_estado_sociedad (estado_sociedad)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Contadores
CREATE TABLE tn_tarjetavirtual_contadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    no_tarjeta VARCHAR(20) NOT NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    primer_apellido VARCHAR(100) NOT NULL,
    segundo_apellido VARCHAR(100),
    no_expd INT NOT NULL,
    tipo_documento VARCHAR(10) NOT NULL,
    no_documento BIGINT NOT NULL UNIQUE,
    universidad VARCHAR(200),
    estado_contador VARCHAR(50) DEFAULT 'ACTIVO',
    resolucion VARCHAR(20),
    fecha_estado DATETIME,
    fecha_radicacion DATETIME,
    fecha_resolucion DATE,
    acta_jcc INT,
    fecha_grado DATE,
    seccional VARCHAR(100),
    fecha_emision DATETIME,
    tipo_asociado_id INT NOT NULL COMMENT 'primeraVez, duplicado',
    estado_tarjeta_id INT NOT NULL COMMENT 'Activa, Emitida y Cancelada',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_contadores_estado_tarjeta_id
    FOREIGN KEY (estado_tarjeta_id)
    REFERENCES tn_tarjetavirtual_estados_tarjetas(id),

    CONSTRAINT fk_contadores_tipo_asociado_id
    FOREIGN KEY (tipo_asociado_id)
    REFERENCES tn_tarjetavirtual_tipos_asociados(id),

    INDEX idx_no_tarjeta (no_tarjeta),
    INDEX idx_no_documento (no_documento),
    INDEX idx_no_expd (no_expd),
    INDEX idx_estado_contador (estado_contador)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE tn_tarjetavirtual_contadores
ADD COLUMN correo VARCHAR(200) NULL DEFAULT "no_registra@example.test";

ALTER TABLE tn_tarjetavirtual_contadores
ADD COLUMN foto LONGTEXT DEFAULT NULL AFTER correo;

ALTER TABLE tn_tarjetavirtual_sociedades
ADD COLUMN foto LONGTEXT DEFAULT NULL  AFTER estado_tarjeta_id;

INSERT INTO tn_tarjetavirtual_tipos_asociados(nombre)
VALUES ('modificacion');

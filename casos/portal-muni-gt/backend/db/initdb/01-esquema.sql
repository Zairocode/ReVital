-- Esquema de SIREC, sistema de recaudacion de la muni FICTICIA MuniSoke GT (caso de demo de ReVital).
-- Hecho "como en la epoca" a proposito: MySQL 5.5, claves de operadores en MD5 sin sal, sin cifrado de datos personales.
CREATE DATABASE IF NOT EXISTS sirec DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE sirec;

CREATE TABLE contribuyentes (
  id INT PRIMARY KEY,
  nombres VARCHAR(80) NOT NULL,
  apellidos VARCHAR(80) NOT NULL,
  dpi VARCHAR(20) NOT NULL UNIQUE,
  nit VARCHAR(15),
  telefono VARCHAR(12),
  direccion VARCHAR(120),
  zona TINYINT,
  nota VARCHAR(20) NOT NULL DEFAULT 'DATO FICTICIO'
) ENGINE=InnoDB;

CREATE TABLE inmuebles (
  finca VARCHAR(10) PRIMARY KEY,
  contribuyente_id INT NOT NULL,
  zona TINYINT,
  direccion VARCHAR(120),
  valor_fiscal DECIMAL(12,2) NOT NULL,
  tasa_por_millar TINYINT NOT NULL,
  iusi_anual DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
) ENGINE=InnoDB;

CREATE TABLE iusi_trimestres (
  finca VARCHAR(10) NOT NULL,
  anio SMALLINT NOT NULL,
  trimestre TINYINT NOT NULL,
  monto DECIMAL(10,2) NOT NULL,
  estado ENUM('pagado','pendiente','vencido') NOT NULL,
  fecha_pago DATE NULL,
  PRIMARY KEY (finca, anio, trimestre),
  FOREIGN KEY (finca) REFERENCES inmuebles(finca)
) ENGINE=InnoDB;

CREATE TABLE boletos_ornato (
  dpi VARCHAR(20) NOT NULL,
  anio SMALLINT NOT NULL,
  monto DECIMAL(8,2) NOT NULL,
  pagado TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (dpi, anio)
) ENGINE=InnoDB;

CREATE TABLE contadores_agua (
  contador VARCHAR(10) PRIMARY KEY,
  contribuyente_id INT NOT NULL,
  saldo DECIMAL(10,2) NOT NULL DEFAULT 0,
  FOREIGN KEY (contribuyente_id) REFERENCES contribuyentes(id)
) ENGINE=InnoDB;

CREATE TABLE multas_pmt (
  boleta VARCHAR(16) PRIMARY KEY,
  placa VARCHAR(10),
  monto DECIMAL(8,2) NOT NULL,
  estado ENUM('pendiente','pagada') NOT NULL
) ENGINE=InnoDB;

CREATE TABLE ordenes_pago (
  orden VARCHAR(16) PRIMARY KEY,
  concepto ENUM('iusi','ornato','agua','multa') NOT NULL,
  referencia VARCHAR(20) NOT NULL,
  monto DECIMAL(10,2) NOT NULL,
  vence DATE NOT NULL,
  creada TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE solicitudes_laip (
  folio VARCHAR(16) PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  correo VARCHAR(120) NULL,
  descripcion TEXT NOT NULL,
  fecha DATE NOT NULL,
  vence DATE NOT NULL,
  estado ENUM('recibida','en_tramite','resuelta','prorrogada') NOT NULL DEFAULT 'recibida'
) ENGINE=InnoDB;

CREATE TABLE usuarios_sirec (
  usuario VARCHAR(20) PRIMARY KEY,
  nombre VARCHAR(80),
  clave_md5 CHAR(32) NOT NULL,
  rol ENUM('admin','cajero','consulta','laip') NOT NULL
) ENGINE=InnoDB;

-- Usuario de la aplicacion con TODOS los privilegios y acceso desde cualquier host: configuracion insegura tipica.
GRANT ALL PRIVILEGES ON sirec.* TO 'sirec'@'%' IDENTIFIED BY 'sirec2014';
FLUSH PRIVILEGES;

-- Ejecutar dentro de la base de datos db_sistema_impuestos.
CREATE TABLE IF NOT EXISTS `usuarios_usss013325` (
  `idUsuario` int(10) NOT NULL AUTO_INCREMENT,
  `usuario` char(35) NOT NULL,
  `clave` char(35) NOT NULL,
  `nombre` char(85) NOT NULL,
  `direccion` char(100) NOT NULL,
  `telefono` char(9) NOT NULL,
  PRIMARY KEY (`idUsuario`),
  UNIQUE KEY `uq_usuarios_usss013325_usuario` (`usuario`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4;

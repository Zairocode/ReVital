<?php
// Instala Drupal 7 por linea de comandos (sin asistente web). SOLO para el objetivo de demo local.
// Lo ejecuta instalar_drupal.sh dentro del contenedor, desde /var/www/html. Las credenciales de BD
// ya estan en sites/default/settings.php (las escribe el .sh).
define('MAINTENANCE_MODE', 'install');
define('DRUPAL_ROOT', getcwd());
require_once DRUPAL_ROOT . '/includes/install.core.inc';
install_drupal(array(
  'parameters' => array('profile' => 'standard', 'locale' => 'en'),
  'forms' => array('install_configure_form' => array(
    'site_name' => 'Municipalidad ficticia MUNI-GT',
    'site_mail' => 'admin@example.com',
    'account' => array('name' => 'admin', 'mail' => 'admin@example.com',
                       'pass' => array('pass1' => 'admin', 'pass2' => 'admin')),
    'date_default_timezone' => 'America/Guatemala',
    'site_default_country' => 'GT',
    'update_status_module' => array(1 => NULL, 2 => NULL),  // checkboxes en envio programatico: NULL = sin marcar
    'clean_url' => TRUE,
  )),
));
echo "INSTALADO\n";

<?php
// Activa el tema MuniSoke GT en Drupal 7 (CLI). Lo ejecuta aplicar_branding.sh dentro del contenedor. Idempotente.
$_SERVER['REMOTE_ADDR'] = '127.0.0.1';
$_SERVER['HTTP_HOST'] = 'localhost';
define('DRUPAL_ROOT', getcwd());
require_once DRUPAL_ROOT . '/includes/bootstrap.inc';
drupal_bootstrap(DRUPAL_BOOTSTRAP_FULL);
system_rebuild_theme_data();
theme_enable(array('munisoke'));
variable_set('theme_default', 'munisoke');
variable_set('site_name', 'MuniSoke GT');
drupal_flush_all_caches();
echo "BRANDING OK\n";

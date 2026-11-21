# Contrato de la API de SIREC (backend ↔ frontend del portal)
Estado: vigente para el demo · Rama: `feat/backend-sirec`

SIREC es el sistema de recaudación **ficticio** de MuniSoke GT. El portal lo consume en el **mismo origen**: el proxy Apache 2.4.49 envía `/sirec/` a Tomcat (`ProxyPass /sirec/ http://sirec:8080/sirec/` antes de la regla de Drupal). El frontend siempre usa rutas relativas (`/sirec/api/...`), nunca un host ni un puerto.

## Reglas comunes
- JSON en UTF-8. Montos en quetzales (`"moneda": "GTQ"`) como número con 2 decimales. Fechas `AAAA-MM-DD`.
- Los `POST` reciben `application/x-www-form-urlencoded` (como un formulario de la época).
- Error: código HTTP 400/404/500 y cuerpo `{"error": "<codigo>", "mensaje": "<texto claro para el vecino>"}`. El frontend muestra `mensaje`.
- Todos los datos son ficticios. Los nombres de los propietarios llegan **enmascarados** (`"M**** L****"`).
- No hay pagos con tarjeta: el portal solo genera una **orden de pago** para pagar en agencia.

## Endpoints

### `GET /sirec/api/estado`
```json
{"sistema": "SIREC", "version": "3.2.1", "municipalidad": "MuniSoke GT (ficticia)", "hora_servidor": "2026-11-21T13:40:00-06:00"}
```

### `GET /sirec/api/iusi?finca=F-1024`
`finca`: `F-` seguido de 4 o 5 dígitos. Formato inválido → 400 `finca_invalida`; no existe → 404 `finca_no_encontrada`.
```json
{
  "finca": "F-1024", "zona": 3, "direccion": "4a avenida 7-21, zona 3, Soke",
  "propietario": "M**** L****", "valor_fiscal": 185000.00, "tasa_por_millar": 9, "iusi_anual": 1665.00,
  "trimestres": [
    {"anio": 2026, "trimestre": 1, "monto": 416.25, "estado": "pagado", "fecha_pago": "2026-03-12"},
    {"anio": 2026, "trimestre": 2, "monto": 416.25, "estado": "pagado", "fecha_pago": "2026-06-30"},
    {"anio": 2026, "trimestre": 3, "monto": 416.25, "estado": "pendiente", "fecha_pago": null},
    {"anio": 2026, "trimestre": 4, "monto": 416.25, "estado": "pendiente", "fecha_pago": null}
  ],
  "saldo_pendiente": 832.50, "moneda": "GTQ"
}
```
`estado` de cada trimestre: `pagado` | `pendiente` | `vencido`.

### `POST /sirec/api/orden-pago`
Campos: `concepto` (`iusi` | `ornato` | `agua` | `multa`) y `referencia` (finca `F-####` para IUSI, DPI `#### ##### ####` para ornato, contador `A-#####` para agua, boleta `PMT-2026-#####` para multa). Error → 400 `concepto_invalido`, `referencia_invalida` o `sin_saldo` (ya está al día); 404 `referencia_no_encontrada`.
```json
{"orden": "OP-2026-004512", "concepto": "iusi", "referencia": "F-1024", "monto": 832.50, "moneda": "GTQ",
 "vence": "2026-11-28", "pagar_en": "Agencias bancarias autorizadas (ficticio)"}
```

### `POST /sirec/api/laip`
Solicitud de información pública. Campos: `nombre` (obligatorio), `correo` (opcional), `descripcion` (obligatorio, 10–2000 caracteres). Error → 400 `campo_obligatorio` / `descripcion_corta` / `descripcion_larga`. Respuesta **201**:
```json
{"folio": "LAIP-2026-0153", "fecha": "2026-11-21", "vence": "2026-12-07", "estado": "recibida"}
```
`vence` lo calcula el backend (plazo de 10 días); el frontend solo lo muestra.

### `GET /sirec/api/laip/LAIP-2026-0153`
404 `folio_no_encontrado` si no existe.
```json
{"folio": "LAIP-2026-0153", "fecha": "2026-11-21", "vence": "2026-12-07", "estado": "en_tramite", "dias_restantes": 9}
```
`estado`: `recibida` | `en_tramite` | `resuelta` | `prorrogada`.

## Datos semilla garantizados (para probar el frontend)
| Dato | Resultado esperado |
|---|---|
| finca `F-1024` | con saldo pendiente (como el ejemplo) |
| finca `F-2048` | al día: todos los trimestres `pagado`, saldo 0 |
| finca `F-3072` | con trimestres `vencido` |
| finca `F-0000` | 404 `finca_no_encontrada` |
| folio `LAIP-2026-0101` | `resuelta` |
| folio `LAIP-2026-0140` | `en_tramite` |

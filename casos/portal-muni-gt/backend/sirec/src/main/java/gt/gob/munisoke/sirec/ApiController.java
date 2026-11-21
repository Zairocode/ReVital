package gt.gob.munisoke.sirec;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import javax.servlet.http.HttpServletRequest;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.fasterxml.jackson.databind.ObjectMapper;

import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

/**
 * API de SIREC para el portal de la muni FICTICIA MuniSoke GT. Contrato: docs/features/sirec-api.md.
 * Todos los datos son ficticios.
 */
@RestController
public class ApiController {
    static final String JSON = "application/json;charset=UTF-8";
    static final ZoneId GT = ZoneId.of("America/Guatemala");
    static final Pattern FINCA = Pattern.compile("^F-\\d{4,5}$"), DPI = Pattern.compile("^\\d{4} \\d{5} \\d{4}$"),
            CONTADOR = Pattern.compile("^A-\\d{5}$"), BOLETA = Pattern.compile("^PMT-2026-\\d{5}$");
    static final Logger LOG = LogManager.getLogger(ApiController.class);

    @Autowired
    JdbcTemplate jdbc;

    final ObjectMapper json = new ObjectMapper();
    final JedisPool redis = new JedisPool("redis", 6379);  // cache de consultas: sin clave, como venia de fabrica

    static ResponseEntity<Object> error(HttpStatus st, String codigo, String mensaje) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("error", codigo);
        m.put("mensaje", mensaje);
        return ResponseEntity.status(st).body(m);
    }

    static BigDecimal q(BigDecimal v) {
        return (v == null ? BigDecimal.ZERO : v).setScale(2, RoundingMode.HALF_UP);
    }

    static LocalDate hoy() {
        return LocalDate.now(GT);
    }

    /** n dias habiles (lunes a viernes) despues de la fecha. */
    static LocalDate sumarHabiles(LocalDate f, int n) {
        while (n > 0) {
            f = f.plusDays(1);
            if (f.getDayOfWeek() != DayOfWeek.SATURDAY && f.getDayOfWeek() != DayOfWeek.SUNDAY) n--;
        }
        return f;
    }

    static int habilesHasta(LocalDate desde, LocalDate hasta) {
        int n = 0;
        for (LocalDate f = desde.plusDays(1); !f.isAfter(hasta); f = f.plusDays(1))
            if (f.getDayOfWeek() != DayOfWeek.SATURDAY && f.getDayOfWeek() != DayOfWeek.SUNDAY) n++;
        return n;
    }

    static String enmascarar(String nombres, String apellidos) {
        return nombres.substring(0, 1).toUpperCase() + "**** " + apellidos.substring(0, 1).toUpperCase() + "****";
    }

    @GetMapping(value = "/estado", produces = JSON)
    public Map<String, Object> estado() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("sistema", "SIREC");
        m.put("version", "3.2.1");
        m.put("municipalidad", "MuniSoke GT (ficticia)");
        m.put("hora_servidor", OffsetDateTime.now(GT).withNano(0).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME));
        return m;
    }

    @GetMapping(value = "/iusi", produces = JSON)
    public ResponseEntity<Object> iusi(@RequestParam(value = "finca", required = false) String finca, HttpServletRequest req) {
        LOG.info("Consulta IUSI finca=" + finca + " desde " + req.getHeader("X-Forwarded-For"));
        if (finca == null || !FINCA.matcher(finca.trim()).matches())
            return error(HttpStatus.BAD_REQUEST, "finca_invalida", "Escribe el numero de finca como aparece en tu recibo, por ejemplo F-1024.");
        finca = finca.trim();
        try (Jedis r = redis.getResource()) {
            String c = r.get("iusi:" + finca);
            if (c != null) return ResponseEntity.ok().header("Content-Type", JSON).body(json.readValue(c, Map.class));
        } catch (Exception e) {
            LOG.warn("cache no disponible: " + e.getMessage());
        }
        Map<String, Object> inm;
        try {
            inm = jdbc.queryForMap("SELECT i.finca, i.zona, i.direccion, i.valor_fiscal, i.tasa_por_millar, i.iusi_anual, c.nombres, c.apellidos "
                    + "FROM inmuebles i JOIN contribuyentes c ON c.id = i.contribuyente_id WHERE i.finca = ?", finca);
        } catch (EmptyResultDataAccessException e) {
            return error(HttpStatus.NOT_FOUND, "finca_no_encontrada", "No encontramos la finca " + finca + ". Revisa el numero en tu recibo.");
        }
        List<Map<String, Object>> tri = new ArrayList<>();
        BigDecimal saldo = BigDecimal.ZERO;
        for (Map<String, Object> t : jdbc.queryForList("SELECT anio, trimestre, monto, estado, DATE_FORMAT(fecha_pago, '%Y-%m-%d') AS fecha_pago "
                + "FROM iusi_trimestres WHERE finca = ? ORDER BY anio, trimestre", finca)) {
            Map<String, Object> x = new LinkedHashMap<>();
            x.put("anio", ((Number) t.get("anio")).intValue());
            x.put("trimestre", ((Number) t.get("trimestre")).intValue());
            x.put("monto", q((BigDecimal) t.get("monto")));
            x.put("estado", t.get("estado"));
            x.put("fecha_pago", t.get("fecha_pago"));
            if (!"pagado".equals(t.get("estado"))) saldo = saldo.add((BigDecimal) t.get("monto"));
            tri.add(x);
        }
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("finca", inm.get("finca"));
        m.put("zona", ((Number) inm.get("zona")).intValue());
        m.put("direccion", inm.get("direccion"));
        m.put("propietario", enmascarar((String) inm.get("nombres"), (String) inm.get("apellidos")));
        m.put("valor_fiscal", q((BigDecimal) inm.get("valor_fiscal")));
        m.put("tasa_por_millar", ((Number) inm.get("tasa_por_millar")).intValue());
        m.put("iusi_anual", q((BigDecimal) inm.get("iusi_anual")));
        m.put("trimestres", tri);
        m.put("saldo_pendiente", q(saldo));
        m.put("moneda", "GTQ");
        try (Jedis r = redis.getResource()) {
            r.setex("iusi:" + finca, 60, json.writeValueAsString(m));
        } catch (Exception e) {
            LOG.warn("cache no disponible: " + e.getMessage());
        }
        return ResponseEntity.ok().header("Content-Type", JSON).body(m);
    }

    BigDecimal montoPendiente(String concepto, String ref) {
        List<BigDecimal> l;
        switch (concepto) {
            case "iusi":
                if (jdbc.queryForObject("SELECT COUNT(*) FROM inmuebles WHERE finca = ?", Integer.class, ref) == 0) return null;
                return jdbc.queryForObject("SELECT COALESCE(SUM(monto), 0) FROM iusi_trimestres WHERE finca = ? AND estado <> 'pagado'", BigDecimal.class, ref);
            case "ornato":
                l = jdbc.queryForList("SELECT IF(pagado = 1, 0, monto) FROM boletos_ornato WHERE dpi = ? AND anio = 2026", BigDecimal.class, ref);
                break;
            case "agua":
                l = jdbc.queryForList("SELECT saldo FROM contadores_agua WHERE contador = ?", BigDecimal.class, ref);
                break;
            default:
                l = jdbc.queryForList("SELECT IF(estado = 'pagada', 0, monto) FROM multas_pmt WHERE boleta = ?", BigDecimal.class, ref);
        }
        return l.isEmpty() ? null : l.get(0);
    }

    @PostMapping(value = "/orden-pago", produces = JSON)
    public ResponseEntity<Object> ordenPago(@RequestParam(value = "concepto", required = false) String concepto,
                                            @RequestParam(value = "referencia", required = false) String referencia) {
        LOG.info("Orden de pago concepto=" + concepto + " referencia=" + referencia);
        Pattern p = concepto == null ? null : "iusi".equals(concepto) ? FINCA : "ornato".equals(concepto) ? DPI
                : "agua".equals(concepto) ? CONTADOR : "multa".equals(concepto) ? BOLETA : null;
        if (p == null)
            return error(HttpStatus.BAD_REQUEST, "concepto_invalido", "Elige que quieres pagar: IUSI, boleto de ornato, agua o multa.");
        String ref = referencia == null ? "" : referencia.trim();
        if (!p.matcher(ref).matches())
            return error(HttpStatus.BAD_REQUEST, "referencia_invalida", "La referencia no tiene el formato esperado para ese pago.");
        BigDecimal monto = montoPendiente(concepto, ref);
        if (monto == null)
            return error(HttpStatus.NOT_FOUND, "referencia_no_encontrada", "No encontramos " + ref + " en el sistema de recaudacion.");
        if (monto.signum() == 0)
            return error(HttpStatus.BAD_REQUEST, "sin_saldo", "No hay saldo pendiente para " + ref + ". Estas al dia.");
        int n = jdbc.queryForObject("SELECT COUNT(*) FROM ordenes_pago", Integer.class) + 4501;
        String orden = String.format("OP-2026-%06d", n);
        LocalDate vence = hoy().plusDays(7);
        jdbc.update("INSERT INTO ordenes_pago (orden, concepto, referencia, monto, vence) VALUES (?, ?, ?, ?, ?)", orden, concepto, ref, monto, vence.toString());
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("orden", orden);
        m.put("concepto", concepto);
        m.put("referencia", ref);
        m.put("monto", q(monto));
        m.put("moneda", "GTQ");
        m.put("vence", vence.toString());
        m.put("pagar_en", "Agencias bancarias autorizadas (ficticio)");
        return ResponseEntity.ok().header("Content-Type", JSON).body(m);
    }

    @PostMapping(value = "/laip", produces = JSON)
    public ResponseEntity<Object> laip(@RequestParam(value = "nombre", required = false) String nombre,
                                       @RequestParam(value = "correo", required = false) String correo,
                                       @RequestParam(value = "descripcion", required = false) String descripcion) {
        nombre = nombre == null ? "" : nombre.trim();
        descripcion = descripcion == null ? "" : descripcion.trim();
        correo = correo == null || correo.trim().isEmpty() ? null : correo.trim();
        if (nombre.isEmpty() || descripcion.isEmpty())
            return error(HttpStatus.BAD_REQUEST, "campo_obligatorio", "Escribe tu nombre y la informacion que solicitas.");
        if (descripcion.length() < 10)
            return error(HttpStatus.BAD_REQUEST, "descripcion_corta", "Describe con un poco mas de detalle la informacion que necesitas (minimo 10 caracteres).");
        if (descripcion.length() > 2000)
            return error(HttpStatus.BAD_REQUEST, "descripcion_larga", "La descripcion es muy larga (maximo 2000 caracteres).");
        String ultimo = jdbc.queryForObject("SELECT MAX(folio) FROM solicitudes_laip WHERE folio LIKE 'LAIP-2026-%'", String.class);
        int n = ultimo == null ? 1 : Integer.parseInt(ultimo.substring(10)) + 1;
        String folio = String.format("LAIP-2026-%04d", n);
        LocalDate fecha = hoy(), vence = sumarHabiles(fecha, 10);
        jdbc.update("INSERT INTO solicitudes_laip (folio, nombre, correo, descripcion, fecha, vence, estado) VALUES (?, ?, ?, ?, ?, ?, 'recibida')",
                folio, nombre, correo, descripcion, fecha.toString(), vence.toString());
        LOG.info("Solicitud LAIP " + folio + " de " + nombre);
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("folio", folio);
        m.put("fecha", fecha.toString());
        m.put("vence", vence.toString());
        m.put("estado", "recibida");
        return ResponseEntity.status(HttpStatus.CREATED).header("Content-Type", JSON).body(m);
    }

    @GetMapping(value = "/laip/{folio}", produces = JSON)
    public ResponseEntity<Object> seguimiento(@PathVariable("folio") String folio) {
        Map<String, Object> s;
        try {
            s = jdbc.queryForMap("SELECT folio, DATE_FORMAT(fecha, '%Y-%m-%d') AS fecha, DATE_FORMAT(vence, '%Y-%m-%d') AS vence, estado "
                    + "FROM solicitudes_laip WHERE folio = ?", folio);
        } catch (EmptyResultDataAccessException e) {
            return error(HttpStatus.NOT_FOUND, "folio_no_encontrado", "No encontramos la solicitud " + folio + ". Revisa el folio de tu comprobante.");
        }
        Map<String, Object> m = new LinkedHashMap<>(s);
        m.put("dias_restantes", Math.max(0, habilesHasta(hoy(), LocalDate.parse((String) s.get("vence")))));
        return ResponseEntity.ok().header("Content-Type", JSON).body(m);
    }
}

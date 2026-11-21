/**
 * Simulador offline de la API de SIREC para desarrollo y pruebas (?mock=1).
 * Se importa dinámicamente desde js/sirec.js únicamente cuando la URL incluye ?mock=1.
 * Todos los datos son ficticios y respetan el contrato de docs/features/sirec-api.md.
 */

const MOCK_DELAY_MS = 140;

const FINCA_REGEX = /^F-\d{4,5}$/;
const VALID_CONCEPTOS = new Set(['iusi', 'ornato', 'agua', 'multa']);

const FINCAS_SEMILLA = Object.freeze({
  'F-1024': {
    finca: 'F-1024',
    zona: 3,
    direccion: '4a avenida 7-21, zona 3, Soke',
    propietario: 'M**** L****',
    valor_fiscal: 185000.0,
    tasa_por_millar: 9,
    iusi_anual: 1665.0,
    trimestres: [
      { anio: 2026, trimestre: 1, monto: 416.25, estado: 'pagado', fecha_pago: '2026-03-12' },
      { anio: 2026, trimestre: 2, monto: 416.25, estado: 'pagado', fecha_pago: '2026-06-30' },
      { anio: 2026, trimestre: 3, monto: 416.25, estado: 'pendiente', fecha_pago: null },
      { anio: 2026, trimestre: 4, monto: 416.25, estado: 'pendiente', fecha_pago: null },
    ],
    saldo_pendiente: 832.5,
    moneda: 'GTQ',
  },
  'F-2048': {
    finca: 'F-2048',
    zona: 1,
    direccion: '2a calle 5-14, zona 1, Soke',
    propietario: 'C**** R****',
    valor_fiscal: 120000.0,
    tasa_por_millar: 9,
    iusi_anual: 1080.0,
    trimestres: [
      { anio: 2026, trimestre: 1, monto: 270.0, estado: 'pagado', fecha_pago: '2026-03-10' },
      { anio: 2026, trimestre: 2, monto: 270.0, estado: 'pagado', fecha_pago: '2026-06-15' },
      { anio: 2026, trimestre: 3, monto: 270.0, estado: 'pagado', fecha_pago: '2026-09-18' },
      { anio: 2026, trimestre: 4, monto: 270.0, estado: 'pagado', fecha_pago: '2026-11-05' },
    ],
    saldo_pendiente: 0.0,
    moneda: 'GTQ',
  },
  'F-3072': {
    finca: 'F-3072',
    zona: 5,
    direccion: '8a calle 12-40, zona 5, Soke',
    propietario: 'A**** G****',
    valor_fiscal: 240000.0,
    tasa_por_millar: 9,
    iusi_anual: 2160.0,
    trimestres: [
      { anio: 2026, trimestre: 1, monto: 540.0, estado: 'vencido', fecha_pago: null },
      { anio: 2026, trimestre: 2, monto: 540.0, estado: 'vencido', fecha_pago: null },
      { anio: 2026, trimestre: 3, monto: 540.0, estado: 'vencido', fecha_pago: null },
      { anio: 2026, trimestre: 4, monto: 540.0, estado: 'pendiente', fecha_pago: null },
    ],
    saldo_pendiente: 2160.0,
    moneda: 'GTQ',
  },
});

const laipStore = new Map([
  [
    'LAIP-2026-0101',
    {
      folio: 'LAIP-2026-0101',
      fecha: '2026-10-28',
      vence: '2026-11-11',
      estado: 'resuelta',
      dias_restantes: 0,
    },
  ],
  [
    'LAIP-2026-0140',
    {
      folio: 'LAIP-2026-0140',
      fecha: '2026-11-16',
      vence: '2026-11-30',
      estado: 'en_tramite',
      dias_restantes: 6,
    },
  ],
  [
    'LAIP-2026-0120',
    {
      folio: 'LAIP-2026-0120',
      fecha: '2026-11-05',
      vence: '2026-11-27',
      estado: 'prorrogada',
      dias_restantes: 4,
    },
  ],
]);

let nextLaipSeq = 153;
let nextOrdenSeq = 4520;

/**
 * Clona un objeto plano para evitar mutaciones sobre los datos en memoria.
 * @template T
 * @param {T} value
 * @returns {T}
 */
function cloneData(value) {
  return JSON.parse(JSON.stringify(value));
}

/**
 * Devuelve la hora actual formateada en ISO-8601 con zona horaria de Guatemala (-06:00).
 * @returns {string}
 */
function getGuatemalaIsoTimestamp() {
  const nowUtcMs = Date.now();
  const gtDate = new Date(nowUtcMs - 6 * 60 * 60 * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  const y = gtDate.getUTCFullYear();
  const m = pad(gtDate.getUTCMonth() + 1);
  const d = pad(gtDate.getUTCDate());
  const hh = pad(gtDate.getUTCHours());
  const mm = pad(gtDate.getUTCMinutes());
  const ss = pad(gtDate.getUTCSeconds());
  return `${y}-${m}-${d}T${hh}:${mm}:${ss}-06:00`;
}

/**
 * Normaliza los parámetros recibidos (URLSearchParams, objeto o query string).
 * @param {string} path
 * @param {URLSearchParams | Record<string, unknown> | undefined} params
 * @returns {{ pathname: string, fields: Record<string, string> }}
 */
function parsePathAndParams(path, params) {
  const rawPath = String(path || '');
  const qIndex = rawPath.indexOf('?');
  const pathname = qIndex >= 0 ? rawPath.slice(0, qIndex) : rawPath;
  const fields = {};

  if (qIndex >= 0) {
    const query = new URLSearchParams(rawPath.slice(qIndex + 1));
    query.forEach((value, key) => {
      fields[key] = value;
    });
  }

  if (params instanceof URLSearchParams) {
    params.forEach((value, key) => {
      fields[key] = value;
    });
  } else if (params && typeof params === 'object') {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        fields[key] = String(value);
      }
    });
  }

  return { pathname, fields };
}

/**
 * Crea una respuesta homogénea estilo SIREC.
 * @param {number} status
 * @param {Record<string, unknown>} data
 * @returns {{ ok: boolean, status: number, data: Record<string, unknown> }}
 */
function buildResponse(status, data) {
  return {
    ok: status >= 200 && status < 300,
    status,
    data: cloneData(data),
  };
}

/**
 * Resuelve GET /sirec/api/iusi?finca=...
 * @param {Record<string, string>} fields
 */
function handleGetIusi(fields) {
  const finca = String(fields.finca || '').trim();
  if (!FINCA_REGEX.test(finca)) {
    return buildResponse(400, {
      error: 'finca_invalida',
      mensaje:
        'El número de finca debe tener el formato F- seguido de 4 o 5 dígitos (por ejemplo, F-1024).',
    });
  }

  const record = FINCAS_SEMILLA[finca];
  if (!record) {
    return buildResponse(404, {
      error: 'finca_no_encontrada',
      mensaje: 'No se encontró ninguna finca registrada con el número indicado.',
    });
  }

  return buildResponse(200, record);
}

/**
 * Resuelve POST /sirec/api/orden-pago
 * @param {Record<string, string>} fields
 */
function handlePostOrdenPago(fields) {
  const concepto = String(fields.concepto || '').trim().toLowerCase();
  const rawReferencia = String(fields.referencia || '').trim();

  if (!VALID_CONCEPTOS.has(concepto)) {
    return buildResponse(400, {
      error: 'concepto_invalido',
      mensaje:
        'El concepto seleccionado no es válido. Elige IUSI, boleto de ornato, agua o multa PMT.',
    });
  }

  if (!rawReferencia) {
    return buildResponse(400, {
      error: 'referencia_invalida',
      mensaje: 'Ingresa una referencia válida para generar la orden de pago.',
    });
  }

  const pagarEn = 'Agencias bancarias autorizadas (ficticio)';
  const vence = '2026-11-28';

  if (concepto === 'iusi') {
    const finca = rawReferencia.toUpperCase();
    if (!FINCA_REGEX.test(finca)) {
      return buildResponse(400, {
        error: 'referencia_invalida',
        mensaje:
          'El número de finca debe tener el formato F- seguido de 4 o 5 dígitos (por ejemplo, F-1024).',
      });
    }

    const record = FINCAS_SEMILLA[finca];
    if (!record) {
      return buildResponse(404, {
        error: 'referencia_no_encontrada',
        mensaje: 'No se encontró ninguna finca registrada con el número indicado.',
      });
    }

    if (record.saldo_pendiente <= 0) {
      return buildResponse(400, {
        error: 'sin_saldo',
        mensaje: `No hay saldo pendiente para ${finca}. Estás al día.`,
      });
    }

    const ordenCode =
      finca === 'F-1024'
        ? 'OP-2026-004512'
        : finca === 'F-3072'
          ? 'OP-2026-004519'
          : `OP-2026-${String(nextOrdenSeq++).padStart(6, '0')}`;

    return buildResponse(200, {
      orden: ordenCode,
      concepto: 'iusi',
      referencia: finca,
      monto: record.saldo_pendiente,
      moneda: 'GTQ',
      vence,
      pagar_en: pagarEn,
    });
  }

  if (concepto === 'ornato') {
    const soloPermitidos = /^[\d\s-]+$/.test(rawReferencia);
    const digits = rawReferencia.replace(/[\s-]+/g, '');
    if (!soloPermitidos || !/^\d{13}$/.test(digits)) {
      return buildResponse(400, {
        error: 'referencia_invalida',
        mensaje: 'El DPI debe contener exactamente 13 dígitos (por ejemplo, 1001 47673 0101).',
      });
    }

    if (digits === '0000000000000') {
      return buildResponse(404, {
        error: 'referencia_no_encontrada',
        mensaje: 'No se encontró registro de contribuyente para el DPI indicado.',
      });
    }

    return buildResponse(200, {
      orden: `OP-2026-${String(nextOrdenSeq++).padStart(6, '0')}`,
      concepto: 'ornato',
      referencia: `${digits.slice(0, 4)} ${digits.slice(4, 9)} ${digits.slice(9)}`,
      monto: 15.0,
      moneda: 'GTQ',
      vence,
      pagar_en: pagarEn,
    });
  }

  if (concepto === 'agua') {
    const ref = rawReferencia.toUpperCase();
    if (!/^A-\d{5}$/.test(ref)) {
      return buildResponse(400, {
        error: 'referencia_invalida',
        mensaje: 'El número de contador debe tener el formato A- seguido de 5 dígitos (por ejemplo, A-10006).',
      });
    }

    if (ref.endsWith('0000')) {
      return buildResponse(404, {
        error: 'referencia_no_encontrada',
        mensaje: 'No se encontró ningún contador de agua registrado con la referencia indicada.',
      });
    }

    return buildResponse(200, {
      orden: `OP-2026-${String(nextOrdenSeq++).padStart(6, '0')}`,
      concepto: 'agua',
      referencia: ref,
      monto: 605.56,
      moneda: 'GTQ',
      vence,
      pagar_en: pagarEn,
    });
  }

  // multa
  const boleta = rawReferencia.toUpperCase();
  if (!/^PMT-2026-\d{5}$/.test(boleta)) {
    return buildResponse(400, {
      error: 'referencia_invalida',
      mensaje: 'El número de boleta debe tener el formato PMT-2026- seguido de 5 dígitos (por ejemplo, PMT-2026-00101).',
    });
  }

  if (boleta.endsWith('00000')) {
    return buildResponse(404, {
      error: 'referencia_no_encontrada',
      mensaje: 'No se encontró ninguna boleta de multa PMT con la referencia indicada.',
    });
  }

  return buildResponse(200, {
    orden: `OP-2026-${String(nextOrdenSeq++).padStart(6, '0')}`,
    concepto: 'multa',
    referencia: boleta,
    monto: 150.0,
    moneda: 'GTQ',
    vence,
    pagar_en: pagarEn,
  });
}

/**
 * Resuelve POST /sirec/api/laip
 * @param {Record<string, string>} fields
 */
function handlePostLaip(fields) {
  const nombre = String(fields.nombre || '').trim();
  const descripcion = String(fields.descripcion || '').trim();

  if (!nombre || !descripcion) {
    return buildResponse(400, {
      error: 'campo_obligatorio',
      mensaje: 'Completa tu nombre y la descripción de la información solicitada.',
    });
  }

  if (descripcion.length < 10) {
    return buildResponse(400, {
      error: 'descripcion_corta',
      mensaje:
        'La descripción debe tener al menos 10 caracteres para poder atender tu solicitud.',
    });
  }

  if (descripcion.length > 2000) {
    return buildResponse(400, {
      error: 'campo_obligatorio',
      mensaje: 'La descripción no puede superar los 2,000 caracteres.',
    });
  }

  const folio = `LAIP-2026-${String(nextLaipSeq++).padStart(4, '0')}`;
  const fecha = '2026-11-21';
  const vence = '2026-12-07';

  laipStore.set(folio, {
    folio,
    fecha,
    vence,
    estado: 'recibida',
    dias_restantes: 10,
  });

  return buildResponse(201, {
    folio,
    fecha,
    vence,
    estado: 'recibida',
  });
}

/**
 * Resuelve GET /sirec/api/laip/:folio
 * @param {string} encodedFolio
 */
function handleGetLaip(encodedFolio) {
  let folio = '';
  try {
    folio = decodeURIComponent(encodedFolio || '').trim().toUpperCase();
  } catch {
    folio = String(encodedFolio || '').trim().toUpperCase();
  }

  const record = laipStore.get(folio);
  if (!record) {
    return buildResponse(404, {
      error: 'folio_no_encontrado',
      mensaje: 'No se encontró ninguna solicitud registrada con ese número de folio.',
    });
  }

  return buildResponse(200, record);
}

/**
 * Ejecuta una petición simulada contra el contrato de SIREC.
 * @param {'GET' | 'POST'} method
 * @param {string} path
 * @param {URLSearchParams | Record<string, unknown>} [params]
 * @returns {Promise<{ ok: boolean, status: number, data: Record<string, unknown> }>}
 */
export async function mockRequest(method, path, params) {
  const normalizedMethod = String(method || 'GET').toUpperCase();
  const { pathname, fields } = parsePathAndParams(path, params);

  await new Promise((resolve) => {
    setTimeout(resolve, MOCK_DELAY_MS);
  });

  if (normalizedMethod === 'GET' && pathname === '/sirec/api/estado') {
    return buildResponse(200, {
      sistema: 'SIREC',
      version: '3.2.1',
      municipalidad: 'MuniSoke GT (ficticia)',
      hora_servidor: getGuatemalaIsoTimestamp(),
    });
  }

  if (normalizedMethod === 'GET' && pathname === '/sirec/api/iusi') {
    return handleGetIusi(fields);
  }

  if (normalizedMethod === 'POST' && pathname === '/sirec/api/orden-pago') {
    return handlePostOrdenPago(fields);
  }

  if (normalizedMethod === 'POST' && pathname === '/sirec/api/laip') {
    return handlePostLaip(fields);
  }

  if (normalizedMethod === 'GET' && pathname.startsWith('/sirec/api/laip/')) {
    const rawFolio = pathname.slice('/sirec/api/laip/'.length);
    return handleGetLaip(rawFolio);
  }

  return buildResponse(404, {
    error: 'ruta_no_encontrada',
    mensaje: 'El recurso solicitado no existe en SIREC.',
  });
}

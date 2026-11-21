/**
 * Integración frontend con SIREC (Sistema de Recaudación ficticio de MuniSoke GT).
 * - ES module puro, 100% offline, sin dependencias externas.
 * - Todas las llamadas usan rutas relativas /sirec/api/... (mismo origen).
 * - Modo mock (?mock=1): importa dinámicamente ./sirec-mock.js solo cuando aplica.
 * - Construcción segura del DOM (createElement + textContent, sin inyección HTML).
 */

const MSG_NO_DISPONIBLE =
  'El sistema de recaudación no está disponible, intenta más tarde.';
const REQUEST_TIMEOUT_MS = 12000;
const SVG_NS = 'http://www.w3.org/2000/svg';

const FINCA_REGEX = /^F-\d{4,5}$/;
const ALFANUM_REF_REGEX = /^(?=.*[A-Za-z0-9])[A-Za-z0-9-]{4,32}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const GTQ_FORMATTER = new Intl.NumberFormat('es-GT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const CONCEPTO_META = Object.freeze({
  iusi: {
    nombre: 'IUSI',
    label: 'Número de finca',
    placeholder: 'Ej. F-1024',
    hint: 'Formato F- seguido de 4 o 5 dígitos (por ejemplo, F-1024).',
    errorMsg:
      'Ingresa un número de finca válido (formato F- seguido de 4 o 5 dígitos, ej. F-1024).',
    normalize: (val) => val.trim().toUpperCase(),
    validate: (val) => FINCA_REGEX.test(val),
  },
  ornato: {
    nombre: 'Boleto de Ornato',
    label: 'Número de DPI (ficticio)',
    placeholder: 'Ej. 1001 47673 0101',
    hint: 'Ingresa 13 dígitos de DPI ficticio (puedes separar con espacios o guiones).',
    errorMsg: 'Ingresa un DPI válido de 13 dígitos (por ejemplo, 1001 47673 0101).',
    // SIREC guarda el DPI como "#### ##### ####": se envía siempre con ese formato.
    normalize: (val) => {
      const d = val.replace(/[\s-]+/g, '');
      return /^\d{13}$/.test(d) ? `${d.slice(0, 4)} ${d.slice(4, 9)} ${d.slice(9)}` : val.trim();
    },
    validate: (val) => /^[\d\s-]+$/.test(val) && val.replace(/[\s-]+/g, '').length === 13,
  },
  agua: {
    nombre: 'Agua EMPASOKE',
    label: 'Número de contador',
    placeholder: 'Ej. A-10006',
    hint: 'Formato A- seguido de 5 dígitos, como aparece en tu recibo de agua.',
    errorMsg: 'Ingresa un número de contador válido (formato A- seguido de 5 dígitos, ej. A-10006).',
    normalize: (val) => val.trim().toUpperCase(),
    validate: (val) => /^A-\d{5}$/.test(val),
  },
  multa: {
    nombre: 'Multa PMT',
    label: 'Número de boleta PMT',
    placeholder: 'Ej. PMT-2026-00101',
    hint: 'Formato PMT-2026- seguido de 5 dígitos, como aparece en tu boleta.',
    errorMsg: 'Ingresa un número de boleta válido (formato PMT-2026- seguido de 5 dígitos, ej. PMT-2026-00101).',
    normalize: (val) => val.trim().toUpperCase(),
    validate: (val) => /^PMT-2026-\d{5}$/.test(val),
  },
});

const IUSI_ESTADO_LABELS = Object.freeze({
  pagado: { label: 'Pagado', badgeClass: 'sirec-badge--pagado', icon: 'check' },
  pendiente: { label: 'Pendiente', badgeClass: 'sirec-badge--pendiente', icon: 'clock' },
  vencido: { label: 'Vencido', badgeClass: 'sirec-badge--vencido', icon: 'alert' },
});

const LAIP_ESTADO_LABELS = Object.freeze({
  recibida: { label: 'Recibida', badgeClass: 'sirec-badge--recibida', icon: 'inbox' },
  en_tramite: { label: 'En trámite', badgeClass: 'sirec-badge--en_tramite', icon: 'clock' },
  resuelta: { label: 'Resuelta', badgeClass: 'sirec-badge--resuelta', icon: 'check' },
  prorrogada: { label: 'Prorrogada', badgeClass: 'sirec-badge--prorrogada', icon: 'alert' },
});

let mockModulePromise = null;
let initializedRoot = null;

/**
 * Indica si el modo mock local está activo mediante ?mock=1 en la URL.
 * @returns {boolean}
 */
export function esModoMock() {
  if (typeof window === 'undefined' || !window.location) {
    return false;
  }
  try {
    return new URLSearchParams(window.location.search).get('mock') === '1';
  } catch {
    return false;
  }
}

/**
 * Formatea un monto numérico en quetzales con prefijo fijo "Q " (ej. "Q 1,665.00").
 * @param {number | string} monto
 * @returns {string}
 */
export function formatearQuetzales(monto) {
  const num = Number(monto);
  const safeNum = Number.isFinite(num) ? num : 0;
  return `Q ${GTQ_FORMATTER.format(safeNum)}`;
}

/**
 * Carga perezosamente el módulo mock solo cuando ?mock=1 está activo.
 * @returns {Promise<{ mockRequest: Function }>}
 */
function loadMockModule() {
  if (!mockModulePromise) {
    mockModulePromise = import('./sirec-mock.js');
  }
  return mockModulePromise;
}

/**
 * Ejecuta una petición contra SIREC (o el mock si ?mock=1).
 * @param {'GET' | 'POST'} method
 * @param {string} path Ruta relativa iniciando con /sirec/api/...
 * @param {Record<string, string>} [bodyFields]
 * @returns {Promise<{ ok: boolean, status: number, data?: Record<string, any>, error?: string, mensaje?: string }>}
 */
async function sirecRequest(method, path, bodyFields) {
  if (esModoMock()) {
    try {
      const { mockRequest } = await loadMockModule();
      const params =
        method === 'POST' && bodyFields ? new URLSearchParams(bodyFields) : undefined;
      const res = await mockRequest(method, path, params);
      if (res && res.ok) {
        return { ok: true, status: res.status, data: res.data };
      }
      const mensaje =
        res?.data && typeof res.data.mensaje === 'string' && res.data.mensaje.trim()
          ? res.data.mensaje.trim()
          : MSG_NO_DISPONIBLE;
      return {
        ok: false,
        status: res?.status || 500,
        error: res?.data?.error || 'sistema_no_disponible',
        mensaje,
        data: res?.data,
      };
    } catch {
      return {
        ok: false,
        status: 0,
        error: 'sistema_no_disponible',
        mensaje: MSG_NO_DISPONIBLE,
      };
    }
  }

  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const timeoutId = controller
    ? window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
    : null;

  try {
    /** @type {RequestInit} */
    const init = {
      method,
      headers: {
        Accept: 'application/json',
      },
      credentials: 'same-origin',
      signal: controller ? controller.signal : undefined,
    };

    if (method === 'POST') {
      const formParams = new URLSearchParams();
      Object.entries(bodyFields || {}).forEach(([key, value]) => {
        formParams.append(key, value ?? '');
      });
      init.headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8';
      init.body = formParams.toString();
    }

    const response = await fetch(path, init);
    const rawText = await response.text();
    let parsed = null;

    if (rawText) {
      try {
        const maybeJson = JSON.parse(rawText);
        if (maybeJson && typeof maybeJson === 'object' && !Array.isArray(maybeJson)) {
          parsed = maybeJson;
        }
      } catch {
        parsed = null;
      }
    }

    if (response.ok) {
      if (!parsed) {
        return {
          ok: false,
          status: response.status,
          error: 'respuesta_invalida',
          mensaje: MSG_NO_DISPONIBLE,
        };
      }
      return { ok: true, status: response.status, data: parsed };
    }

    const backendMensaje =
      parsed && typeof parsed.mensaje === 'string' && parsed.mensaje.trim()
        ? parsed.mensaje.trim()
        : null;

    return {
      ok: false,
      status: response.status,
      error: (parsed && parsed.error) || 'sistema_no_disponible',
      mensaje: backendMensaje || MSG_NO_DISPONIBLE,
      data: parsed || undefined,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      error: 'sistema_no_disponible',
      mensaje: MSG_NO_DISPONIBLE,
    };
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }
}

/**
 * GET /sirec/api/estado
 */
export function obtenerEstado() {
  return sirecRequest('GET', '/sirec/api/estado');
}

/**
 * GET /sirec/api/iusi?finca=...
 * @param {string} finca
 */
export function consultarIusi(finca) {
  const normalized = String(finca || '').trim().toUpperCase();
  return sirecRequest('GET', `/sirec/api/iusi?finca=${encodeURIComponent(normalized)}`);
}

/**
 * POST /sirec/api/orden-pago
 * Acepta ({ concepto, referencia }) o (concepto, referencia).
 * @param {{ concepto: string, referencia: string } | string} conceptoOrPayload
 * @param {string} [referenciaArg]
 */
export function generarOrdenPago(conceptoOrPayload, referenciaArg) {
  const payload =
    typeof conceptoOrPayload === 'object' && conceptoOrPayload !== null
      ? conceptoOrPayload
      : { concepto: conceptoOrPayload, referencia: referenciaArg };

  return sirecRequest('POST', '/sirec/api/orden-pago', {
    concepto: String(payload.concepto || '').trim().toLowerCase(),
    referencia: String(payload.referencia || '').trim(),
  });
}

/**
 * POST /sirec/api/laip
 * @param {{ nombre: string, correo?: string, descripcion: string }} payload
 */
export function crearSolicitudLaip({ nombre, correo = '', descripcion }) {
  return sirecRequest('POST', '/sirec/api/laip', {
    nombre: String(nombre || '').trim(),
    correo: String(correo || '').trim(),
    descripcion: String(descripcion || '').trim(),
  });
}

/**
 * GET /sirec/api/laip/:folio
 * @param {string} folio
 */
export function consultarSeguimientoLaip(folio) {
  const normalized = String(folio || '').trim().toUpperCase();
  return sirecRequest('GET', `/sirec/api/laip/${encodeURIComponent(normalized)}`);
}

/* -------------------------------------------------------------------------- */
/* Helpers seguros de construcción de DOM                                     */
/* -------------------------------------------------------------------------- */

/**
 * Crea un elemento HTML con atributos y nodos hijos de forma segura.
 * @param {string} tag
 * @param {Record<string, string | boolean | null | undefined>} [attrs]
 * @param {Array<Node | string | null | undefined>} [children]
 * @returns {HTMLElement}
 */
function createEl(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (value === undefined || value === null || value === false) return;
    if (key === 'className') {
      node.className = String(value);
    } else if (value === true) {
      node.setAttribute(key, '');
    } else {
      node.setAttribute(key, String(value));
    }
  });
  children.forEach((child) => {
    if (child === null || child === undefined) return;
    if (typeof child === 'string' || typeof child === 'number') {
      node.appendChild(document.createTextNode(String(child)));
    } else {
      node.appendChild(child);
    }
  });
  return node;
}

/**
 * Crea un ícono SVG estático controlado mediante DOM SVG puro.
 * @param {'check' | 'clock' | 'alert' | 'inbox' | 'printer' | 'arrow'} name
 * @param {number} [size]
 * @returns {SVGSVGElement}
 */
function createSvgIcon(name, size = 16) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('width', String(size));
  svg.setAttribute('height', String(size));
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2.1');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');

  const appendShape = (shapeTag, shapeAttrs) => {
    const shape = document.createElementNS(SVG_NS, shapeTag);
    Object.entries(shapeAttrs).forEach(([k, v]) => shape.setAttribute(k, v));
    svg.appendChild(shape);
  };

  switch (name) {
    case 'check':
      appendShape('circle', { cx: '12', cy: '12', r: '9' });
      appendShape('path', { d: 'm8.5 12.2 2.4 2.4 4.8-5.1' });
      break;
    case 'clock':
      appendShape('circle', { cx: '12', cy: '12', r: '9' });
      appendShape('path', { d: 'M12 7.5V12l3 2' });
      break;
    case 'alert':
      appendShape('path', {
        d: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z',
      });
      appendShape('line', { x1: '12', y1: '9', x2: '12', y2: '13' });
      appendShape('line', { x1: '12', y1: '17', x2: '12.01', y2: '17' });
      break;
    case 'inbox':
      appendShape('rect', { x: '3', y: '5', width: '18', height: '14', rx: '2' });
      appendShape('path', { d: 'm3 12 4.5 0 2 3h5l2-3H21' });
      break;
    case 'printer':
      appendShape('polyline', { points: '6 9 6 3 18 3 18 9' });
      appendShape('path', {
        d: 'M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2',
      });
      appendShape('rect', { x: '6', y: '14', width: '12', height: '7' });
      break;
    case 'arrow':
    default:
      appendShape('path', { d: 'M5 12h14' });
      appendShape('path', { d: 'm13 6 6 6-6 6' });
      break;
  }

  return svg;
}

/**
 * Crea una insignia accesible (ícono SVG + texto, nunca solo color).
 * @param {{ label: string, badgeClass: string, icon: 'check' | 'clock' | 'alert' | 'inbox' }} spec
 * @returns {HTMLSpanElement}
 */
function createBadge(spec) {
  return createEl(
    'span',
    { className: `sirec-badge ${spec.badgeClass}` },
    [createSvgIcon(spec.icon, 14), createEl('span', {}, [spec.label])]
  );
}

/**
 * Crea una fila dt/dd dentro de un <dl class="sirec-dl">.
 * @param {string} term
 * @param {Node | string} value
 * @param {string} [extraClass]
 * @returns {HTMLDivElement}
 */
function createDlRow(term, value, extraClass = '') {
  return createEl(
    'div',
    { className: extraClass ? `sirec-dl-item ${extraClass}` : 'sirec-dl-item' },
    [createEl('dt', {}, [term]), createEl('dd', {}, [value])]
  );
}

/**
 * Limpia y renderiza el estado de carga en un contenedor de resultados.
 * @param {HTMLElement | null} container
 * @param {string} message
 */
function renderLoadingState(container, message) {
  if (!container) return;
  container.setAttribute('aria-busy', 'true');
  container.replaceChildren(
    createEl('div', { className: 'sirec-state sirec-state--loading', role: 'status' }, [
      createEl('span', { className: 'sirec-spinner', 'aria-hidden': 'true' }),
      createEl('span', { className: 'sirec-state-msg' }, [message]),
    ])
  );
}

/**
 * Limpia y renderiza el estado de error accesible en un contenedor de resultados.
 * @param {HTMLElement | null} container
 * @param {string} title
 * @param {string} message
 */
function renderErrorState(container, title, message) {
  if (!container) return;
  container.setAttribute('aria-busy', 'false');
  container.replaceChildren(
    createEl('div', { className: 'sirec-state sirec-state--error', role: 'alert' }, [
      createSvgIcon('alert', 20),
      createEl('div', {}, [
        createEl('p', { className: 'sirec-state-title' }, [title]),
        createEl('p', { className: 'sirec-state-msg' }, [message || MSG_NO_DISPONIBLE]),
      ]),
    ])
  );
}

/**
 * Marca o limpia el error inline en un campo de formulario.
 * @param {HTMLElement | null} inputEl
 * @param {HTMLElement | null} errorEl
 * @param {string} message
 */
function setFieldError(inputEl, errorEl, message) {
  if (!inputEl) return;
  const fieldWrap = inputEl.closest('.sirec-field');
  const hasError = Boolean(message);

  if (fieldWrap) {
    fieldWrap.classList.toggle('has-error', hasError);
  }

  if (hasError) {
    inputEl.setAttribute('aria-invalid', 'true');
  } else {
    inputEl.removeAttribute('aria-invalid');
  }

  if (errorEl) {
    errorEl.textContent = hasError ? message : '';
    errorEl.hidden = !hasError;
  }
}

/**
 * Enfoca un elemento de forma segura respetando preventScroll cuando se solicita.
 * @param {HTMLElement | null} el
 * @param {boolean} [preventScroll]
 */
function safeFocus(el, preventScroll = false) {
  if (!el || typeof el.focus !== 'function') return;
  try {
    el.focus({ preventScroll });
  } catch {
    el.focus();
  }
}

/**
 * Desplaza suavemente hasta la sección #tramites respetando prefers-reduced-motion.
 * @param {HTMLElement} target
 */
function scrollToSection(target) {
  if (!target || typeof target.scrollIntoView !== 'function') return;
  const prefersReducedMotion =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  target.scrollIntoView({
    behavior: prefersReducedMotion ? 'auto' : 'smooth',
    block: 'start',
  });
}

/**
 * Registra utilitarios de depuración/QA en window.__munisoke.sirec sin pisar propiedades existentes.
 * @param {Record<string, unknown>} extra
 */
function exposeDebugApi(extra = {}) {
  if (typeof window === 'undefined') return;
  window.__munisoke = window.__munisoke || {};
  window.__munisoke.sirec = {
    esModoMock,
    formatearQuetzales,
    obtenerEstado,
    consultarIusi,
    generarOrdenPago,
    crearSolicitudLaip,
    consultarSeguimientoLaip,
    ...extra,
  };
}

/**
 * Inicializa la interfaz de trámites en línea conectada a SIREC dentro de #tramites.
 * En páginas internas de Drupal donde #tramites no existe, sale limpiamente sin peticiones.
 */
export function initSirec() {
  const root = document.getElementById('tramites');
  if (!root) {
    exposeDebugApi({ mounted: false });
    return null;
  }

  if (initializedRoot === root) {
    return window.__munisoke?.sirec || null;
  }
  initializedRoot = root;

  // Referencias globales de estado y aviso
  const statusBox = document.getElementById('sirec-status');
  const statusText = document.getElementById('sirec-status-text');
  const mockBadge = document.getElementById('sirec-mock-badge');
  const statusRetryBtn = document.getElementById('sirec-status-retry');
  const noticeBox = document.getElementById('sirec-notice');

  const isMock = esModoMock();
  if (mockBadge) {
    mockBadge.hidden = !isMock;
  }

  /* ------------------------------------------------------------------------ */
  /* Estado de conexión SIREC                                                 */
  /* ------------------------------------------------------------------------ */
  async function checkEstado() {
    if (statusBox) {
      statusBox.dataset.status = 'loading';
    }
    if (statusText) {
      statusText.textContent = 'Verificando conexión con SIREC…';
    }
    if (statusRetryBtn) {
      statusRetryBtn.hidden = true;
      statusRetryBtn.disabled = true;
    }

    const res = await obtenerEstado();

    if (res.ok && res.data) {
      const version = res.data.version ? `v${res.data.version}` : '';
      const muni = res.data.municipalidad || 'MuniSoke GT (ficticia)';
      if (statusBox) {
        statusBox.dataset.status = 'online';
      }
      if (statusText) {
        statusText.textContent = `SIREC ${version} en línea · ${muni}`.replace(/\s+/g, ' ').trim();
      }
      if (statusRetryBtn) {
        statusRetryBtn.hidden = true;
        statusRetryBtn.disabled = false;
      }
      return res;
    }

    if (statusBox) {
      statusBox.dataset.status = 'offline';
    }
    if (statusText) {
      statusText.textContent = res.mensaje || MSG_NO_DISPONIBLE;
    }
    if (statusRetryBtn) {
      statusRetryBtn.hidden = false;
      statusRetryBtn.disabled = false;
    }
    return res;
  }

  if (statusRetryBtn) {
    statusRetryBtn.addEventListener('click', () => {
      checkEstado();
    });
  }

  /* ------------------------------------------------------------------------ */
  /* Aviso contextual                                                         */
  /* ------------------------------------------------------------------------ */
  function setNotice(message) {
    if (!noticeBox) return;
    const text = String(message || '').trim();
    noticeBox.textContent = text;
    noticeBox.hidden = !text;
  }

  /* ------------------------------------------------------------------------ */
  /* Pestañas WAI-ARIA                                                        */
  /* ------------------------------------------------------------------------ */
  const tabs = Array.from(root.querySelectorAll('[data-sirec-tab]'));
  const panels = Array.from(root.querySelectorAll('[data-sirec-panel]'));

  const getTabKey = (tabEl) =>
    (tabEl.dataset.sirecTab || tabEl.id.replace(/^tab-/, '')).trim().toLowerCase();

  const getPanelKey = (panelEl) =>
    (panelEl.dataset.sirecPanel || panelEl.id.replace(/^panel-/, '')).trim().toLowerCase();

  /**
   * Activa una pestaña SIREC y sincroniza atributos ARIA y paneles.
   * @param {string} key
   * @param {{ focusTab?: boolean, focusInput?: boolean, scroll?: boolean, keepNotice?: boolean }} [options]
   */
  function activateTab(
    key,
    { focusTab = false, focusInput = false, scroll = false, keepNotice = false } = {}
  ) {
    const normalizedKey = String(key || '').trim().toLowerCase();
    const targetTab = tabs.find((t) => getTabKey(t) === normalizedKey) || tabs[0];
    if (!targetTab) return;

    const resolvedKey = getTabKey(targetTab);
    const controlledId = targetTab.getAttribute('aria-controls');

    if (!keepNotice) {
      setNotice('');
    }

    tabs.forEach((tab) => {
      const isSelected = tab === targetTab;
      tab.setAttribute('aria-selected', String(isSelected));
      tab.setAttribute('tabindex', isSelected ? '0' : '-1');
      tab.classList.toggle('is-active', isSelected);
    });

    let activePanel = null;
    panels.forEach((panel) => {
      const matches =
        getPanelKey(panel) === resolvedKey ||
        (controlledId && panel.id === controlledId);
      panel.hidden = !matches;
      if (matches) {
        activePanel = panel;
      }
    });

    if (scroll) {
      scrollToSection(root);
    }

    if (focusTab) {
      safeFocus(targetTab, scroll);
    } else if (focusInput && activePanel) {
      const firstControl = activePanel.querySelector(
        'input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
      );
      safeFocus(firstControl, scroll);
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => {
      activateTab(getTabKey(tab), { focusTab: false });
    });

    tab.addEventListener('keydown', (event) => {
      if (tabs.length === 0) return;
      let nextIndex = null;
      if (event.key === 'ArrowRight') {
        nextIndex = (index + 1) % tabs.length;
      } else if (event.key === 'ArrowLeft') {
        nextIndex = (index - 1 + tabs.length) % tabs.length;
      } else if (event.key === 'Home') {
        nextIndex = 0;
      } else if (event.key === 'End') {
        nextIndex = tabs.length - 1;
      }

      if (nextIndex !== null) {
        event.preventDefault();
        activateTab(getTabKey(tabs[nextIndex]), { focusTab: true });
      }
    });
  });

  // Asegurar estado inicial coherente de pestañas
  const initiallySelected =
    tabs.find((t) => t.getAttribute('aria-selected') === 'true') || tabs[0];
  if (initiallySelected) {
    activateTab(getTabKey(initiallySelected), { keepNotice: true });
  }

  /* ------------------------------------------------------------------------ */
  /* Formulario 2: Orden de pago (se define antes para enlazar desde IUSI)    */
  /* ------------------------------------------------------------------------ */
  const ordenForm = document.getElementById('form-orden');
  const ordenConcepto = document.getElementById('orden-concepto');
  const ordenConceptoError = document.getElementById('orden-concepto-error');
  const ordenRefLabel = document.getElementById('orden-referencia-label');
  const ordenRefInput = document.getElementById('orden-referencia');
  const ordenRefHint = document.getElementById('orden-referencia-hint');
  const ordenRefError = document.getElementById('orden-referencia-error');
  const ordenSubmitBtn = document.getElementById('btn-orden-submit');
  const ordenResultado = document.getElementById('orden-resultado');

  function updateOrdenReferenciaMeta(conceptoKey) {
    const meta = CONCEPTO_META[conceptoKey] || CONCEPTO_META.iusi;
    if (ordenRefLabel) {
      ordenRefLabel.replaceChildren(
        document.createTextNode(`${meta.label} `),
        createEl('span', { className: 'req', 'aria-hidden': 'true' }, ['*'])
      );
    }
    if (ordenRefInput) {
      ordenRefInput.setAttribute('placeholder', meta.placeholder);
    }
    if (ordenRefHint) {
      ordenRefHint.textContent = meta.hint;
    }
    setFieldError(ordenConcepto, ordenConceptoError, '');
    setFieldError(ordenRefInput, ordenRefError, '');
  }

  function renderOrdenSuccess(data) {
    if (!ordenResultado) return;
    ordenResultado.setAttribute('aria-busy', 'false');

    const conceptoKey = String(data.concepto || '').toLowerCase();
    const conceptoNombre = CONCEPTO_META[conceptoKey]?.nombre || data.concepto || '—';

    const printBtn = createEl(
      'button',
      {
        type: 'button',
        id: 'btn-orden-imprimir',
        className: 'btn sirec-btn-primary',
      },
      [createSvgIcon('printer', 16), createEl('span', {}, ['Imprimir orden de pago'])]
    );
    printBtn.addEventListener('click', () => {
      window.print();
    });

    const voucher = createEl(
      'article',
      {
        id: 'orden-comprobante',
        className: 'sirec-voucher',
        'aria-label': 'Orden de pago generada',
      },
      [
        createEl('div', { className: 'sirec-voucher-print-head' }, [
          createEl('strong', {}, ['MuniSoke GT · Municipalidad de Soke']),
          createEl('span', {}, [
            'Orden de pago para agencia bancaria · Portal ficticio de demostración',
          ]),
        ]),
        createEl('div', { className: 'sirec-voucher-top' }, [
          createEl('div', {}, [
            createEl('span', { className: 'sirec-voucher-label' }, ['Número de orden']),
            createEl('strong', { className: 'sirec-voucher-code' }, [data.orden || '—']),
          ]),
          createEl('div', {}, [
            createEl('span', { className: 'sirec-voucher-label' }, ['Monto a pagar']),
            createEl('strong', { className: 'sirec-voucher-amount' }, [
              formatearQuetzales(data.monto),
            ]),
          ]),
        ]),
        createEl('dl', { className: 'sirec-dl sirec-voucher-meta' }, [
          createDlRow('Concepto', conceptoNombre),
          createDlRow('Referencia', data.referencia || '—'),
          createDlRow('Fecha límite de pago', data.vence || '—'),
          createDlRow('Dónde pagar', data.pagar_en || 'Agencias bancarias autorizadas (ficticio)'),
        ]),
        createEl('p', { className: 'sirec-voucher-note' }, [
          'Presenta esta orden impresa o el número de orden en agencia bancaria autorizada. MuniSoke GT no solicita datos de tarjeta ni realiza cobros en línea.',
        ]),
        createEl('div', { className: 'sirec-actions no-print' }, [printBtn]),
      ]
    );

    ordenResultado.replaceChildren(voucher);
  }

  let ordenInFlight = false;

  async function submitOrdenPago() {
    if (!ordenForm || ordenInFlight) return;

    const concepto = String(ordenConcepto?.value || '').trim().toLowerCase();
    const meta = CONCEPTO_META[concepto];
    const rawRef = String(ordenRefInput?.value || '');
    const normalizedRef = meta ? meta.normalize(rawRef) : rawRef.trim();

    if (ordenRefInput && normalizedRef) {
      ordenRefInput.value = normalizedRef;
    }

    let firstInvalid = null;

    if (!meta) {
      setFieldError(
        ordenConcepto,
        ordenConceptoError,
        'Selecciona un concepto válido para generar la orden de pago.'
      );
      firstInvalid = firstInvalid || ordenConcepto;
    } else {
      setFieldError(ordenConcepto, ordenConceptoError, '');
    }

    if (!normalizedRef || (meta && !meta.validate(normalizedRef))) {
      setFieldError(
        ordenRefInput,
        ordenRefError,
        meta ? meta.errorMsg : 'Ingresa una referencia válida.'
      );
      firstInvalid = firstInvalid || ordenRefInput;
    } else {
      setFieldError(ordenRefInput, ordenRefError, '');
    }

    if (firstInvalid) {
      if (ordenResultado) ordenResultado.replaceChildren(); // no dejar a la vista un resultado de una consulta anterior
      safeFocus(firstInvalid);
      return;
    }

    ordenInFlight = true;
    if (ordenSubmitBtn) ordenSubmitBtn.disabled = true;
    renderLoadingState(ordenResultado, 'Generando orden de pago en SIREC…');

    try {
      const res = await generarOrdenPago({ concepto, referencia: normalizedRef });
      if (res.ok && res.data) {
        renderOrdenSuccess(res.data);
      } else {
        renderErrorState(
          ordenResultado,
          'No se pudo generar la orden de pago',
          res.mensaje || MSG_NO_DISPONIBLE
        );
      }
    } finally {
      ordenInFlight = false;
      if (ordenSubmitBtn) ordenSubmitBtn.disabled = false;
      if (ordenResultado) ordenResultado.setAttribute('aria-busy', 'false');
    }
  }

  if (ordenConcepto) {
    updateOrdenReferenciaMeta(ordenConcepto.value || 'iusi');
    ordenConcepto.addEventListener('change', () => {
      updateOrdenReferenciaMeta(ordenConcepto.value);
    });
  }

  if (ordenRefInput) {
    ordenRefInput.addEventListener('input', () => {
      setFieldError(ordenRefInput, ordenRefError, '');
    });
  }

  if (ordenForm) {
    ordenForm.addEventListener('submit', (event) => {
      event.preventDefault();
      submitOrdenPago();
    });
  }

  /* ------------------------------------------------------------------------ */
  /* Formulario 1: Consulta IUSI                                              */
  /* ------------------------------------------------------------------------ */
  const iusiForm = document.getElementById('form-iusi');
  const iusiFincaInput = document.getElementById('iusi-finca');
  const iusiFincaError = document.getElementById('iusi-finca-error');
  const iusiSubmitBtn = document.getElementById('btn-iusi-submit');
  const iusiResultado = document.getElementById('iusi-resultado');

  function renderIusiSuccess(data) {
    if (!iusiResultado) return;
    iusiResultado.setAttribute('aria-busy', 'false');

    const head = createEl('div', { className: 'sirec-card-head' }, [
      createEl('h4', {}, [`Finca ${data.finca} · Zona ${data.zona}`]),
      createEl('p', {}, [
        `${data.direccion || '—'} · Propietario: ${data.propietario || '—'}`,
      ]),
    ]);

    const saldoNum = Number(data.saldo_pendiente) || 0;
    const dl = createEl('dl', { className: 'sirec-dl' }, [
      createDlRow('Valor fiscal', formatearQuetzales(data.valor_fiscal)),
      createDlRow('Tasa por millar', `${data.tasa_por_millar} por millar`),
      createDlRow('IUSI anual', formatearQuetzales(data.iusi_anual)),
      createDlRow(
        'Saldo pendiente',
        formatearQuetzales(saldoNum),
        'sirec-saldo-box'
      ),
    ]);

    const tbody = createEl('tbody');
    const trimestres = Array.isArray(data.trimestres) ? data.trimestres : [];
    trimestres.forEach((trim) => {
      const estadoSpec = IUSI_ESTADO_LABELS[trim.estado] || {
        label: String(trim.estado || '—'),
        badgeClass: 'sirec-badge--pendiente',
        icon: 'clock',
      };
      tbody.appendChild(
        createEl('tr', {}, [
          createEl('td', {}, [String(trim.anio ?? '—')]),
          createEl('td', {}, [`T${trim.trimestre ?? '—'}`]),
          createEl('td', {}, [formatearQuetzales(trim.monto)]),
          createEl('td', {}, [createBadge(estadoSpec)]),
          createEl('td', {}, [trim.fecha_pago ? String(trim.fecha_pago) : '—']),
        ])
      );
    });

    const tableWrap = createEl('div', { className: 'sirec-table-wrap' }, [
      createEl('table', { className: 'sirec-table' }, [
        createEl('caption', {}, ['Detalle de trimestres']),
        createEl('thead', {}, [
          createEl('tr', {}, [
            createEl('th', { scope: 'col' }, ['Año']),
            createEl('th', { scope: 'col' }, ['Trimestre']),
            createEl('th', { scope: 'col' }, ['Monto']),
            createEl('th', { scope: 'col' }, ['Estado']),
            createEl('th', { scope: 'col' }, ['Fecha de pago']),
          ]),
        ]),
        tbody,
      ]),
    ]);

    const cardChildren = [head, dl, tableWrap];

    if (saldoNum > 0) {
      const generarBtn = createEl(
        'button',
        { type: 'button', className: 'btn sirec-btn-primary' },
        [createEl('span', {}, ['Generar orden de pago del saldo']), createSvgIcon('arrow', 16)]
      );
      generarBtn.addEventListener('click', () => {
        activateTab('orden', { scroll: false });
        if (ordenConcepto) {
          ordenConcepto.value = 'iusi';
          updateOrdenReferenciaMeta('iusi');
        }
        if (ordenRefInput) {
          ordenRefInput.value = data.finca;
        }
        submitOrdenPago();
      });

      cardChildren.push(createEl('div', { className: 'sirec-actions' }, [generarBtn]));
    } else {
      cardChildren.push(
        createEl('div', { className: 'sirec-state sirec-state--success', role: 'status' }, [
          createSvgIcon('check', 18),
          createEl('p', { className: 'sirec-state-msg' }, [
            'Tu inmueble está al día. No tienes saldo pendiente por pagar.',
          ]),
        ])
      );
    }

    iusiResultado.replaceChildren(createEl('div', { className: 'sirec-card' }, cardChildren));
  }

  let iusiInFlight = false;

  async function submitIusi() {
    if (!iusiForm || iusiInFlight) return;

    const finca = String(iusiFincaInput?.value || '').trim().toUpperCase();
    if (iusiFincaInput && finca) {
      iusiFincaInput.value = finca;
    }

    if (!FINCA_REGEX.test(finca)) {
      setFieldError(
        iusiFincaInput,
        iusiFincaError,
        'Ingresa un número de finca válido con formato F- seguido de 4 o 5 dígitos (por ejemplo, F-1024).'
      );
      if (iusiResultado) iusiResultado.replaceChildren(); // no dejar a la vista un resultado de una consulta anterior
      safeFocus(iusiFincaInput);
      return;
    }

    setFieldError(iusiFincaInput, iusiFincaError, '');
    iusiInFlight = true;
    if (iusiSubmitBtn) iusiSubmitBtn.disabled = true;
    renderLoadingState(iusiResultado, 'Consultando estado de cuenta IUSI en SIREC…');

    try {
      const res = await consultarIusi(finca);
      if (res.ok && res.data) {
        renderIusiSuccess(res.data);
      } else {
        renderErrorState(
          iusiResultado,
          'No se pudo consultar el estado de cuenta',
          res.mensaje || MSG_NO_DISPONIBLE
        );
      }
    } finally {
      iusiInFlight = false;
      if (iusiSubmitBtn) iusiSubmitBtn.disabled = false;
      if (iusiResultado) iusiResultado.setAttribute('aria-busy', 'false');
    }
  }

  if (iusiFincaInput) {
    iusiFincaInput.addEventListener('input', () => {
      setFieldError(iusiFincaInput, iusiFincaError, '');
    });
  }

  if (iusiForm) {
    iusiForm.addEventListener('submit', (event) => {
      event.preventDefault();
      submitIusi();
    });
  }

  /* ------------------------------------------------------------------------ */
  /* Formulario 4: Seguimiento LAIP (definido antes para enlazar desde LAIP)  */
  /* ------------------------------------------------------------------------ */
  const segForm = document.getElementById('form-seguimiento');
  const segFolioInput = document.getElementById('seguimiento-folio');
  const segFolioError = document.getElementById('seguimiento-folio-error');
  const segSubmitBtn = document.getElementById('btn-seguimiento-submit');
  const segResultado = document.getElementById('seguimiento-resultado');

  function formatDiasRestantes(estado, dias) {
    if (estado === 'resuelta') {
      return 'Solicitud resuelta (0 días restantes)';
    }
    const n = Number(dias);
    if (!Number.isFinite(n)) return '—';
    if (n === 1) return '1 día hábil restante';
    return `${n} días hábiles restantes`;
  }

  function renderSeguimientoSuccess(data) {
    if (!segResultado) return;
    segResultado.setAttribute('aria-busy', 'false');

    const estadoSpec = LAIP_ESTADO_LABELS[data.estado] || {
      label: String(data.estado || '—'),
      badgeClass: 'sirec-badge--en_tramite',
      icon: 'clock',
    };

    const card = createEl('div', { className: 'sirec-card' }, [
      createEl('div', { className: 'sirec-card-head' }, [
        createEl('h4', {}, [`Seguimiento de solicitud ${data.folio || ''}`]),
        createEl('p', {}, [
          'Información conforme al plazo legal de 10 días hábiles (Decreto 57-2008 LAIP).',
        ]),
      ]),
      createEl('dl', { className: 'sirec-dl' }, [
        createDlRow('Folio', data.folio || '—'),
        createDlRow('Fecha de registro', data.fecha || '—'),
        createDlRow('Fecha límite de respuesta', data.vence || '—'),
        createDlRow('Estado', createBadge(estadoSpec)),
        createDlRow(
          'Días restantes',
          formatDiasRestantes(data.estado, data.dias_restantes)
        ),
      ]),
    ]);

    segResultado.replaceChildren(card);
  }

  let segInFlight = false;

  async function submitSeguimiento() {
    if (!segForm || segInFlight) return;

    const folio = String(segFolioInput?.value || '').trim().toUpperCase();
    if (segFolioInput && folio) {
      segFolioInput.value = folio;
    }

    if (!folio || !ALFANUM_REF_REGEX.test(folio)) {
      setFieldError(
        segFolioInput,
        segFolioError,
        'Ingresa un número de folio válido (por ejemplo, LAIP-2026-0140).'
      );
      if (segResultado) segResultado.replaceChildren(); // no dejar a la vista un resultado de una consulta anterior
      safeFocus(segFolioInput);
      return;
    }

    setFieldError(segFolioInput, segFolioError, '');
    segInFlight = true;
    if (segSubmitBtn) segSubmitBtn.disabled = true;
    renderLoadingState(segResultado, 'Consultando estado del folio en SIREC…');

    try {
      const res = await consultarSeguimientoLaip(folio);
      if (res.ok && res.data) {
        renderSeguimientoSuccess(res.data);
      } else {
        renderErrorState(
          segResultado,
          'No se encontró el seguimiento solicitado',
          res.mensaje || MSG_NO_DISPONIBLE
        );
      }
    } finally {
      segInFlight = false;
      if (segSubmitBtn) segSubmitBtn.disabled = false;
      if (segResultado) segResultado.setAttribute('aria-busy', 'false');
    }
  }

  if (segFolioInput) {
    segFolioInput.addEventListener('input', () => {
      setFieldError(segFolioInput, segFolioError, '');
    });
  }

  if (segForm) {
    segForm.addEventListener('submit', (event) => {
      event.preventDefault();
      submitSeguimiento();
    });
  }

  /* ------------------------------------------------------------------------ */
  /* Formulario 3: Solicitud de información pública (LAIP)                    */
  /* ------------------------------------------------------------------------ */
  const laipForm = document.getElementById('form-laip');
  const laipNombreInput = document.getElementById('laip-nombre');
  const laipNombreError = document.getElementById('laip-nombre-error');
  const laipCorreoInput = document.getElementById('laip-correo');
  const laipCorreoError = document.getElementById('laip-correo-error');
  const laipDescInput = document.getElementById('laip-descripcion');
  const laipDescCount = document.getElementById('laip-descripcion-count');
  const laipDescError = document.getElementById('laip-descripcion-error');
  const laipSubmitBtn = document.getElementById('btn-laip-submit');
  const laipResultado = document.getElementById('laip-resultado');

  function updateLaipCounter() {
    if (!laipDescInput || !laipDescCount) return;
    const len = laipDescInput.value.length;
    laipDescCount.textContent = `${len} / 2000 caracteres`;
  }

  function renderLaipSuccess(data) {
    if (!laipResultado) return;
    laipResultado.setAttribute('aria-busy', 'false');

    const estadoSpec = LAIP_ESTADO_LABELS[data.estado] || LAIP_ESTADO_LABELS.recibida;

    const seguirBtn = createEl(
      'button',
      { type: 'button', className: 'btn sirec-btn-secondary' },
      [
        createEl('span', {}, ['Consultar seguimiento de este folio']),
        createSvgIcon('arrow', 16),
      ]
    );
    seguirBtn.addEventListener('click', () => {
      activateTab('seguimiento', { scroll: false });
      if (segFolioInput && data.folio) {
        segFolioInput.value = data.folio;
      }
      setFieldError(segFolioInput, segFolioError, '');
      submitSeguimiento();
    });

    const card = createEl('div', { className: 'sirec-card' }, [
      createEl('div', { className: 'sirec-state sirec-state--success', role: 'status' }, [
        createSvgIcon('check', 20),
        createEl('div', {}, [
          createEl('p', { className: 'sirec-state-title' }, [
            'Solicitud LAIP registrada correctamente',
          ]),
          createEl('p', { className: 'sirec-state-msg' }, [
            'Conserva tu número de folio para consultar el avance dentro del plazo de 10 días hábiles.',
          ]),
        ]),
      ]),
      createEl('dl', { className: 'sirec-dl' }, [
        createDlRow('Folio', data.folio || '—'),
        createDlRow('Fecha de registro', data.fecha || '—'),
        createDlRow('Fecha límite de respuesta', data.vence || '—'),
        createDlRow('Estado', createBadge(estadoSpec)),
      ]),
      createEl('div', { className: 'sirec-actions' }, [seguirBtn]),
    ]);

    laipResultado.replaceChildren(card);
  }

  let laipInFlight = false;

  async function submitLaip() {
    if (!laipForm || laipInFlight) return;

    const nombre = String(laipNombreInput?.value || '').trim();
    const correo = String(laipCorreoInput?.value || '').trim();
    const descripcion = String(laipDescInput?.value || '').trim();

    let firstInvalid = null;

    if (!nombre) {
      setFieldError(laipNombreInput, laipNombreError, 'Ingresa tu nombre completo.');
      firstInvalid = firstInvalid || laipNombreInput;
    } else {
      setFieldError(laipNombreInput, laipNombreError, '');
    }

    if (correo && !EMAIL_REGEX.test(correo)) {
      setFieldError(
        laipCorreoInput,
        laipCorreoError,
        'Ingresa un correo electrónico válido o deja el campo vacío.'
      );
      firstInvalid = firstInvalid || laipCorreoInput;
    } else {
      setFieldError(laipCorreoInput, laipCorreoError, '');
    }

    if (!descripcion) {
      setFieldError(
        laipDescInput,
        laipDescError,
        'Describe la información pública que deseas solicitar.'
      );
      firstInvalid = firstInvalid || laipDescInput;
    } else if (descripcion.length < 10) {
      setFieldError(
        laipDescInput,
        laipDescError,
        'La descripción debe tener al menos 10 caracteres para poder atender tu solicitud.'
      );
      firstInvalid = firstInvalid || laipDescInput;
    } else if (descripcion.length > 2000) {
      setFieldError(
        laipDescInput,
        laipDescError,
        'La descripción no puede superar los 2,000 caracteres.'
      );
      firstInvalid = firstInvalid || laipDescInput;
    } else {
      setFieldError(laipDescInput, laipDescError, '');
    }

    if (firstInvalid) {
      if (laipResultado) laipResultado.replaceChildren(); // no dejar a la vista un resultado de una consulta anterior
      safeFocus(firstInvalid);
      return;
    }

    laipInFlight = true;
    if (laipSubmitBtn) laipSubmitBtn.disabled = true;
    renderLoadingState(laipResultado, 'Registrando solicitud de información pública…');

    try {
      const res = await crearSolicitudLaip({ nombre, correo, descripcion });
      if (res.ok && res.data) {
        laipForm.reset();
        updateLaipCounter();
        renderLaipSuccess(res.data);
      } else {
        renderErrorState(
          laipResultado,
          'No se pudo registrar tu solicitud LAIP',
          res.mensaje || MSG_NO_DISPONIBLE
        );
      }
    } finally {
      laipInFlight = false;
      if (laipSubmitBtn) laipSubmitBtn.disabled = false;
      if (laipResultado) laipResultado.setAttribute('aria-busy', 'false');
    }
  }

  if (laipNombreInput) {
    laipNombreInput.addEventListener('input', () => {
      setFieldError(laipNombreInput, laipNombreError, '');
    });
  }
  if (laipCorreoInput) {
    laipCorreoInput.addEventListener('input', () => {
      setFieldError(laipCorreoInput, laipCorreoError, '');
    });
  }
  if (laipDescInput) {
    updateLaipCounter();
    laipDescInput.addEventListener('input', () => {
      updateLaipCounter();
      setFieldError(laipDescInput, laipDescError, '');
    });
  }

  if (laipForm) {
    laipForm.addEventListener('submit', (event) => {
      event.preventDefault();
      submitLaip();
    });
  }

  /* ------------------------------------------------------------------------ */
  /* Triggers externos ([data-sirec-open]) en todo el portal                  */
  /* ------------------------------------------------------------------------ */
  document.addEventListener('click', (event) => {
    const trigger =
      event.target instanceof Element ? event.target.closest('[data-sirec-open]') : null;
    if (!trigger) return;

    event.preventDefault();

    const tabKey = trigger.getAttribute('data-sirec-open') || 'iusi';
    const concepto = trigger.getAttribute('data-sirec-concepto');
    const notice = trigger.getAttribute('data-sirec-notice');

    setNotice(notice || '');
    activateTab(tabKey, { scroll: true, keepNotice: Boolean(notice) });

    if (tabKey === 'orden' && concepto && CONCEPTO_META[concepto] && ordenConcepto) {
      ordenConcepto.value = concepto;
      updateOrdenReferenciaMeta(concepto);
      safeFocus(ordenRefInput, true);
    } else {
      const targetPanel = panels.find((p) => !p.hidden);
      const firstControl = targetPanel?.querySelector(
        'input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
      );
      safeFocus(firstControl, true);
    }
  });

  const controller = {
    mounted: true,
    activateTab,
    checkEstado,
  };

  exposeDebugApi(controller);
  checkEstado();

  return controller;
}

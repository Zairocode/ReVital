import { initHeroScene } from './scene-3d.js';
import { initAnimations } from './animations.js';
import { initSirec } from './sirec.js';

const THEME_STORAGE_KEY = 'munisoke-theme-v2';
const VALID_THEMES = new Set(['light', 'dark']);

let heroScene = null;
let animationsController = null;
let searchHighlightTimer = null;
let lastHighlightedEl = null;

/**
 * Lee la preferencia guardada en localStorage de forma segura.
 * @returns {'light' | 'dark' | null}
 */
function readStoredTheme() {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    return VALID_THEMES.has(saved) ? saved : null;
  } catch {
    return null;
  }
}

/**
 * Guarda la preferencia de tema en localStorage de forma segura.
 * @param {'light' | 'dark'} theme
 */
function saveStoredTheme(theme) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignorar errores de almacenamiento en modos restringidos/privados
  }
}

/**
 * Devuelve el tema activo del portal ('light' o 'dark').
 * @returns {'light' | 'dark'}
 */
function getTheme() {
  const docTheme = document.documentElement.dataset.theme;
  if (VALID_THEMES.has(docTheme)) {
    return docTheme;
  }
  // Claro por defecto: un portal municipal se usa de dia; el oscuro es opcional.
  return readStoredTheme() || 'light';
}

/**
 * Actualiza los atributos ARIA, etiqueta e ícono del botón #theme-toggle.
 * @param {'light' | 'dark'} theme
 */
function updateThemeButton(theme) {
  const toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;

  const isDark = theme === 'dark';
  const nextActionLabel = isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';

  toggleBtn.setAttribute('aria-pressed', String(isDark));
  toggleBtn.setAttribute('aria-label', nextActionLabel);
  toggleBtn.setAttribute('title', nextActionLabel);

  const labelEl = toggleBtn.querySelector('.theme-label');
  if (labelEl) {
    labelEl.textContent = isDark ? 'Activar modo claro' : 'Activar modo oscuro';
  }

  const sunIcon = toggleBtn.querySelector('[data-theme-icon="sun"], [data-theme-icon="light"]');
  const moonIcon = toggleBtn.querySelector('[data-theme-icon="moon"], [data-theme-icon="dark"]');

  if (sunIcon && moonIcon) {
    sunIcon.toggleAttribute('hidden', !isDark);
    moonIcon.toggleAttribute('hidden', isDark);
  } else {
    const singleIcon = toggleBtn.querySelector('[data-theme-icon]');
    if (singleIcon && singleIcon.children.length === 0) {
      singleIcon.textContent = isDark ? '☀' : '☾';
    }
  }
}

/**
 * Aplica el tema al documento, sincroniza UI, escena 3D y emite evento global.
 * @param {'light' | 'dark'} theme
 * @param {{ persist?: boolean, dispatch?: boolean }} [options]
 * @returns {'light' | 'dark'}
 */
function setTheme(theme, { persist = true, dispatch = true } = {}) {
  const resolved = theme === 'dark' ? 'dark' : 'light';
  document.documentElement.dataset.theme = resolved;

  if (persist) {
    saveStoredTheme(resolved);
  }

  updateThemeButton(resolved);

  if (heroScene && typeof heroScene.setTheme === 'function') {
    try {
      heroScene.setTheme(resolved);
    } catch {
      // No interrumpir el cambio de tema si el renderer 3D reporta un problema
    }
  }

  if (dispatch) {
    window.dispatchEvent(
      new CustomEvent('munisoke:themechange', {
        detail: { theme: resolved },
      })
    );
  }

  return resolved;
}

/**
 * Inicializa la gestión de tema claro/oscuro y el botón #theme-toggle.
 */
function initThemeControl() {
  const stored = readStoredTheme();
  // Claro por defecto; solo cambia si el visitante lo elige con el boton.
  const initialTheme = stored || 'light';

  // Sincroniza estado inicial sin sobrescribir localStorage si el usuario no eligió manualmente
  setTheme(initialTheme, { persist: false, dispatch: false });

  const toggleBtn = document.getElementById('theme-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const nextTheme = getTheme() === 'dark' ? 'light' : 'dark';
      setTheme(nextTheme, { persist: true, dispatch: true });
    });
  }

}

/**
 * Inicializa el menú de navegación móvil accesible (#nav-toggle y #nav-links).
 */
function initMobileNav() {
  const navToggle = document.getElementById('nav-toggle');
  const navLinks = document.getElementById('nav-links');
  if (!navToggle || !navLinks) return;

  const isOpen = () => navLinks.classList.contains('is-open');

  const setMenuState = (open, { returnFocus = false } = {}) => {
    navLinks.classList.toggle('is-open', open);
    navToggle.setAttribute('aria-expanded', String(open));
    navToggle.setAttribute(
      'aria-label',
      open ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'
    );

    if (!open && returnFocus) {
      navToggle.focus();
    }
  };

  setMenuState(false);

  navToggle.addEventListener('click', () => {
    setMenuState(!isOpen());
  });

  navLinks.addEventListener('click', (event) => {
    const link = event.target instanceof Element ? event.target.closest('a[href]') : null;
    if (link && isOpen()) {
      setMenuState(false);
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen()) {
      setMenuState(false, { returnFocus: true });
    }
  });

  document.addEventListener('click', (event) => {
    if (!isOpen() || !(event.target instanceof Node)) return;
    if (!navLinks.contains(event.target) && !navToggle.contains(event.target)) {
      setMenuState(false);
    }
  });

  const syncDesktopState = () => {
    if (!isOpen()) return;
    const toggleStyle = window.getComputedStyle(navToggle);
    if (toggleStyle.display === 'none') {
      setMenuState(false);
    }
  };

  window.addEventListener('resize', syncDesktopState, { passive: true });
}

/**
 * Normaliza cadenas para búsqueda insensible a mayúsculas y tildes.
 * @param {string} value
 * @returns {string}
 */
function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Obtiene una etiqueta legible para anunciar un elemento encontrado.
 * @param {Element} el
 * @returns {string}
 */
function getElementLabel(el) {
  const heading = el.querySelector('h3, h4, b, strong');
  const raw = heading ? heading.textContent : el.textContent;
  return String(raw || '').replace(/\s+/g, ' ').trim();
}

/**
 * Enfoca programáticamente el elemento encontrado sin alterar el scroll en curso.
 * @param {HTMLElement} el
 */
function focusSearchTarget(el) {
  const nativelyFocusableSelector = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]';
  let focusTarget = el.matches(nativelyFocusableSelector)
    ? el
    : el.querySelector(nativelyFocusableSelector);

  let addedTempTabindex = false;
  if (!focusTarget) {
    focusTarget = el;
    focusTarget.setAttribute('tabindex', '-1');
    addedTempTabindex = true;
  }

  try {
    focusTarget.focus({ preventScroll: true });
  } catch {
    focusTarget.focus();
  }

  if (addedTempTabindex) {
    focusTarget.addEventListener(
      'blur',
      () => {
        focusTarget.removeAttribute('tabindex');
      },
      { once: true }
    );
  }
}

/**
 * Aplica un resalte temporal al resultado encontrado.
 * @param {HTMLElement} el
 */
function highlightSearchTarget(el) {
  if (lastHighlightedEl && lastHighlightedEl !== el) {
    lastHighlightedEl.classList.remove('is-search-match');
  }
  if (searchHighlightTimer !== null) {
    window.clearTimeout(searchHighlightTimer);
  }

  el.classList.add('is-search-match');
  lastHighlightedEl = el;

  searchHighlightTimer = window.setTimeout(() => {
    el.classList.remove('is-search-match');
    if (lastHighlightedEl === el) {
      lastHighlightedEl = null;
    }
    searchHighlightTimer = null;
  }, 2400);
}

/**
 * Inicializa el buscador demostrativo accesible (#site-search y #search-feedback).
 */
function initSiteSearch() {
  const form = document.getElementById('site-search');
  if (!form) return;

  const input = form.querySelector('input[type="search"], input');
  const feedback = document.getElementById('search-feedback');
  if (!input) return;

  const announce = (message) => {
    if (!feedback) return;
    if (feedback.hidden) {
      feedback.hidden = false;
    }
    feedback.textContent = message;
  };

  form.addEventListener('submit', (event) => {
    event.preventDefault();

    const rawQuery = input.value.trim();
    const normalizedQuery = normalizeText(rawQuery);

    if (!normalizedQuery) {
      announce('Escribe una palabra clave para buscar un trámite, noticia o documento.');
      input.focus();
      return;
    }

    const candidatesSet = new Set([
      ...document.querySelectorAll('[data-service], .tile'),
      ...document.querySelectorAll('.np'),
      ...document.querySelectorAll('.tlist a'),
    ]);

    const tokens = normalizedQuery.split(/\s+/).filter((token) => token.length >= 2);
    const matches = [];

    candidatesSet.forEach((el) => {
      if (!(el instanceof HTMLElement)) return;
      const haystack = normalizeText(
        `${el.dataset.service || ''} ${el.dataset.keywords || ''} ${el.textContent || ''}`
      );

      let score = 0;
      if (haystack.includes(normalizedQuery)) {
        score = 2;
      } else if (tokens.length > 1 && tokens.every((token) => haystack.includes(token))) {
        score = 1;
      }

      if (score > 0) {
        matches.push({ el, score, label: getElementLabel(el) });
      }
    });

    matches.sort((a, b) => b.score - a.score);

    if (matches.length === 0) {
      announce(
        `No se encontraron resultados para "${rawQuery}". Prueba con: agua, multas, ornato, IUSI, licencias o presupuesto.`
      );
      return;
    }

    const best = matches[0];
    if (matches.length === 1) {
      announce(`Resultado encontrado: "${best.label}". Navegando al elemento correspondiente.`);
    } else {
      announce(
        `${matches.length} resultados encontrados para "${rawQuery}". Mostrando "${best.label}".`
      );
    }

    const prefersReducedMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    best.el.scrollIntoView({
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
      block: 'center',
    });

    highlightSearchTarget(best.el);
    focusSearchTarget(best.el);
  });
}

/**
 * Inicializa progresivamente la escena 3D del hero sin comprometer el resto del portal.
 */
function initHero3DProgressive() {
  const canvas =
    document.getElementById('hero-canvas') ||
    document.getElementById('hero-3d-canvas') ||
    document.querySelector('[data-hero-canvas]') ||
    document.querySelector('.hero canvas');

  const container =
    canvas?.closest('.hero') ||
    document.getElementById('inicio') ||
    document.getElementById('hero-3d') ||
    document.getElementById('hero-scene') ||
    document.querySelector('[data-hero-3d]') ||
    canvas?.closest('.hero-stage, .hero-bg') ||
    canvas?.parentElement ||
    document.querySelector('.hero');

  if (!canvas || !container || typeof initHeroScene !== 'function') {
    return;
  }

  try {
    heroScene = initHeroScene({ canvas, container, getTheme }) || null;
  } catch (error) {
    heroScene = null;
    if (typeof console !== 'undefined' && typeof console.warn === 'function') {
      console.warn('[MuniSoke] Fallback 2D activo: no se pudo inicializar la escena 3D.', error);
    }
  }
}

/**
 * Punto de entrada principal del portal MuniSoke GT.
 */
function bootstrap() {
  initThemeControl();
  initMobileNav();
  initSiteSearch();

  // Exponer utilitario ligero de depuración / QA
  window.__munisoke = {
    getTheme,
    setTheme,
  };

  try {
    animationsController = initAnimations();
  } catch (error) {
    animationsController = null;
    if (typeof console !== 'undefined' && typeof console.warn === 'function') {
      console.warn('[MuniSoke] Animaciones omitidas por error en inicialización.', error);
    }
  }

  try {
    initSirec();
  } catch (error) {
    if (typeof console !== 'undefined' && typeof console.warn === 'function') {
      console.warn('[MuniSoke] Integración SIREC omitida por error en inicialización.', error);
    }
  }

  initHero3DProgressive();

  // Si hay cambio de tamaño o carga tardía, mantener ScrollTrigger sincronizado
  window.addEventListener(
    'munisoke:themechange',
    () => {
      animationsController?.refresh?.();
    },
    { passive: true }
  );
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap, { once: true });
} else {
  bootstrap();
}

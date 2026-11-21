import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

/**
 * Restaura los valores finales exactos de todos los contadores numéricos.
 */
function setFinalCounterValues() {
  const counters = document.querySelectorAll('[data-count-to]');
  counters.forEach((el) => {
    const target = Number(el.dataset.countTo);
    if (!Number.isFinite(target)) return;
    const suffix = el.dataset.countSuffix || '';
    el.textContent = `${target}${suffix}`;
  });
}

/**
 * Inicializa la coreografía institucional de animaciones GSAP + ScrollTrigger.
 * - Solo anima propiedades compositor-friendly: transform (x, y, scale, rotation) y opacity
 *   (además de textContent para contadores numéricos).
 * - Respeta estrictamente prefers-reduced-motion: reduce mediante gsap.matchMedia().
 * - Progresivo: todo el contenido es visible por defecto en CSS si JS falla o tarda.
 *
 * @returns {{ refresh: () => void, destroy: () => void }}
 */
export function initAnimations() {
  let destroyed = false;
  const mm = gsap.matchMedia();

  // 1. Coreografía completa cuando no hay preferencia de movimiento reducido
  mm.add('(prefers-reduced-motion: no-preference)', () => {
    const activeCounterTweens = [];

    // 1.1 Entrada inmediata del hero (t = 0, sin delay, opacity inicial 0.01 para proteger LCP)
    const heroItems = gsap.utils.toArray('[data-anim="hero-item"]');
    if (heroItems.length > 0) {
      gsap.from(heroItems, {
        y: 18,
        opacity: 0.01,
        duration: 0.55,
        stagger: 0.07,
        ease: 'power2.out',
        clearProps: 'transform,opacity',
      });
    }

    // 1.2 Revelado de encabezados de sección (cada uno con su ScrollTrigger)
    const sectionHeads = gsap.utils.toArray('[data-anim="section-head"]');
    sectionHeads.forEach((head) => {
      gsap.from(head, {
        y: 20,
        opacity: 0,
        duration: 0.55,
        ease: 'power2.out',
        clearProps: 'transform,opacity',
        scrollTrigger: {
          trigger: head,
          start: 'top 88%',
          once: true,
        },
      });
    });

    // 1.3 Tarjetas de servicios en cascada suave
    const serviceCards = gsap.utils.toArray('[data-anim="service-card"]');
    if (serviceCards.length > 0) {
      const servTrigger = document.querySelector('.serv') || serviceCards[0];
      gsap.from(serviceCards, {
        y: 22,
        opacity: 0,
        duration: 0.5,
        stagger: 0.055,
        ease: 'power2.out',
        clearProps: 'transform,opacity',
        scrollTrigger: {
          trigger: servTrigger,
          start: 'top 86%',
          once: true,
        },
      });
    }

    // 1.4 Cifras institucionales y contadores numéricos
    const statItems = gsap.utils.toArray('[data-anim="stat-item"]');
    const counterEls = gsap.utils.toArray('[data-count-to]');
    const cifrasTrigger =
      document.querySelector('#cifras') ||
      document.querySelector('.stats') ||
      statItems[0] ||
      counterEls[0];

    if (statItems.length > 0 && cifrasTrigger) {
      gsap.from(statItems, {
        y: 18,
        opacity: 0,
        duration: 0.5,
        stagger: 0.08,
        ease: 'power2.out',
        clearProps: 'transform,opacity',
        scrollTrigger: {
          trigger: cifrasTrigger,
          start: 'top 86%',
          once: true,
        },
      });
    }

    if (counterEls.length > 0 && cifrasTrigger) {
      ScrollTrigger.create({
        trigger: cifrasTrigger,
        start: 'top 86%',
        once: true,
        onEnter: () => {
          counterEls.forEach((el) => {
            const target = Number(el.dataset.countTo);
            if (!Number.isFinite(target)) return;
            const suffix = el.dataset.countSuffix || '';
            const proxy = { val: 0 };

            const tween = gsap.to(proxy, {
              val: target,
              duration: 1.1,
              ease: 'power2.out',
              onUpdate: () => {
                el.textContent = `${Math.round(proxy.val)}${suffix}`;
              },
              onComplete: () => {
                el.textContent = `${target}${suffix}`;
              },
            });

            activeCounterTweens.push(tween);
          });
        },
      });
    }

    // 1.5 Tarjetas de noticias en cascada
    const newsCards = gsap.utils.toArray('[data-anim="news-card"]');
    if (newsCards.length > 0) {
      const newsTrigger = document.querySelector('.news') || newsCards[0];
      gsap.from(newsCards, {
        y: 24,
        opacity: 0,
        duration: 0.55,
        stagger: 0.09,
        ease: 'power2.out',
        clearProps: 'transform,opacity',
        scrollTrigger: {
          trigger: newsTrigger,
          start: 'top 86%',
          once: true,
        },
      });
    }

    // 1.6 Ítems de transparencia LAIP
    const transpItems = gsap.utils.toArray('[data-anim="transp-item"]');
    if (transpItems.length > 0) {
      const transpTrigger = document.querySelector('.tlist') || transpItems[0];
      gsap.from(transpItems, {
        y: 14,
        opacity: 0,
        duration: 0.45,
        stagger: 0.045,
        ease: 'power2.out',
        clearProps: 'transform,opacity',
        scrollTrigger: {
          trigger: transpTrigger,
          start: 'top 88%',
          once: true,
        },
      });
    }

    return () => {
      activeCounterTweens.forEach((tween) => tween.kill());
      activeCounterTweens.length = 0;
      setFinalCounterValues();
    };
  });

  // 2. Microinteracciones sutiles solo en dispositivos con hover y sin reduced-motion
  mm.add('(prefers-reduced-motion: no-preference) and (hover: hover)', () => {
    const cleanups = [];

    // 2.1 Elevación limpia del ícono .ic en tarjetas de servicios
    const serviceCards = gsap.utils.toArray('[data-anim="service-card"]');
    serviceCards.forEach((card) => {
      const icon = card.querySelector('.ic');
      if (!icon) return;

      const onEnter = (event) => {
        if (event.pointerType === 'touch') return;
        gsap.to(icon, {
          y: -3,
          scale: 1.05,
          duration: 0.22,
          ease: 'power2.out',
          overwrite: 'auto',
        });
      };

      const onLeave = () => {
        gsap.to(icon, {
          y: 0,
          scale: 1,
          duration: 0.22,
          ease: 'power2.out',
          overwrite: 'auto',
          clearProps: 'transform',
        });
      };

      card.addEventListener('pointerenter', onEnter);
      card.addEventListener('pointerleave', onLeave);

      cleanups.push(() => {
        card.removeEventListener('pointerenter', onEnter);
        card.removeEventListener('pointerleave', onLeave);
        gsap.killTweensOf(icon);
        gsap.set(icon, { clearProps: 'transform' });
      });
    });

    // 2.2 Desplazamiento horizontal sutil en flecha de tarjetas de noticias
    const newsCards = gsap.utils.toArray('[data-anim="news-card"]');
    newsCards.forEach((card) => {
      const arrow = card.querySelector('.more svg, .more-icon');
      if (!arrow) return;

      const onEnter = (event) => {
        if (event.pointerType === 'touch') return;
        gsap.to(arrow, {
          x: 4,
          duration: 0.22,
          ease: 'power2.out',
          overwrite: 'auto',
        });
      };

      const onLeave = () => {
        gsap.to(arrow, {
          x: 0,
          duration: 0.22,
          ease: 'power2.out',
          overwrite: 'auto',
          clearProps: 'transform',
        });
      };

      card.addEventListener('pointerenter', onEnter);
      card.addEventListener('pointerleave', onLeave);

      cleanups.push(() => {
        card.removeEventListener('pointerenter', onEnter);
        card.removeEventListener('pointerleave', onLeave);
        gsap.killTweensOf(arrow);
        gsap.set(arrow, { clearProps: 'transform' });
      });
    });

    return () => {
      cleanups.forEach((fn) => fn());
    };
  });

  // 3. Garantía explícita para prefers-reduced-motion: reduce
  mm.add('(prefers-reduced-motion: reduce)', () => {
    const allAnimated = gsap.utils.toArray(
      [
        '[data-anim="hero-item"]',
        '[data-anim="section-head"]',
        '[data-anim="service-card"]',
        '[data-anim="stat-item"]',
        '[data-anim="news-card"]',
        '[data-anim="transp-item"]',
        '[data-anim="service-card"] .ic',
        '[data-anim="news-card"] .more svg',
        '[data-anim="news-card"] .more-icon',
      ].join(', ')
    );

    if (allAnimated.length > 0) {
      gsap.set(allAnimated, { clearProps: 'transform,opacity' });
    }

    setFinalCounterValues();
  });

  // Recalcular puntos de ScrollTrigger tras la carga de fuentes locales
  if (typeof document !== 'undefined' && document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => {
      if (!destroyed) {
        ScrollTrigger.refresh();
      }
    });
  }

  return {
    refresh() {
      if (!destroyed) {
        ScrollTrigger.refresh();
      }
    },
    destroy() {
      if (destroyed) return;
      destroyed = true;
      mm.revert();
    },
  };
}

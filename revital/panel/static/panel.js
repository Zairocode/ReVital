/* ReVital panel: animaciones (GSAP, local), pantalla de carga y recarga automatica.
   Todo es opcional: si este archivo no corre (navegador viejo), el panel funciona igual sin animaciones. */
(function () {
  "use strict";
  var g = window.gsap;
  var reducir = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------------------------------------------------------------- pantalla de carga
  function carga() {
    var c = document.getElementById("carga");
    if (!c) return;
    var vista = false;
    try { vista = sessionStorage.getItem("revital-carga") === "1"; sessionStorage.setItem("revital-carga", "1"); } catch (e) {}
    if (vista || !g || reducir) { c.parentNode.removeChild(c); return; }
    c.classList.add("js");
    var tl = g.timeline({ onComplete: function () { if (c.parentNode) c.parentNode.removeChild(c); } });
    tl.from("#carga .letra", { y: 60, opacity: 0, duration: 0.7, ease: "power3.out", stagger: { each: 0.07, from: "start" } })
      .from("#carga .lema", { opacity: 0, y: 10, duration: 0.5 }, "-=0.3")
      .to("#carga .barra i", { scaleX: 1, duration: 0.7, ease: "power2.inOut" }, "-=0.4")
      .to("#carga .letra", { y: -40, opacity: 0, duration: 0.45, ease: "power2.in", stagger: { each: 0.04, from: "end" } }, "+=0.15")
      .to(c, { opacity: 0, duration: 0.35 }, "-=0.2");
  }

  // ---------------------------------------------------------------- animaciones de entrada y graficas
  function contar(el) {
    var txt = el.firstChild && el.firstChild.nodeType === 3 ? el.firstChild : null;
    if (!txt) return;
    var fin = parseInt(txt.nodeValue, 10);
    if (isNaN(fin) || fin <= 0) return;
    var o = { v: 0 };
    g.to(o, { v: fin, duration: 1.1, ease: "power2.out", delay: 0.25,
      onUpdate: function () { txt.nodeValue = String(Math.round(o.v)); } });
  }

  function trazos() {
    var ls = document.querySelectorAll(".tz");
    for (var i = 0; i < ls.length; i++) {
      var p = ls[i], L = 0;
      try { L = p.getTotalLength(); } catch (e) { continue; }
      p.style.strokeDasharray = L;
      p.style.strokeDashoffset = L;
      g.to(p, { strokeDashoffset: 0, duration: 1.4, ease: "power2.out", delay: 0.35 });
    }
  }

  function animar() {
    if (!g || reducir) return;
    g.from(".hero .llaves, .hero h1, .buscar, .consent", { y: 24, opacity: 0, duration: 0.7, ease: "power3.out", stagger: 0.08 });
    g.from(".tb .w, .anim", { y: 26, opacity: 0, duration: 0.6, ease: "power3.out", stagger: 0.06, clearProps: "transform" });
    g.from(".sg", { scaleY: 0, transformOrigin: "50% 100%", duration: 0.4, ease: "back.out(2)", delay: 0.3, stagger: { each: 0.008 } });
    g.from(".tk", { opacity: 0, duration: 0.25, delay: 0.3, stagger: { each: 0.012 } });
    g.from(".ar", { opacity: 0, duration: 0.9, delay: 0.6 });
    g.from(".ag", { rotation: -120, svgOrigin: "110 98", duration: 1.2, ease: "elastic.out(1, 0.6)", delay: 0.4 });
    trazos();
    var nums = document.querySelectorAll(".tb .big, .ent .n");
    for (var i = 0; i < nums.length; i++) contar(nums[i]);
    g.to(".escaneo .pulso", { scale: 1.9, opacity: 0, duration: 1.4, repeat: -1, ease: "power1.out" });
  }

  // ---------------------------------------------------------------- recarga automatica
  function recarga() {
    var v = null, ocupado = false;
    function mirar() {
      if (ocupado) return;
      ocupado = true;
      var x = new XMLHttpRequest();
      x.open("GET", "/api/estado", true);
      x.onreadystatechange = function () {
        if (x.readyState !== 4) return;
        ocupado = false;
        if (x.status !== 200) return;
        var d;
        try { d = JSON.parse(x.responseText); } catch (e) { return; }
        var escribiendo = document.activeElement && /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
        if (v !== null && d.v !== v && !escribiendo) { location.reload(); return; }
        v = d.v;
      };
      x.send();
    }
    mirar();
    setInterval(mirar, 4000);
  }

  function listo() { carga(); animar(); recarga(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", listo); else listo();
})();

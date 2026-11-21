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
    var cc = g.utils.toArray("#carga .cc");
    var tl = g.timeline({ onComplete: function () { if (c.parentNode) c.parentNode.removeChild(c); } });
    // 0 - 1.3 s: los cubos caen y se arman
    tl.from(cc, { y: -260, opacity: 0, duration: 0.65, ease: "bounce.out", stagger: { each: 0.07, from: "random" } }, 0)
      .from("#carga .marca-c", { y: 30, opacity: 0, duration: 0.6, ease: "power3.out" }, 0.6);
    // 1.3 - 3.2 s: se mueven (saltan y se reacomodan)
    for (var k = 0; k < 3; k++) {
      tl.to(g.utils.shuffle(cc.slice()).slice(0, 5), { y: -26, duration: 0.28, ease: "power2.out", yoyo: true, repeat: 1, stagger: 0.06 }, 1.3 + k * 0.62);
    }
    // 3.2 - 4 s: se elevan, se desvanecen y entra el panel
    tl.to(cc, { y: -40, opacity: 0, duration: 0.45, ease: "power2.in", stagger: { each: 0.025, from: "end" } }, 3.25)
      .to("#carga .marca-c", { y: -20, opacity: 0, duration: 0.35, ease: "power2.in" }, 3.4)
      .to(c, { opacity: 0, duration: 0.3 }, 3.7);
  }

  function reloj() {
    var r = document.getElementById("reloj");
    if (!r) return;
    function dos(n) { return (n < 10 ? "0" : "") + n; }
    setInterval(function () { var d = new Date(); r.textContent = dos(d.getHours()) + ":" + dos(d.getMinutes()) + ":" + dos(d.getSeconds()); }, 1000);
  }

  // ---------------------------------------------------------------- animaciones de entrada y graficas
  function contar(el) {
    var txt = el.firstChild && el.firstChild.nodeType === 3 ? el.firstChild : null;
    if (!txt) return;
    var fin = parseInt(txt.nodeValue, 10);
    if (isNaN(fin) || fin <= 0) return;
    var o = { v: 0 };
    g.to(o, { v: fin, duration: 1.8, ease: "power2.out", delay: 0.4,
      onUpdate: function () { txt.nodeValue = String(Math.round(o.v)); } });
  }

  function trazos() {
    var ls = document.querySelectorAll(".tz");
    for (var i = 0; i < ls.length; i++) {
      var p = ls[i], L = 0;
      try { L = p.getTotalLength(); } catch (e) { continue; }
      p.style.strokeDasharray = L;
      p.style.strokeDashoffset = L;
      g.to(p, { strokeDashoffset: 0, duration: 2.3, ease: "power2.out", delay: 0.6 });
    }
  }

  function animar() {
    if (!g || reducir) return;
    g.from(".hero .llaves, .hero h1 span, .buscar, .consent", { y: 24, opacity: 0, duration: 0.7, ease: "power3.out", stagger: 0.07 });
    g.from(".visor .cubo", { y: -80, opacity: 0, duration: 0.6, ease: "back.out(1.6)", delay: 0.3, stagger: { each: 0.035, from: "start" } });
    g.to(".visor .c-coral", { y: -7, duration: 1.1, ease: "sine.inOut", yoyo: true, repeat: -1, delay: 1.4, stagger: { each: 0.15, from: "random" } });
    g.to(".visor .marca", { rotation: 90, duration: 3, ease: "none", repeat: -1, transformOrigin: "50% 50%" });
    g.from(".tb .w, .anim", { y: 26, opacity: 0, duration: 1.0, ease: "power3.out", stagger: 0.11, clearProps: "transform" });
    g.from(".sg", { scaleY: 0, transformOrigin: "50% 100%", duration: 0.7, ease: "back.out(2)", delay: 0.5, stagger: { each: 0.014 } });
    g.from(".tk", { opacity: 0, duration: 0.4, delay: 0.5, stagger: { each: 0.02 } });
    g.from(".ar", { opacity: 0, duration: 1.5, delay: 1.0 });
    g.from(".ag", { rotation: -120, svgOrigin: "110 98", duration: 2.0, ease: "elastic.out(1, 0.6)", delay: 0.7 });
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

  function listo() { carga(); reloj(); animar(); recarga(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", listo); else listo();
})();

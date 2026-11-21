"""Cubos isometricos en SVG (sin librerias): pantalla de carga y visor de componentes del Inicio.

En el visor cada cubo es un componente del sistema analizado: coral = vulnerable, verde = correcto, gris = relleno.
GSAP (static/panel.js) los anima; sin JavaScript se ven quietos.
"""
import math

COLORES = {  # (cara superior, izquierda, derecha)
    "gris": ("#3a3a3f", "#26262a", "#1b1b1e"),
    "coral": ("#ff8a6e", "#ff5a3c", "#c4432b"),
    "verde": ("#6fe0b4", "#34c38f", "#24875f"),
    "crema": ("#fbf6df", "#d8d3bd", "#ada895"),
    "blanco": ("#ffffff", "#e6e6ea", "#b4b4bc"),
}


def _f(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


def cubo(gx, gy, gz, s, ox, oy, color="gris", clase="cubo"):
    """Un cubo en la celda (gx, gy) a la altura gz. s = lado en pixeles; (ox, oy) = origen en pantalla."""
    a, b = s * math.cos(math.pi / 6), s * 0.5
    x, y = ox + (gx - gy) * a, oy + (gx + gy) * b - gz * s
    sup, izq, der = COLORES.get(color, COLORES["gris"])
    pts = lambda *p: " ".join("%s,%s" % (_f(px), _f(py)) for px, py in p)
    return ('<g class="%s c-%s">'
            '<polygon points="%s" fill="%s"/><polygon points="%s" fill="%s"/><polygon points="%s" fill="%s"/>'
            '<polyline points="%s" fill="none" stroke="#0e0e0f" stroke-width=".8" stroke-opacity=".55"/></g>'
            % (clase, color,
               pts((x, y), (x + a, y + b), (x, y + 2 * b), (x - a, y + b)), sup,
               pts((x - a, y + b), (x, y + 2 * b), (x, y + 2 * b + s), (x - a, y + b + s)), izq,
               pts((x, y + 2 * b), (x + a, y + b), (x + a, y + b + s), (x, y + 2 * b + s)), der,
               pts((x - a, y + b), (x, y + 2 * b), (x + a, y + b))))


def _ordenar(celdas):
    """Pintar de atras hacia adelante y de abajo hacia arriba para que se tapen bien."""
    return sorted(celdas, key=lambda c: (c[0] + c[1], c[2], c[0]))


def _pila(n):
    """Piramide escalonada: base 3x3 (hasta 14 cubos) o 4x4 (hasta 30). Orden: de abajo hacia la cima."""
    lados = (3, 2, 1) if n <= 14 else (4, 3, 2, 1)
    out = []
    for z, lado in enumerate(lados):
        off = (lados[0] - lado) / 2.0
        for gx in range(lado):
            for gy in range(lado):
                out.append((gx + off, gy + off, z))
    return out


def visor(filas, ancho=420, alto=360, s=34):
    """Piramide de cubos: uno por componente (filas = tablero.resumen(h)['filas']).
    Relleno gris en la base, componentes correctos (verde) en medio y vulnerables (coral) en la cima."""
    vul = sum(1 for f in filas if f["vulnerable"])
    ok = len(filas) - vul
    posiciones = _pila(len(filas))
    n = len(posiciones)
    vul, ok = min(vul, n), min(ok, n - min(vul, n))
    colores = ["gris"] * (n - vul - ok) + ["verde"] * ok + ["coral"] * vul  # mismo orden que posiciones: base -> cima
    celdas = sorted(zip(posiciones, colores), key=lambda c: (c[0][0] + c[0][1], c[0][2], c[0][0]))
    base = 3 if n <= 14 else 4
    ox, oy = ancho / 2.0 - (base - 1) * 0 , alto / 2.0 - (base - 1) * s * .5 + s * .3
    cubos = "".join(cubo(p[0], p[1], p[2], s, ox, oy, col) for p, col in celdas)
    marcas = "".join('<g class="marca" transform="translate(%d %d)"><path d="M-6 0H6M0-6V6" stroke="#ff5a3c" stroke-width="1.400"/></g>' % xy
                     for xy in ((60, 70), (ancho - 70, 50), (ancho - 40, alto - 150), (70, alto - 60), (ancho - 110, alto - 40)))
    guias = ('<line x1="%d" y1="40" x2="%d" y2="%d" stroke="#3a3a3f" stroke-dasharray="3 5"/>'
             '<line x1="40" y1="%d" x2="%d" y2="%d" stroke="#3a3a3f" stroke-dasharray="3 5"/>'
             % (ancho * .25, ancho * .25, alto - 40, alto * .3, ancho * .45, alto * .3))
    return '<svg class="visor" width="%d" height="%d" viewBox="0 0 %d %d">%s%s%s</svg>' % (ancho, alto, ancho, alto, guias, marcas, cubos)


def carga(ancho=360, alto=300, s=34):
    """Cubos de la pantalla de carga: rejilla 3x3 de cubos blancos (GSAP los mueve 4 segundos)."""
    celdas = []
    for gx in range(3):
        for gy in range(3):
            celdas.append((gx, gy, 0))
    celdas += [(0, 0, 1), (1, 0, 1), (0, 1, 1), (0, 0, 2)]
    ox, oy = ancho / 2.0, alto / 2.0 - 2.2 * s
    return ('<svg class="cubos-c" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            % (ancho, alto, ancho, alto, "".join(cubo(c[0], c[1], c[2], s, ox, oy, "blanco", "cubo cc")
                                                 for c in _ordenar(celdas))))

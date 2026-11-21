/**
 * MuniSoke GT — Escena 3D procedural para el hero (Three.js, 100% offline).
 * Maqueta arquitectónica editorial del altiplano guatemalteco:
 *   - Cadena de 3 volcanes low-poly con relieve determinístico y niebla atmosférica.
 *   - Valle y pequeña ciudad municipal de Soke (Palacio Municipal con torre de reloj,
 *     Parque Central con glorieta, ~22 edificios cívicos/residenciales, ventanas cálidas
 *     y arboledas de pinos y copas lima).
 *   - Domo de cielo degradado, sol dorado con halo sutil y nubes low-poly minimalistas.
 *   - Iluminación reactiva al tema claro/oscuro, parallax suave, pausa automática
 *     fuera de vista/pestaña oculta y respeto estricto a prefers-reduced-motion.
 */

import {
  ACESFilmicToneMapping,
  AdditiveBlending,
  AmbientLight,
  BackSide,
  BoxGeometry,
  BufferAttribute,
  Color,
  ConeGeometry,
  CylinderGeometry,
  DirectionalLight,
  FogExp2,
  Group,
  HemisphereLight,
  IcosahedronGeometry,
  MathUtils,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  PointLight,
  RingGeometry,
  SRGBColorSpace,
  Scene,
  SphereGeometry,
  WebGLRenderer,
} from 'three';

/* -------------------------------------------------------------------------- */
/*  Utilidades determinísticas y relieve del terreno                          */
/* -------------------------------------------------------------------------- */

/**
 * Generador pseudoaleatorio determinístico (Mulberry32) para que la maqueta
 * sea 100% reproducible y cuidadosamente compuesta sin aleatoriedad caótica.
 */
function createRng(seed) {
  let state = seed >>> 0;
  return function next() {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Altura determinística del valle de Soke.
 * Crea una meseta suave y nivelada para la ciudad municipal (x: 0.5..11.2, z: -9.5..-3.5)
 * y ondulaciones suaves hacia el horizonte y los flancos.
 */
function getTerrainHeight(x, z) {
  const waveA = Math.sin(x * 0.14 + 0.5) * Math.cos(z * 0.16 - 0.3) * 0.42;
  const waveB = Math.sin(x * 0.29 - z * 0.21 + 1.1) * 0.16;
  const backRise = Math.max(0, (-z - 10.5) * 0.11);
  const leftSlope = Math.max(0, (-x - 3.0) * 0.055);
  const rawHeight = waveA + waveB + backRise + leftSlope;

  // Meseta cívica de la ciudad de Soke (suave nivelación en la zona urbana)
  const dx = (x - 5.9) / 6.2;
  const dz = (z + 6.4) / 3.4;
  const radialSq = dx * dx + dz * dz;
  const plateauMask = Math.exp(-radialSq * 1.45);
  const plateauHeight = 0.28;

  return MathUtils.lerp(rawHeight, plateauHeight, plateauMask);
}

/* -------------------------------------------------------------------------- */
/*  Paletas institucionales para modo claro y modo oscuro                     */
/* -------------------------------------------------------------------------- */

const THEME_PRESETS = {
  light: {
    skyZenith: new Color('#3f86d6'),
    skyMidLeft: new Color('#6aa9e8'),
    skyMidRight: new Color('#7db7ef'),
    skyHorizonLeft: new Color('#bcdcf7'),
    skyHorizonRight: new Color('#d9ecfb'),
    skySunBlush: new Color('#fde4a8'),
    fogColor: new Color('#c4ddf3'),
    fogDensity: 0.012,
    sunCore: new Color('#f6b11f'),
    sunInnerHalo: new Color('#ffd470'),
    sunOuterHalo: new Color('#f6b11f'),
    sunInnerOpacity: 0.38,
    sunOuterOpacity: 0.18,
    keyColor: new Color('#fff1cf'),
    keyIntensity: 2.6,
    hemiSky: new Color('#d4e8ff'),
    hemiGround: new Color('#3d7a45'),
    hemiIntensity: 1.15,
    rimColor: new Color('#ffffff'),
    rimIntensity: 0.35,
    ambientColor: new Color('#ffffff'),
    ambientIntensity: 0.4,
    plazaLightColor: new Color('#ffbf4a'),
    plazaLightIntensity: 0.4,
    windowPrimaryEmissive: 0.42,
    windowSecondaryEmissive: 0.3,
    clockEmissive: 0.65,
    cloudColor: new Color('#ffffff'),
    cloudEmissive: new Color('#e8f1fb'),
    cloudEmissiveIntensity: 0.3,
    cloudOpacity: 0.55,
    exposure: 1.1,
  },
  dark: {
    skyZenith: new Color('#132a5c'),
    skyMidLeft: new Color('#1d3c7a'),
    skyMidRight: new Color('#2a4f93'),
    skyHorizonLeft: new Color('#3a5a9a'),
    skyHorizonRight: new Color('#7a7fb3'),
    skySunBlush: new Color('#d39a78'),
    fogColor: new Color('#2a4378'),
    fogDensity: 0.02,
    sunCore: new Color('#ffd67a'),
    sunInnerHalo: new Color('#f6b11f'),
    sunOuterHalo: new Color('#7ba3eb'),
    sunInnerOpacity: 0.2,
    sunOuterOpacity: 0.09,
    keyColor: new Color('#7ca4e8'),
    keyIntensity: 1.35,
    hemiSky: new Color('#5a7fc4'),
    hemiGround: new Color('#0f2a1f'),
    hemiIntensity: 0.75,
    rimColor: new Color('#f6b11f'),
    rimIntensity: 0.36,
    ambientColor: new Color('#6582bd'),
    ambientIntensity: 0.3,
    plazaLightColor: new Color('#ffb636'),
    plazaLightIntensity: 3.9,
    windowPrimaryEmissive: 2.2,
    windowSecondaryEmissive: 1.55,
    clockEmissive: 2.25,
    cloudColor: new Color('#8095c4'),
    cloudEmissive: new Color('#2c3f6b'),
    cloudEmissiveIntensity: 0.16,
    cloudOpacity: 0.22,
    exposure: 1.08,
  },
};

function normalizeTheme(theme) {
  return theme === 'dark' ? 'dark' : 'light';
}

/* -------------------------------------------------------------------------- */
/*  Constructores de geometría procedural                                     */
/* -------------------------------------------------------------------------- */

/**
 * Domo de cielo con degradado esférico por vértice.
 * Mantiene el tercio izquierdo en azul cívico sereno para máxima legibilidad del texto
 * y aporta una suave luminosidad dorada hacia el sol a la derecha.
 */
function buildSkyDome() {
  const geometry = new SphereGeometry(64, 28, 18);
  const posAttr = geometry.attributes.position;
  const count = posAttr.count;
  const colors = new Float32Array(count * 3);
  const dirs = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    const x = posAttr.getX(i);
    const y = posAttr.getY(i);
    const z = posAttr.getZ(i);
    const len = Math.hypot(x, y, z) || 1;
    dirs[i * 3] = x / len;
    dirs[i * 3 + 1] = y / len;
    dirs[i * 3 + 2] = z / len;
  }

  geometry.setAttribute('color', new BufferAttribute(colors, 3));

  const material = new MeshBasicMaterial({
    vertexColors: true,
    side: BackSide,
    depthWrite: false,
    fog: false,
  });

  const mesh = new Mesh(geometry, material);
  mesh.renderOrder = -10;

  // Dirección aproximada del sol en el cielo derecho
  const sunDirX = 0.47;
  const sunDirY = 0.29;
  const sunDirZ = -0.83;

  // Colores temporales reutilizables (cero asignaciones por frame)
  const cZenith = new Color();
  const cMidLeft = new Color();
  const cMidRight = new Color();
  const cHorLeft = new Color();
  const cHorRight = new Color();
  const cBlush = new Color();
  const cHorMix = new Color();
  const cMidMix = new Color();
  const cOut = new Color();

  function updateColors(blend) {
    const L = THEME_PRESETS.light;
    const D = THEME_PRESETS.dark;

    cZenith.copy(L.skyZenith).lerp(D.skyZenith, blend);
    cMidLeft.copy(L.skyMidLeft).lerp(D.skyMidLeft, blend);
    cMidRight.copy(L.skyMidRight).lerp(D.skyMidRight, blend);
    cHorLeft.copy(L.skyHorizonLeft).lerp(D.skyHorizonLeft, blend);
    cHorRight.copy(L.skyHorizonRight).lerp(D.skyHorizonRight, blend);
    cBlush.copy(L.skySunBlush).lerp(D.skySunBlush, blend);

    const colorAttr = geometry.attributes.color;
    const arr = colorAttr.array;

    for (let i = 0; i < count; i++) {
      const dx = dirs[i * 3];
      const dy = dirs[i * 3 + 1];
      const dz = dirs[i * 3 + 2];

      // Factor izquierda (-1) -> derecha (+1) suavizado
      const sideT = MathUtils.smoothstep(dx, -0.55, 0.65);
      // Elevación sobre el horizonte
      const elev = MathUtils.clamp((dy + 0.08) / 0.92, 0, 1);

      cHorMix.copy(cHorLeft).lerp(cHorRight, sideT);
      cMidMix.copy(cMidLeft).lerp(cMidRight, sideT);

      if (elev < 0.38) {
        const t = elev / 0.38;
        cOut.copy(cHorMix).lerp(cMidMix, MathUtils.smoothstep(t, 0, 1));
      } else {
        const t = (elev - 0.38) / 0.62;
        cOut.copy(cMidMix).lerp(cZenith, MathUtils.smoothstep(t, 0, 1));
      }

      // Rubor solar sutil alrededor del sol en el horizonte derecho
      const sunDot = Math.max(0, dx * sunDirX + dy * sunDirY + dz * sunDirZ);
      const blushStrength = Math.pow(sunDot, 4.5) * 0.42;
      cOut.lerp(cBlush, blushStrength);

      arr[i * 3] = cOut.r;
      arr[i * 3 + 1] = cOut.g;
      arr[i * 3 + 2] = cOut.b;
    }

    colorAttr.needsUpdate = true;
  }

  return { mesh, updateColors };
}

/**
 * Terreno estilizado low-poly del valle municipal de Soke.
 */
function buildValleyTerrain() {
  const geometry = new PlaneGeometry(82, 48, 56, 32);
  geometry.rotateX(-Math.PI / 2);

  const pos = geometry.attributes.position;
  const colors = new Float32Array(pos.count * 3);

  const cDeepValley = new Color('#0b311d');
  const cMidGreen = new Color('#134c2c');
  const cCivicMeadow = new Color('#1a6339');
  const cFoothill = new Color('#0e3d24');
  const cTemp = new Color();

  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i) - 9.0;
    pos.setZ(i, z);

    const y = getTerrainHeight(x, z);
    pos.setY(i, y);

    // Variación cromática orgánica según cercanía al valle urbano y elevación
    const townDist = Math.hypot((x - 5.9) * 0.72, z + 6.4);
    const meadowMix = MathUtils.clamp(1 - townDist / 10.5, 0, 1);
    const elevMix = MathUtils.clamp((y + 0.4) / 2.2, 0, 1);

    cTemp.copy(cDeepValley).lerp(cMidGreen, elevMix);
    cTemp.lerp(cCivicMeadow, meadowMix * 0.68);
    if (z < -13) {
      cTemp.lerp(cFoothill, MathUtils.clamp((-z - 13) / 10, 0, 0.7));
    }

    // Pequeña variación determinística de faceta para riqueza táctil
    const facetTint = Math.sin(x * 0.85 + z * 0.63) * 0.025;
    colors[i * 3] = MathUtils.clamp(cTemp.r + facetTint, 0, 1);
    colors[i * 3 + 1] = MathUtils.clamp(cTemp.g + facetTint * 1.15, 0, 1);
    colors[i * 3 + 2] = MathUtils.clamp(cTemp.b + facetTint * 0.8, 0, 1);
  }

  geometry.setAttribute('color', new BufferAttribute(colors, 3));
  geometry.computeVertexNormals();

  const material = new MeshStandardMaterial({
    vertexColors: true,
    flatShading: true,
    roughness: 0.92,
    metalness: 0.02,
  });

  const mesh = new Mesh(geometry, material);
  return mesh;
}

/**
 * Volcán guatemalteco low-poly con estrías naturales y cráter sutilmente truncado.
 * Desplazamiento 100% determinístico mediante armónicos trigonométricos con semilla fija.
 */
function buildVolcano({
  radius,
  height,
  topRadius,
  radialSegments,
  heightSegments,
  seed,
  baseHex,
  midHex,
  ridgeHex,
  summitHex,
}) {
  const geometry = new CylinderGeometry(
    topRadius,
    radius,
    height,
    radialSegments,
    heightSegments,
    false
  );

  // Alinear la base del volcán en y = 0
  geometry.translate(0, height * 0.5, 0);

  const pos = geometry.attributes.position;
  const colors = new Float32Array(pos.count * 3);

  const cBase = new Color(baseHex);
  const cMid = new Color(midHex);
  const cRidge = new Color(ridgeHex);
  const cSummit = new Color(summitHex);
  const cOut = new Color();

  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i);
    let y = pos.getY(i);
    let z = pos.getZ(i);

    const r = Math.hypot(x, z);
    const yNorm = MathUtils.clamp(y / height, 0, 1);
    const angle = Math.atan2(z, x);

    // Cráter sutil en el centro de la tapa superior
    if (yNorm > 0.985 && r < topRadius * 0.55) {
      y -= topRadius * 0.34;
    } else if (r > 0.001) {
      // Perfil cóncavo natural de estratovolcán (base más tendida, cima elegante)
      const concaveFlare = 1 + Math.pow(1 - yNorm, 2.1) * 0.28;

      // Estrías y aristas volcánicas determinísticas
      const ridgeA = Math.sin(angle * 3 + seed * 1.3 + yNorm * 1.4) * 0.11;
      const ridgeB = Math.cos(angle * 5 - seed * 2.1 - yNorm * 2.2) * 0.075;
      const ridgeC = Math.sin(angle * 8 + seed * 0.7 + yNorm * 3.8) * 0.04;

      // Atenuación suave hacia el borde del cráter para mantener silueta limpia
      const ridgeEnvelope = Math.sin(MathUtils.clamp(yNorm, 0.04, 0.96) * Math.PI);
      const radialScale = concaveFlare * (1 + (ridgeA + ridgeB + ridgeC) * (0.35 + ridgeEnvelope * 0.75));

      x *= radialScale;
      z *= radialScale;

      // Ligera ondulación orgánica en el borde del cráter
      if (yNorm > 0.92) {
        y += Math.sin(angle * 2 + seed) * topRadius * 0.16 * ((yNorm - 0.92) / 0.08);
      } else if (yNorm > 0.05) {
        y += (ridgeB * 0.35 + ridgeC * 0.25) * height * 0.14;
      }
    }

    pos.setXYZ(i, x, y, z);

    // Coloración por altitud y facetas (bosque profundo -> pino altiplano -> roca/cumbre)
    const ridgeHighlight = Math.sin(angle * 4 + seed) * 0.5 + 0.5;
    if (yNorm < 0.52) {
      cOut.copy(cBase).lerp(cMid, MathUtils.smoothstep(yNorm, 0.04, 0.52));
    } else if (yNorm < 0.84) {
      cOut.copy(cMid).lerp(cRidge, MathUtils.smoothstep(yNorm, 0.52, 0.84));
    } else {
      cOut.copy(cRidge).lerp(cSummit, MathUtils.smoothstep(yNorm, 0.84, 1.0));
    }

    cOut.offsetHSL(0, 0, (ridgeHighlight - 0.5) * 0.032);

    colors[i * 3] = cOut.r;
    colors[i * 3 + 1] = cOut.g;
    colors[i * 3 + 2] = cOut.b;
  }

  geometry.setAttribute('color', new BufferAttribute(colors, 3));
  geometry.computeVertexNormals();

  const material = new MeshStandardMaterial({
    vertexColors: true,
    flatShading: true,
    roughness: 0.9,
    metalness: 0.03,
  });

  return new Mesh(geometry, material);
}

/**
 * Colinas secundarias low-poly entre el valle y la cadena volcánica para
 * reforzar la profundidad atmosférica por planos.
 */
function buildFoothillRidge(width, height, depth, seed, colorHex) {
  const geometry = new ConeGeometry(width * 0.5, height, 11, 3);
  geometry.translate(0, height * 0.5, 0);
  geometry.scale(1.35, 1, depth / width);

  const pos = geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const yNorm = y / height;
    const angle = Math.atan2(z, x);
    const mod = 1 + Math.sin(angle * 3 + seed) * 0.14 + Math.cos(angle * 5 - seed) * 0.08;
    pos.setXYZ(i, x * mod, y * (1 + Math.sin(angle * 2 + seed) * 0.06 * yNorm), z * mod);
  }
  geometry.computeVertexNormals();

  const material = new MeshStandardMaterial({
    color: colorHex,
    flatShading: true,
    roughness: 0.93,
    metalness: 0.02,
  });

  return new Mesh(geometry, material);
}

/**
 * Construye la pequeña ciudad municipal de Soke:
 *   - Parque Central con glorieta/kiosco y áreas verdes lima/bosque.
 *   - Palacio Municipal con pórtico, techo terracota y torre del reloj iluminada.
 *   - ~22 edificios cívicos y residenciales de alturas escalonadas con ventanas cálidas.
 *   - Arboledas low-poly de pinos y copas redondeadas.
 */
function buildMunicipalTown() {
  const townGroup = new Group();
  const rng = createRng(20260507);

  // Materiales compartidos de arquitectura editorial guatemalteca
  const materials = {
    plazaStone: new MeshStandardMaterial({ color: '#c4d0e0', flatShading: true, roughness: 0.88, metalness: 0.04 }),
    plazaTrim: new MeshStandardMaterial({ color: '#8ea3bf', flatShading: true, roughness: 0.85, metalness: 0.05 }),
    lawn: new MeshStandardMaterial({ color: '#14874d', flatShading: true, roughness: 0.9, metalness: 0.02 }),
    palaceWall: new MeshStandardMaterial({ color: '#e5ebf4', flatShading: true, roughness: 0.78, metalness: 0.04 }),
    palaceBase: new MeshStandardMaterial({ color: '#8398b5', flatShading: true, roughness: 0.85, metalness: 0.05 }),
    terracotta: new MeshStandardMaterial({ color: '#b95f42', flatShading: true, roughness: 0.84, metalness: 0.03 }),
    terracottaDark: new MeshStandardMaterial({ color: '#9c4c34', flatShading: true, roughness: 0.86, metalness: 0.03 }),
    slateRoof: new MeshStandardMaterial({ color: '#395278', flatShading: true, roughness: 0.8, metalness: 0.08 }),
    goldTrim: new MeshStandardMaterial({ color: '#f6b11f', flatShading: true, roughness: 0.35, metalness: 0.45 }),
    trunk: new MeshStandardMaterial({ color: '#5b4231', flatShading: true, roughness: 0.94, metalness: 0.0 }),
    pineDark: new MeshStandardMaterial({ color: '#106e3f', flatShading: true, roughness: 0.88, metalness: 0.02 }),
    pineMid: new MeshStandardMaterial({ color: '#158a4f', flatShading: true, roughness: 0.86, metalness: 0.02 }),
    canopyLime: new MeshStandardMaterial({ color: '#9bd60d', flatShading: true, roughness: 0.82, metalness: 0.02 }),
  };

  // Paleta de fachadas para los edificios del centro urbano
  const facadeMaterials = [
    new MeshStandardMaterial({ color: '#dde4ef', flatShading: true, roughness: 0.82, metalness: 0.03 }),
    new MeshStandardMaterial({ color: '#e8e0d2', flatShading: true, roughness: 0.84, metalness: 0.03 }),
    new MeshStandardMaterial({ color: '#526d94', flatShading: true, roughness: 0.78, metalness: 0.06 }),
    new MeshStandardMaterial({ color: '#314d7a', flatShading: true, roughness: 0.78, metalness: 0.08 }),
    new MeshStandardMaterial({ color: '#d7c4a5', flatShading: true, roughness: 0.85, metalness: 0.03 }),
    new MeshStandardMaterial({ color: '#c4d3cc', flatShading: true, roughness: 0.84, metalness: 0.03 }),
  ];

  // Ventanas cálidas reactivas al tema (dos tonos para riqueza visual)
  const windowPrimaryMat = new MeshStandardMaterial({
    color: '#ffe08a',
    emissive: new Color('#f6b11f'),
    emissiveIntensity: 0.42,
    roughness: 0.25,
    metalness: 0.05,
  });

  const windowSecondaryMat = new MeshStandardMaterial({
    color: '#fff0bd',
    emissive: new Color('#ffd269'),
    emissiveIntensity: 0.3,
    roughness: 0.28,
    metalness: 0.05,
  });

  const clockFaceMat = new MeshStandardMaterial({
    color: '#fff6d6',
    emissive: new Color('#f6b11f'),
    emissiveIntensity: 0.65,
    roughness: 0.2,
    metalness: 0.1,
  });

  // Geometrías reutilizables para bajo consumo de memoria
  const unitBox = new BoxGeometry(1, 1, 1);
  const windowGeo = new BoxGeometry(0.11, 0.14, 0.025);
  const pineLowerGeo = new ConeGeometry(0.28, 0.66, 6);
  const pineUpperGeo = new ConeGeometry(0.21, 0.56, 6);
  const trunkGeo = new CylinderGeometry(0.035, 0.05, 0.28, 5);
  const roundTreeGeo = new IcosahedronGeometry(0.24, 0);

  /* --- 1. Parque Central de Soke --- */
  const plazaX = 4.1;
  const plazaZ = -5.7;
  const plazaY = getTerrainHeight(plazaX, plazaZ);

  const plazaGroup = new Group();
  plazaGroup.position.set(plazaX, plazaY, plazaZ);

  const plazaBase = new Mesh(unitBox, materials.plazaTrim);
  plazaBase.scale.set(2.85, 0.14, 2.25);
  plazaBase.position.y = 0.05;
  plazaGroup.add(plazaBase);

  const plazaDeck = new Mesh(unitBox, materials.plazaStone);
  plazaDeck.scale.set(2.6, 0.07, 2.02);
  plazaDeck.position.y = 0.14;
  plazaGroup.add(plazaDeck);

  // Cuatro jardines simétricos del parque central
  const quadOffsets = [
    [-0.72, -0.52],
    [0.72, -0.52],
    [-0.72, 0.52],
    [0.72, 0.52],
  ];
  for (const [qx, qz] of quadOffsets) {
    const lawn = new Mesh(unitBox, materials.lawn);
    lawn.scale.set(0.86, 0.06, 0.62);
    lawn.position.set(qx, 0.18, qz);
    plazaGroup.add(lawn);
  }

  // Glorieta / kiosco octagonal tradicional en el centro del parque
  const kioskBase = new Mesh(new CylinderGeometry(0.36, 0.42, 0.16, 8), materials.plazaTrim);
  kioskBase.position.y = 0.25;
  plazaGroup.add(kioskBase);

  const kioskPillarGeo = new CylinderGeometry(0.025, 0.028, 0.38, 5);
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2;
    const pillar = new Mesh(kioskPillarGeo, materials.palaceWall);
    pillar.position.set(Math.cos(a) * 0.27, 0.5, Math.sin(a) * 0.27);
    plazaGroup.add(pillar);
  }

  const kioskRoof = new Mesh(new ConeGeometry(0.45, 0.28, 8), materials.terracotta);
  kioskRoof.position.y = 0.81;
  plazaGroup.add(kioskRoof);

  const kioskFinial = new Mesh(new SphereGeometry(0.045, 8, 6), materials.goldTrim);
  kioskFinial.position.y = 0.97;
  plazaGroup.add(kioskFinial);

  townGroup.add(plazaGroup);

  /* --- 2. Palacio Municipal de Soke con Torre del Reloj --- */
  const palaceX = 6.55;
  const palaceZ = -6.75;
  const palaceY = getTerrainHeight(palaceX, palaceZ);

  const palaceGroup = new Group();
  palaceGroup.position.set(palaceX, palaceY, palaceZ);
  palaceGroup.rotation.y = -0.14;

  // Zócalo institucional
  const plinth = new Mesh(unitBox, materials.palaceBase);
  plinth.scale.set(3.25, 0.24, 1.55);
  plinth.position.y = 0.1;
  palaceGroup.add(plinth);

  // Cuerpo principal del Palacio Municipal
  const mainBody = new Mesh(unitBox, materials.palaceWall);
  mainBody.scale.set(3.02, 1.12, 1.32);
  mainBody.position.y = 0.78;
  palaceGroup.add(mainBody);

  // Cornisa superior
  const cornice = new Mesh(unitBox, materials.plazaStone);
  cornice.scale.set(3.16, 0.1, 1.44);
  cornice.position.y = 1.37;
  palaceGroup.add(cornice);

  // Techo inclinado terracota del palacio
  const palaceRoof = new Mesh(new CylinderGeometry(0.58, 1.02, 0.34, 4), materials.terracotta);
  palaceRoof.rotation.y = Math.PI / 4;
  palaceRoof.scale.set(2.22, 1, 1.0);
  palaceRoof.position.y = 1.58;
  palaceGroup.add(palaceRoof);

  // Columnata / pórtico frontal del Palacio (número par para dejar libre el portal central)
  const colPositions = [-1.18, -0.68, -0.24, 0.24, 0.68, 1.18];
  for (const cx of colPositions) {
    const col = new Mesh(unitBox, materials.plazaStone);
    col.scale.set(0.1, 0.95, 0.14);
    col.position.set(cx, 0.7, 0.69);
    palaceGroup.add(col);
  }

  // Frontón central
  const porticoRoof = new Mesh(unitBox, materials.terracottaDark);
  porticoRoof.scale.set(1.38, 0.11, 0.34);
  porticoRoof.position.set(0, 1.24, 0.68);
  palaceGroup.add(porticoRoof);

  // Portal central iluminado en planta baja
  const mainDoor = new Mesh(windowGeo, windowPrimaryMat);
  mainDoor.scale.set(1.55, 2.05, 1);
  mainDoor.position.set(0, 0.44, 0.672);
  palaceGroup.add(mainDoor);

  // Ventanas cálidas del Palacio (simétricas entre pilastras en 2 niveles)
  const lowerWinX = [-0.93, -0.46, 0.46, 0.93];
  for (let i = 0; i < lowerWinX.length; i++) {
    const win = new Mesh(windowGeo, i % 2 === 0 ? windowPrimaryMat : windowSecondaryMat);
    win.scale.set(1.15, 1.25, 1);
    win.position.set(lowerWinX[i], 0.56, 0.672);
    palaceGroup.add(win);
  }

  const upperWinX = [-0.93, -0.46, 0, 0.46, 0.93];
  for (let i = 0; i < upperWinX.length; i++) {
    const win = new Mesh(windowGeo, i % 2 === 0 ? windowSecondaryMat : windowPrimaryMat);
    win.scale.set(1.15, 1.25, 1);
    win.position.set(upperWinX[i], 1.0, 0.672);
    palaceGroup.add(win);
  }

  // Torre del reloj / campanario cívico
  const towerBody = new Mesh(unitBox, materials.palaceWall);
  towerBody.scale.set(0.68, 1.18, 0.68);
  towerBody.position.set(0, 2.02, 0.08);
  palaceGroup.add(towerBody);

  const towerTrim = new Mesh(unitBox, materials.plazaStone);
  towerTrim.scale.set(0.78, 0.09, 0.78);
  towerTrim.position.set(0, 2.62, 0.08);
  palaceGroup.add(towerTrim);

  // Esfera iluminada del reloj municipal (frente y costado)
  const clockDialGeo = new CylinderGeometry(0.18, 0.18, 0.04, 14);
  clockDialGeo.rotateX(Math.PI / 2);
  const clockFront = new Mesh(clockDialGeo, clockFaceMat);
  clockFront.position.set(0, 2.24, 0.43);
  palaceGroup.add(clockFront);

  const clockRimGeo = new RingGeometry(0.16, 0.2, 16);
  const clockRim = new Mesh(clockRimGeo, materials.goldTrim);
  clockRim.position.set(0, 2.24, 0.455);
  palaceGroup.add(clockRim);

  // Chapitel de la torre
  const towerCap = new Mesh(new ConeGeometry(0.52, 0.56, 4), materials.terracottaDark);
  towerCap.rotation.y = Math.PI / 4;
  towerCap.position.set(0, 2.94, 0.08);
  palaceGroup.add(towerCap);

  const spire = new Mesh(new CylinderGeometry(0.015, 0.03, 0.34, 6), materials.goldTrim);
  spire.position.set(0, 3.32, 0.08);
  palaceGroup.add(spire);

  townGroup.add(palaceGroup);

  /* --- 3. Conjunto urbano de 22 edificios cívicos y residenciales --- */
  // Coordenadas cuidadosamente compuestas en torno al parque y la avenida cívica
  const buildingSpecs = [
    // Flanco oeste del parque (transición suave hacia la izquierda)
    { x: 0.95, z: -6.1, w: 0.78, h: 0.92, d: 0.74, roof: 'terracotta', matIdx: 0, rot: 0.06 },
    { x: 1.72, z: -7.15, w: 0.88, h: 1.38, d: 0.82, roof: 'flat', matIdx: 2, rot: -0.04 },
    { x: 2.05, z: -5.3, w: 0.74, h: 0.82, d: 0.72, roof: 'terracotta', matIdx: 1, rot: 0.08 },
    { x: 2.55, z: -8.1, w: 0.95, h: 1.62, d: 0.88, roof: 'slate', matIdx: 3, rot: -0.06 },
    { x: 1.2, z: -4.75, w: 0.68, h: 0.7, d: 0.66, roof: 'terracotta', matIdx: 4, rot: 0.1 },

    // Avenida norte / trasera del parque y palacio (edificios más altos para silueta escalonada)
    { x: 3.7, z: -8.25, w: 1.05, h: 1.95, d: 0.92, roof: 'flat', matIdx: 0, rot: -0.05 },
    { x: 4.95, z: -8.5, w: 0.92, h: 1.55, d: 0.86, roof: 'terracotta', matIdx: 1, rot: 0.04 },
    { x: 6.3, z: -8.7, w: 1.15, h: 2.15, d: 0.95, roof: 'slate', matIdx: 2, rot: -0.08 },
    { x: 7.75, z: -8.35, w: 0.96, h: 1.78, d: 0.86, roof: 'flat', matIdx: 3, rot: -0.1 },
    { x: 9.0, z: -7.95, w: 0.88, h: 1.45, d: 0.82, roof: 'terracotta', matIdx: 5, rot: -0.12 },

    // Flanco este (junto al Palacio Municipal)
    { x: 8.65, z: -6.55, w: 0.98, h: 1.58, d: 0.86, roof: 'flat', matIdx: 0, rot: -0.15 },
    { x: 9.85, z: -6.85, w: 0.84, h: 1.18, d: 0.78, roof: 'terracotta', matIdx: 4, rot: -0.18 },
    { x: 10.65, z: -5.9, w: 0.9, h: 1.32, d: 0.82, roof: 'slate', matIdx: 2, rot: -0.14 },
    { x: 9.6, z: -5.25, w: 0.8, h: 0.96, d: 0.74, roof: 'terracotta', matIdx: 1, rot: -0.12 },
    { x: 11.35, z: -7.2, w: 0.82, h: 1.08, d: 0.78, roof: 'terracotta', matIdx: 5, rot: -0.2 },

    // Primer plano cívico (borde sur de la plaza, alturas más bajas para no tapar el palacio)
    { x: 2.85, z: -4.15, w: 0.76, h: 0.74, d: 0.68, roof: 'terracotta', matIdx: 1, rot: 0.05 },
    { x: 5.5, z: -4.35, w: 0.82, h: 0.84, d: 0.72, roof: 'terracotta', matIdx: 4, rot: -0.06 },
    { x: 6.7, z: -4.55, w: 0.86, h: 0.98, d: 0.74, roof: 'flat', matIdx: 0, rot: -0.08 },
    { x: 7.9, z: -4.85, w: 0.84, h: 1.06, d: 0.76, roof: 'terracotta', matIdx: 5, rot: -0.1 },
    { x: 8.95, z: -4.25, w: 0.74, h: 0.78, d: 0.68, roof: 'slate', matIdx: 3, rot: -0.12 },

    // Casas bajas en las laderas exteriores
    { x: -0.2, z: -6.95, w: 0.7, h: 0.68, d: 0.64, roof: 'terracotta', matIdx: 1, rot: 0.14 },
    { x: 10.75, z: -4.65, w: 0.76, h: 0.86, d: 0.68, roof: 'terracotta', matIdx: 0, rot: -0.16 },
  ];

  for (const spec of buildingSpecs) {
    const bGroup = new Group();
    const by = getTerrainHeight(spec.x, spec.z);
    bGroup.position.set(spec.x, by - 0.04, spec.z);
    bGroup.rotation.y = spec.rot;

    // Volumen principal
    const body = new Mesh(unitBox, facadeMaterials[spec.matIdx % facadeMaterials.length]);
    body.scale.set(spec.w, spec.h, spec.d);
    body.position.y = spec.h * 0.5;
    bGroup.add(body);

    // Remate de cubierta (techo inclinado terracota, pizarra o pretil plano)
    if (spec.roof === 'terracotta') {
      const roof = new Mesh(
        new ConeGeometry(Math.max(spec.w, spec.d) * 0.74, 0.28, 4),
        rng() > 0.45 ? materials.terracotta : materials.terracottaDark
      );
      roof.rotation.y = Math.PI / 4;
      roof.scale.set(spec.w / Math.max(spec.w, spec.d), 1, spec.d / Math.max(spec.w, spec.d));
      roof.position.y = spec.h + 0.14;
      bGroup.add(roof);
    } else if (spec.roof === 'slate') {
      const cap = new Mesh(unitBox, materials.slateRoof);
      cap.scale.set(spec.w * 1.05, 0.1, spec.d * 1.05);
      cap.position.y = spec.h + 0.05;
      bGroup.add(cap);

      const penthouse = new Mesh(unitBox, materials.plazaTrim);
      penthouse.scale.set(spec.w * 0.48, 0.16, spec.d * 0.48);
      penthouse.position.set(0, spec.h + 0.16, -spec.d * 0.08);
      bGroup.add(penthouse);
    } else {
      const parapet = new Mesh(unitBox, materials.plazaStone);
      parapet.scale.set(spec.w * 1.04, 0.08, spec.d * 1.04);
      parapet.position.y = spec.h + 0.04;
      bGroup.add(parapet);
    }

    // Ventanas cálidas en la fachada frontal (y ocasionalmente lateral)
    const floors = Math.max(1, Math.floor((spec.h - 0.18) / 0.36));
    const cols = spec.w > 0.9 ? 3 : 2;
    const xStep = (spec.w * 0.64) / Math.max(1, cols - 1);

    for (let f = 0; f < floors; f++) {
      const wy = 0.3 + f * 0.35;
      if (wy > spec.h - 0.16) break;

      for (let c = 0; c < cols; c++) {
        // Dejar algunas ventanas apagadas de forma determinística para realismo
        if (rng() < 0.22) continue;
        const wx = cols === 1 ? 0 : -spec.w * 0.32 + c * xStep;
        const win = new Mesh(windowGeo, rng() > 0.38 ? windowPrimaryMat : windowSecondaryMat);
        win.position.set(wx, wy, spec.d * 0.5 + 0.012);
        bGroup.add(win);
      }

      // Ventana lateral ocasional en edificios altos
      if (spec.h > 1.25 && rng() > 0.42) {
        const sideWin = new Mesh(windowGeo, windowSecondaryMat);
        sideWin.rotation.y = Math.PI / 2;
        sideWin.position.set(-spec.w * 0.5 - 0.012, wy, 0);
        bGroup.add(sideWin);
      }
    }

    townGroup.add(bGroup);
  }

  /* --- 4. Arboledas low-poly (pinos del altiplano y copas parque/lima) --- */
  function createTree(x, z, kind, scale) {
    const g = new Group();
    const ty = getTerrainHeight(x, z);
    g.position.set(x, ty - 0.03, z);
    g.scale.setScalar(scale);

    const trunk = new Mesh(trunkGeo, materials.trunk);
    trunk.position.y = 0.14;
    g.add(trunk);

    if (kind === 'pine') {
      const lower = new Mesh(pineLowerGeo, rng() > 0.45 ? materials.pineDark : materials.pineMid);
      lower.position.y = 0.52;
      lower.rotation.y = rng() * Math.PI;
      g.add(lower);

      const upper = new Mesh(pineUpperGeo, materials.pineMid);
      upper.position.y = 0.88;
      upper.rotation.y = rng() * Math.PI;
      g.add(upper);
    } else {
      const canopyMat = kind === 'lime' ? materials.canopyLime : materials.pineMid;
      const canopy = new Mesh(roundTreeGeo, canopyMat);
      canopy.position.y = 0.46;
      canopy.scale.set(1.05, 0.92, 1.05);
      canopy.rotation.set(rng(), rng(), 0);
      g.add(canopy);
    }

    return g;
  }

  // Árboles del Parque Central (toques de acento lima #9bd60d institucional)
  const parkTrees = [
    [3.35, -5.2, 'lime', 0.85],
    [4.88, -5.18, 'round', 0.92],
    [3.38, -6.22, 'round', 0.88],
    [4.86, -6.22, 'lime', 0.82],
    [2.72, -5.75, 'pine', 0.95],
    [5.48, -5.68, 'lime', 0.78],
  ];
  for (const [x, z, kind, s] of parkTrees) {
    townGroup.add(createTree(x, z, kind, s));
  }

  // Arboledas perimetrales y laderas cercanas (enmarcando la ciudad hacia los volcanes)
  const groveTrees = [
    [-1.2, -7.8, 'pine', 1.1],
    [-0.5, -8.6, 'pine', 1.25],
    [0.3, -8.2, 'pine', 1.05],
    [1.4, -9.1, 'pine', 1.3],
    [3.1, -9.4, 'pine', 1.2],
    [4.4, -9.7, 'pine', 1.35],
    [5.6, -9.8, 'pine', 1.18],
    [7.4, -9.6, 'pine', 1.32],
    [8.6, -9.3, 'pine', 1.22],
    [10.2, -8.8, 'pine', 1.3],
    [11.6, -8.2, 'pine', 1.28],
    [12.4, -6.7, 'pine', 1.15],
    [12.1, -5.3, 'round', 0.95],
    [11.7, -4.4, 'lime', 0.88],
    [4.2, -4.1, 'round', 0.82],
    [1.8, -4.05, 'pine', 0.95],
    [0.2, -5.35, 'pine', 1.02],
    [-2.4, -6.5, 'pine', 1.15],
    [-3.6, -7.4, 'pine', 1.22],
    [-5.2, -9.2, 'pine', 1.35],
    [-6.6, -10.1, 'pine', 1.4],
    [7.5, -5.6, 'lime', 0.76],
    [8.2, -7.4, 'round', 0.85],
    [9.9, -7.8, 'pine', 1.1],
  ];
  for (const [x, z, kind, s] of groveTrees) {
    townGroup.add(createTree(x, z, kind, s));
  }

  return {
    group: townGroup,
    windowPrimaryMat,
    windowSecondaryMat,
    clockFaceMat,
  };
}

/**
 * Sol dorado institucional con halo translúcido aditivo sutil.
 */
function buildSunAndHalo() {
  const group = new Group();
  group.position.set(13.2, 8.1, -23.5);

  const coreMat = new MeshBasicMaterial({
    color: '#f6b11f',
    fog: false,
  });
  const core = new Mesh(new SphereGeometry(1.72, 24, 18), coreMat);
  group.add(core);

  const innerHaloMat = new MeshBasicMaterial({
    color: '#ffd470',
    transparent: true,
    opacity: 0.32,
    blending: AdditiveBlending,
    depthWrite: false,
    fog: false,
  });
  const innerHalo = new Mesh(new SphereGeometry(2.55, 24, 18), innerHaloMat);
  group.add(innerHalo);

  const outerHaloMat = new MeshBasicMaterial({
    color: '#f6b11f',
    transparent: true,
    opacity: 0.14,
    blending: AdditiveBlending,
    depthWrite: false,
    fog: false,
  });
  const outerHalo = new Mesh(new RingGeometry(2.15, 4.35, 36), outerHaloMat);
  group.add(outerHalo);

  return { group, coreMat, innerHaloMat, outerHaloMat, innerHalo, outerHalo };
}

/**
 * 4 nubes low-poly minimalistas formadas por icosaedros suaves con baja opacidad.
 */
function buildLowPolyClouds() {
  const cloudMat = new MeshStandardMaterial({
    color: '#eef4ff',
    emissive: new Color('#c9deff'),
    emissiveIntensity: 0.22,
    flatShading: true,
    roughness: 0.95,
    metalness: 0.0,
    transparent: true,
    opacity: 0.27,
    depthWrite: false,
  });

  const puffGeo = new IcosahedronGeometry(1, 0);

  const cloudDefs = [
    { x: 1.5, y: 7.4, z: -15.8, scale: 1.15, speed: 0.095, puffs: [[-1.1, -0.08, 0, 0.82], [0, 0.22, 0.1, 1.12], [1.15, -0.05, -0.1, 0.85], [0.45, 0.1, -0.35, 0.72]] },
    { x: 11.4, y: 6.3, z: -13.2, scale: 0.92, speed: 0.12, puffs: [[-0.95, -0.06, 0, 0.76], [0.05, 0.18, 0.08, 1.0], [0.95, -0.08, 0, 0.72]] },
    { x: -7.8, y: 6.9, z: -16.8, scale: 1.05, speed: 0.075, puffs: [[-1.05, -0.1, 0, 0.8], [0, 0.16, 0.06, 1.05], [1.05, -0.08, -0.06, 0.78]] },
    { x: 18.2, y: 8.2, z: -18.5, scale: 1.25, speed: 0.085, puffs: [[-1.2, -0.06, 0, 0.85], [-0.15, 0.24, 0.1, 1.15], [1.05, 0.02, -0.1, 0.88], [1.8, -0.14, 0, 0.65]] },
  ];

  const root = new Group();
  const clouds = [];

  for (const def of cloudDefs) {
    const cg = new Group();
    cg.position.set(def.x, def.y, def.z);
    cg.scale.set(def.scale * 1.18, def.scale * 0.56, def.scale * 0.78);

    for (const [px, py, pz, ps] of def.puffs) {
      const puff = new Mesh(puffGeo, cloudMat);
      puff.position.set(px, py, pz);
      puff.scale.setScalar(ps);
      cg.add(puff);
    }

    root.add(cg);
    clouds.push({
      group: cg,
      baseX: def.x,
      baseY: def.y,
      speed: def.speed,
      phase: def.x * 0.37,
    });
  }

  return { root, clouds, material: cloudMat };
}

/* -------------------------------------------------------------------------- */
/*  API pública: initHeroScene({ canvas, container, getTheme })               */
/* -------------------------------------------------------------------------- */

/**
 * Inicializa la escena 3D procedural del hero para MuniSoke GT.
 *
 * @param {object} params
 * @param {HTMLCanvasElement} params.canvas - Elemento <canvas id="hero-3d-canvas">
 * @param {HTMLElement} params.container - Elemento <section id="inicio" class="hero">
 * @param {() => ('light'|'dark')} [params.getTheme] - Función que devuelve el tema actual
 * @returns {{ setTheme: (theme: string) => void, destroy: () => void } | null}
 */
export function initHeroScene({ canvas, container, getTheme } = {}) {
  if (!canvas || !container) {
    return null;
  }

  const markFailed = () => {
    container.classList.remove('is-webgl-ready');
    container.classList.add('is-webgl-failed');
  };

  const markReady = () => {
    container.classList.remove('is-webgl-failed');
    container.classList.add('is-webgl-ready');
  };

  // Verificar soporte WebGL2 limpiamente (Three.js v0.187.0 requiere WebGL2)
  // sin provocar errores no capturados en consola cuando no hay soporte WebGL.
  let glContext = null;
  try {
    glContext = canvas.getContext('webgl2', {
      alpha: false,
      antialias: true,
      powerPreference: 'high-performance',
      depth: true,
      stencil: false,
    });
  } catch {
    glContext = null;
  }

  if (!glContext) {
    markFailed();
    return null;
  }

  let renderer = null;
  try {
    renderer = new WebGLRenderer({
      canvas,
      context: glContext,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
  } catch {
    markFailed();
    return null;
  }

  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = THEME_PRESETS.light.exposure;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  /* --- Escena, Niebla y Cámara --- */
  const scene = new Scene();
  const fog = new FogExp2(THEME_PRESETS.light.fogColor.getHex(), THEME_PRESETS.light.fogDensity);
  scene.fog = fog;

  const camera = new PerspectiveCamera(34, 16 / 9, 0.5, 110);

  // Grupo maestro del paisaje (permite rotación parallax ultra sutil)
  const worldGroup = new Group();
  scene.add(worldGroup);

  /* --- Cielo, Terreno, Volcanes, Ciudad, Sol y Nubes --- */
  const skyDome = buildSkyDome();
  scene.add(skyDome.mesh);

  const terrain = buildValleyTerrain();
  worldGroup.add(terrain);

  // Cadena volcánica guatemalteca (3 volcanes estilizados)
  const mainVolcano = buildVolcano({
    radius: 9.2,
    height: 9.8,
    topRadius: 0.74,
    radialSegments: 20,
    heightSegments: 9,
    seed: 1.7,
    baseHex: '#0e3d24',
    midHex: '#15532f',
    ridgeHex: '#1d663b',
    summitHex: '#2f5249',
  });
  mainVolcano.position.set(6.2, -0.35, -15.6);
  worldGroup.add(mainVolcano);

  const eastVolcano = buildVolcano({
    radius: 8.1,
    height: 8.2,
    topRadius: 0.62,
    radialSegments: 18,
    heightSegments: 8,
    seed: 4.3,
    baseHex: '#0c3720',
    midHex: '#134c2b',
    ridgeHex: '#1b5f37',
    summitHex: '#2c4c45',
  });
  eastVolcano.position.set(16.9, -0.45, -18.2);
  worldGroup.add(eastVolcano);

  const westVolcano = buildVolcano({
    radius: 9.0,
    height: 7.3,
    topRadius: 0.68,
    radialSegments: 18,
    heightSegments: 8,
    seed: 7.9,
    baseHex: '#0c341f',
    midHex: '#12492a',
    ridgeHex: '#195a34',
    summitHex: '#2a4a44',
  });
  westVolcano.position.set(-8.6, -0.5, -20.6);
  worldGroup.add(westVolcano);

  // Colinas / estribaciones secundarias para separar visualmente ciudad y volcanes
  const ridgeCenter = buildFoothillRidge(11.5, 2.55, 7.2, 2.2, '#124a2b');
  ridgeCenter.position.set(1.2, -0.25, -11.9);
  worldGroup.add(ridgeCenter);

  const ridgeRight = buildFoothillRidge(10.2, 2.85, 6.8, 5.1, '#165834');
  ridgeRight.position.set(12.2, -0.25, -12.4);
  worldGroup.add(ridgeRight);

  const ridgeLeft = buildFoothillRidge(12.4, 2.25, 7.6, 8.4, '#0f3f25');
  ridgeLeft.position.set(-10.2, -0.35, -13.2);
  worldGroup.add(ridgeLeft);

  // Ciudad municipal de Soke
  const town = buildMunicipalTown();
  worldGroup.add(town.group);

  // Sol dorado con halo
  const sun = buildSunAndHalo();
  worldGroup.add(sun.group);

  // Nubes low-poly minimalistas
  const cloudsData = buildLowPolyClouds();
  worldGroup.add(cloudsData.root);

  /* --- Iluminación institucional --- */
  const hemiLight = new HemisphereLight(
    THEME_PRESETS.light.hemiSky,
    THEME_PRESETS.light.hemiGround,
    THEME_PRESETS.light.hemiIntensity
  );
  scene.add(hemiLight);

  const keyLight = new DirectionalLight(
    THEME_PRESETS.light.keyColor,
    THEME_PRESETS.light.keyIntensity
  );
  keyLight.position.set(16, 14, 7);
  scene.add(keyLight);

  const rimLight = new DirectionalLight(
    THEME_PRESETS.light.rimColor,
    THEME_PRESETS.light.rimIntensity
  );
  rimLight.position.set(-14, 8, -10);
  scene.add(rimLight);

  const ambientLight = new AmbientLight(
    THEME_PRESETS.light.ambientColor,
    THEME_PRESETS.light.ambientIntensity
  );
  scene.add(ambientLight);

  // Luz cálida ambiental sobre el Parque Central y el Palacio Municipal (acogedora en modo oscuro)
  const plazaLight = new PointLight(
    THEME_PRESETS.light.plazaLightColor,
    THEME_PRESETS.light.plazaLightIntensity,
    15,
    1.7
  );
  plazaLight.position.set(5.4, 2.35, -5.85);
  worldGroup.add(plazaLight);

  /* --- Estado reactivo (tema, cámara responsiva, parallax, visibilidad) --- */
  const initialTheme = normalizeTheme(typeof getTheme === 'function' ? getTheme() : 'light');
  let targetThemeBlend = initialTheme === 'dark' ? 1 : 0;
  let currentThemeBlend = targetThemeBlend;
  let lastAppliedThemeBlend = -1;

  const reducedMotionMQ =
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(prefers-reduced-motion: reduce)')
      : null;
  const finePointerMQ =
    typeof window.matchMedia === 'function'
      ? window.matchMedia('(pointer: fine)')
      : null;

  let prefersReducedMotion = Boolean(reducedMotionMQ && reducedMotionMQ.matches);
  let hasFinePointer = Boolean(finePointerMQ && finePointerMQ.matches);

  let isDestroyed = false;
  let isContextLost = false;
  let isInViewport = true;
  let isDocHidden = Boolean(document.hidden);
  let rafId = 0;
  let lastTimestamp = 0;
  let elapsedTime = 0;

  // Encuadre base responsivo (se recalcula en resize según relación de aspecto)
  const camBase = {
    x: -0.35,
    y: 4.35,
    z: 12.1,
    lookX: 1.55,
    lookY: 2.35,
    lookZ: -7.2,
  };

  // Estado de parallax suavizado
  let targetMouseX = 0;
  let targetMouseY = 0;
  let smoothMouseX = 0;
  let smoothMouseY = 0;
  let targetScroll = 0;
  let smoothScroll = 0;

  // Aplicar estado visual según mezcla claro (0) <-> oscuro (1)
  function applyThemeBlend(blend) {
    const L = THEME_PRESETS.light;
    const D = THEME_PRESETS.dark;

    skyDome.updateColors(blend);

    fog.color.copy(L.fogColor).lerp(D.fogColor, blend);
    fog.density = MathUtils.lerp(L.fogDensity, D.fogDensity, blend);

    sun.coreMat.color.copy(L.sunCore).lerp(D.sunCore, blend);
    sun.innerHaloMat.color.copy(L.sunInnerHalo).lerp(D.sunInnerHalo, blend);
    sun.outerHaloMat.color.copy(L.sunOuterHalo).lerp(D.sunOuterHalo, blend);
    sun.innerHaloMat.opacity = MathUtils.lerp(L.sunInnerOpacity, D.sunInnerOpacity, blend);
    sun.outerHaloMat.opacity = MathUtils.lerp(L.sunOuterOpacity, D.sunOuterOpacity, blend);

    keyLight.color.copy(L.keyColor).lerp(D.keyColor, blend);
    keyLight.intensity = MathUtils.lerp(L.keyIntensity, D.keyIntensity, blend);

    hemiLight.color.copy(L.hemiSky).lerp(D.hemiSky, blend);
    hemiLight.groundColor.copy(L.hemiGround).lerp(D.hemiGround, blend);
    hemiLight.intensity = MathUtils.lerp(L.hemiIntensity, D.hemiIntensity, blend);

    rimLight.color.copy(L.rimColor).lerp(D.rimColor, blend);
    rimLight.intensity = MathUtils.lerp(L.rimIntensity, D.rimIntensity, blend);

    ambientLight.color.copy(L.ambientColor).lerp(D.ambientColor, blend);
    ambientLight.intensity = MathUtils.lerp(L.ambientIntensity, D.ambientIntensity, blend);

    plazaLight.color.copy(L.plazaLightColor).lerp(D.plazaLightColor, blend);
    plazaLight.intensity = MathUtils.lerp(L.plazaLightIntensity, D.plazaLightIntensity, blend);

    town.windowPrimaryMat.emissiveIntensity = MathUtils.lerp(
      L.windowPrimaryEmissive,
      D.windowPrimaryEmissive,
      blend
    );
    town.windowSecondaryMat.emissiveIntensity = MathUtils.lerp(
      L.windowSecondaryEmissive,
      D.windowSecondaryEmissive,
      blend
    );
    town.clockFaceMat.emissiveIntensity = MathUtils.lerp(L.clockEmissive, D.clockEmissive, blend);

    cloudsData.material.color.copy(L.cloudColor).lerp(D.cloudColor, blend);
    cloudsData.material.emissive.copy(L.cloudEmissive).lerp(D.cloudEmissive, blend);
    cloudsData.material.emissiveIntensity = MathUtils.lerp(
      L.cloudEmissiveIntensity,
      D.cloudEmissiveIntensity,
      blend
    );
    cloudsData.material.opacity = MathUtils.lerp(L.cloudOpacity, D.cloudOpacity, blend);

    renderer.toneMappingExposure = MathUtils.lerp(L.exposure, D.exposure, blend);
    lastAppliedThemeBlend = blend;
  }

  // Actualiza posición de cámara y halo solar orientado hacia cámara
  function updateCameraTransform() {
    const mouseFactor = prefersReducedMotion ? 0 : 1;
    const scrollFactor = prefersReducedMotion ? 0 : 1;

    const mx = smoothMouseX * mouseFactor;
    const my = smoothMouseY * mouseFactor;
    const sc = smoothScroll * scrollFactor;

    camera.position.set(
      camBase.x + mx * 0.65,
      camBase.y - my * 0.34 - sc * 0.85,
      camBase.z
    );
    camera.lookAt(
      camBase.lookX + mx * 0.25,
      camBase.lookY - my * 0.14 - sc * 0.28,
      camBase.lookZ
    );

    // Leve rotación del diorama en respuesta al puntero
    worldGroup.rotation.y = mx * 0.022;
    worldGroup.rotation.x = my * 0.009;

    // Mantener el anillo del halo solar encarado limpiamente a la cámara
    sun.outerHalo.lookAt(camera.position);
  }

  // Render de un único frame (usado en inicio, reduced-motion, resize y setTheme estático)
  function renderSingleFrame() {
    if (isDestroyed || isContextLost) return;
    if (Math.abs(lastAppliedThemeBlend - currentThemeBlend) > 0.0001) {
      applyThemeBlend(currentThemeBlend);
    }
    updateCameraTransform();
    renderer.render(scene, camera);
  }

  /* --- Redimensionamiento robusto sin distorsión ni layout thrashing --- */
  function updateSize() {
    if (isDestroyed) return;
    const rect = container.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width || container.clientWidth || window.innerWidth));
    const height = Math.max(1, Math.round(rect.height || container.clientHeight || 420));

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);

    const aspect = width / height;
    // Adaptación elegante entre pantallas anchas (texto a la izq., escena a la der.)
    // y pantallas estrechas/móviles (centrando el volcán y el Palacio en cuadro)
    const narrowT = MathUtils.clamp((1.85 - aspect) / 1.05, 0, 1);

    camera.fov = MathUtils.lerp(33.5, 43.5, narrowT);
    camera.aspect = aspect;
    camera.updateProjectionMatrix();

    camBase.x = MathUtils.lerp(-0.4, 3.05, narrowT);
    camBase.y = MathUtils.lerp(4.35, 4.75, narrowT);
    camBase.z = MathUtils.lerp(12.1, 14.8, narrowT);
    camBase.lookX = MathUtils.lerp(1.45, 5.2, narrowT);
    camBase.lookY = MathUtils.lerp(2.35, 2.45, narrowT);
    camBase.lookZ = -7.2;

    if (prefersReducedMotion || !rafId) {
      renderSingleFrame();
    }
  }

  /* --- Bucle de animación (controlado por visibilidad y reduced-motion) --- */
  function stopLoop() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
    lastTimestamp = 0;
  }

  function tick(timestamp) {
    rafId = 0;
    if (isDestroyed || isContextLost || prefersReducedMotion || !isInViewport || isDocHidden) {
      return;
    }

    const dt = lastTimestamp ? Math.min((timestamp - lastTimestamp) / 1000, 0.05) : 0.016;
    lastTimestamp = timestamp;
    elapsedTime += dt;

    // Transición suave de tema (~0.55s)
    if (Math.abs(currentThemeBlend - targetThemeBlend) > 0.001) {
      const themeLerp = 1 - Math.exp(-5.4 * dt);
      currentThemeBlend = MathUtils.lerp(currentThemeBlend, targetThemeBlend, themeLerp);
      if (Math.abs(currentThemeBlend - targetThemeBlend) <= 0.001) {
        currentThemeBlend = targetThemeBlend;
      }
      applyThemeBlend(currentThemeBlend);
    }

    // Interpolación suave e independiente de framerate para parallax
    const parallaxLerp = 1 - Math.exp(-3.6 * dt);
    smoothMouseX = MathUtils.lerp(smoothMouseX, targetMouseX, parallaxLerp);
    smoothMouseY = MathUtils.lerp(smoothMouseY, targetMouseY, parallaxLerp);
    smoothScroll = MathUtils.lerp(smoothScroll, targetScroll, parallaxLerp);

    // Deriva muy lenta y serena de las nubes low-poly
    for (const cloud of cloudsData.clouds) {
      cloud.group.position.x += cloud.speed * dt;
      if (cloud.group.position.x > 25) {
        cloud.group.position.x = -21;
      }
      cloud.group.position.y = cloud.baseY + Math.sin(elapsedTime * 0.35 + cloud.phase) * 0.08;
    }

    // Respiración apenas perceptible del halo solar
    const pulse = 1 + Math.sin(elapsedTime * 0.65) * 0.035;
    sun.innerHalo.scale.setScalar(pulse);
    sun.outerHalo.scale.setScalar(1 + Math.sin(elapsedTime * 0.65 - 0.5) * 0.025);

    updateCameraTransform();
    renderer.render(scene, camera);

    rafId = requestAnimationFrame(tick);
  }

  function syncRunState() {
    const shouldRun =
      !isDestroyed && !isContextLost && !prefersReducedMotion && isInViewport && !isDocHidden;

    if (shouldRun && !rafId) {
      lastTimestamp = 0;
      rafId = requestAnimationFrame(tick);
    } else if (!shouldRun && rafId) {
      stopLoop();
    }
  }

  /* --- Listeners: Parallax (mouse + scroll), Visibilidad, Resize, Reduced Motion, Context Loss --- */
  function updateScrollTarget() {
    if (prefersReducedMotion || isDestroyed) return;
    const rect = container.getBoundingClientRect();
    const h = rect.height || 1;
    // 0 cuando el hero está en la parte superior, 1 cuando sale por arriba
    targetScroll = MathUtils.clamp(-rect.top / h, 0, 1);
  }

  function onPointerMove(e) {
    if (!hasFinePointer || prefersReducedMotion || !isInViewport || isDestroyed) return;
    const rect = container.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const ny = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    targetMouseX = MathUtils.clamp(nx, -1, 1);
    targetMouseY = MathUtils.clamp(ny, -1, 1);
  }

  function onPointerLeave() {
    targetMouseX = 0;
    targetMouseY = 0;
  }

  function onVisibilityChange() {
    isDocHidden = Boolean(document.hidden);
    syncRunState();
  }

  function onReducedMotionChange(event) {
    prefersReducedMotion = Boolean(event.matches);
    if (prefersReducedMotion) {
      stopLoop();
      targetMouseX = 0;
      targetMouseY = 0;
      smoothMouseX = 0;
      smoothMouseY = 0;
      targetScroll = 0;
      smoothScroll = 0;
      currentThemeBlend = targetThemeBlend;
      applyThemeBlend(currentThemeBlend);
      renderSingleFrame();
    } else {
      updateScrollTarget();
      syncRunState();
    }
  }

  function onFinePointerChange(event) {
    hasFinePointer = Boolean(event.matches);
    if (!hasFinePointer) {
      targetMouseX = 0;
      targetMouseY = 0;
    }
  }

  function onContextLost(event) {
    event.preventDefault();
    isContextLost = true;
    stopLoop();
    markFailed();
  }

  function onPageHide(event) {
    if (event && event.persisted) {
      stopLoop();
      return;
    }
    destroy();
  }

  function onContextRestored() {
    isContextLost = false;
    applyThemeBlend(currentThemeBlend);
    updateSize();
    renderSingleFrame();
    markReady();
    syncRunState();
  }

  // IntersectionObserver para pausar cuando el hero sale del viewport
  let intersectionObserver = null;
  if (typeof IntersectionObserver !== 'undefined') {
    intersectionObserver = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;
        isInViewport = entry.isIntersecting;
        syncRunState();
      },
      { threshold: 0.01 }
    );
    intersectionObserver.observe(container);
  }

  // ResizeObserver sobre container + window.resize (para cambios de DPR/zoom)
  let resizeObserver = null;
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      updateSize();
    });
    resizeObserver.observe(container);
  }
  window.addEventListener('resize', updateSize, { passive: true });

  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('scroll', updateScrollTarget, { passive: true });
  window.addEventListener('pointermove', onPointerMove, { passive: true });
  window.addEventListener('pagehide', onPageHide);
  document.documentElement.addEventListener('pointerleave', onPointerLeave, { passive: true });
  canvas.addEventListener('webglcontextlost', onContextLost, false);
  canvas.addEventListener('webglcontextrestored', onContextRestored, false);

  if (reducedMotionMQ) {
    if (typeof reducedMotionMQ.addEventListener === 'function') {
      reducedMotionMQ.addEventListener('change', onReducedMotionChange);
    } else if (typeof reducedMotionMQ.addListener === 'function') {
      reducedMotionMQ.addListener(onReducedMotionChange);
    }
  }

  if (finePointerMQ) {
    if (typeof finePointerMQ.addEventListener === 'function') {
      finePointerMQ.addEventListener('change', onFinePointerChange);
    } else if (typeof finePointerMQ.addListener === 'function') {
      finePointerMQ.addListener(onFinePointerChange);
    }
  }

  /* --- Render inicial y señalización de listo --- */
  try {
    applyThemeBlend(currentThemeBlend);
    updateScrollTarget();
    updateSize();
    renderSingleFrame();
    markReady();
  } catch {
    destroy();
    markFailed();
    return null;
  }

  // Iniciar bucle continuo solo si no está activo prefers-reduced-motion
  syncRunState();

  /* --- API devuelta al coordinador del portal --- */
  function setTheme(theme) {
    if (isDestroyed) return;
    targetThemeBlend = normalizeTheme(theme) === 'dark' ? 1 : 0;

    if (prefersReducedMotion || !isInViewport || isDocHidden) {
      currentThemeBlend = targetThemeBlend;
      applyThemeBlend(currentThemeBlend);
      if (!isContextLost) {
        renderSingleFrame();
      }
    }
  }

  function destroy() {
    if (isDestroyed) return;
    isDestroyed = true;

    stopLoop();

    if (intersectionObserver) {
      intersectionObserver.disconnect();
      intersectionObserver = null;
    }

    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    window.removeEventListener('resize', updateSize);

    document.removeEventListener('visibilitychange', onVisibilityChange);
    window.removeEventListener('scroll', updateScrollTarget);
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pagehide', onPageHide);
    document.documentElement.removeEventListener('pointerleave', onPointerLeave);
    canvas.removeEventListener('webglcontextlost', onContextLost);
    canvas.removeEventListener('webglcontextrestored', onContextRestored);

    if (reducedMotionMQ) {
      if (typeof reducedMotionMQ.removeEventListener === 'function') {
        reducedMotionMQ.removeEventListener('change', onReducedMotionChange);
      } else if (typeof reducedMotionMQ.removeListener === 'function') {
        reducedMotionMQ.removeListener(onReducedMotionChange);
      }
    }

    if (finePointerMQ) {
      if (typeof finePointerMQ.removeEventListener === 'function') {
        finePointerMQ.removeEventListener('change', onFinePointerChange);
      } else if (typeof finePointerMQ.removeListener === 'function') {
        finePointerMQ.removeListener(onFinePointerChange);
      }
    }

    // Liberar todas las geometrías y materiales únicos de la escena
    const geometries = new Set();
    const materials = new Set();
    scene.traverse((obj) => {
      if (obj.geometry) geometries.add(obj.geometry);
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          for (const m of obj.material) materials.add(m);
        } else {
          materials.add(obj.material);
        }
      }
    });

    for (const geo of geometries) geo.dispose();
    for (const mat of materials) mat.dispose();

    renderer.dispose();
  }

  return { setTheme, destroy };
}

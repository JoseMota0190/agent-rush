/* ============================================================
   AGENT RUSH — escena 3D (Three.js)
   Sala, mesa holográfica, sillas y tres robots humanoides sentados.
   Sin build step: importa el módulo vendorizado.
   ============================================================ */

import * as THREE from "./vendor/three.module.js";

const ACCENTS = {
  strategist: 0xffb020,
  coder: 0x35d6ff,
  auditor: 0xa970ff,
  debugger: 0xffb020,
};

const ROBOT_SLOTS = [
  { role: "strategist", angle: Math.PI + 0.55 },
  { role: "coder",      angle: Math.PI },
  { role: "auditor",    angle: Math.PI - 0.55 },
];

const ORCH_SLOTS = [
  { role: "debugger", angle: Math.PI + 0.55 },
  { role: "coder",    angle: Math.PI },
  { role: "auditor",  angle: Math.PI - 0.55 },
];

const ROBOT_RADIUS = 1.50;

/* ------------------------------------------------------------
   renderer / scene / camera
   ------------------------------------------------------------ */

let renderer, scene, camera, clock;
let bots = new Map();
let labelEls = new Map();
let labelLayer = null;
let container = null;

let tableRings = [];
let dust = null;
let human = null;
let neonLight = null;
let currentMode = "spectator";
let camTarget = new THREE.Vector3(0, 1.0, -0.4);
let camPos = new THREE.Vector3(0, 1.9, 5.6);
let camFov = 40;
let raf = 0;

const CAMS = {
  spectator:    { pos: new THREE.Vector3(0, 2.00, 4.85), target: new THREE.Vector3(0, 1.02, -0.95), fov: 38 },
  orchestrator: { pos: new THREE.Vector3(0, 1.56, 2.85), target: new THREE.Vector3(0, 1.10, -1.00), fov: 52 },
};

/* ------------------------------------------------------------
   helpers
   ------------------------------------------------------------ */

function mat(color, { metalness = 0.8, roughness = 0.42, emissive = 0x000000, emissiveIntensity = 0 } = {}) {
  return new THREE.MeshStandardMaterial({ color, metalness, roughness, emissive, emissiveIntensity });
}

function part(geo, material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z);
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

function glowTexture(inner = "rgba(120,235,255,0.95)", outer = "rgba(53,214,255,0)") {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, inner);
  g.addColorStop(0.45, inner.replace(/0\.95\)$/, "0.35)"));
  g.addColorStop(1, outer);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function makeGlow(color, size, opacity = 0.9) {
  const hex = `#${new THREE.Color(color).getHexString()}`;
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: glowTexture(`${hex}ee`, `${hex}00`),
      transparent: true,
      opacity,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      toneMapped: false,
    })
  );
  sprite.scale.set(size, size, 1);
  return sprite;
}

/* ------------------------------------------------------------
   room
   ------------------------------------------------------------ */

function buildRoom() {
  const room = new THREE.Group();

  // floor
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(18, 14),
    mat(0x070e16, { metalness: 0.5, roughness: 0.75 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  room.add(floor);

  // floor grid
  const grid = new THREE.GridHelper(18, 36, 0x1d4a63, 0x102a3a);
  grid.position.y = 0.005;
  grid.material.transparent = true;
  grid.material.opacity = 0.45;
  room.add(grid);

  // back wall
  const back = new THREE.Mesh(new THREE.PlaneGeometry(18, 5.2), mat(0x0a1622, { metalness: 0.35, roughness: 0.85 }));
  back.position.set(0, 2.6, -5.0);
  back.receiveShadow = true;
  room.add(back);

  // wall panels (vertical seams)
  const seamMat = mat(0x0d1c2a, { metalness: 0.5, roughness: 0.6 });
  for (let x = -7.5; x <= 7.5; x += 1.5) {
    const seam = new THREE.Mesh(new THREE.BoxGeometry(0.03, 5.0, 0.06), seamMat);
    seam.position.set(x, 2.5, -4.96);
    room.add(seam);
  }

  // ceiling
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(18, 14), mat(0x060b12, { metalness: 0.3, roughness: 0.9 }));
  ceil.rotation.x = Math.PI / 2;
  ceil.position.y = 4.4;
  room.add(ceil);

  // ceiling light strips
  const stripMat = new THREE.MeshBasicMaterial({ color: 0xbfefff, toneMapped: false });
  for (let i = 0; i < 4; i++) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.04, 3.2), stripMat);
    strip.position.set(-3.3 + i * 2.2, 4.36, -1.4);
    room.add(strip);
  }

  // side wall vents (kept subtle; no bright monitors in frame)
  const ventMat = mat(0x0a141f, { metalness: 0.6, roughness: 0.6 });
  for (const x of [-4.2, 4.2]) {
    for (let i = 0; i < 5; i++) {
      const slat = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.03, 0.05), ventMat);
      slat.position.set(x, 1.9 + i * 0.11, -4.9);
      room.add(slat);
    }
  }

  scene.add(room);
}

/* ------------------------------------------------------------
   neon signs (canvas textures)
   ------------------------------------------------------------ */

function signTexture(lines, { color = "#ffb020", border = true, size = 256 } = {}) {
  const c = document.createElement("canvas");
  c.width = size * 2;
  c.height = size;
  const ctx = c.getContext("2d");

  ctx.clearRect(0, 0, c.width, c.height);

  if (border) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 10;
    ctx.shadowColor = color;
    ctx.shadowBlur = 34;
    ctx.strokeRect(14, 14, c.width - 28, c.height - 28);
    ctx.strokeRect(14, 14, c.width - 28, c.height - 28);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = color;
  ctx.shadowBlur = 40;
  ctx.fillStyle = color;

  const fontSize = lines.length > 1 ? 108 : 124;
  ctx.font = `800 ${fontSize}px Bahnschrift, "Segoe UI", system-ui, sans-serif`;

  // auto-fit: shrink if the widest line overflows the canvas
  const maxWidth = c.width - 90;
  let widest = 0;
  for (const line of lines) widest = Math.max(widest, ctx.measureText(line).width);
  if (widest > maxWidth) {
    const fitted = Math.floor(fontSize * (maxWidth / widest));
    ctx.font = `800 ${fitted}px Bahnschrift, "Segoe UI", system-ui, sans-serif`;
  }

  lines.forEach((line, i) => {
    const y = c.height / 2 + (i - (lines.length - 1) / 2) * (fontSize * 1.05);
    ctx.fillText(line, c.width / 2, y);
  });

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function buildSigns() {
  // AGENT RUSH
  const agentTex = signTexture(["AGENT", "RUSH"], { color: "#ffb020" });
  const agent = new THREE.Mesh(
    new THREE.PlaneGeometry(2.0, 1.0),
    new THREE.MeshBasicMaterial({ map: agentTex, transparent: true, toneMapped: false })
  );
  agent.position.set(2.9, 2.55, -4.9);
  agent.rotation.z = -0.035;
  scene.add(agent);

  neonLight = new THREE.PointLight(0xffb020, 9, 9, 2);
  neonLight.position.set(2.9, 2.4, -4.2);
  scene.add(neonLight);

  // VULTR SANDBOX
  const vultrTex = signTexture(["VULTR", "SANDBOX"], { color: "#5fe4ff", size: 200 });
  const vultr = new THREE.Mesh(
    new THREE.PlaneGeometry(1.15, 0.57),
    new THREE.MeshBasicMaterial({ map: vultrTex, transparent: true, toneMapped: false })
  );
  vultr.position.set(-3.25, 2.55, -4.88);
  scene.add(vultr);
}

/* ------------------------------------------------------------
   table
   ------------------------------------------------------------ */

function buildTable() {
  const group = new THREE.Group();

  const pedestal = part(new THREE.CylinderGeometry(0.16, 0.22, 0.78, 24), mat(0x0e1926, { metalness: 0.9, roughness: 0.35 }), 0, 0.39, 0);
  group.add(pedestal);

  const base = part(new THREE.CylinderGeometry(0.42, 0.5, 0.06, 32), mat(0x0b141f), 0, 0.03, 0);
  group.add(base);

  const top = part(new THREE.CylinderGeometry(1.05, 1.05, 0.1, 48), mat(0x111e2b, { metalness: 0.85, roughness: 0.3 }), 0, 0.79, 0);
  group.add(top);

  // emissive rim
  const rim = new THREE.Mesh(
    new THREE.TorusGeometry(1.05, 0.013, 12, 96),
    new THREE.MeshBasicMaterial({ color: 0x3fb9d8, toneMapped: false })
  );
  rim.rotation.x = Math.PI / 2;
  rim.position.y = 0.845;
  group.add(rim);

  // holographic disc
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(0.8, 64),
    new THREE.MeshBasicMaterial({
      color: 0x35d6ff,
      transparent: true,
      opacity: 0.1,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      toneMapped: false,
    })
  );
  disc.rotation.x = -Math.PI / 2;
  disc.position.y = 0.85;
  group.add(disc);

  // rotating rings
  for (let i = 0; i < 2; i++) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.36 + i * 0.24, 0.372 + i * 0.24, 64),
      new THREE.MeshBasicMaterial({
        color: i === 0 ? 0x7fe9ff : 0xffb020,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        toneMapped: false,
      })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.86 + i * 0.002;
    ring.userData.spin = i === 0 ? 0.45 : -0.32;
    group.add(ring);
    tableRings.push(ring);
  }

  // holo core
  const core = makeGlow(0x9df3ff, 0.42, 0.5);
  core.position.set(0, 0.92, 0);
  group.add(core);

  const light = new THREE.PointLight(0x35d6ff, 4.5, 6.5, 2);
  light.position.set(0, 1.35, 0);
  group.add(light);

  scene.add(group);
}

/* ------------------------------------------------------------
   chairs
   ------------------------------------------------------------ */

function buildChair(angle) {
  const g = new THREE.Group();
  const m = mat(0x18242f, { metalness: 0.72, roughness: 0.48 });

  const seat = part(new THREE.BoxGeometry(0.5, 0.09, 0.46), m, 0, 0.62, 0);
  const back = part(new THREE.BoxGeometry(0.46, 0.42, 0.06), m, 0, 0.84, 0.22);
  const stem = part(new THREE.CylinderGeometry(0.05, 0.06, 0.6, 12), m, 0, 0.31, 0);
  const foot = part(new THREE.CylinderGeometry(0.26, 0.3, 0.04, 24), m, 0, 0.02, 0);

  g.add(seat, back, stem, foot);

  // subtle rim light strip on the backrest
  const strip = new THREE.Mesh(
    new THREE.BoxGeometry(0.42, 0.02, 0.014),
    new THREE.MeshBasicMaterial({ color: 0x2c7fa3, toneMapped: false })
  );
  strip.position.set(0, 1.24, 0.295);
  g.add(strip);

  const r = ROBOT_RADIUS + 0.30;
  g.position.set(Math.sin(angle) * r, 0, Math.cos(angle) * r);
  g.rotation.y = angle;
  return g;
}

/* ------------------------------------------------------------
   robot
   ------------------------------------------------------------ */

function buildRobot(role) {
  const accent = ACCENTS[role] ?? 0x35d6ff;
  const bodyMat = mat(0x223040, { metalness: 0.86, roughness: 0.34 });
  const jointMat = mat(0x101b26, { metalness: 0.72, roughness: 0.48 });
  const plateMat = mat(0x2b3a4a, { metalness: 0.9, roughness: 0.26 });

  const visorMat = new THREE.MeshStandardMaterial({
    color: 0x061a22,
    emissive: accent,
    emissiveIntensity: 2.2,
    metalness: 0.3,
    roughness: 0.2,
  });

  const root = new THREE.Group();

  // ---- pelvis / torso ----
  root.add(part(new THREE.BoxGeometry(0.34, 0.16, 0.24), jointMat, 0, 0.7, 0));

  const torso = part(new THREE.BoxGeometry(0.4, 0.44, 0.26), bodyMat, 0, 0.98, 0);
  torso.geometry.translate(0, 0, 0);
  root.add(torso);

  // chest plate
  const chest = part(new THREE.BoxGeometry(0.3, 0.26, 0.06), plateMat, 0, 1.03, -0.14);
  root.add(chest);

  // core light
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.045, 16, 16),
    new THREE.MeshBasicMaterial({ color: accent, toneMapped: false }));
  core.position.set(0, 1.03, -0.175);
  root.add(core);

  const coreGlow = makeGlow(accent, 0.42, 0.75);
  coreGlow.position.copy(core.position);
  root.add(coreGlow);

  // ---- shoulders ----
  for (const side of [-1, 1]) {
    root.add(part(new THREE.SphereGeometry(0.07, 16, 16), plateMat, side * 0.235, 1.14, 0));
  }

  // ---- neck + head ----
  root.add(part(new THREE.CylinderGeometry(0.055, 0.06, 0.09, 12), jointMat, 0, 1.28, 0));

  const headGroup = new THREE.Group();
  headGroup.position.set(0, 1.42, 0);

  const head = part(new THREE.BoxGeometry(0.26, 0.26, 0.26), bodyMat, 0, 0, 0);
  headGroup.add(head);

  // helmet crest
  const crest = part(new THREE.BoxGeometry(0.2, 0.03, 0.22), plateMat, 0, 0.14, 0.01);
  headGroup.add(crest);

  // visor
  const visor = part(new THREE.BoxGeometry(0.2, 0.08, 0.02), visorMat, 0, 0.02, -0.135);
  headGroup.add(visor);

  // jaw vents
  for (let i = 0; i < 3; i++) {
    const vent = part(new THREE.BoxGeometry(0.11, 0.008, 0.01), jointMat, 0, -0.06 - i * 0.022, -0.122);
    headGroup.add(vent);
  }

  // antenna
  const antenna = part(new THREE.CylinderGeometry(0.006, 0.006, 0.08, 6), jointMat, 0, 0.2, 0.04);
  headGroup.add(antenna);
  const tip = makeGlow(accent, 0.16, 0.9);
  tip.position.set(0, 0.245, 0.04);
  headGroup.add(tip);

  root.add(headGroup);

  // ---- arms ----
  const arms = {};
  for (const side of [-1, 1]) {
    const shoulder = new THREE.Group();
    shoulder.position.set(side * 0.255, 1.14, 0);

    const upper = part(new THREE.BoxGeometry(0.09, 0.30, 0.09), bodyMat, 0, -0.15, 0);
    shoulder.add(upper);

    const elbow = new THREE.Group();
    elbow.position.set(0, -0.30, 0);
    elbow.rotation.x = 0.50;

    const fore = part(new THREE.BoxGeometry(0.08, 0.28, 0.08), bodyMat, 0, -0.14, 0);
    elbow.add(fore);

    const hand = part(new THREE.BoxGeometry(0.10, 0.05, 0.15), plateMat, 0, -0.30, -0.03);
    elbow.add(hand);

    shoulder.add(elbow);
    shoulder.rotation.x = 0.85;

    root.add(shoulder);
    arms[side < 0 ? "left" : "right"] = { shoulder, elbow, base: 0.85, elbowBase: 0.50 };
  }

  // ---- legs (seated) ----
  for (const side of [-1, 1]) {
    const hip = new THREE.Group();
    hip.position.set(side * 0.11, 0.7, 0);

    const thigh = part(new THREE.CylinderGeometry(0.075, 0.065, 0.42, 12), bodyMat, 0, -0.21, 0);
    hip.add(thigh);

    const knee = new THREE.Group();
    knee.position.set(0, -0.42, 0);

    const shin = part(new THREE.CylinderGeometry(0.06, 0.05, 0.56, 12), bodyMat, 0, -0.28, 0);
    knee.add(shin);

    const foot = part(new THREE.BoxGeometry(0.1, 0.05, 0.2), jointMat, 0, -0.57, -0.05);
    knee.add(foot);

    hip.add(knee);
    hip.rotation.x = Math.PI / 2; // thigh forward
    knee.rotation.x = -Math.PI / 2; // shin down

    root.add(hip);
  }

  return {
    role,
    group: root,
    headGroup,
    visorMat,
    core,
    coreGlow,
    arms,
    state: "idle",
    phase: Math.random() * Math.PI * 2,
    accent,
  };
}

/* ------------------------------------------------------------
   human silhouette (orchestrator POV)
   ------------------------------------------------------------ */

function buildHuman() {
  const g = new THREE.Group();
  const dark = mat(0x05080d, { metalness: 0.1, roughness: 0.95 });

  const head = part(new THREE.SphereGeometry(0.19, 24, 24), dark, 0, 1.22, 0);
  head.scale.set(0.92, 1.1, 0.95);
  g.add(head);

  const neck = part(new THREE.CylinderGeometry(0.11, 0.14, 0.18, 12), dark, 0, 1.02, 0);
  g.add(neck);

  const shoulders = part(new THREE.SphereGeometry(0.3, 24, 16), dark, 0, 0.88, 0.02);
  shoulders.scale.set(2.05, 0.82, 1.0);
  g.add(shoulders);

  // rim light on the head (cyan from the table)
  const rim = makeGlow(0x4fd6ff, 0.55, 0.35);
  rim.position.set(0, 1.36, -0.08);
  g.add(rim);

  g.position.set(0, -0.02, 1.18);
  g.scale.setScalar(0.86);
  g.visible = false;
  return g;
}

/* ------------------------------------------------------------
   dust
   ------------------------------------------------------------ */

function buildDust() {
  const count = 260;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 12;
    positions[i * 3 + 1] = Math.random() * 3.6 + 0.2;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 9;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const m = new THREE.PointsMaterial({
    size: 0.022,
    color: 0x8fdcff,
    transparent: true,
    opacity: 0.45,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const points = new THREE.Points(geo, m);
  points.userData.positions = positions;
  return points;
}

/* ------------------------------------------------------------
   labels (HTML overlay, projected each frame)
   ------------------------------------------------------------ */

function makeLabel(role, name, sub) {
  const wrap = document.createElement("div");
  wrap.className = "bot-label";
  wrap.dataset.role = role;

  const tag = document.createElement("span");
  tag.className = "bot-tag";
  tag.innerHTML = sub ? `${name} <span>${sub}</span>` : name;

  const state = document.createElement("span");
  state.className = "bot-state";
  state.dataset.state = "idle";
  state.textContent = "IDLE";

  wrap.append(tag, state);
  labelLayer.appendChild(wrap);
  return { wrap, tag, state };
}

/* ------------------------------------------------------------
   public API
   ------------------------------------------------------------ */

export function initScene(canvas, labels) {
  container = canvas;
  labelLayer = labels;

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x04070d);
  scene.fog = new THREE.FogExp2(0x04070d, 0.035);

  camera = new THREE.PerspectiveCamera(40, canvas.clientWidth / canvas.clientHeight, 0.1, 60);
  camera.position.copy(camPos);
  camera.lookAt(camTarget);

  clock = new THREE.Clock();

  buildRoom();
  buildSigns();
  buildTable();
  buildDust();
  dust = buildDust();
  scene.add(dust);
  human = buildHuman();
  scene.add(human);

  // lights
  scene.add(new THREE.AmbientLight(0x12222f, 1.9));
  scene.add(new THREE.HemisphereLight(0x2a4a66, 0x04070c, 0.85));

  const key = new THREE.DirectionalLight(0x9fd8ff, 0.85);
  key.position.set(-4, 6, 4);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -8;
  key.shadow.camera.right = 8;
  key.shadow.camera.top = 8;
  key.shadow.camera.bottom = -8;
  scene.add(key);

  const rim = new THREE.PointLight(0x2f8fb0, 3, 9, 2);
  rim.position.set(-4.5, 2.8, -3.4);
  scene.add(rim);

  const fill = new THREE.PointLight(0x1d4a63, 2.2, 9, 2);
  fill.position.set(4.5, 2.6, 1.5);
  scene.add(fill);

  // back rim light: outlines the seated robots against the dark wall
  const backRim = new THREE.PointLight(0x63d8ff, 5.5, 7, 2);
  backRim.position.set(0, 2.1, -3.6);
  scene.add(backRim);

  // front fill: keeps the robot plating readable from the camera side
  const frontFill = new THREE.PointLight(0xa9dcff, 3.2, 8, 2);
  frontFill.position.set(0, 2.2, 3.4);
  scene.add(frontFill);

  // robots + chairs + labels
  for (const slot of ROBOT_SLOTS) {
    const bot = buildRobot(slot.role);
    const r = ROBOT_RADIUS;
    bot.group.position.set(Math.sin(slot.angle) * r, 0, Math.cos(slot.angle) * r);
    bot.group.rotation.y = slot.angle;
    bot.group.userData.slotAngle = slot.angle;
    scene.add(bot.group);
    scene.add(buildChair(slot.angle));
    bots.set(slot.role, bot);

    const sub = slot.role === "coder" ? "(MODEL 2)" : slot.role === "strategist" ? "(MODEL 1)" : "(MODEL 3)";
    const name = slot.role.toUpperCase();
    const el = makeLabel(slot.role, name, sub);
    labelEls.set(slot.role, el);
  }

  // orchestrator labels are handled by relabeling the same three robots

  window.addEventListener("resize", onResize);
  animate();
  setMode("spectator", true);
}

export function setMode(mode, instant = false) {
  currentMode = mode;
  const cfg = CAMS[mode] ?? CAMS.spectator;
  camPos = cfg.pos.clone();
  camTarget = cfg.target.clone();
  camFov = cfg.fov;

  if (instant) {
    camera.position.copy(camPos);
    camera.fov = camFov;
    camera.updateProjectionMatrix();
    camera.lookAt(camTarget);
  }

  if (human) human.visible = mode === "orchestrator";

  // relabel bots for orchestrator mode
  const relabel = {
    strategist: mode === "orchestrator" ? "ROBOT DEBUGGER" : "STRATEGIST",
    coder: "CODER",
    auditor: mode === "orchestrator" ? "ROBOT AUDITOR" : "AUDITOR",
  };
  for (const [role, el] of labelEls) {
    if (role === "debugger") continue;
    const isOrch = mode === "orchestrator";
    const sub = isOrch ? "" : role === "coder" ? "(MODEL 2)" : role === "strategist" ? "(MODEL 1)" : "(MODEL 3)";
    el.tag.innerHTML = `${relabel[role] ?? role.toUpperCase()}${sub ? ` <span>${sub}</span>` : ""}`;
    el.wrap.classList.toggle("is-orch", isOrch);
  }
}

export function setBotState(role, state) {
  const bot = bots.get(role);
  if (!bot) return;
  bot.state = state;

  const el = labelEls.get(role);
  if (el) {
    el.state.dataset.state = state;
    el.state.textContent = {
      idle: "OBSERVING",
      thinking: "THINKING",
      typing: "TYPING",
      error: "ERROR FOUND",
      approved: "APPROVED",
    }[state] ?? state.toUpperCase();
  }

  const colors = {
    idle: 0x2b7f99,
    thinking: 0xffb020,
    typing: 0x35d6ff,
    error: 0xff4d5e,
    approved: 0x4dffa1,
  };
  const c = colors[state] ?? 0x35d6ff;
  bot.visorMat.emissive.setHex(c);
  bot.visorMat.emissiveIntensity = state === "idle" ? 1.1 : 2.6;
  bot.core.material.color.setHex(c);
}

export function setRoomProgress(room) {
  /* hook for future per-room scene changes */
  return room;
}

/* ------------------------------------------------------------
   frame loop
   ------------------------------------------------------------ */

const _v = new THREE.Vector3();

function projectLabel(bot, el, offsetY) {
  _v.copy(bot.group.position);
  _v.y += offsetY;
  _v.project(camera);

  const w = container.clientWidth;
  const h = container.clientHeight;
  const x = (_v.x * 0.5 + 0.5) * w;
  const y = (-_v.y * 0.5 + 0.5) * h;

  const visible = _v.z < 1 && _v.z > -1;
  el.wrap.style.transform = `translate(-50%, -50%) translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
  el.wrap.style.opacity = visible ? "1" : "0";
}

function animate() {
  raf = requestAnimationFrame(animate);
  const t = clock.getElapsedTime();
  const dt = clock.getDelta();

  // camera easing
  camera.position.lerp(camPos, 0.08);
  camera.fov += (camFov - camera.fov) * 0.08;
  camera.updateProjectionMatrix();
  camera.lookAt(camTarget);

  // table rings
  for (const ring of tableRings) {
    ring.rotation.z += ring.userData.spin * dt;
  }

  // robots idle
  for (const bot of bots.values()) {
    const { headGroup, arms, phase, state } = bot;

    headGroup.rotation.y = Math.sin(t * 0.6 + phase) * 0.12;
    headGroup.rotation.x = Math.sin(t * 0.9 + phase) * 0.04;

    if (state === "typing") {
      arms.left.shoulder.rotation.x = 0.85 + Math.sin(t * 9) * 0.08;
      arms.right.shoulder.rotation.x = 0.85 + Math.sin(t * 9 + Math.PI) * 0.08;
      arms.left.elbow.rotation.x = 0.50 + Math.sin(t * 9 + 1) * 0.1;
      arms.right.elbow.rotation.x = 0.50 + Math.sin(t * 9 + 2) * 0.1;
    } else if (state === "error") {
      headGroup.rotation.y = Math.sin(t * 14) * 0.05;
      arms.left.shoulder.rotation.x += (1.02 - arms.left.shoulder.rotation.x) * 0.08;
      arms.right.shoulder.rotation.x += (1.02 - arms.right.shoulder.rotation.x) * 0.08;
    } else {
      arms.left.shoulder.rotation.x += (0.85 - arms.left.shoulder.rotation.x) * 0.08;
      arms.right.shoulder.rotation.x += (0.85 - arms.right.shoulder.rotation.x) * 0.08;
      arms.left.elbow.rotation.x += (0.50 - arms.left.elbow.rotation.x) * 0.08;
      arms.right.elbow.rotation.x += (0.50 - arms.right.elbow.rotation.x) * 0.08;
    }

    // visor breathing
    const base = bot.state === "idle" ? 1.1 : 2.6;
    bot.visorMat.emissiveIntensity = base + Math.sin(t * 2.2 + phase) * 0.35;
  }

  // dust drift
  if (dust) {
    const pos = dust.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) + dt * 0.06;
      if (y > 3.9) y = 0.2;
      pos.setY(i, y);
    }
    pos.needsUpdate = true;
    dust.rotation.y = t * 0.01;
  }

  // neon flicker
  if (neonLight) {
    neonLight.intensity = 8.4 + Math.sin(t * 11) * 0.35 + Math.sin(t * 3.3) * 0.5;
  }

  // human breathing
  if (human && human.visible) {
    human.position.y = Math.sin(t * 1.1) * 0.006;
  }

  // labels
  for (const [role, bot] of bots) {
    const el = labelEls.get(role);
    if (!el) continue;
    projectLabel(bot, el, 1.85);
    // state chip sits just below the name
    el.wrap.style.setProperty("--state-offset", "26px");
  }

  renderer.render(scene, camera);
}

function onResize() {
  if (!renderer || !container) return;
  const w = container.clientWidth;
  const h = container.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

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
  { role: "strategist", angle: Math.PI + 0.72 },
  { role: "coder",      angle: Math.PI },
  { role: "auditor",    angle: Math.PI - 0.72 },
];

const ORCH_SLOTS = [
  { role: "debugger", angle: Math.PI + 0.55 },
  { role: "coder",    angle: Math.PI },
  { role: "auditor",  angle: Math.PI - 0.55 },
];

const ROBOT_RADIUS = 1.74;

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
  spectator:    { pos: new THREE.Vector3(0, 2.10, 5.25), target: new THREE.Vector3(0, 1.05, -1.55), fov: 42 },
  orchestrator: { pos: new THREE.Vector3(0, 1.56, 2.85), target: new THREE.Vector3(0, 1.10, -1.00), fov: 52 },
  hero:         { pos: new THREE.Vector3(0, 1.92, 4.72), target: new THREE.Vector3(0, 1.02, -1.55), fov: 44 },
};

let environmentState = "ready";
let doorLedCtx = null;
let doorLedTexture = null;
let doorAlarm = null;
let tableDiscMat = null;
let tableLight = null;

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

  const W = 15;      // ancho
  const D = 11;      // profundidad
  const H = 4.8;     // alto
  const BACK = -D / 2;
  const HALF_W = W / 2;

  const wallMat = new THREE.MeshStandardMaterial({
    color: 0x18283a,
    metalness: 0.55,
    roughness: 0.62,
    emissive: 0x0a1a28,
    emissiveIntensity: 0.55,
  });
  const panelMat = new THREE.MeshStandardMaterial({
    color: 0x21344a,
    metalness: 0.7,
    roughness: 0.42,
    emissive: 0x0c1e2e,
    emissiveIntensity: 0.4,
  });
  const trimMat = new THREE.MeshStandardMaterial({
    color: 0x3a5168,
    metalness: 0.85,
    roughness: 0.28,
  });
  const floorMat = new THREE.MeshStandardMaterial({
    color: 0x0d1824,
    metalness: 0.8,
    roughness: 0.35,
  });
  const glowMat = new THREE.MeshBasicMaterial({ color: 0x4fd4ff, toneMapped: false });

  // ---------------- floor ----------------
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, D), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  room.add(floor);

  const grid = new THREE.GridHelper(W, 30, 0x2c6285, 0x14324a);
  grid.position.y = 0.012;
  grid.material.transparent = true;
  grid.material.opacity = 0.55;
  room.add(grid);

  // pool of light under the table
  const floorGlow = new THREE.Mesh(
    new THREE.CircleGeometry(3.2, 64),
    new THREE.MeshBasicMaterial({
      color: 0x2a7fae,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      toneMapped: false,
    })
  );
  floorGlow.rotation.x = -Math.PI / 2;
  floorGlow.position.y = 0.02;
  room.add(floorGlow);

  // ---------------- back wall ----------------
  const backWall = new THREE.Mesh(new THREE.PlaneGeometry(W, H), wallMat);
  backWall.position.set(0, H / 2, BACK);
  backWall.receiveShadow = true;
  room.add(backWall);

  // wall panel seams
  for (let x = -HALF_W + 1.2; x <= HALF_W - 1.2; x += 1.5) {
    const seam = new THREE.Mesh(new THREE.BoxGeometry(0.03, H - 0.4, 0.05), trimMat);
    seam.position.set(x, H / 2, BACK + 0.03);
    room.add(seam);
  }
  // horizontal wall bands
  for (const y of [0.35, 3.9]) {
    const band = new THREE.Mesh(new THREE.BoxGeometry(W - 0.2, 0.05, 0.06), trimMat);
    band.position.set(0, y, BACK + 0.04);
    room.add(band);
  }

  // glowing baseboard (floor/wall junction) — the "closed room" cue
  for (const cfg of [
    { w: W - 0.3, pos: [0, 0.1, BACK + 0.08], rot: 0 },
    { w: D - 0.3, pos: [-HALF_W + 0.08, 0.1, 0], rot: Math.PI / 2 },
    { w: D - 0.3, pos: [HALF_W - 0.08, 0.1, 0], rot: Math.PI / 2 },
  ]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(cfg.w, 0.045, 0.05), glowMat);
    strip.position.set(...cfg.pos);
    strip.rotation.y = cfg.rot;
    room.add(strip);
  }

  // upper glowing trim (reads as ceiling edge)
  for (const cfg of [
    { w: W - 0.3, pos: [0, H - 0.25, BACK + 0.08], rot: 0 },
    { w: D - 0.3, pos: [-HALF_W + 0.08, H - 0.25, 0], rot: Math.PI / 2 },
    { w: D - 0.3, pos: [HALF_W - 0.08, H - 0.25, 0], rot: Math.PI / 2 },
  ]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(cfg.w, 0.03, 0.04), glowMat);
    strip.position.set(...cfg.pos);
    strip.rotation.y = cfg.rot;
    strip.material = new THREE.MeshBasicMaterial({ color: 0x2f8fb8, toneMapped: false });
    room.add(strip);
  }

  // ---------------- door on the back wall ----------------
  const door = new THREE.Group();
  const doorPanel = new THREE.Mesh(new THREE.BoxGeometry(2.1, 3.9, 0.1), panelMat);
  doorPanel.position.set(0, 1.95, BACK + 0.06);
  door.add(doorPanel);

  for (const x of [-1.12, 1.12]) {
    const jamb = new THREE.Mesh(new THREE.BoxGeometry(0.14, 4.15, 0.22), trimMat);
    jamb.position.set(x, 2.06, BACK + 0.1);
    door.add(jamb);
  }
  const lintel = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.14, 0.22), trimMat);
  lintel.position.set(0, 4.14, BACK + 0.1);
  door.add(lintel);

  // door split line + handle
  const split = new THREE.Mesh(new THREE.BoxGeometry(0.03, 3.7, 0.03), trimMat);
  split.position.set(0, 1.95, BACK + 0.12);
  door.add(split);
  const handle = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.1, 0.05), trimMat);
  handle.position.set(0.72, 2.0, BACK + 0.14);
  door.add(handle);

  // door glow line + frame accents so the exit reads in the dark
  const doorGlow = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.02, 0.02), glowMat);
  doorGlow.position.set(0, 4.0, BACK + 0.16);
  door.add(doorGlow);

  for (const x of [-1.12, 1.12]) {
    const edge = new THREE.Mesh(new THREE.BoxGeometry(0.02, 3.9, 0.02), glowMat);
    edge.position.set(x, 2.0, BACK + 0.17);
    door.add(edge);
  }
  const topEdge = new THREE.Mesh(new THREE.BoxGeometry(2.26, 0.02, 0.02), glowMat);
  topEdge.position.set(0, 3.95, BACK + 0.17);
  door.add(topEdge);

  // ---------------- electronic lock panel + LED ----------------
  const ledCanvas = document.createElement("canvas");
  ledCanvas.width = 256;
  ledCanvas.height = 96;
  doorLedCtx = ledCanvas.getContext("2d");
  paintDoorLed("LOCKED", "#ff4d5e");
  doorLedTexture = new THREE.CanvasTexture(ledCanvas);
  doorLedTexture.colorSpace = THREE.SRGBColorSpace;
  doorLedTexture.anisotropy = 4;

  const led = new THREE.Mesh(
    new THREE.PlaneGeometry(0.66, 0.25),
    new THREE.MeshBasicMaterial({ map: doorLedTexture, transparent: true, toneMapped: false })
  );
  led.position.set(0.72, 2.62, BACK + 0.135);
  door.add(led);

  const keypad = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.38, 0.035), trimMat);
  keypad.position.set(0.72, 2.05, BACK + 0.14);
  door.add(keypad);
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 3; col++) {
      const key = new THREE.Mesh(
        new THREE.BoxGeometry(0.055, 0.045, 0.012),
        new THREE.MeshBasicMaterial({ color: 0x9fe6ff, toneMapped: false })
      );
      key.position.set(0.62 + col * 0.095, 1.92 + row * 0.085, BACK + 0.165);
      door.add(key);
    }
  }

  // red emergency beacon near the door (turns green when unlocked)
  doorAlarm = new THREE.PointLight(0xff3344, 1.8, 5.2, 2);
  doorAlarm.position.set(0, 3.45, BACK + 0.75);
  room.add(doorAlarm);

  const beacon = new THREE.Mesh(
    new THREE.CylinderGeometry(0.055, 0.055, 0.16, 12),
    new THREE.MeshBasicMaterial({ color: 0xff3344, toneMapped: false })
  );
  beacon.position.set(0, 3.45, BACK + 0.14);
  beacon.rotation.z = Math.PI / 2;
  door.add(beacon);

  room.add(door);

  // side panels next to the door
  for (const x of [-4.9, 4.9]) {
    const panel = new THREE.Mesh(new THREE.BoxGeometry(1.5, 2.6, 0.1), panelMat);
    panel.position.set(x, 2.4, BACK + 0.05);
    room.add(panel);
    for (let i = 0; i < 4; i++) {
      const vent = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.035, 0.04), trimMat);
      vent.position.set(x, 1.7 + i * 0.32, BACK + 0.09);
      room.add(vent);
    }
  }

  // ---------------- side walls ----------------
  for (const side of [-1, 1]) {
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(D, H), wallMat);
    wall.position.set(side * HALF_W, H / 2, 0);
    wall.rotation.y = side * -Math.PI / 2;
    wall.receiveShadow = true;
    room.add(wall);

    // vertical seams + horizontal bands on the side walls
    for (let z = -D / 2 + 1.5; z <= D / 2 - 1.5; z += 2) {
      const seam = new THREE.Mesh(new THREE.BoxGeometry(0.05, H - 0.4, 0.03), trimMat);
      seam.position.set(side * (HALF_W - 0.03), H / 2, z);
      room.add(seam);
    }
    for (const y of [0.35, 3.9]) {
      const band = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.05, D - 0.2), trimMat);
      band.position.set(side * (HALF_W - 0.04), y, 0);
      room.add(band);
    }

    // wall panel blocks
    for (const z of [-3, 0.5, 3.5]) {
      const p = new THREE.Mesh(new THREE.BoxGeometry(0.08, 2.2, 1.4), panelMat);
      p.position.set(side * (HALF_W - 0.06), 2.3, z);
      room.add(p);
    }
  }

  // ---------------- corner pillars ----------------
  for (const x of [-HALF_W + 0.14, HALF_W - 0.14]) {
    for (const z of [BACK + 0.14, D / 2 - 0.14]) {
      const pillar = new THREE.Mesh(new THREE.BoxGeometry(0.34, H, 0.34), panelMat);
      pillar.position.set(x, H / 2, z);
      room.add(pillar);
      const strip = new THREE.Mesh(new THREE.BoxGeometry(0.05, H - 1.2, 0.05), glowMat);
      strip.position.set(x, H / 2, z);
      room.add(strip);
    }
  }

  // ---------------- ceiling ----------------
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(W, D), mat(0x101c28, { metalness: 0.45, roughness: 0.8 }));
  ceil.rotation.x = Math.PI / 2;
  ceil.position.y = H;
  room.add(ceil);

  // recessed light bars
  const stripMat = new THREE.MeshBasicMaterial({ color: 0x9fe6ff, toneMapped: false });
  for (const z of [-3.4, 0, 3.4]) {
    for (const x of [-2.4, 2.4]) {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.04, 2.6), stripMat);
      bar.position.set(x, H - 0.03, z);
      room.add(bar);
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
  agent.position.set(3.05, 3.15, -5.26);
  agent.rotation.z = -0.03;
  scene.add(agent);

  neonLight = new THREE.PointLight(0xffb020, 10, 10, 2);
  neonLight.position.set(3.05, 3.0, -4.6);
  scene.add(neonLight);

  // VULTR SANDBOX
  const vultrTex = signTexture(["VULTR", "SANDBOX"], { color: "#5fe4ff", size: 200 });
  const vultr = new THREE.Mesh(
    new THREE.PlaneGeometry(1.5, 0.75),
    new THREE.MeshBasicMaterial({ map: vultrTex, transparent: true, toneMapped: false })
  );
  vultr.position.set(-3.05, 3.15, -5.26);
  scene.add(vultr);

  const vultrLight = new THREE.PointLight(0x5fe4ff, 5, 8, 2);
  vultrLight.position.set(-3.05, 3.0, -4.6);
  scene.add(vultrLight);

  // small environmental signage, mounted on the back wall flanks
  const restrictedTex = signTexture(["RESTRICTED", "AREA"], { color: "#ff7a45", size: 200 });
  const restricted = new THREE.Mesh(
    new THREE.PlaneGeometry(1.05, 0.52),
    new THREE.MeshBasicMaterial({ map: restrictedTex, transparent: true, toneMapped: false })
  );
  restricted.position.set(5.35, 2.35, -5.26);
  scene.add(restricted);

  const securityTex = signTexture(["SECURITY", "ZONE"], { color: "#5fe4ff", size: 200 });
  const security = new THREE.Mesh(
    new THREE.PlaneGeometry(1.05, 0.52),
    new THREE.MeshBasicMaterial({ map: securityTex, transparent: true, toneMapped: false })
  );
  security.position.set(-5.35, 2.35, -5.26);
  scene.add(security);

  // side-wall signs: escape protocol (amber) and authorized access (green)
  const escapeTex = signTexture(["ESCAPE", "PROTOCOL"], { color: "#ffb020", size: 200 });
  const escapeSign = new THREE.Mesh(
    new THREE.PlaneGeometry(1.3, 0.62),
    new THREE.MeshBasicMaterial({ map: escapeTex, transparent: true, toneMapped: false })
  );
  escapeSign.position.set(-7.42, 2.55, 2.1);
  escapeSign.rotation.y = Math.PI / 2;
  scene.add(escapeSign);

  const accessTex = signTexture(["AUTHORIZED", "ACCESS ONLY"], { color: "#13DB8C", size: 200 });
  const accessSign = new THREE.Mesh(
    new THREE.PlaneGeometry(1.3, 0.62),
    new THREE.MeshBasicMaterial({ map: accessTex, transparent: true, toneMapped: false })
  );
  accessSign.position.set(7.42, 2.55, 2.1);
  accessSign.rotation.y = -Math.PI / 2;
  scene.add(accessSign);
}

/* ------------------------------------------------------------
   door LED + environment states
   ------------------------------------------------------------ */

function paintDoorLed(text, color) {
  if (!doorLedCtx) return;
  const ctx = doorLedCtx;
  ctx.clearRect(0, 0, 256, 96);
  ctx.fillStyle = "rgba(3,8,14,0.92)";
  ctx.fillRect(0, 0, 256, 96);
  ctx.strokeStyle = color;
  ctx.lineWidth = 6;
  ctx.shadowColor = color;
  ctx.shadowBlur = 18;
  ctx.strokeRect(5, 5, 246, 86);
  ctx.fillStyle = color;
  ctx.font = "800 32px 'JetBrains Mono', Consolas, monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 128, 51);
  if (doorLedTexture) doorLedTexture.needsUpdate = true;
}

export function setEnvironmentState(state) {
  environmentState = state;

  if (state === "unlocked") {
    paintDoorLed("UNLOCKED", "#13DB8C");
    if (doorAlarm) {
      doorAlarm.color.setHex(0x13db8c);
      doorAlarm.intensity = 2.6;
    }
    if (tableDiscMat) tableDiscMat.opacity = 0.18;
    if (tableLight) {
      tableLight.color.setHex(0x13db8c);
      tableLight.intensity = 5.2;
    }
    if (neonLight) neonLight.color.setHex(0xffad25);
    return;
  }

  if (state === "active") {
    paintDoorLed("LOCKED", "#ffad25");
    if (doorAlarm) {
      doorAlarm.color.setHex(0xff3344);
      doorAlarm.intensity = 2.8;
    }
    if (tableDiscMat) tableDiscMat.opacity = 0.16;
    if (tableLight) {
      tableLight.color.setHex(0x35d6ff);
      tableLight.intensity = 6.5;
    }
    return;
  }

  paintDoorLed("LOCKED", "#ff4d5e");
  if (doorAlarm) {
    doorAlarm.color.setHex(0xff3344);
    doorAlarm.intensity = 1.8;
  }
  if (tableDiscMat) tableDiscMat.opacity = 0.1;
  if (tableLight) {
    tableLight.color.setHex(0x35d6ff);
    tableLight.intensity = 4.5;
  }
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
  tableDiscMat = new THREE.MeshBasicMaterial({
    color: 0x35d6ff,
    transparent: true,
    opacity: 0.1,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const disc = new THREE.Mesh(new THREE.CircleGeometry(0.8, 64), tableDiscMat);
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

  tableLight = new THREE.PointLight(0x35d6ff, 4.5, 6.5, 2);
  tableLight.position.set(0, 1.35, 0);
  group.add(tableLight);

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
   texturas de pecho y consola
   ------------------------------------------------------------ */

function chestTexture(role, sub, accentHex) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 256;
  const ctx = c.getContext("2d");

  // dark display backing so the text reads against the metal chest
  ctx.fillStyle = "rgba(4,10,17,0.92)";
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.strokeStyle = accentHex;
  ctx.globalAlpha = 0.5;
  ctx.lineWidth = 4;
  ctx.strokeRect(6, 6, c.width - 12, c.height - 12);
  ctx.globalAlpha = 1;

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.shadowColor = accentHex;
  ctx.shadowBlur = 16;

  ctx.fillStyle = accentHex;
  let roleSize = 126;
  ctx.font = `800 ${roleSize}px Bahnschrift, "Segoe UI", system-ui, sans-serif`;
  const roleWidth = ctx.measureText(role).width;
  const roleMax = c.width - 60;
  if (roleWidth > roleMax) {
    roleSize = Math.floor(roleSize * (roleMax / roleWidth));
    ctx.font = `800 ${roleSize}px Bahnschrift, "Segoe UI", system-ui, sans-serif`;
  }
  ctx.fillText(role, 256, 104);

  ctx.globalAlpha = 0.85;
  ctx.font = '500 52px Bahnschrift, "Segoe UI", system-ui, sans-serif';
  ctx.fillText(sub, 256, 196);

  // thin rule under the role
  ctx.globalAlpha = 0.55;
  ctx.fillRect(96, 156, 320, 3);

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function consoleTexture(accentHex) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 320;
  const ctx = c.getContext("2d");

  ctx.fillStyle = "rgba(5,12,20,0.96)";
  ctx.fillRect(0, 0, c.width, c.height);

  // header bar
  ctx.fillStyle = accentHex;
  ctx.globalAlpha = 0.85;
  ctx.fillRect(0, 0, c.width, 26);
  ctx.globalAlpha = 1;

  // fake code lines
  ctx.fillStyle = "#5f8ba6";
  const widths = [210, 300, 150, 330, 240, 190, 290, 120];
  widths.forEach((w, i) => {
    const y = 62 + i * 30;
    ctx.globalAlpha = 0.35 + Math.random() * 0.35;
    ctx.fillRect(34, y, w, 8);
  });

  // accent cursor
  ctx.globalAlpha = 1;
  ctx.fillStyle = accentHex;
  ctx.fillRect(34, 302, 46, 10);

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

/* ------------------------------------------------------------
   robot
   ------------------------------------------------------------ */

function buildRobot(role) {
  const accent = ACCENTS[role] ?? 0x35d6ff;
  const bodyMat = mat(0x2b3c4e, { metalness: 0.7, roughness: 0.42 });
  const jointMat = mat(0x14202c, { metalness: 0.72, roughness: 0.48 });
  const plateMat = mat(0x35485c, { metalness: 0.85, roughness: 0.3 });

  const visorMat = new THREE.MeshStandardMaterial({
    color: 0x0a2029,
    emissive: accent,
    emissiveIntensity: 3.2,
    metalness: 0.3,
    roughness: 0.2,
  });

  const root = new THREE.Group();

  // ---- pelvis / torso ----
  root.add(part(new THREE.BoxGeometry(0.34, 0.16, 0.24), jointMat, 0, 0.7, 0));

  const torso = part(new THREE.BoxGeometry(0.46, 0.46, 0.28), bodyMat, 0, 0.98, 0);
  torso.geometry.translate(0, 0, 0);
  root.add(torso);

  // chest plate with the model name engraved
  const chest = part(new THREE.BoxGeometry(0.5, 0.38, 0.06), mat(0x16232f, { metalness: 0.55, roughness: 0.6 }), 0, 1.03, -0.15);
  root.add(chest);

  const accentHex = `#${new THREE.Color(accent).getHexString()}`;
  const roleLabel = {
    strategist: "STRATEGIST",
    coder: "CODER",
    auditor: "AUDITOR",
  }[role] ?? role.toUpperCase();
  const modelLabel = {
    strategist: "MODEL 1",
    coder: "MODEL 2",
    auditor: "MODEL 3",
  }[role] ?? "";

  const namePlate = new THREE.Mesh(
    new THREE.PlaneGeometry(0.48, 0.24),
    new THREE.MeshBasicMaterial({
      map: chestTexture(roleLabel, modelLabel, accentHex),
      transparent: true,
      toneMapped: false,
    })
  );
  namePlate.position.set(0, 1.04, -0.184);
  namePlate.rotation.y = Math.PI;
  root.add(namePlate);

  // status LED under the plate
  const statusLed = new THREE.Mesh(
    new THREE.BoxGeometry(0.24, 0.016, 0.012),
    new THREE.MeshBasicMaterial({ color: 0x2b7f99, toneMapped: false })
  );
  statusLed.position.set(0, 0.86, -0.184);
  root.add(statusLed);

  // core light (below the plate)
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 16),
    new THREE.MeshBasicMaterial({ color: accent, toneMapped: false }));
  core.position.set(0, 0.80, -0.184);
  root.add(core);

  const coreGlow = makeGlow(accent, 0.22, 0.55);
  coreGlow.position.copy(core.position);
  root.add(coreGlow);

  // accent light so amber/violet read as clearly as cyan
  const accentLight = new THREE.PointLight(accent, 1.0, 2.0, 2);
  accentLight.position.set(0, 0.95, -0.62);
  root.add(accentLight);

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
    elbow.rotation.x = 0.38;

    const fore = part(new THREE.BoxGeometry(0.08, 0.28, 0.08), bodyMat, 0, -0.14, 0);
    elbow.add(fore);

    const hand = part(new THREE.BoxGeometry(0.10, 0.05, 0.15), plateMat, 0, -0.30, -0.03);
    elbow.add(hand);

    shoulder.add(elbow);
    shoulder.rotation.x = 0.62;

    root.add(shoulder);
    arms[side < 0 ? "left" : "right"] = { shoulder, elbow, base: 0.62, elbowBase: 0.38 };
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

  // ---- console in front of the robot ----
  const consoleGroup = new THREE.Group();
  consoleGroup.position.set(0, 0, -0.46);

  const desk = part(new THREE.BoxGeometry(0.46, 0.04, 0.3), jointMat, 0, 0.78, 0);
  consoleGroup.add(desk);

  const stand = part(new THREE.CylinderGeometry(0.03, 0.045, 0.3, 10), jointMat, 0, 0.62, 0.03);
  consoleGroup.add(stand);

  const screenMat = new THREE.MeshBasicMaterial({
    map: consoleTexture(accentHex),
    transparent: true,
    toneMapped: false,
    side: THREE.DoubleSide,
  });
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.34, 0.21), screenMat);
  screen.rotation.x = -0.72;
  screen.position.set(0, 0.88, -0.02);
  consoleGroup.add(screen);

  // thin glowing bezel
  const bezel = new THREE.Mesh(
    new THREE.BoxGeometry(0.37, 0.24, 0.012),
    new THREE.MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.1, toneMapped: false })
  );
  bezel.rotation.x = -0.72;
  bezel.position.set(0, 0.88, -0.027);
  consoleGroup.add(bezel);

  root.add(consoleGroup);

  return {
    role,
    group: root,
    headGroup,
    visorMat,
    core,
    coreGlow,
    statusLed,
    screenMat,
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
  scene.add(new THREE.AmbientLight(0x1a3040, 2.6));
  scene.add(new THREE.HemisphereLight(0x3a6486, 0x060c14, 1.15));

  const key = new THREE.DirectionalLight(0x9fd8ff, 1.15);
  key.position.set(-4, 7, 5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -9;
  key.shadow.camera.right = 9;
  key.shadow.camera.top = 9;
  key.shadow.camera.bottom = -9;
  key.shadow.bias = -0.0008;
  scene.add(key);

  const rim = new THREE.PointLight(0x2f8fb0, 6, 11, 2);
  rim.position.set(-5.5, 3.2, -3.8);
  scene.add(rim);

  const fill = new THREE.PointLight(0x1d4a63, 5, 11, 2);
  fill.position.set(5.5, 3.0, 2.0);
  scene.add(fill);

  // back rim light: outlines the seated robots against the wall
  const backRim = new THREE.PointLight(0x63d8ff, 7, 8, 2);
  backRim.position.set(0, 2.4, -3.8);
  scene.add(backRim);

  // front fill: keeps the robot plating readable from the camera side
  const frontFill = new THREE.PointLight(0xa9dcff, 4, 9, 2);
  frontFill.position.set(0, 2.4, 3.4);
  scene.add(frontFill);

  // wall wash: makes the enclosure readable instead of a black void
  const wallWashL = new THREE.PointLight(0x2f7fa8, 6, 9, 2);
  wallWashL.position.set(-5.0, 3.6, -4.2);
  scene.add(wallWashL);

  const wallWashR = new THREE.PointLight(0x2f7fa8, 6, 9, 2);
  wallWashR.position.set(5.0, 3.6, -4.2);
  scene.add(wallWashR);

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
}

export function setBotState(role, state) {
  const bot = bots.get(role);
  if (!bot) return;
  bot.state = state;

  const colors = {
    idle: 0x2b7f99,
    thinking: 0xffb020,
    typing: 0x4dffa1,
    error: 0xff4d5e,
    approved: 0x4dffa1,
  };
  const c = colors[state] ?? 0x35d6ff;

  bot.visorMat.emissive.setHex(c);
  bot.visorMat.emissiveIntensity = state === "idle" ? 1.8 : 3.2;
  bot.core.material.color.setHex(c);
  bot.statusLed.material.color.setHex(c);
  bot.statusLed.scale.x = state === "typing" ? 1.0 + Math.random() * 0.3 : 1;
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

  // cinematic drift for the landing hero; game cameras stay fixed
  if (currentMode === "hero") {
    camPos.set(Math.sin(t * 0.10) * 0.55, 1.92 + Math.sin(t * 0.07) * 0.05, 4.72);
    camTarget.set(0, 1.02, -1.55);
    camFov = 44;
  }

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
      arms.left.shoulder.rotation.x = 0.62 + Math.sin(t * 9) * 0.06;
      arms.right.shoulder.rotation.x = 0.62 + Math.sin(t * 9 + Math.PI) * 0.06;
      arms.left.elbow.rotation.x = 0.38 + Math.sin(t * 9 + 1) * 0.08;
      arms.right.elbow.rotation.x = 0.38 + Math.sin(t * 9 + 2) * 0.08;
    } else if (state === "error") {
      headGroup.rotation.y = Math.sin(t * 14) * 0.05;
      arms.left.shoulder.rotation.x += (0.8 - arms.left.shoulder.rotation.x) * 0.08;
      arms.right.shoulder.rotation.x += (0.8 - arms.right.shoulder.rotation.x) * 0.08;
    } else {
      arms.left.shoulder.rotation.x += (0.62 - arms.left.shoulder.rotation.x) * 0.08;
      arms.right.shoulder.rotation.x += (0.62 - arms.right.shoulder.rotation.x) * 0.08;
      arms.left.elbow.rotation.x += (0.38 - arms.left.elbow.rotation.x) * 0.08;
      arms.right.elbow.rotation.x += (0.38 - arms.right.elbow.rotation.x) * 0.08;
    }

    // visor breathing
    const base = bot.state === "idle" ? 1.8 : 3.2;
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

  // door emergency beacon + shared-table activity
  if (doorAlarm) {
    const base = environmentState === "unlocked" ? 2.4 : environmentState === "active" ? 2.8 : 1.8;
    const speed = environmentState === "unlocked" ? 1.1 : 3.4;
    doorAlarm.intensity = base + Math.sin(t * speed) * 0.22;
  }
  if (tableDiscMat && environmentState === "active") {
    tableDiscMat.opacity = 0.16 + Math.sin(t * 3.2) * 0.03;
  }

  // human breathing
  if (human && human.visible) {
    human.position.y = Math.sin(t * 1.1) * 0.006;
  }

  // (labels are engraved on the chest plates now)

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

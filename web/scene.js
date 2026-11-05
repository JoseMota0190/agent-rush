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
  spectator:    { pos: new THREE.Vector3(0, 2.12, 5.10), target: new THREE.Vector3(0, 1.08, -1.35), fov: 44 },
  orchestrator: { pos: new THREE.Vector3(0, 1.55, 2.6), target: new THREE.Vector3(0, 1.10, -0.95), fov: 55 },
  hero:         { pos: new THREE.Vector3(0, 2.20, 5.80), target: new THREE.Vector3(0, 1.00, -1.35), fov: 50 },
};

let environmentState = "ready";
let doorLedCtx = null;
let doorLedTexture = null;
let doorAlarm = null;
let emergencyFixtures = [];
let emergencyLights = [];
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

  // Vault-grade steel: thick plates, heavy frames and rivets.
  const vaultMat = new THREE.MeshStandardMaterial({
    color: 0x263644,
    metalness: 0.5,
    roughness: 0.5,
    emissive: 0x0e1e2c,
    emissiveIntensity: 0.7,
  });
  const vaultPlateMat = new THREE.MeshStandardMaterial({
    color: 0x344554,
    metalness: 0.4,
    roughness: 0.52,
    emissive: 0x10202e,
    emissiveIntensity: 0.7,
  });
  const vaultFrameMat = new THREE.MeshStandardMaterial({
    color: 0x6b8094,
    metalness: 0.55,
    roughness: 0.38,
    emissive: 0x10202c,
    emissiveIntensity: 0.4,
  });
  const rivetMat = new THREE.MeshStandardMaterial({
    color: 0xb8c6d2,
    metalness: 0.75,
    roughness: 0.3,
  });
  const wallLightMat = new THREE.MeshBasicMaterial({ color: 0x2f8fb8, toneMapped: false });

  function buildVaultWall(width, height, cols, rows) {
    const g = new THREE.Group();

    // Thick reinforced slab behind the plates.
    const slab = new THREE.Mesh(new THREE.BoxGeometry(width, height, 0.42), vaultMat);
    slab.position.set(0, height / 2, -0.30);
    slab.receiveShadow = true;
    g.add(slab);

    const margin = 0.32;
    const gap = 0.16;
    const plateW = (width - margin * 2 - gap * (cols - 1)) / cols;
    const plateH = (height - 0.55 - gap * (rows - 1)) / rows;
    const baseY = 0.28;

    const addRivet = (x, y, z = 0.18) => {
      const rivet = new THREE.Mesh(new THREE.SphereGeometry(0.045, 8, 8), rivetMat);
      rivet.position.set(x, y, z);
      g.add(rivet);
    };

    for (let c = 0; c < cols; c++) {
      for (let r = 0; r < rows; r++) {
        const x = -width / 2 + margin + plateW / 2 + c * (plateW + gap);
        const y = baseY + plateH / 2 + r * (plateH + gap);

        const plate = new THREE.Mesh(new THREE.BoxGeometry(plateW, plateH, 0.08), vaultPlateMat);
        plate.position.set(x, y, -0.05);
        plate.castShadow = true;
        plate.receiveShadow = true;
        g.add(plate);

        const barT = 0.07;
        const barD = 0.14;
        const barZ = 0.02;
        const top = new THREE.Mesh(new THREE.BoxGeometry(plateW + barT * 2, barT, barD), vaultFrameMat);
        top.position.set(x, y + plateH / 2 + barT / 2, barZ);
        g.add(top);
        const bottom = top.clone();
        bottom.position.y = y - plateH / 2 - barT / 2;
        g.add(bottom);
        const left = new THREE.Mesh(new THREE.BoxGeometry(barT, plateH + barT * 2, barD), vaultFrameMat);
        left.position.set(x - plateW / 2 - barT / 2, y, barZ);
        g.add(left);
        const right = left.clone();
        right.position.x = x + plateW / 2 + barT / 2;
        g.add(right);

        addRivet(x - plateW / 2 + 0.12, y - plateH / 2 + 0.12);
        addRivet(x + plateW / 2 - 0.12, y - plateH / 2 + 0.12);
        addRivet(x - plateW / 2 + 0.12, y + plateH / 2 - 0.12);
        addRivet(x + plateW / 2 - 0.12, y + plateH / 2 - 0.12);
      }
    }

    // Heavy base / top bands.
    const baseBand = new THREE.Mesh(new THREE.BoxGeometry(width, 0.34, 0.20), vaultFrameMat);
    baseBand.position.set(0, 0.17, 0.08);
    g.add(baseBand);
    const topBand = baseBand.clone();
    topBand.position.y = height - 0.17;
    g.add(topBand);

    // Reinforced corner braces.
    for (const side of [-1, 1]) {
      const brace = new THREE.Mesh(new THREE.BoxGeometry(0.32, height - 0.1, 0.28), vaultFrameMat);
      brace.position.set(side * (width / 2 - 0.16), height / 2, 0.12);
      g.add(brace);
      for (const y of [0.6, height / 2, height - 0.6]) {
        addRivet(side * (width / 2 - 0.16), y, 0.22);
      }
    }

    return g;
  }

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

  // ---------------- back vault wall ----------------
  const backVault = buildVaultWall(W, H, 3, 2);
  backVault.position.set(0, 0, BACK);
  room.add(backVault);

  // glowing baseboard (floor/wall junction) — the "closed room" cue
  for (const cfg of [
    { w: W - 0.6, pos: [0, 0.38, BACK + 0.30], rot: 0 },
    { w: D - 0.6, pos: [-HALF_W + 0.30, 0.38, 0], rot: Math.PI / 2 },
    { w: D - 0.6, pos: [HALF_W - 0.30, 0.38, 0], rot: Math.PI / 2 },
  ]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(cfg.w, 0.045, 0.05), glowMat);
    strip.position.set(...cfg.pos);
    strip.rotation.y = cfg.rot;
    room.add(strip);
  }

  // upper glowing trim (reads as ceiling edge)
  for (const cfg of [
    { w: W - 0.6, pos: [0, H - 0.42, BACK + 0.30], rot: 0 },
    { w: D - 0.6, pos: [-HALF_W + 0.30, H - 0.42, 0], rot: Math.PI / 2 },
    { w: D - 0.6, pos: [HALF_W - 0.30, H - 0.42, 0], rot: Math.PI / 2 },
  ]) {
    const strip = new THREE.Mesh(new THREE.BoxGeometry(cfg.w, 0.03, 0.04), glowMat);
    strip.position.set(...cfg.pos);
    strip.rotation.y = cfg.rot;
    strip.material = new THREE.MeshBasicMaterial({ color: 0x2f8fb8, toneMapped: false });
    room.add(strip);
  }

  // ---------------- door on the back wall ----------------
  const door = new THREE.Group();

  // Reinforced door panel - thicker
  const doorPanel = new THREE.Mesh(new THREE.BoxGeometry(2.1, 3.9, 0.18), vaultPlateMat);
  doorPanel.position.set(0, 1.95, BACK + 0.26);
  door.add(doorPanel);

  // Thicker reinforced jambs/frame
  for (const x of [-1.12, 1.12]) {
    const jamb = new THREE.Mesh(new THREE.BoxGeometry(0.22, 4.3, 0.3), vaultFrameMat);
    jamb.position.set(x, 2.06, BACK + 0.28);
    door.add(jamb);
  }
  const lintel = new THREE.Mesh(new THREE.BoxGeometry(2.54, 0.22, 0.3), vaultFrameMat);
  lintel.position.set(0, 4.22, BACK + 0.28);
  door.add(lintel);

  // Subtle hazard band at the bottom of the jambs.
  const hazardMat = new THREE.MeshBasicMaterial({ color: 0xd18a1a, toneMapped: false });
  const hazardDarkMat = new THREE.MeshBasicMaterial({ color: 0x14181c, toneMapped: false });
  for (const x of [-1.12, 1.12]) {
    for (let i = 0; i < 5; i++) {
      const stripe = new THREE.Mesh(
        new THREE.BoxGeometry(0.2, 0.26, 0.03),
        i % 2 === 0 ? hazardMat : hazardDarkMat
      );
      stripe.position.set(x, 0.35 + i * 0.28, BACK + 0.40);
      door.add(stripe);
    }
  }

  // Door split line (center seal)
  const split = new THREE.Mesh(new THREE.BoxGeometry(0.04, 3.9, 0.04), trimMat);
  split.position.set(0, 1.95, BACK + 0.28);
  door.add(split);
  const handle = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.1, 0.05), vaultFrameMat);
  handle.position.set(0.72, 2.0, BACK + 0.30);
  door.add(handle);

  // Heavy vault locking wheel.
  const wheel = new THREE.Group();
  wheel.position.set(-0.42, 1.9, BACK + 0.32);
  const wheelRing = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.04, 10, 24), vaultFrameMat);
  wheel.add(wheelRing);
  const wheelHub = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.08, 12), vaultFrameMat);
  wheelHub.rotation.x = Math.PI / 2;
  wheel.add(wheelHub);
  for (let i = 0; i < 4; i++) {
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.55, 0.035), vaultFrameMat);
    spoke.rotation.z = (i * Math.PI) / 4;
    wheel.add(spoke);
  }
  door.add(wheel);

  // Threshold plate (floor)
  const threshold = new THREE.Mesh(
    new THREE.BoxGeometry(2.54, 0.02, 0.5),
    new THREE.MeshStandardMaterial({ color: 0x2a3a4a, metalness: 0.9, roughness: 0.2 })
  );
  threshold.position.set(0, 0.01, BACK + 0.34);
  door.add(threshold);

  // Door glow line + frame accents so the exit reads in the dark
  const doorGlow = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.02, 0.02), glowMat);
  doorGlow.position.set(0, 4.08, BACK + 0.28);
  door.add(doorGlow);

  for (const x of [-1.12, 1.12]) {
    const edge = new THREE.Mesh(new THREE.BoxGeometry(0.02, 3.9, 0.02), glowMat);
    edge.position.set(x, 2.0, BACK + 0.28);
    door.add(edge);
  }
  const topEdge = new THREE.Mesh(new THREE.BoxGeometry(2.26, 0.02, 0.02), glowMat);
  topEdge.position.set(0, 3.95, BACK + 0.21);
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
  led.position.set(0.72, 2.62, BACK + 0.22);
  door.add(led);

  const keypad = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.38, 0.035), trimMat);
  keypad.position.set(0.72, 2.05, BACK + 0.22);
  door.add(keypad);
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 3; col++) {
      const key = new THREE.Mesh(
        new THREE.BoxGeometry(0.055, 0.045, 0.012),
        new THREE.MeshBasicMaterial({ color: 0x9fe6ff, toneMapped: false })
      );
      key.position.set(0.62 + col * 0.095, 1.92 + row * 0.085, BACK + 0.245);
      door.add(key);
    }
  }

  // Two red emergency fixtures near the door (wall-mounted)
  for (const x of [-1.6, 1.6]) {
    const fixtureMat = new THREE.MeshBasicMaterial({ color: 0xff3344, toneMapped: false });
    const fixture = new THREE.Mesh(
      new THREE.BoxGeometry(0.18, 0.18, 0.12),
      fixtureMat
    );
    fixture.position.set(x, 3.3, BACK + 0.12);
    door.add(fixture);
    emergencyFixtures.push(fixtureMat);

    const fixtureGlow = new THREE.PointLight(0xff3344, 1.2, 3.5, 2);
    fixtureGlow.position.set(x, 3.3, BACK + 0.5);
    room.add(fixtureGlow);
    emergencyLights.push(fixtureGlow);
  }

  // Red emergency beacon near the door (turns green when unlocked)
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
  door.userData.beacon = beacon;

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

  // ---------------- side vault walls ----------------
  for (const side of [-1, 1]) {
    const sideVault = buildVaultWall(D, H, 2, 2);
    sideVault.position.set(side * HALF_W, 0, 0);
    sideVault.rotation.y = side * -Math.PI / 2;
    room.add(sideVault);
  }

  // ---------------- ceiling ----------------
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(W, D), mat(0x101c28, { metalness: 0.45, roughness: 0.8 }));
  ceil.rotation.x = Math.PI / 2;
  ceil.position.y = H;
  room.add(ceil);

  // Ceiling cross beams (3)
  const beamMat = new THREE.MeshStandardMaterial({ color: 0x18283a, metalness: 0.55, roughness: 0.62 });
  for (const z of [-2.5, 0, 2.5]) {
    const beam = new THREE.Mesh(new THREE.BoxGeometry(W - 1.0, 0.18, 0.35), beamMat);
    beam.position.set(0, H - 0.18, z);
    room.add(beam);
    // Accent strip on beam
    const strip = new THREE.Mesh(new THREE.BoxGeometry(W - 1.0, 0.02, 0.04), wallLightMat);
    strip.position.set(0, H - 0.28, z);
    room.add(strip);
  }

  // Side ducts/panels (2)
  for (const x of [-6.0, 6.0]) {
    const duct = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.35, D - 1.0), panelMat);
    duct.position.set(x, H - 0.175, 0);
    room.add(duct);
    // Vent slits on duct
    for (let i = 0; i < 8; i++) {
      const slit = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.02, 0.8), trimMat);
      slit.position.set(x, H - 0.1, -3.5 + i * 1.0);
      room.add(slit);
    }
  }

  // Soft cyan ceiling wash (emissive strips along perimeter)
  const ceilingWashMat = new THREE.MeshBasicMaterial({ color: 0x1a4a6a, transparent: true, opacity: 0.35, toneMapped: false });
  for (const cfg of [
    { w: W - 0.6, pos: [0, H - 0.05, -D / 2 + 0.3], rot: 0 },
    { w: W - 0.6, pos: [0, H - 0.05, D / 2 - 0.3], rot: 0 },
    { w: D - 0.6, pos: [-W / 2 + 0.3, H - 0.05, 0], rot: Math.PI / 2 },
    { w: D - 0.6, pos: [W / 2 - 0.3, H - 0.05, 0], rot: Math.PI / 2 },
  ]) {
    const wash = new THREE.Mesh(new THREE.BoxGeometry(cfg.w, 0.06, 0.4), ceilingWashMat);
    wash.position.set(...cfg.pos);
    wash.rotation.y = cfg.rot;
    room.add(wash);
  }

  // Recessed light bars
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

function brandLogoTexture() {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 256;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);

  // Orange diamond outline (AGENT RUSH mark).
  ctx.save();
  ctx.translate(124, 128);
  ctx.rotate(Math.PI / 4);
  ctx.strokeStyle = "#ffad25";
  ctx.lineWidth = 16;
  ctx.lineJoin = "round";
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(-52, -52, 104, 104, 10);
  } else {
    ctx.rect(-52, -52, 104, 104);
  }
  ctx.stroke();
  ctx.restore();

  // AGENT white / RUSH orange.
  const font = '800 96px Bahnschrift, "Segoe UI", Arial, sans-serif';
  ctx.font = font;
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  const agent = "AGENT";
  const rush = "RUSH";
  const agentW = ctx.measureText(agent).width;
  const startX = 205;
  ctx.fillStyle = "#f4f8ff";
  ctx.fillText(agent, startX, 132);
  ctx.fillStyle = "#ffad25";
  ctx.fillText(rush, startX + agentW + 30, 132);

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function vultrLogoTexture() {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 192;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, c.width, c.height);

  // Vultr V mark.
  ctx.fillStyle = "#2f7bff";
  ctx.beginPath();
  ctx.moveTo(20, 20);
  ctx.lineTo(92, 20);
  ctx.lineTo(192, 172);
  ctx.lineTo(120, 172);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#e8f1ff";
  ctx.beginPath();
  ctx.moveTo(120, 172);
  ctx.lineTo(192, 172);
  ctx.lineTo(292, 20);
  ctx.lineTo(220, 20);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = "#9cc4ff";
  ctx.globalAlpha = 0.55;
  ctx.beginPath();
  ctx.moveTo(220, 20);
  ctx.lineTo(292, 20);
  ctx.lineTo(250, 96);
  ctx.lineTo(210, 60);
  ctx.closePath();
  ctx.fill();
  ctx.globalAlpha = 1;

  ctx.font = '700 96px Bahnschrift, "Segoe UI", Arial, sans-serif';
  ctx.fillStyle = "#f4f8ff";
  ctx.textBaseline = "middle";
  ctx.textAlign = "left";
  ctx.fillText("VULTR", 330, 100);

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function buildSigns() {
  const plaqueMat = new THREE.MeshStandardMaterial({
    color: 0x0b141d,
    metalness: 0.9,
    roughness: 0.26,
    emissive: 0x03070b,
    emissiveIntensity: 0.4,
  });
  const plaqueFrameMat = new THREE.MeshStandardMaterial({
    color: 0x2f3f4f,
    metalness: 0.95,
    roughness: 0.2,
  });

  // AGENT RUSH logo plaque (right).
  const agentFrame = new THREE.Mesh(new THREE.BoxGeometry(3.04, 1.0, 0.08), plaqueFrameMat);
  agentFrame.position.set(2.78, 3.25, -5.18);
  scene.add(agentFrame);
  const agentPlaque = new THREE.Mesh(new THREE.BoxGeometry(2.9, 0.86, 0.07), plaqueMat);
  agentPlaque.position.set(2.78, 3.25, -5.14);
  scene.add(agentPlaque);
  const agentLogo = new THREE.Mesh(
    new THREE.PlaneGeometry(2.65, 0.66),
    new THREE.MeshBasicMaterial({ map: brandLogoTexture(), transparent: true, toneMapped: false })
  );
  agentLogo.position.set(2.78, 3.25, -5.10);
  scene.add(agentLogo);

  neonLight = new THREE.PointLight(0xffad25, 3.6, 9, 2);
  neonLight.position.set(2.78, 2.95, -4.70);
  scene.add(neonLight);

  // VULTR logo plaque (left).
  const vultrFrame = new THREE.Mesh(new THREE.BoxGeometry(2.54, 0.84, 0.08), plaqueFrameMat);
  vultrFrame.position.set(-2.78, 3.25, -5.18);
  scene.add(vultrFrame);
  const vultrPlaque = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.7, 0.07), plaqueMat);
  vultrPlaque.position.set(-2.78, 3.25, -5.14);
  scene.add(vultrPlaque);

  const vultrLogo = new THREE.Mesh(
    new THREE.PlaneGeometry(2.2, 0.41),
    new THREE.MeshBasicMaterial({ map: vultrLogoTexture(), transparent: true, toneMapped: false })
  );
  vultrLogo.position.set(-2.78, 3.25, -5.10);
  scene.add(vultrLogo);

  const vultrLight = new THREE.PointLight(0x5fe4ff, 3.0, 8, 2);
  vultrLight.position.set(-2.78, 2.95, -4.70);
  scene.add(vultrLight);
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

  const unlocked = state === "unlocked";
  for (const material of emergencyFixtures) {
    material.color.setHex(unlocked ? 0x13db8c : 0xff3344);
  }
  for (const light of emergencyLights) {
    light.color.setHex(unlocked ? 0x13db8c : 0xff3344);
    light.intensity = unlocked ? 1.5 : 1.0;
  }

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

  // Reduced table top radius by ~8.5% (1.05 -> 0.96)
  const TOP_RADIUS = 0.96;
  const top = part(new THREE.CylinderGeometry(TOP_RADIUS, TOP_RADIUS, 0.1, 48), mat(0x111e2b, { metalness: 0.85, roughness: 0.3 }), 0, 0.79, 0);
  group.add(top);

  // emissive rim
  const rim = new THREE.Mesh(
    new THREE.TorusGeometry(TOP_RADIUS, 0.013, 12, 96),
    new THREE.MeshBasicMaterial({ color: 0x3fb9d8, toneMapped: false })
  );
  rim.rotation.x = Math.PI / 2;
  rim.position.y = 0.845;
  group.add(rim);

  // holographic disc (proportionally reduced)
  tableDiscMat = new THREE.MeshBasicMaterial({
    color: 0x35d6ff,
    transparent: true,
    opacity: 0.1,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  });
  const disc = new THREE.Mesh(new THREE.CircleGeometry(0.73, 64), tableDiscMat);
  disc.rotation.x = -Math.PI / 2;
  disc.position.y = 0.85;
  group.add(disc);

  // rotating rings (proportionally reduced)
  for (let i = 0; i < 2; i++) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.33 + i * 0.22, 0.342 + i * 0.22, 64),
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

  // Body group (scaled ~13% larger for presence)
  const bodyGroup = new THREE.Group();
  bodyGroup.scale.setScalar(1.13);
  root.add(bodyGroup);

  // ---- pelvis / torso ----
  bodyGroup.add(part(new THREE.BoxGeometry(0.34, 0.16, 0.24), jointMat, 0, 0.7, 0));

  const torso = part(new THREE.BoxGeometry(0.46, 0.46, 0.28), bodyMat, 0, 0.98, 0);
  torso.geometry.translate(0, 0, 0);
  bodyGroup.add(torso);

  // chest plate with the model name engraved
  const chest = part(new THREE.BoxGeometry(0.5, 0.38, 0.06), mat(0x16232f, { metalness: 0.55, roughness: 0.6 }), 0, 1.03, -0.15);
  bodyGroup.add(chest);

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
  bodyGroup.add(namePlate);

  // status LED under the plate
  const statusLed = new THREE.Mesh(
    new THREE.BoxGeometry(0.24, 0.016, 0.012),
    new THREE.MeshBasicMaterial({ color: 0x2b7f99, toneMapped: false })
  );
  statusLed.position.set(0, 0.86, -0.184);
  bodyGroup.add(statusLed);

  // core light (below the plate)
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.035, 16, 16),
    new THREE.MeshBasicMaterial({ color: accent, toneMapped: false }));
  core.position.set(0, 0.80, -0.184);
  bodyGroup.add(core);

  const coreGlow = makeGlow(accent, 0.22, 0.55);
  coreGlow.position.copy(core.position);
  bodyGroup.add(coreGlow);

  // accent light so amber/violet read as clearly as cyan
  const accentLight = new THREE.PointLight(accent, 1.0, 2.0, 2);
  accentLight.position.set(0, 0.95, -0.62);
  bodyGroup.add(accentLight);

  // ---- shoulders ----
  for (const side of [-1, 1]) {
    bodyGroup.add(part(new THREE.SphereGeometry(0.07, 16, 16), plateMat, side * 0.235, 1.14, 0));
  }

  // ---- neck + head ----
  bodyGroup.add(part(new THREE.CylinderGeometry(0.055, 0.06, 0.09, 12), jointMat, 0, 1.28, 0));

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

  bodyGroup.add(headGroup);

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

    bodyGroup.add(shoulder);
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

    bodyGroup.add(hip);
  }

  // ---- console in front of the robot (unscaled, positioned relative to root) ----
  const consoleGroup = new THREE.Group();
  // Adjust console position slightly back to account for scaled body reaching forward
  consoleGroup.position.set(0, 0, -0.48);

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
    bodyGroup,
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
  scene.add(new THREE.AmbientLight(0x1a3040, 3.0));
  scene.add(new THREE.HemisphereLight(0x3a6486, 0x060c14, 1.3));

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
  const wallWashL = new THREE.PointLight(0x2f7fa8, 8.0, 10, 2);
  wallWashL.position.set(-5.0, 3.6, -4.2);
  scene.add(wallWashL);

  const wallWashR = new THREE.PointLight(0x2f7fa8, 8.0, 10, 2);
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
    camPos.set(Math.sin(t * 0.10) * 0.35, 2.20 + Math.sin(t * 0.07) * 0.04, 5.80);
    camTarget.set(0, 1.00, -1.35);
    camFov = 50;
  } else {
    // Portrait / tablet framing: pull back and widen slightly so the room
    // and all three agents stay readable inside a tall canvas.
    const cfg = CAMS[currentMode] ?? CAMS.spectator;
    const portrait = Math.max(0, Math.min(1, (1.15 - camera.aspect) / 0.6));
    camPos.set(cfg.pos.x, cfg.pos.y + portrait * 0.12, cfg.pos.z + portrait * 1.6);
    camFov = cfg.fov + portrait * 12;
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

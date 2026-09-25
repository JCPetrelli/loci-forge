// loci-forge web player: loads assets/<palace>/ exported by scripts/export_web.py.
// Open index.html?palace=<name> (default: archive).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { Input } from './input.js';
import { LociHints } from './loci.js';
import { Mannequin } from './mannequin.js';
import { buildWorld, Mover } from './physics.js';
import { Player } from './player.js';

const params = new URLSearchParams(location.search);
const palace = params.get('palace') || 'archive';
const base = `assets/${palace}/`;

const ui = {
  overlay: document.getElementById('overlay'),
  status: document.getElementById('status'),
  progress: document.getElementById('progress'),
  start: document.getElementById('start'),
  title: document.getElementById('title'),
};

// Blender (x, y, z) Z-up -> three (x, z, -y) Y-up
const fromBlender = ([x, y, z]) => new THREE.Vector3(x, z, -y);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0e0c0a);
scene.fog = new THREE.Fog(0x14110e, 14, 55);
scene.add(new THREE.HemisphereLight(0xffe0bd, 0x2b2119, 2.2));
const key = new THREE.DirectionalLight(0xffd7a8, 1.2);
key.position.set(-3, 8, 4);
scene.add(key);

const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.03, 200);
let lens = 24;

function fitCamera() {
  const aspect = innerWidth / innerHeight;
  // Blender's sensor fit AUTO: 36 mm across the larger side.
  const half = Math.atan(18 / lens);
  const vfov = aspect >= 1 ? 2 * Math.atan(Math.tan(half) / aspect) : 2 * half;
  camera.fov = THREE.MathUtils.radToDeg(vfov);
  camera.aspect = aspect;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}
addEventListener('resize', fitCamera);

const loadingManager = new THREE.LoadingManager();
loadingManager.onProgress = (_url, loaded, total) => {
  ui.progress.style.width = `${Math.round((loaded / total) * 100)}%`;
};
const draco = new DRACOLoader().setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/libs/draco/gltf/');
const loader = new GLTFLoader(loadingManager).setDRACOLoader(draco);

// Collision and glass come from glTF extras written by the exporter
// (userData.loci_nocollide, userData.loci_glass), not from names.
function preparePalace(root) {
  const colliders = [];
  root.traverse((obj) => {
    if (!obj.isMesh) return;
    const glass = obj.userData.loci_glass;
    if (glass) {
      obj.material = new THREE.MeshBasicMaterial({
        color: new THREE.Color().setRGB(...glass.color, THREE.LinearSRGBColorSpace),
        transparent: true,
        opacity: glass.opacity,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      obj.renderOrder = 1;
    } else {
      // Lighting is baked into the atlas: draw it as is.
      obj.material = new THREE.MeshBasicMaterial({ map: obj.material.map, side: THREE.DoubleSide });
    }
    if (!obj.userData.loci_nocollide) colliders.push(obj);
  });
  return colliders;
}

async function main() {
  // palace.json is always refetched; its export time versions the other assets,
  // so a re-export is never hidden behind the browser's cache.
  const info = await (await fetch(`${base}palace.json`, { cache: 'no-cache' })).json();
  const v = `?v=${encodeURIComponent(info.exported)}`;
  ui.title.textContent = info.palace;
  document.title = `${info.palace} · loci-forge`;
  lens = info.walker.lens;
  fitCamera();

  ui.status.textContent = 'Loading palace…';
  const [palaceGltf, mannequinGltf, hints] = await Promise.all([
    loader.loadAsync(`${base}palace.glb${v}`),
    loader.loadAsync(`${base}mannequin.glb${v}`),
    LociHints.load(`${base}loci.json`, fromBlender), // no-cache: edited by hand between exports
  ]);
  scene.add(palaceGltf.scene);
  if (hints) scene.add(hints.group);
  const colliders = preparePalace(palaceGltf.scene);

  ui.status.textContent = 'Building collision…';
  await new Promise((r) => setTimeout(r));
  const mover = new Mover(buildWorld(colliders), { height: info.walker.eye_height + 0.13 });

  const mannequin = new Mannequin(mannequinGltf.scene);
  scene.add(mannequin.root);
  const player = new Player({
    mannequin, mover, camera,
    settings: info.walker,
    spawn: fromBlender(info.spawn.location),
    yaw: info.spawn.yaw,
  });
  player.place();

  const input = new Input(renderer.domElement);
  window.loci = { player, input, mover, scene, camera, renderer, hints }; // for the console and tests
  ui.status.textContent = 'Ready';
  ui.start.hidden = false;
  ui.start.addEventListener('click', () => input.lock());

  // Only run the loop while walking; when paused, the last frame stays on screen.
  const clock = new THREE.Clock();
  const render = () => renderer.render(scene, camera);
  const loop = () => {
    if (hints && input.pressed.has('KeyL')) hints.toggle(); // read before player.update consumes it
    player.update(Math.min(clock.getDelta(), 0.05), input);
    hints?.update(clock.elapsedTime);
    render();
  };
  input.onLockChange = (locked) => {
    ui.overlay.classList.toggle('hidden', locked);
    ui.start.textContent = 'Click to continue';
    clock.getDelta();
    renderer.setAnimationLoop(locked ? loop : null);
  };
  addEventListener('resize', render);
  render();
}

main().catch((err) => {
  console.error(err);
  ui.status.textContent = `Could not load "${palace}": ${err.message}`;
});

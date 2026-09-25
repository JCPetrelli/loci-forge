// Loci hints: floating numbers over the places to hang images on, in walking
// order. Read from assets/<palace>/loci.json, copied there by the exporter
// from palaces/<palace>/loci.json. Toggled with L.
import * as THREE from 'three';

const SIZE = 0.42; // metres
const BOB = 0.06; // metres of float up and down

// Every fifth locus gets a golden hand and every tenth a "Decimus", as the
// Rhetorica ad Herennium (III.18) marks them, so the learner can count along.
const STYLES = {
  plain: { fill: 'rgba(20, 17, 14, 0.82)', ring: '#c9a36a', text: '#f3e6cf' },
  hand: { fill: '#c9a36a', ring: '#f3e6cf', text: '#1a140e' },
  decimus: { fill: '#4a1d4f', ring: '#c9a36a', text: '#f3e6cf', double: true },
};

function badge(n) {
  const kind = n % 10 === 0 ? 'decimus' : n % 5 === 0 ? 'hand' : 'plain';
  const style = STYLES[kind];
  const px = 128;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = px;
  const g = canvas.getContext('2d');
  g.beginPath();
  g.arc(px / 2, px / 2, px / 2 - 6, 0, Math.PI * 2);
  g.fillStyle = style.fill;
  g.fill();
  g.lineWidth = 6;
  g.strokeStyle = style.ring;
  g.stroke();
  if (style.double) {
    g.beginPath();
    g.arc(px / 2, px / 2, px / 2 - 16, 0, Math.PI * 2);
    g.lineWidth = 3;
    g.stroke();
  }
  g.fillStyle = style.text;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  let y = px / 2 + 4;
  if (kind === 'hand') {
    g.font = '30px "Apple Color Emoji", "Segoe UI Emoji", sans-serif';
    g.fillText('\u270B', px / 2, 34);
    y = px / 2 + 18;
  }
  g.font = `${kind === 'hand' ? 52 : n > 9 ? 56 : 66}px Georgia, "Times New Roman", serif`;
  g.fillText(String(n), px / 2, y);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

export class LociHints {
  // `fromBlender` maps a Blender [x, y, z] to a three.js Vector3.
  constructor(loci, fromBlender) {
    this.group = new THREE.Group();
    this.group.visible = false;
    this.markers = loci.map((locus, i) => {
      const map = badge(i + 1);
      // Two sprites per number: a solid one hidden by walls, and a faint one
      // drawn through them, so the whole route stays readable from anywhere.
      const front = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false }));
      const behind = new THREE.Sprite(new THREE.SpriteMaterial({ map, transparent: true, opacity: 0.22, depthTest: false, depthWrite: false }));
      const marker = new THREE.Group();
      behind.renderOrder = 2;
      front.renderOrder = 3;
      for (const sprite of [behind, front]) {
        sprite.scale.setScalar(SIZE);
        marker.add(sprite);
      }
      marker.position.copy(fromBlender(locus.at));
      marker.userData = { base: marker.position.y, label: locus.label, n: i + 1 };
      this.group.add(marker);
      return marker;
    });
  }

  static async load(url, fromBlender) {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) return null; // a palace without loci
    return new LociHints((await res.json()).loci, fromBlender);
  }

  get visible() { return this.group.visible; }

  toggle() {
    this.group.visible = !this.group.visible;
    return this.group.visible;
  }

  update(time) {
    if (!this.group.visible) return;
    for (const m of this.markers) m.position.y = m.userData.base + Math.sin(time * 1.6 + m.userData.n * 0.7) * BOB;
  }
}

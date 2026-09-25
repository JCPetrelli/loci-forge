// The wooden mannequin exported from Blender: parts named Loci_<role>, each with
// its origin at its joint. The walk cycle is a port of
// scripts/loci_walker/character.py `animate`. Blender's Z-up axes map to three's
// as X -> x, Y -> -z, Z -> y, so a Blender rotation (x, y, z) becomes (x, z, -y)
// applied in 'YZX' order.
import * as THREE from 'three';

const HIP_HEIGHT = 0.93;
const JOINT_ROLES = new Set(['neck']);

export class Mannequin {
  constructor(gltfScene) {
    this.root = gltfScene.getObjectByName('Loci_Player') || gltfScene;
    this.parts = {};
    const wood = new THREE.MeshStandardMaterial({ color: 0xc49a6c, roughness: 0.55 });
    const joint = new THREE.MeshStandardMaterial({ color: 0x5e3b22, roughness: 0.5 });
    this.root.traverse((obj) => {
      const match = /^Loci_(.+)$/.exec(obj.name);
      if (!match || obj === this.root) return;
      const role = match[1];
      this.parts[role] = this.parts[role] || obj;
      // Blender applies XYZ Euler as X, then Y, then Z. With its Y and Z axes
      // mapped to three's -Z and Y, that same order is three's 'YZX'.
      obj.rotation.order = 'YZX';
      if (obj.isMesh) {
        obj.material = JOINT_ROLES.has(role) ? joint : wood;
        obj.castShadow = false;
      }
    });
    this.root.position.set(0, 0, 0);
    this.root.rotation.set(0, 0, 0);
  }

  setVisible(visible) {
    this.root.visible = visible;
  }

  rot(role, [x, y, z]) {
    const part = this.parts[role];
    if (part) part.rotation.set(x, z, -y);
  }

  // Mirrors pose() in scripts/loci_walker/character.py; keep the two in step.
  // phase: walk cycle (radians); amount: 0 standing .. 1 full stride;
  // air: 0 grounded .. 1 airborne; rise: 1 going up .. 0 coming down;
  // land: 0..1 crouch right after touching down.
  animate(phase, amount, air = 0, rise = 0, land = 0) {
    const s = Math.sin(phase);
    const c = Math.cos(phase);
    const a = amount * (1 - air);
    const tuck = air * rise;
    const reach = air * (1 - rise);
    for (const [side, sign, offset] of [['l', 1, 0], ['r', -1, Math.PI]]) {
      const sw = Math.sin(phase + offset);
      const lift = Math.max(0, Math.cos(phase + offset));
      const stagger = 0.12 * sign * air;
      this.rot(`thigh_${side}`, [0.5 * sw * a + 0.75 * tuck + 0.3 * reach + stagger + 0.55 * land, 0, 0]);
      this.rot(`shin_${side}`, [-(0.1 + 0.9 * lift) * a - 1.25 * tuck - 0.35 * reach - 1.1 * land, 0, 0]);
      this.rot(`foot_${side}`, [(0.25 * lift - 0.1 * sw) * a + 0.35 * tuck + 0.15 * reach + 0.5 * land, 0, 0]);
      this.rot(`upper_arm_${side}`, [-0.45 * sw * a + 1.3 * tuck + 0.5 * reach + 0.25 * land,
        (0.1 + 0.3 * air + 0.15 * land) * sign, 0]);
      this.rot(`forearm_${side}`, [0.15 + 0.35 * a * Math.max(0, -sw) + 0.45 * tuck + 0.2 * reach, 0, 0]);
      this.rot(`hand_${side}`, [0, 0, 0]);
    }
    this.rot('pelvis', [0, 0.04 * c * a, 0.12 * s * a]);
    this.rot('chest', [-(0.06 * a + 0.2 * tuck - 0.08 * reach + 0.3 * land), 0, -0.2 * s * a]);
    this.rot('neck', [0, 0, 0.08 * s * a]);
    this.rot('head', [0.04 * a + 0.12 * tuck + 0.15 * land, 0, 0]);
    const pelvis = this.parts.pelvis;
    if (pelvis) pelvis.position.y = HIP_HEIGHT - 0.035 * a * Math.abs(s) - 0.12 * land;
  }
}

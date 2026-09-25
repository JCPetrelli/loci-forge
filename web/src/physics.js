// Collision world and character movement: a port of scripts/loci_walker/physics.py
// to three.js (Y up). A stack of spheres above the step height pushes the body
// out of walls; a downward ray finds the ground, climbs steps and follows ramps.
import * as THREE from 'three';
import { MeshBVH } from 'three-mesh-bvh';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const UP = new THREE.Vector3(0, 1, 0);
const DOWN = new THREE.Vector3(0, -1, 0);
const GROUND_SNAP = 0.3;

export function buildWorld(meshes) {
  const parts = meshes.map((mesh) => {
    mesh.updateWorldMatrix(true, false);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', mesh.geometry.getAttribute('position').clone());
    if (mesh.geometry.index) g.setIndex(mesh.geometry.index.clone());
    return g.applyMatrix4(mesh.matrixWorld);
  });
  // mergeGeometries needs all parts indexed, or none.
  const uniform = parts.every((g) => g.index) ? parts : parts.map((g) => (g.index ? g.toNonIndexed() : g));
  return new MeshBVH(mergeGeometries(uniform));
}

export class Mover {
  constructor(bvh, { radius = 0.3, height = 1.75, stepHeight = 0.35 } = {}) {
    this.bvh = bvh;
    this.radius = radius;
    this.height = height;
    this.stepHeight = stepHeight;
    this.samples = [];
    for (let h = stepHeight + radius; h < height - radius; h += radius) this.samples.push(h);
    this.samples.push(height - radius);
    this._ray = new THREE.Ray();
    this._hit = {};
    this._center = new THREE.Vector3();
    this._away = new THREE.Vector3();
    this._delta = new THREE.Vector3();
    this._probe = new THREE.Vector3();
    this.result = { pos: new THREE.Vector3(), vy: 0, grounded: false };
  }

  // Advance one tick. Returns this.result ({ pos, vy, grounded }), reused every call.
  move(pos, velocity, vy, dt, gravity, grounded) {
    const out = this.result;
    const p = out.pos.copy(pos);
    const delta = this._delta.set(velocity.x, 0, velocity.z).multiplyScalar(dt);
    const steps = Math.floor(delta.length() / (this.radius * 0.5)) + 1;
    delta.divideScalar(steps);
    for (let i = 0; i < steps; i++) {
      p.add(delta);
      this.pushOut(p);
    }

    vy -= gravity * dt;
    if (vy > 0 && this.ray(this._probe.copy(p).addScaledVector(UP, this.height - 0.05), UP, vy * dt + 0.05) !== null) vy = 0;
    p.y += vy * dt;

    const fall = Math.max(0, -vy * dt);
    const origin = this._probe.copy(p);
    origin.y += fall + this.stepHeight;
    const hit = this.cast(origin, DOWN, fall + this.stepHeight + GROUND_SNAP);
    const snap = grounded ? GROUND_SNAP : 0;
    if (hit && vy <= 0 && p.y <= hit.point.y + snap) {
      p.y = hit.point.y;
      out.vy = 0;
      out.grounded = true;
    } else {
      out.vy = vy;
      out.grounded = false;
    }
    return out;
  }

  cast(origin, direction, far) {
    this._ray.set(origin, direction);
    const hit = this.bvh.raycastFirst(this._ray, THREE.DoubleSide, 0, far);
    return hit && hit.distance <= far ? hit : null;
  }

  // Distance to the first hit along the ray, or null.
  ray(origin, direction, far) {
    const hit = this.cast(origin, direction, far);
    return hit ? hit.distance : null;
  }

  pushOut(p) {
    const r = this.radius;
    for (let iter = 0; iter < 3; iter++) {
      let moved = false;
      for (const h of this.samples) {
        this._center.set(p.x, p.y + h, p.z);
        const hit = this.bvh.closestPointToPoint(this._center, this._hit, 0, r);
        if (!hit || hit.distance >= r) continue;
        this._away.subVectors(this._center, hit.point);
        if (this._away.lengthSq() < 1e-12) continue;
        this._away.normalize().multiplyScalar(r - hit.distance + 1e-3);
        this._away.y = 0;
        if (this._away.lengthSq() > 1e-12) {
          p.add(this._away);
          moved = true;
        }
      }
      if (!moved) return;
    }
  }
}

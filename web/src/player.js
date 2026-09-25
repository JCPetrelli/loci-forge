// The walker: movement, facing, walk cycle and first/third-person camera.
// A port of scripts/loci_walker/controller.py. Yaw 0 looks along -Z (Blender +Y).
import * as THREE from 'three';

const PITCH_LIMIT = THREE.MathUtils.degToRad(80);
const FALL_LIMIT = 50;
const CAMERA_MARGIN = 0.2;

// Scratch vectors, reused every frame.
const _forward = new THREE.Vector3();
const _right = new THREE.Vector3();
const _wish = new THREE.Vector3();
const _back = new THREE.Vector3();
const forward = (yaw, out = _forward) => out.set(-Math.sin(yaw), 0, -Math.cos(yaw));
const right = (yaw, out = _right) => out.set(Math.cos(yaw), 0, -Math.sin(yaw));

function turnTowards(current, target, t) {
  const diff = ((target - current + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  return current + diff * t;
}

export class Player {
  constructor({ mannequin, mover, camera, settings, spawn, yaw }) {
    this.mannequin = mannequin;
    this.mover = mover;
    this.camera = camera;
    this.s = settings;
    this.spawn = spawn.clone();
    this.pos = spawn.clone();
    this.yaw = yaw;
    this.facing = yaw;
    this.pitch = -0.15;
    this.vy = 0;
    this.grounded = false;
    this.phase = 0;
    this.stride = 0;
    this.air = 0;
    this.rise = 0;
    this.land = 0;
    this.third = settings.third_person;
    this.distance = settings.third_person_distance;
    this.pivot = new THREE.Vector3();
    this.mannequin.setVisible(this.third);
  }

  // Pose the mannequin and camera without advancing time (before the first frame).
  place() {
    this.mannequin.root.position.copy(this.pos);
    this.mannequin.root.rotation.set(0, this.facing, 0);
    this.mannequin.animate(0, 0);
    this.updateCamera();
  }

  update(dt, input) {
    const s = this.s;
    const { look, wheel, pressed } = input.consume();
    const sens = s.mouse_sensitivity;
    this.yaw -= look.x * sens;
    this.pitch = THREE.MathUtils.clamp(this.pitch - look.y * sens, -PITCH_LIMIT, PITCH_LIMIT);
    if (wheel) this.distance = THREE.MathUtils.clamp(this.distance * (wheel > 0 ? 1.1 : 0.9), 0.5, 12);
    if (pressed.has('KeyV')) {
      this.third = !this.third;
      this.mannequin.setVisible(this.third);
    }
    if (pressed.has('Space') && this.grounded) {
      this.vy = s.jump_speed;
      this.grounded = false;
    }

    const { x, y } = input.axis();
    const wish = _wish.copy(right(this.yaw)).multiplyScalar(x).addScaledVector(forward(this.yaw), y);
    const moving = wish.lengthSq() > 1e-6;
    if (moving) wish.normalize();
    const running = input.running();
    const speed = s.walk_speed * (running ? s.run_multiplier : 1);

    const wasGrounded = this.grounded;
    const fallSpeed = -this.vy;
    const r = this.mover.move(this.pos, wish.multiplyScalar(speed), this.vy, dt, s.gravity, this.grounded);
    this.pos.copy(r.pos);
    this.vy = r.vy;
    this.grounded = r.grounded;
    if (this.pos.y < this.spawn.y - FALL_LIMIT) {
      this.pos.copy(this.spawn);
      this.vy = 0;
    }

    if (!this.third) this.facing = this.yaw;
    else if (moving) this.facing = turnTowards(this.facing, Math.atan2(-wish.x, -wish.z), Math.min(1, dt * 12));

    const walking = moving && this.grounded;
    this.stride += ((walking ? 1 : 0) - this.stride) * Math.min(1, dt * 10);
    if (walking) this.phase += dt * speed * 3.2;
    this.air += ((this.grounded ? 0 : 1) - this.air) * Math.min(1, dt * 14);
    this.rise += ((this.vy > 0 ? 1 : 0) - this.rise) * Math.min(1, dt * 8);
    if (this.grounded && !wasGrounded && fallSpeed > 1) this.land = Math.min(1, fallSpeed / 6);
    this.land = Math.max(0, this.land - dt * 4);

    const root = this.mannequin.root;
    root.position.copy(this.pos);
    root.rotation.set(0, this.facing, 0);
    this.mannequin.animate(this.phase, this.stride * (running ? 1.3 : 1), this.air, this.rise, this.land);
    this.updateCamera();
  }

  updateCamera() {
    const cam = this.camera;
    cam.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
    if (!this.third) {
      cam.position.set(this.pos.x, this.pos.y + this.s.eye_height, this.pos.z);
      return;
    }
    const pivot = this.pivot.copy(this.pos).addScaledVector(right(this.yaw), 0.35);
    pivot.y += this.s.eye_height * 0.95;
    const back = _back.set(0, 0, 1).applyEuler(cam.rotation);
    let d = this.distance;
    const hit = this.mover.ray(pivot, back, d + CAMERA_MARGIN);
    if (hit !== null) d = Math.max(CAMERA_MARGIN, hit - CAMERA_MARGIN);
    cam.position.copy(pivot).addScaledVector(back, d);
  }
}

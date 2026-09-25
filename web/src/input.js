// Keyboard state and pointer-lock mouse look.
const MOVE = {
  KeyW: [0, 1], ArrowUp: [0, 1],
  KeyS: [0, -1], ArrowDown: [0, -1],
  KeyA: [-1, 0], ArrowLeft: [-1, 0],
  KeyD: [1, 0], ArrowRight: [1, 0],
};

export class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.keys = new Set();
    this.look = { x: 0, y: 0 };
    this.wheel = 0;
    this.pressed = new Set(); // keys pressed since the last frame
    this.frame = { look: { x: 0, y: 0 }, wheel: 0, pressed: new Set() };
    this.move = { x: 0, y: 0 };
    this.locked = false;

    addEventListener('keydown', (e) => {
      if (!this.locked) return;
      if (!e.repeat) this.pressed.add(e.code);
      this.keys.add(e.code);
      if (e.code.startsWith('Arrow') || e.code === 'Space') e.preventDefault();
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    addEventListener('mousemove', (e) => {
      if (!this.locked) return;
      this.look.x += e.movementX;
      this.look.y += e.movementY;
    });
    addEventListener('wheel', (e) => { if (this.locked) this.wheel += Math.sign(e.deltaY); }, { passive: true });
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === canvas;
      if (!this.locked) this.keys.clear();
      this.onLockChange?.(this.locked);
    });
  }

  lock() {
    this.canvas.requestPointerLock();
  }

  axis() {
    this.move.x = this.move.y = 0;
    for (const k of this.keys) {
      if (MOVE[k]) { this.move.x += MOVE[k][0]; this.move.y += MOVE[k][1]; }
    }
    return this.move;
  }

  running() {
    return this.keys.has('ShiftLeft') || this.keys.has('ShiftRight');
  }

  // Hand over this frame's accumulated input and start a fresh one.
  // The returned object is reused: read it before the next call.
  consume() {
    const f = this.frame;
    f.look.x = this.look.x; f.look.y = this.look.y;
    f.wheel = this.wheel;
    [f.pressed, this.pressed] = [this.pressed, f.pressed];
    this.pressed.clear();
    this.look.x = this.look.y = 0;
    this.wheel = 0;
    return f;
  }
}

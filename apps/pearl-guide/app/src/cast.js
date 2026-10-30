import { Quaternion, Vector3 } from 'three';

const Y = new Vector3(0, 1, 0);
const q = new Quaternion();

// Everything the story moves is an Actor: a scene object with a remembered rest pose and its own materials,
// so it can fade without fading its twins. The story resets every actor and re-poses it each frame.

export class Actor {
  constructor(name, obj, { own = true, shown = false } = {}) {
    this.name = name;
    this.obj = obj;
    this.shown = shown; // child parts of a bigger actor are visible whenever their parent is
    this.base = { p: obj.position.clone(), q: obj.quaternion.clone(), s: obj.scale.clone() };
    this.mats = [];
    if (own) {
      obj.traverse((o) => {
        if (!o.isMesh) return;
        o.material = Array.isArray(o.material) ? o.material.map((m) => this.adopt(m)) : this.adopt(o.material);
      });
    }
    this.alpha = 1;
    obj.visible = shown;
  }

  adopt(m) {
    const c = m.clone();
    c.userData.baseOpacity = m.opacity;
    c.userData.baseTransparent = m.transparent;
    this.mats.push(c);
    return c;
  }

  reset() {
    const o = this.obj;
    o.visible = this.shown;
    o.position.copy(this.base.p);
    o.quaternion.copy(this.base.q);
    o.scale.copy(this.base.s);
    if (this.alpha !== 1) this.fade(1);
  }

  fade(a) {
    this.alpha = a;
    for (const m of this.mats) {
      const transparent = a < 0.999 || m.userData.baseTransparent;
      if (m.transparent !== transparent) {
        m.transparent = transparent;
        m.needsUpdate = true;
      }
      m.opacity = m.userData.baseOpacity * a;
      m.depthWrite = m.userData.baseTransparent ? false : a > 0.6;
    }
    return this;
  }

  /** Show at opacity a (0 hides). */
  show(a = 1) {
    this.obj.visible = a > 0.004;
    if (a !== this.alpha) this.fade(a);
    return this;
  }

  at(x, y, z) {
    this.obj.position.set(x, y, z);
    return this;
  }

  /** Yaw ry, then pitch rx, then roll rz about the local axes (radians). */
  turn(ry = 0, rx = 0, rz = 0) {
    this.obj.rotation.set(rx, ry, rz, 'YXZ');
    return this;
  }

  /** Turn about the model's own y axis from its rest pose (propeller hubs: y is the shaft). */
  spin(angle) {
    this.obj.quaternion.copy(this.base.q).multiply(q.setFromAxisAngle(Y, angle));
    return this;
  }

  size(s) {
    if (typeof s === 'number') this.obj.scale.setScalar(s);
    else this.obj.scale.set(s[0], s[1], s[2]);
    return this;
  }
}

export class Cast {
  constructor(root) {
    this.root = root;
    this.map = new Map();
  }

  add(name, obj, opts) {
    obj.removeFromParent();
    this.root.add(obj);
    return this.wrap(name, obj, opts);
  }

  /** Register an object that stays where it is in the scene graph. */
  wrap(name, obj, opts) {
    if (this.map.has(name)) throw new Error(`actor ${name} exists`);
    const a = new Actor(name, obj, opts);
    this.map.set(name, a);
    return a;
  }

  /** A named part inside an actor's model: moves with it, fades with it. */
  part(name, parent, nodeName = name) {
    const node = this.get(parent).obj.getObjectByName(nodeName);
    if (!node) throw new Error(`no ${nodeName} in ${parent}`);
    return this.wrap(name, node, { own: false, shown: true });
  }

  get(name) {
    const a = this.map.get(name);
    if (!a) throw new Error(`no actor ${name}`);
    return a;
  }

  has(name) {
    return this.map.has(name);
  }

  reset() {
    for (const a of this.map.values()) a.reset();
  }
}

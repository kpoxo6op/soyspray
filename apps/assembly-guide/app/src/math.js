// Small vector and quaternion helpers used by the timeline. Quaternions are [x, y, z, w].

export const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
export const lerp = (a, b, t) => a + (b - a) * t;

export function lerp3(a, b, t, out = [0, 0, 0]) {
  out[0] = a[0] + (b[0] - a[0]) * t;
  out[1] = a[1] + (b[1] - a[1]) * t;
  out[2] = a[2] + (b[2] - a[2]) * t;
  return out;
}

export function add3(a, b, out = [0, 0, 0]) {
  out[0] = a[0] + b[0];
  out[1] = a[1] + b[1];
  out[2] = a[2] + b[2];
  return out;
}

export function scale3(a, s, out = [0, 0, 0]) {
  out[0] = a[0] * s;
  out[1] = a[1] * s;
  out[2] = a[2] * s;
  return out;
}

export function sub3(a, b, out = [0, 0, 0]) {
  out[0] = a[0] - b[0];
  out[1] = a[1] - b[1];
  out[2] = a[2] - b[2];
  return out;
}

export const dot3 = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const len3 = (a) => Math.hypot(a[0], a[1], a[2]);
export const dist3 = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);

export function cross3(a, b, out = [0, 0, 0]) {
  const x = a[1] * b[2] - a[2] * b[1];
  const y = a[2] * b[0] - a[0] * b[2];
  const z = a[0] * b[1] - a[1] * b[0];
  out[0] = x;
  out[1] = y;
  out[2] = z;
  return out;
}

export function normalize3(a, out = [0, 0, 0]) {
  const l = len3(a) || 1;
  out[0] = a[0] / l;
  out[1] = a[1] / l;
  out[2] = a[2] / l;
  return out;
}

/** Quaternion of the rotation taking local +y onto `y` and local +z onto `z` (made orthogonal). */
export function basisQuat(y, z) {
  const Y = normalize3(y);
  const X = normalize3(cross3(Y, z));
  const Z = cross3(X, Y);
  // rotation matrix columns X, Y, Z -> quaternion
  const m00 = X[0], m01 = Y[0], m02 = Z[0];
  const m10 = X[1], m11 = Y[1], m12 = Z[1];
  const m20 = X[2], m21 = Y[2], m22 = Z[2];
  const tr = m00 + m11 + m22;
  let q;
  if (tr > 0) {
    const s = Math.sqrt(tr + 1) * 2;
    q = [(m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s];
  } else if (m00 > m11 && m00 > m22) {
    const s = Math.sqrt(1 + m00 - m11 - m22) * 2;
    q = [0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s];
  } else if (m11 > m22) {
    const s = Math.sqrt(1 + m11 - m00 - m22) * 2;
    q = [(m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s];
  } else {
    const s = Math.sqrt(1 + m22 - m00 - m11) * 2;
    q = [(m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s];
  }
  return qnormalize(q);
}

export function qnormalize(q, out = [0, 0, 0, 1]) {
  const l = Math.hypot(q[0], q[1], q[2], q[3]) || 1;
  out[0] = q[0] / l;
  out[1] = q[1] / l;
  out[2] = q[2] / l;
  out[3] = q[3] / l;
  return out;
}

export function qmul(a, b, out = [0, 0, 0, 1]) {
  const [ax, ay, az, aw] = a;
  const [bx, by, bz, bw] = b;
  out[0] = ax * bw + aw * bx + ay * bz - az * by;
  out[1] = ay * bw + aw * by + az * bx - ax * bz;
  out[2] = az * bw + aw * bz + ax * by - ay * bx;
  out[3] = aw * bw - ax * bx - ay * by - az * bz;
  return out;
}

export function qaxis(axis, angle) {
  const s = Math.sin(angle / 2);
  const l = Math.hypot(axis[0], axis[1], axis[2]) || 1;
  return [(axis[0] / l) * s, (axis[1] / l) * s, (axis[2] / l) * s, Math.cos(angle / 2)];
}

export function qrotate(q, v, out = [0, 0, 0]) {
  const [x, y, z, w] = q;
  const [vx, vy, vz] = v;
  const tx = 2 * (y * vz - z * vy);
  const ty = 2 * (z * vx - x * vz);
  const tz = 2 * (x * vy - y * vx);
  out[0] = vx + w * tx + (y * tz - z * ty);
  out[1] = vy + w * ty + (z * tx - x * tz);
  out[2] = vz + w * tz + (x * ty - y * tx);
  return out;
}

// Rotation taking unit vector a onto unit vector b.
export function qfromTo(a, b) {
  const d = a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  if (d < -0.999999) {
    const ortho = Math.abs(a[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0];
    const ax = [a[1] * ortho[2] - a[2] * ortho[1], a[2] * ortho[0] - a[0] * ortho[2], a[0] * ortho[1] - a[1] * ortho[0]];
    return qaxis(ax, Math.PI);
  }
  const c = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  return qnormalize([c[0], c[1], c[2], 1 + d]);
}

export function slerp(a, b, t, out = [0, 0, 0, 1]) {
  let bx = b[0], by = b[1], bz = b[2], bw = b[3];
  let cos = a[0] * bx + a[1] * by + a[2] * bz + a[3] * bw;
  if (cos < 0) {
    cos = -cos;
    bx = -bx; by = -by; bz = -bz; bw = -bw;
  }
  let k0, k1;
  if (cos > 0.9995) {
    k0 = 1 - t;
    k1 = t;
  } else {
    const theta = Math.acos(cos);
    const s = Math.sin(theta);
    k0 = Math.sin((1 - t) * theta) / s;
    k1 = Math.sin(t * theta) / s;
  }
  out[0] = a[0] * k0 + bx * k1;
  out[1] = a[1] * k0 + by * k1;
  out[2] = a[2] * k0 + bz * k1;
  out[3] = a[3] * k0 + bw * k1;
  return qnormalize(out, out);
}

// Easing curves, all mapping [0, 1] onto [0, 1].
export const EASE = {
  linear: (t) => t,
  inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  out: (t) => 1 - Math.pow(1 - t, 3),
  in: (t) => t * t * t,
  smooth: (t) => t * t * (3 - 2 * t),
  // Gentle settle for the last few millimetres of an insertion.
  settle: (t) => 1 - Math.pow(1 - t, 2.2),
};

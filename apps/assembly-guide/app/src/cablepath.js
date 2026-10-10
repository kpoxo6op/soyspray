// Pure cable centreline geometry (no three.js), shared by the timeline, the renderer and tests.
//
// Every cable is laid out as   A lead -> slack coil -> route B,   with plug B travelling along
// route B while the cable pays out of the coil. The coil's (fractional) number of turns is
// solved so the drawn centreline always keeps the cable's real length: a stock lead keeps its
// spare in the coil, a custom-crimped Ethernet lead ends with no turns left.

import { add3, sub3, scale3, dot3, len3, normalize3, cross3, qfromTo, qrotate, lerp3 } from './math.js';

// ---------------------------------------------------------------- polylines

export function cumulative(pts) {
  const cum = new Float64Array(pts.length);
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1];
    const b = pts[i];
    cum[i] = cum[i - 1] + Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  }
  return cum;
}

export function polyLength(pts) {
  let l = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1];
    const b = pts[i];
    l += Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  }
  return l;
}

function locate(cum, s) {
  const n = cum.length;
  if (s <= 0) return [0, 0];
  if (s >= cum[n - 1]) return [n - 2, 1];
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (cum[mid] <= s) lo = mid;
    else hi = mid;
  }
  const span = cum[hi] - cum[lo];
  return [lo, span > 0 ? (s - cum[lo]) / span : 0];
}

export function pointAt(pts, cum, s) {
  if (pts.length === 1) return [...pts[0]];
  const [i, f] = locate(cum, s);
  const a = pts[i];
  const b = pts[i + 1];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

export function tangentAt(pts, cum, s) {
  const total = cum[cum.length - 1];
  return normalize3(sub3(pointAt(pts, cum, Math.min(total, s + 2)), pointAt(pts, cum, Math.max(0, s - 2))));
}

/** The part of a polyline between arclengths s0 and s1, with exact cut points. */
export function slice(pts, cum, s0, s1) {
  const total = cum[cum.length - 1];
  s0 = Math.max(0, Math.min(total, s0));
  s1 = Math.max(s0, Math.min(total, s1));
  const out = [pointAt(pts, cum, s0)];
  for (let i = 0; i < pts.length; i++) if (cum[i] > s0 + 1e-6 && cum[i] < s1 - 1e-6) out.push(pts[i]);
  out.push(pointAt(pts, cum, s1));
  return out;
}

/** n points evenly spaced along the polyline's length. */
export function resample(pts, n, out = []) {
  const cum = cumulative(pts);
  const total = cum[cum.length - 1];
  let j = 0;
  for (let k = 0; k < n; k++) {
    const s = (total * k) / (n - 1);
    while (j < pts.length - 2 && cum[j + 1] < s) j++;
    const span = cum[j + 1] - cum[j];
    const f = span > 0 ? Math.min(1, Math.max(0, (s - cum[j]) / span)) : 0;
    const a = pts[j];
    const b = pts[j + 1] || a;
    const o = out[k] || (out[k] = [0, 0, 0]);
    o[0] = a[0] + (b[0] - a[0]) * f;
    o[1] = a[1] + (b[1] - a[1]) * f;
    o[2] = a[2] + (b[2] - a[2]) * f;
  }
  out.length = n;
  return out;
}

// ---------------------------------------------------------------- curves

/**
 * Dense centripetal Catmull-Rom curve through `ctrl`. Optional start/end directions add phantom
 * points so the curve leaves and arrives along those directions.
 */
export function spline(ctrl, { startDir = null, endDir = null, step = 3 } = {}) {
  const n = ctrl.length;
  if (n < 2) return ctrl.map((p) => [...p]);
  const first = startDir
    ? sub3(ctrl[0], scale3(normalize3(startDir), Math.max(8, len3(sub3(ctrl[1], ctrl[0])))))
    : sub3(scale3(ctrl[0], 2), ctrl[1]);
  const last = endDir
    ? add3(ctrl[n - 1], scale3(normalize3(endDir), Math.max(8, len3(sub3(ctrl[n - 1], ctrl[n - 2])))))
    : sub3(scale3(ctrl[n - 1], 2), ctrl[n - 2]);
  const P = [first, ...ctrl, last];
  const out = [[...ctrl[0]]];
  for (let i = 1; i < P.length - 2; i++) {
    const p0 = P[i - 1];
    const p1 = P[i];
    const p2 = P[i + 1];
    const p3 = P[i + 2];
    const t01 = Math.pow(len3(sub3(p1, p0)) || 1e-3, 0.5);
    const t12 = Math.pow(len3(sub3(p2, p1)) || 1e-3, 0.5);
    const t23 = Math.pow(len3(sub3(p3, p2)) || 1e-3, 0.5);
    // tangents (Barry-Goldman form for centripetal Catmull-Rom)
    const m1 = [0, 0, 0];
    const m2 = [0, 0, 0];
    for (let k = 0; k < 3; k++) {
      m1[k] = t12 * ((p1[k] - p0[k]) / t01 - (p2[k] - p0[k]) / (t01 + t12) + (p2[k] - p1[k]) / t12);
      m2[k] = t12 * ((p2[k] - p1[k]) / t12 - (p3[k] - p1[k]) / (t12 + t23) + (p3[k] - p2[k]) / t23);
    }
    const segLen = len3(sub3(p2, p1));
    if (i === 1 && startDir) m1.splice(0, 3, ...scale3(normalize3(startDir), segLen));
    if (i === P.length - 3 && endDir) m2.splice(0, 3, ...scale3(normalize3(endDir), segLen));
    const steps = Math.max(2, Math.ceil(segLen / step));
    for (let s = 1; s <= steps; s++) {
      const t = s / steps;
      const t2 = t * t;
      const t3 = t2 * t;
      const h00 = 2 * t3 - 3 * t2 + 1;
      const h10 = t3 - 2 * t2 + t;
      const h01 = -2 * t3 + 3 * t2;
      const h11 = t3 - t2;
      out.push([0, 1, 2].map((k) => h00 * p1[k] + h10 * m1[k] + h01 * p2[k] + h11 * m2[k]));
    }
  }
  return out;
}

/** Cubic Hermite join from a (leaving along da) to b (arriving along db). */
export function hermite(a, da, b, db, step = 3) {
  const d = len3(sub3(b, a));
  const k = Math.max(4, d * 0.55);
  const m1 = scale3(normalize3(da), k);
  const m2 = scale3(normalize3(db), k);
  const steps = Math.max(2, Math.ceil(d / step));
  const out = [];
  for (let s = 0; s <= steps; s++) {
    const t = s / steps;
    const t2 = t * t;
    const t3 = t2 * t;
    const h00 = 2 * t3 - 3 * t2 + 1;
    const h10 = t3 - 2 * t2 + t;
    const h01 = -2 * t3 + 3 * t2;
    const h11 = t3 - t2;
    out.push([0, 1, 2].map((i) => h00 * a[i] + h10 * m1[i] + h01 * b[i] + h11 * m2[i]));
  }
  return out;
}

// ---------------------------------------------------------------- coils

/**
 * Elliptical helix through a fixed entry point:
 *   P(th) = centre + U a cos th + V b sin th + AX pitch (th - th0) / 2pi,
 * with the centre placed so that P(th0) is always `entry`, whatever the semi-axes.
 */
export function coilPoint(c, th, a, b) {
  const { entry, U, V, AX, pitch, theta0 } = c;
  const c0 = Math.cos(theta0);
  const s0 = Math.sin(theta0);
  const ca = Math.cos(th);
  const sa = Math.sin(th);
  const h = (pitch * (th - theta0)) / (2 * Math.PI);
  return [0, 1, 2].map((k) => entry[k] + U[k] * a * (ca - c0) + V[k] * b * (sa - s0) + AX[k] * h);
}

function coilTangent(c, th, a, b) {
  const { U, V, AX, pitch } = c;
  return normalize3([0, 1, 2].map((k) => -U[k] * a * Math.sin(th) + V[k] * b * Math.cos(th) + (AX[k] * pitch) / (2 * Math.PI)));
}

export function coilTurnLength(a, b, pitch) {
  const h = ((a - b) * (a - b)) / ((a + b) * (a + b));
  const ellipse = Math.PI * (a + b) * (1 + (3 * h) / (10 + Math.sqrt(4 - 3 * h)));
  return Math.hypot(ellipse, pitch);
}

export function coilPoints(c, turns, a, b, segsPerTurn = 28) {
  const n = Math.max(1, Math.ceil(turns * segsPerTurn));
  const out = [];
  for (let i = 0; i <= n; i++) out.push(coilPoint(c, c.theta0 + (2 * Math.PI * turns * i) / n, a, b));
  return out;
}

// ---------------------------------------------------------------- whole cable

/** Coil semi-axes for a dress value (0 = as laid, 1 = tightened). */
function coilAxes(coil, dress) {
  const t = Math.max(0, Math.min(1, dress));
  const a = coil.a + (coil.aTight - coil.a) * t;
  const b = coil.b + (coil.bTight - coil.b) * t;
  return [a, b];
}

/**
 * Centreline of a cable for a state { sA, sB, dress }:
 *   sA    how far plug A's exit sits back along the A lead (0 = seated),
 *   sB    how far plug B has travelled along route B (routeLen = seated),
 *   dress coil tightening 0..1.
 * Returns { points, turns, length }.
 */
export function cableCentreline(cab, state) {
  const { aLead, aCum, routeB, routeCum, coil, length } = cab;
  const aPart = slice(aLead, aCum, state.sA, aCum[aCum.length - 1]);
  const routeLen = routeCum[routeCum.length - 1];
  const sB = Math.max(0, Math.min(routeLen, state.sB));
  const bPart = sB > 0.01 ? slice(routeB, routeCum, 0, sB) : [routeB[0]];
  const [a, b] = coilAxes(coil, state.dress);
  const per = coilTurnLength(a, b, coil.pitch);
  const startDir = tangentAt(routeB, routeCum, 0);
  const lead = polyLength(aPart);
  const tail = polyLength(bPart);
  function at(turns) {
    const coilPts = coilPoints(coil, turns, a, b);
    const thEnd = coil.theta0 + 2 * Math.PI * turns;
    const exit = coilPts[coilPts.length - 1];
    const join = hermite(exit, coilTangent(coil, thEnd, a, b), bPart[0], startDir);
    const joinLen = polyLength(join);
    const coilLen = polyLength(coilPts);
    return { points: [...aPart, ...coilPts.slice(1), ...join.slice(1), ...bPart.slice(1)], turns,
      length: lead + coilLen + joinLen + tail };
  }
  let lo = 0, hi = Math.max(1, (length - lead - tail) / per + 1);
  const zero = at(0);
  if (zero.length >= length - 0.02) return zero;
  while (at(hi).length < length) hi *= 1.5;
  let result;
  for (let i = 0; i < 25; i++) {
    const mid = (lo + hi) / 2;
    result = at(mid);
    if (Math.abs(result.length - length) < 0.02) break;
    if (result.length < length) lo = mid;
    else hi = mid;
  }
  return result;
}

// Parallel-transport frames are built from the socket backwards along the fixed route.
// They have no dependence on playback history and do not flip at vertical sections.
const routeFrames = new WeakMap();
function transportedUp(pts, cum, s, finalUp, direction) {
  const key = `${direction}:${finalUp.join(',')}`;
  let variants = routeFrames.get(pts);
  if (!variants) routeFrames.set(pts, variants = new Map());
  let ups = variants.get(key);
  if (!ups) {
    ups = new Array(pts.length);
    const anchor = direction === 1 ? 0 : pts.length - 1;
    const increment = direction === 1 ? 1 : -1;
    let n = scale3(tangentAt(pts, cum, cum[anchor]), direction);
    let u = sub3(finalUp, scale3(n, dot3(finalUp, n)));
    if (len3(u) < 1e-5) u = cross3(n, [1, 0, 0]);
    ups[anchor] = normalize3(u);
    for (let i = anchor + increment; i >= 0 && i < pts.length; i += increment) {
      const next = scale3(tangentAt(pts, cum, cum[i]), direction);
      u = qrotate(qfromTo(n, next), ups[i - increment]);
      ups[i] = normalize3(sub3(u, scale3(next, dot3(u, next))));
      n = next;
    }
    variants.set(key, ups);
  }
  const [i, f] = locate(cum, s);
  return normalize3(lerp3(ups[i], ups[i + 1], f));
}

/** Pose of a plug whose cable exit sits at arclength s on `pts`, leading along +s (plug B). */
export function leadingPlugPose(pts, cum, s, up, len) {
  const exit = pointAt(pts, cum, s);
  const t = tangentAt(pts, cum, Math.min(s, cum[cum.length - 1] - 1e-3));
  return plugPose(exit, scale3(t, -1), transportedUp(pts, cum, s, up, -1), len);
}

/** Pose of a plug whose cable leaves along +s from arclength s (plug A, trailing). */
export function trailingPlugPose(pts, cum, s, up, len) {
  const exit = pointAt(pts, cum, s);
  const t = tangentAt(pts, cum, s);
  return plugPose(exit, t, transportedUp(pts, cum, s, up, 1), len);
}

function plugPose(exit, yDir, up, len) {
  // +y of the connector points from its body to the cable; the body extends len along -y.
  let u = sub3(up, scale3(yDir, dot3(up, yDir)));
  if (len3(u) < 1e-3) u = cross3(yDir, Math.abs(yDir[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]);
  return { exit, yDir: normalize3(yDir), up: normalize3(u), origin: sub3(exit, scale3(normalize3(yDir), len)) };
}

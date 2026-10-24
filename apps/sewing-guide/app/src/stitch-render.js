// Draws a stitch as the machine would sew it: a thread polyline through the needle
// penetration points for the chosen width and length. Pure function: returns SVG markup.
//
// Geometry kinds (x is in half-widths, -1 = left swing, 1 = right swing):
//   line  { pts: [[x, dy], ...] }               dy in stitch lengths; repeats downwards
//   satin { period, left(t), right(t), step }    dense zigzag between two envelopes, t = 0..1 per period (mm)
//   motif { strokes: [[[x, y], ...], ...], h }   polylines in unit space (y 0..1), one motif per h mm

export const THREAD_MM = 0.45;

function lineThread(geom, W, L, heightMm) {
  const half = W / 2;
  const out = [];
  let y = 0;
  let guard = 0;
  out.push([0 * half, 0]);
  while (y < heightMm && guard++ < 4000) {
    for (const [x, dy] of geom.pts) {
      y += dy * L;
      out.push([x * half, y]);
      if (y > heightMm + L) break;
    }
  }
  return [out];
}

function satinThread(geom, W, L, heightMm) {
  const half = W / 2;
  const step = Math.max(0.12, geom.step * (L / (geom.defaultLength || L || 1)));
  const out = [];
  let y = 0;
  let side = 0;
  let guard = 0;
  while (y < heightMm && guard++ < 6000) {
    const t = (y % geom.period) / geom.period;
    const x = side ? geom.right(t) : geom.left(t);
    out.push([x * half, y]);
    y += step;
    side ^= 1;
  }
  return [out];
}

function motifThread(geom, W, L, heightMm) {
  const half = W / 2;
  const h = geom.h * (L / (geom.defaultLength || L || 1));
  const paths = [];
  let y0 = 0;
  let guard = 0;
  while (y0 < heightMm && guard++ < 400) {
    for (const stroke of geom.strokes) {
      paths.push(stroke.map(([x, y]) => [x * half, y0 + y * h]));
    }
    y0 += h;
  }
  return paths;
}

export function threadPaths(stitch, { width, length, heightMm }) {
  const g = stitch.geom;
  const W = Math.max(0, width);
  const L = Math.max(0.1, length);
  if (g.kind === 'line') return lineThread(g, W, L, heightMm);
  if (g.kind === 'satin') return satinThread(g, W, L, heightMm);
  return motifThread(g, W, L, heightMm);
}

const fmt = (n) => (Math.round(n * 100) / 100).toString();

/**
 * Render a stitch to an SVG string.
 * @param stitch  stitch record from data/stitches.js
 * @param o.width  stitch width in mm (0 for straight stitches is drawn as a straight line)
 * @param o.length stitch length in mm
 * @param o.heightMm sewn length to show
 * @param o.pxPerMm scale
 * @param o.dots   draw needle penetration dots (line kind only)
 */
export function renderStitchSVG(stitch, o = {}) {
  const width = o.width ?? stitch.width.def;
  const length = o.length ?? stitch.length.def;
  const heightMm = o.heightMm ?? 30;
  const s = o.pxPerMm ?? 5;
  const dots = o.dots ?? false;
  const pad = 1.5;
  const maxW = Math.max(width, stitch.width.max || 7, 2);
  const paths = threadPaths(stitch, { width, length, heightMm });
  const w = (maxW + pad * 2) * s;
  const h = (heightMm + pad * 2) * s;
  const cx = w / 2;
  const d = paths
    .map((p) => p.map(([x, y], i) => `${i ? 'L' : 'M'}${fmt(cx + x * s)} ${fmt((pad + y) * s)}`).join(''))
    .join('');
  let dotMarkup = '';
  if (dots && stitch.geom.kind === 'line') {
    dotMarkup = paths[0]
      .filter(([, y]) => y <= heightMm)
      .map(([x, y]) => `<circle cx="${fmt(cx + x * s)}" cy="${fmt((pad + y) * s)}" r="${fmt(0.28 * s)}"/>`)
      .join('');
  }
  const stroke = THREAD_MM * s;
  return (
    `<svg class="stitch-svg" viewBox="0 0 ${fmt(w)} ${fmt(h)}" width="${fmt(w)}" height="${fmt(h)}" role="img" aria-label="${stitch.no} ${stitch.name.en}">` +
    `<path class="thread" d="${d}" fill="none" stroke="currentColor" stroke-width="${fmt(stroke)}" stroke-linecap="round" stroke-linejoin="round"/>` +
    (dotMarkup ? `<g class="needle-dots" fill="var(--accent)">${dotMarkup}</g>` : '') +
    `</svg>`
  );
}

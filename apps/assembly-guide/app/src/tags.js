// Name tags pinned to parts in the 3D view. A chapter lists { text, node, at, side, from, until }:
// `at` is a point in the node's own frame (mm), `side` the compass direction of the tag from that
// point on screen, `from` and `until` seconds into the chapter (until defaults to its end).

import { Quaternion, Vector3 } from 'three';

const NS = 'http://www.w3.org/2000/svg';
const SIDES = { n: [0, -1], s: [0, 1], e: [1, 0], w: [-1, 0], ne: [0.8, -0.6], nw: [-0.8, -0.6], se: [0.8, 0.6], sw: [-0.8, 0.6] };
const MARGIN = 8;
const GAP = 4;

export function createTags({ root, before, player, timeline, viewer }) {
  const items = timeline.chapters.flatMap((c) => c.tags.map((tag) => ({
    tag,
    from: c.start + (tag.from ?? 0.4),
    until: tag.until == null ? c.end : c.start + tag.until,
  })));
  if (!items.length) return { update() {} };

  const layer = document.createElement('div');
  layer.className = 'tags';
  layer.setAttribute('aria-hidden', 'true');
  root.insertBefore(layer, before);
  const svg = document.createElementNS(NS, 'svg');
  svg.classList.add('tag-leaders');
  layer.appendChild(svg);
  for (const it of items) {
    it.el = document.createElement('span');
    it.el.className = 'tag';
    it.el.textContent = it.tag.text;
    layer.appendChild(it.el);
    it.line = document.createElementNS(NS, 'line');
    it.dot = document.createElementNS(NS, 'circle');
    it.dot.setAttribute('r', '2.6');
    svg.append(it.line, it.dot);
    it.on = false;
  }

  const q = new Quaternion();
  const p = new Vector3();
  const offset = new Vector3();
  let width = 0;

  function show(it, on) {
    if (it.on === on) return;
    it.on = on;
    it.el.classList.toggle('on', on);
    it.line.classList.toggle('on', on);
    it.dot.classList.toggle('on', on);
  }

  function update() {
    const t = player.time;
    const box = layer.getBoundingClientRect();
    const canvas = viewer.canvas.getBoundingClientRect();
    const floor = box.height - viewer.bottomInset; // keep clear of the caption and transport bar
    if (box.width !== width) {
      width = box.width;
      svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
      for (const it of items) it.size = null; // the type size may have changed with the layout
    }
    const reach = box.width < 640 ? 30 : 48;
    const placed = [];
    for (const it of items) {
      const s = t >= it.from && t < it.until ? viewer.state.get(it.tag.node) : null;
      if (!s || s.alpha < 0.5) {
        show(it, false);
        continue;
      }
      q.set(s.q[0], s.q[1], s.q[2], s.q[3]);
      offset.set(...(it.tag.at || [0, 0, 0])).applyQuaternion(q);
      p.set(s.p[0], s.p[1], s.p[2]).add(offset);
      const a = viewer.projectRackPoint(p);
      const ax = a.x + canvas.left - box.left;
      const ay = a.y + canvas.top - box.top;
      if (!a.visible || ay > floor) {
        show(it, false);
        continue;
      }
      if (!it.size) it.size = [it.el.offsetWidth, it.el.offsetHeight];
      const [w, h] = it.size;
      const [dx, dy] = SIDES[it.tag.side] || SIDES.n;
      const tx = ax + dx * reach;
      const ty = ay + dy * reach;
      let x = dx > 0.3 ? tx : dx < -0.3 ? tx - w : tx - w / 2;
      let y = dy > 0.3 ? ty : dy < -0.3 ? ty - h : ty - h / 2;
      x = Math.min(Math.max(x, MARGIN), box.width - w - MARGIN);
      // Step clear of tags already placed this frame, away from the point it names.
      for (let pass = 0; pass < 3; pass++) {
        const hit = placed.find((o) => x < o.x + o.w + GAP && o.x < x + w + GAP && y < o.y + o.h + GAP && o.y < y + h + GAP);
        if (!hit) break;
        y = dy < 0 ? hit.y - h - GAP : hit.y + hit.h + GAP;
      }
      y = Math.min(Math.max(y, MARGIN), floor - h - MARGIN);
      placed.push({ x, y, w, h });
      it.el.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
      // The leader runs from the point to the nearest edge of the tag.
      const ex = Math.min(Math.max(ax, x), x + w);
      const ey = Math.min(Math.max(ay, y), y + h);
      it.line.setAttribute('x1', ax.toFixed(1));
      it.line.setAttribute('y1', ay.toFixed(1));
      it.line.setAttribute('x2', ex.toFixed(1));
      it.line.setAttribute('y2', ey.toFixed(1));
      it.dot.setAttribute('cx', ax.toFixed(1));
      it.dot.setAttribute('cy', ay.toFixed(1));
      show(it, true);
    }
  }
  return { update };
}

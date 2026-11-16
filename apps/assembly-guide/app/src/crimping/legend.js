// The T568B strip pinned over the view while the wires are lined up, trimmed and pushed into the plug.
import { T568B, WIRE_COLOURS } from './crimp-layout.js';

const css = (hex) => `#${hex.toString(16).padStart(6, '0')}`;

export function legendHTML() {
  const swatch = (w) => (w.white
    ? `background:repeating-linear-gradient(90deg, ${css(WIRE_COLOURS.white)} 0 5px, ${css(w.colour)} 5px 8px)`
    : `background:${css(w.colour)}`);
  return `<p class="legend-title">T568B · clip down, gold contacts up · left to right</p>
    <ol class="legend-wires">${T568B.map((w) => `<li><span class="legend-swatch" style="${swatch(w)}"></span><b>${w.pin}</b><small>${w.name}</small></li>`).join('')}</ol>`;
}

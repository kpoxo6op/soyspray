// Decoder for data/v3/meshes.bin (written by cad/render.mjs) and data/trays.bin (the node tray).
// Layout: uint32 header length, JSON header, then per part float32 positions and u16/u32 indices.

export function decodeMeshes(bytes) {
  const buf = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const view = new DataView(buf);
  const headerLen = view.getUint32(0, true);
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, headerLen)));
  const base = 4 + headerLen;
  const out = {};
  for (const [name, h] of Object.entries(header)) {
    const [po, pl] = h.positions;
    const [io, il] = h.indices;
    const positions = new Float32Array(buf, base + po, pl / 4);
    const indices = h.indexType === 'u16' ? new Uint16Array(buf, base + io, il / 2) : new Uint32Array(buf, base + io, il / 4);
    out[name] = { ...h, positions, indices };
  }
  return out;
}

export const title = 'Evidence intake: interruption and retry';
export const state = v => v.worker === 'Running' ? v.phase : `${v.phase}: ${v.worker}`;
export const step = a => ({WriteMarker:'write completion marker',Publish:'rename into versions',Seal:'make root read-only',Crash:'process stops',Retry:'retry same archive',Done:null}[a] ?? a);
export const group = v => v.worker === 'Retry rejected' ? 'failure' : v.phase === 'Published read-only' ? 'ready' : 'progress';
export const colors = {failure:'pink',ready:'teal',progress:'blue'};

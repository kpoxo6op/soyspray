export const title = 'Stale-operation recovery: last-moment replacement';
export const state = v => `${v.operation}: ${v.stage}`;
export const step = a => ({Reread:'re-read operation',Replace:'controller starts a new operation',Patch:'submit termination request',Done:null}[a] ?? a);
export const group = v => ['Conflict','Stopped'].includes(v.stage) ? 'safe' : 'pending';
export const colors = {safe:'teal',pending:'blue'};

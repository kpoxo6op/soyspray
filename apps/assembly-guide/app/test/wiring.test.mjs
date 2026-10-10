import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CABLES, POSES, INTEGRAL_PLUGS } from '../src/wiring.js';
import { PORTS, CONNECTORS, seatedPose, portFrame } from '../src/ports.js';
import { wireState } from '../src/wiring-state.js';
import { cableCentreline, polyLength, leadingPlugPose, trailingPlugPose } from '../src/cablepath.js';
import { buildTimeline } from '../src/timeline.js';
import { basisQuat, dot3 } from '../src/math.js';
import { placements } from './helpers.mjs';

const timeline = buildTimeline(placements);
const poseAt = (c,s,end) => {
  const p = c.plugs[end];
  return end === 'a' ? trailingPlugPose(c.aLead,c.aCum,s.sA,p.frame.u,CONNECTORS[p.type].len)
    : leadingPlugPose(c.routeB,c.routeCum,s.sB,p.frame.u,CONNECTORS[p.type].len);
};

// Contract: every piece of the real cluster has its data and power connection.
// A missing lead or a double-booked USB socket was not covered by the rack/player tests.
test('equipment wiring uses compatible, unique sockets and covers power and data', () => {
  const occupied = new Set();
  // A plug-in adapter could otherwise share an outlet with a detachable mains lead.
  // The existing connector checks covered cable ends, but did not count these fixtures.
  for (const fixture of INTEGRAL_PLUGS) {
    const key = fixture.at.join(':');
    assert.ok(!occupied.has(key), `socket reused by fixture: ${key}`);
    occupied.add(key);
    assert.equal(PORTS[POSES[fixture.at[0]].model][fixture.at[1]].type, fixture.type);
  }
  for (const c of CABLES) {
    for (const end of ['a','b']) if (c.plugs[end]) {
      const p = c.plugs[end]; if (!p.port) continue; const key = p.port.join(':');
      assert.ok(!occupied.has(key), `socket reused: ${key}`); occupied.add(key);
      assert.equal(PORTS[POSES[p.port[0]].model][p.port[1]].type,p.type);
    }
  }
  for (let i = 0; i < 3; i++) for (const port of ['rj45','power']) assert.ok(occupied.has(`node${i}:${port}`));
  for (let i = 0; i < 3; i++) assert.ok(occupied.has(`brick${i}:c5`));
  for (const key of ['usbA:usb','usbB:usb','router:power','router:lan','router:wan','switch:dc','powerline:eth','wallSocket:L']) assert.ok(occupied.has(key),key);
  // Compatibility and uniqueness alone could allow the spare board to be chained into L2.
  assert.equal(CABLES.find(c=>c.id==='spareCord').plugs.b.port,null,'spare board stays disconnected');
  assert.equal([...occupied].filter(x => x.startsWith('node0:usb')).length,3,'two disks and the Zigbee extension use three rear USB sockets');
  assert.ok(CABLES.filter(c=>!c.custom).every(c=>c.stock===c.length && c.stock>=460),'factory leads are intact');
});

// Contract: deployment, dressing and rewind retain the full length, not a stretching tube.
test('cables keep their nominal arc length throughout payout and dressing', () => {
  for (const c of CABLES) {
    const chapter = timeline.chapters.find(x=>x.wire===c.id), ties=timeline.chapters.find(x=>x.id==='zip-ties');
    for (const start of [chapter.start,ties.start]) for (let i=0;i<=30;i++) {
      const s=wireState(timeline,c,start+i*6.2/30), curve=cableCentreline(c,s);
      assert.ok(Math.abs(polyLength(curve.points)-c.length)<0.3,`${c.id} arc length at ${start+i*6.2/30}: ${curve.length}`);
    }
  }
});

// Contract: a seated connector is aligned to the actual socket, including roll.
test('connectors align with sockets or their unplugged stow pose', () => {
  for (const c of CABLES) for (const end of ['a','b']) if (c.plugs[end]) {
    const s=wireState(timeline,c,timeline.duration), actual=poseAt(c,s,end), p=c.plugs[end];
    const frame=p.port ? portFrame(POSES[p.port[0]].model,p.port[1],POSES[p.port[0]].p,POSES[p.port[0]].q) : p.frame;
    const expected=seatedPose(p.type,frame);
    assert.ok(Math.hypot(...actual.origin.map((v,k)=>v-expected.p[k]))<0.01,`${c.id}.${end} seated`);
    assert.ok(dot3(actual.yDir,frame.n)>0.9999,`${c.id}.${end} normal`);
    assert.ok(dot3(actual.up,frame.u)>0.9999,`${c.id}.${end} roll`);
  }
});

// Contract: no history dependent rewind and no abrupt plug flips near vertical cable runs.
test('reverse and arbitrary seeks retrace wiring; moving plugs rotate continuously', () => {
  for (const c of CABLES) {
    const start=timeline.chapters.find(x=>x.wire===c.id).start;
    const times=Array.from({length:361},(_,i)=>start+i/60);
    const snapshots=times.map(t=>wireState(timeline,c,t));
    for (let i=times.length-1;i>=0;i--) assert.deepEqual(wireState(timeline,c,times[i]),snapshots[i]);
    for (const end of ['a','b']) if (c.plugs[end]) {
      let prev=null;
      for (const state of snapshots) {
        const pose=poseAt(c,state,end), q=basisQuat(pose.yDir,pose.up);
        if (prev && state.alpha>0.9) {
          const angle=2*Math.acos(Math.min(1,Math.abs(q.reduce((a,v,k)=>a+v*prev[k],0))));
          assert.ok(angle<0.65,`${c.id}.${end} plug flips by ${angle} radians`);
        }
        prev=q;
      }
    }
  }
});

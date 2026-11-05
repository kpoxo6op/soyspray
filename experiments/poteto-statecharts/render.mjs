import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const [results, packageDirectory] = process.argv.slice(2);
if (!results || !packageDirectory) throw new Error('Usage: node render.mjs RESULTS_DIR PELE_PACKAGE_DIR');
const require = createRequire(path.resolve(packageDirectory, 'package.json'));
const { render } = require('pele');
const theme = `.pele {
 --pele-bg:#0b2743; --pele-fg:#e9f4ff; --pele-muted:#9bbbd7;
 --pele-line:#8faecb; --pele-surface:#123754; --pele-surface-alt:#102f4e;
 --pele-border:#638aaa; --pele-font:Arial,sans-serif;
}
.pele .blue rect{fill:#153d60}.pele .teal rect{fill:#165345;stroke:#7addbd}
.pele .pink rect{fill:#693b55}
.pele .breaks rect{fill:#622d40!important;stroke:#ff8295!important;stroke-width:2.5px!important}
.pele .breaks text{fill:#ffe7ec!important}
.pele .mayBreak rect{fill:#64441c!important;stroke:#f6c576!important}
.pele .mayBreak text{fill:#fff0d5!important}
.pele .bugPath rect{stroke:#71beff!important;stroke-width:2.5px!important}
.pele .repeats rect{stroke:#d5b0ff!important;stroke-dasharray:6 3}`;

const pages = [
 {id:'01-intake', label:'01 / RECOVERY',title:'A completed marker is not a completed publication',
  subtitle:'A real retry gap in the evidence-pack receiver, reproduced at two interruption points.',
  badge:'CURRENT CODE · REPRODUCED',
  intro:'The uninterrupted path passes. A process exit after writing COMPLETE or after renaming the directory leaves a writable root. Both retries reject it.',
  charts:[['intake-normal','Uninterrupted · 4 model states'],['intake-crash','One interruption · 14 model states']],
  detail:'Shortest failure: verified staging → completion marker → process stops → retry rejected. The second failing path stops after rename.',
  limit:'Real-code replay: synthetic files on the laptop; process exits after actual filesystem calls. Previous version still verifies. Startup rejects the interrupted version. NFS and power-loss durability were not tested.'},
 {id:'02-stale-operation', label:'02 / CONCURRENCY',title:'The last read cannot close the race',
  subtitle:'resourceVersion protects the gap between inspecting an operation and submitting its termination.',
  badge:'CURRENT GUARD PASSES · MUTANT FAILS',
  intro:'A controller may replace the operation immediately after the final read. Keeping the version in the patch rejects that stale request.',
  charts:[['stale-guarded','Current guard · 7 model states'],['stale-mutant','Deliberately removed guard · 7 model states']],
  detail:'Counterexample: re-read reviewed operation → controller replaces it → old request terminates the new operation. Only the deliberately broken variant permits this.',
  limit:'The real client produced the guarded patch. A temporary source mutant removed its version. API conflict semantics were emulated locally; no request was sent to Kubernetes.'},
 {id:'03-promotion', label:'03 / DELIVERY',title:'A source merge should leave the running image alone',
  subtitle:'A small model makes the separate digest-promotion boundary visible.',
  badge:'POLICY MODEL · NO DEPLOYMENT',
  intro:'Building and publishing an image leaves the old digest running. Argo can adopt the new digest only after the separate promotion reaches main.',
  charts:[['promotion-current','Current workflow · 6 model states'],['promotion-mutant','Hypothetical auto-deploy · 7 model states']],
  detail:'The hypothetical shortcut exposes an unapproved runtime after four steps. Current promotion helper tests also pass: seven tests check digest validation and preserved deployment settings.',
  limit:'This is a policy abstraction mapped to the composite action, promotion helper and Argo source. The negative case is model-only. CI credentials, registry behavior and live reconciliation are outside the model.'}
];

const outputs = new Map();
for (const name of fs.readdirSync(results)) {
 const file = path.join(results,name,'chart.mmd');
 if (!fs.existsSync(file)) continue;
 const { svg } = render(fs.readFileSync(file,'utf8'),{limit:1_000_000,outputLimit:8_000_000,maxEdges:10_000,fontFamily:'Arial',fontSize:16});
 const styled = svg.replace(/(<svg\b[^>]*>)/,`$1<style>${theme}</style>`);
 fs.writeFileSync(path.join(results,name,'chart.svg'),styled);
 const width = svg.match(/viewBox="0 0 ([0-9.]+)/)?.[1];
 outputs.set(name,styled.replace('max-width:100%;', `max-width:${width}px;`));
 console.log(name, styled.match(/viewBox="[^"]+"/)?.[0]);
}
const visual = path.join(results,'visuals');
fs.mkdirSync(visual,{recursive:true});
const css = `*{box-sizing:border-box}body{margin:0;background:#081b2e;color:#e9f4ff;font-family:Arial,sans-serif}main{width:1440px;padding:46px 48px 30px;background:radial-gradient(ellipse at top right,#174b6a 0,transparent 50%),#0b2743}.eyebrow{letter-spacing:3px;color:#88c9f0;font-size:15px;font-weight:bold}h1{font-size:39px;line-height:1.12;max-width:1150px;margin:16px 0}p{font-size:20px;line-height:1.45;margin:12px 0;color:#c0d4e7}.badge{display:inline-block;padding:9px 13px;border:1px solid #6897b8;border-radius:6px;color:#a7e9d1;font-size:13px;letter-spacing:1px;font-weight:bold;margin:8px 0}.intro{max-width:1220px}.grid{display:grid;grid-template-columns:1fr;gap:26px;margin-top:24px}.panel{border:1px solid #355a79;border-radius:12px;padding:20px;background:linear-gradient(#ffffff03 1px,transparent 1px),linear-gradient(90deg,#ffffff03 1px,transparent 1px),#0b2743;background-size:24px 24px}h2{font-size:19px;line-height:1.3;margin:0 0 14px;color:#b8ddf5}.panel svg{width:100%;height:auto;display:block;margin:auto;max-width:var(--natural-width)}.detail{font-size:20px;border-left:3px solid #7ed3b5;padding:12px 18px;margin-top:24px}.limit{font-size:16px;line-height:1.45;color:#a5bfd5;margin-top:20px}.footer{display:flex;justify-content:space-between;border-top:1px solid #355a79;margin-top:22px;padding-top:17px;font-size:13px;color:#8faecb;letter-spacing:.7px}a{color:#8ed5ff}${theme}`;
for (const page of pages) {
 const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>${page.title}</title><style>${css}</style><main><div class="eyebrow">SOYSPRAY × PSTACK &nbsp; / &nbsp; ${page.label}</div><h1>${page.title}</h1><p>${page.subtitle}</p><div class="badge">${page.badge}</div><p class="intro">${page.intro}</p><div class="grid">${page.charts.map(([id,label])=>`<section class="panel"><h2>${label}</h2>${outputs.get(id)}</section>`).join('')}</div><div class="detail">${page.detail}</div><p class="limit">${page.limit}</p><div class="footer"><span>TLA+ / TLC 1.7.4 → pstack 0.15.36 → Pele 1.9.0</span><span>EXPERIMENTAL BRANCH · UNMERGED · 30 OCT 2026</span></div></main></html>`;
 fs.writeFileSync(path.join(visual,`${page.id}.html`),html);
}
fs.writeFileSync(path.join(visual,'index.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><title>Soyspray statechart experiments</title><style>${css}</style><main><div class="eyebrow">SOYSPRAY × PSTACK</div><h1>Three experiments. One confirmed recovery gap.</h1><p>Open each result to compare the checked paths and their limits.</p>${pages.map(p=>`<p><a href="${p.id}.html">${p.label} — ${p.title}</a></p>`).join('')}<p class="limit">Six TLC runs. Current guard and promotion models pass; their deliberately broken variants fail. The intake interruption model fails and both failure windows reproduce against real code. A finite model is not a proof of the whole cluster.</p></main></html>`);

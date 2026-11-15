// Reads the chapter lists of the two guides from their own sources and writes data/guides.json, which the
// catalog ships. Run it after a guide changes its chapters: `node tools/extract-guides.mjs` (in app/), with
// `npm ci` done in apps/pearl-guide/app and apps/assembly-guide/app. `npm test` fails when the file is stale.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const apps = resolve(here, '../../..');
const load = (path) => import(pathToFileURL(resolve(apps, path)).href);

export async function extractGuides() {
  const { decodeMeshes } = await load('assembly-guide/app/src/meshes.js');
  const { buildSoyrackTimeline } = await load('assembly-guide/app/src/soyrack/index.js');
  const read = (p) => decodeMeshes(new Uint8Array(readFileSync(resolve(apps, 'assembly-guide/app', p))));
  const rack = buildSoyrackTimeline({ ...read('data/trays.bin'), ...read('data/v3/meshes.bin') });
  let section = '';
  const assembly = rack.chapters.map((c) => {
    if (c.section) section = c.section;
    return { id: c.id, title: c.title, section: section || 'Chapters', start: round(c.start), length: round(c.end - c.start) };
  });

  const { buildTimeline } = await load('pearl-guide/app/src/story.js');
  const pearl = buildTimeline().chapters.map((c) => ({
    id: c.id,
    title: c.title,
    section: 'Stage 0',
    start: round(c.start),
    length: round(c.end - c.start),
    goal: c.goal,
  }));

  return [
    {
      slug: 'assembly',
      title: 'Soyrack assembly',
      summary: 'Print, crimp and bolt together the PETG rack that holds the three cluster nodes, the switch and the power base.',
      path: '/assembly/',
      store: 'explain.assembly.done',
      link: 'id',
      chapters: assembly,
    },
    {
      slug: 'pearl',
      title: 'Pearl, stage 0',
      summary: 'Buy the kit, print the pod, learn to solder and float the first orb of the indoor helium camera robot.',
      path: '/pearl/',
      store: 'pearl.stage0.done',
      link: 'time',
      chapters: pearl,
    },
  ];
}

const round = (s) => Math.round(s * 10) / 10;

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const out = resolve(here, '../data/guides.json');
  writeFileSync(out, JSON.stringify(await extractGuides(), null, 1) + '\n');
  console.log('wrote', out);
}

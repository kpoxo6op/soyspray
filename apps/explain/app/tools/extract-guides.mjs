// Reads the chapter lists of the guides from their own sources and writes data/guides.json, which the catalog
// ships (the crimping explainer is built in the assembly guide's image). Run it after a guide changes its chapters: `node tools/extract-guides.mjs` (in app/), with `npm ci` done
// in apps/pearl-guide/app and apps/assembly-guide/app. `npm test` fails when the file is stale. The network
// explainer lives in this app (network/), so its list is always checked.
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

  const { buildCrimpTimeline } = await load('assembly-guide/app/src/crimping/index.js');
  section = '';
  const crimping = buildCrimpTimeline().chapters.map((c) => {
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

  const { GUIDE, buildSolderTimeline } = await load('pearl-guide/app/src/soldering/story.js');

  return [
    {
      slug: 'assembly',
      title: 'Soyrack assembly',
      summary: 'Print and bolt together the PETG rack that holds the three cluster nodes, the switch and the power base.',
      path: '/assembly/',
      store: 'explain.assembly.done',
      link: 'id',
      chapters: assembly,
    },
    {
      slug: 'crimping',
      title: 'Crimping Ethernet leads',
      summary: 'Cut, strip, line up T568B, crimp and test the five short Ethernet leads for the rack with the crimp kit.',
      path: '/crimping/',
      store: 'explain.crimping.done',
      link: 'id',
      chapters: crimping,
    },
    {
      slug: 'pearl',
      title: 'Pearl, stage 0',
      summary: 'Buy the kit, print the pod, learn to solder and float the first orb of the indoor helium camera robot.',
      path: '/pearl/',
      store: 'pearl.stage0.done',
      link: 'id',
      chapters: pearl,
    },
    {
      slug: 'soldering', title: GUIDE.title, summary: GUIDE.summary, path: '/soldering/',
      store: 'explain.soldering.done', link: 'id',
      chapters: buildSolderTimeline().chapters.map((c) => ({
        id: c.id, title: c.title, section: c.section || GUIDE.section,
        start: round(c.start), length: round(c.end - c.start), goal: c.goal,
      })),
    },
    await networkGuide(),
  ];
}

/** The network explainer's entry, from network/story.js in this app. */
export async function networkGuide() {
  const { buildTimeline } = await import('../network/story.js');
  const chapters = buildTimeline().chapters.map((c) => ({
    id: c.id,
    title: c.title,
    section: c.index < 11 ? 'Your network today' : 'What you could add',
    start: round(c.start),
    length: round(c.end - c.start),
    goal: c.goal,
  }));
  return {
    slug: 'network',
    title: 'Network, explained',
    summary: 'Your home network from zero: addresses, the router, the cluster, Tailscale and firewalls, then subnets and monitoring.',
    path: '/network/',
    store: 'explain.network.done',
    link: 'id',
    chapters,
  };
}

const round = (s) => Math.round(s * 10) / 10;

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const out = resolve(here, '../data/guides.json');
  writeFileSync(out, JSON.stringify(await extractGuides(), null, 1) + '\n');
  console.log('wrote', out);
}

import { startGuide } from './boot.js';
import { CHAPTERS, GUIDE, KIT, buildScene } from './soldering/index.js';
startGuide({
  chapters: CHAPTERS, buildScene, loop: true,
  canvasLabel: 'Soldering bench, 3D view. Drag to turn, scroll or pinch to zoom.',
  sheets: { keys: { done: 'explain.soldering.done', kit: 'pearl.stage0.kit' },
    chapters: { title: GUIDE.title, lede: GUIDE.lede }, kit: KIT, files: false, carry: false },
});

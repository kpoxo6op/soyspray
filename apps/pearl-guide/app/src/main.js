import { startGuide } from './boot.js';
import { CHAPTERS, GUIDE } from './story.js';
import { KIT } from './kit.js';
import { PLATE_NOTE, SETTINGS, STL } from './files.js';
import { buildScene } from './scene.js';

startGuide({
  chapters: CHAPTERS,
  buildScene,
  canvasLabel: 'Pearl, 3D view. Drag to turn, scroll or pinch to zoom.',
  loop: false,
  sheets: {
    keys: { done: 'pearl.stage0.done', kit: 'pearl.stage0.kit' },
    chapters: { title: GUIDE.title, lede: GUIDE.lede },
    kit: KIT,
    files: {
      title: 'Files to print',
      lede: `Pearl v3.1’s printed parts, straight from the design model. ${PLATE_NOTE}`,
      partsTitle: 'Parts',
      parts: STL,
      settingsTitle: 'Bambu Studio',
      settings: SETTINGS,
    },
    carry: true,
  },
});

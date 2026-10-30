# Pearl guide standards

These rules hold for every stage of the Pearl guide. `app/test/content.test.mjs`
enforces the ones a machine can check; the rest are the review list for each new
chapter. Change them only with a dated line at the end.

## Format

- Each stage is a 3D player: chapters of short beats; each beat shows one action
  on the real model and one caption. Readers can pause, scrub, rewind and turn
  the view, as in the assembly guide.
- Models come from Pearl's design files at true size. What the design does not
  have (scale, cup, spool, print bed) is drawn in code at its real size.
- Motion only shows an action or a result: a part landing, solder flowing, a
  balloon filling, a scale reading. Nothing moves for decoration.
- The camera frames the action. Labels name at most five things at once.

## Words

- One caption per beat: an instruction in the second person, then what you
  should see. At most 120 characters, and at least characters ÷ 14 + 1 seconds
  on screen.
- Plain verbs and nouns, New Zealand English, metric. One name per thing: the
  orb, the pod, the shell, the pole cap, the side ducts, the lift duct.
- Numbers carry units and come from the design or a measurement. "About" marks
  an estimate, once. Nothing else decorates a number.
- Each chapter ends with a checkpoint: something you can see, count or weigh,
  and where it is fine to stop.
- Safety sits in the caption where the hazard is, stated once.
- Never: exclamation marks, emoji, em dashes, questions, "simply", "just",
  "easy", "seamless", "unlock", "journey", "elevate", "delve", "leverage",
  "robust", "effortless", "dive into", "it's not X, it's Y".
- Never claim Pearl flies, lifts or is safe before a measurement says so.

## Look

- A dark room, a warm oak bench, real materials and soft shadows.
- One accent colour, amber `#e8ae62`, for progress, focus, label dots and
  checkpoints. No other colour carries meaning.
- System UI type, sentence case, left aligned, captions 16 to 18 px.
- No gradients except the scrims that keep text legible over the 3D view. No
  glass, glows, drop shadows on UI, pill badges above headings, icon grids,
  cards inside cards or stock imagery.
- Phone first: captions above the controls, panels as bottom sheets, 44 px
  touch targets, nothing that needs hover.

## Kit and files

- Each item: the exact product, shop and code, the price with the date it was
  read, and one line on why it is needed. AliExpress items get a search link,
  what to pick and a typical price marked "about".
- Files come from the current design, with settings for the printer Boris owns
  (Bambu Lab P1S) and the weights to expect.

## Before publishing

- `npm test` passes.
- Every beat reviewed by eye at 1440×900 and 390×844: framing, labels on
  target, nothing floating, clipped or left over from an earlier beat.
- No console errors.

## Changes

- 31 Oct 2026: written with Stage 0.

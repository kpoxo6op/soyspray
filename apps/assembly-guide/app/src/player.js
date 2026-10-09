// Playback state for the assembly timeline. No DOM, no clock: the caller feeds elapsed time to tick().

import { clamp } from './math.js';

export const SPEEDS = [0.5, 0.75, 1, 1.5, 2];
const RESTART_GRACE = 1.5; // "previous" restarts the current chapter when this far into it

export class Player {
  constructor({ duration, chapters }) {
    this.duration = duration;
    this.chapters = chapters;
    this.time = 0;
    this.direction = 0; // 1 forward, -1 reverse, 0 paused
    this.speed = 1;
    this.scrubbing = false;
    this.resumeAfterScrub = 0;
    this.listeners = new Set();
  }

  get playing() {
    return this.direction !== 0;
  }

  get reversing() {
    return this.direction < 0;
  }

  get chapterIndex() {
    const cs = this.chapters;
    if (this.time >= this.duration) return cs.length - 1;
    let i = 0;
    while (i + 1 < cs.length && cs[i + 1].start <= this.time) i++;
    return i;
  }

  on(fn) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  emit(reason) {
    for (const fn of this.listeners) fn(reason, this);
  }

  play() {
    if (this.time >= this.duration - 1e-6) this.time = 0;
    this.direction = 1;
    this.emit('play');
  }

  /** Play backwards from the current position (a rewind that keeps every intermediate state). */
  reverse() {
    if (this.time <= 1e-6) return;
    this.direction = -1;
    this.emit('play');
  }

  pause() {
    if (!this.direction) return;
    this.direction = 0;
    this.emit('pause');
  }

  toggle() {
    if (this.playing) this.pause();
    else this.play();
  }

  toggleReverse() {
    if (this.reversing) this.pause();
    else this.reverse();
  }

  seek(t, reason = 'seek') {
    const next = clamp(t, 0, this.duration);
    if (next === this.time) return;
    this.time = next;
    this.emit(reason);
  }

  seekBy(dt) {
    this.seek(this.time + dt);
  }

  goToChapter(i) {
    const c = this.chapters[clamp(i, 0, this.chapters.length - 1)];
    this.seek(c.start, 'chapter');
  }

  nextChapter() {
    const i = this.chapterIndex;
    if (i + 1 < this.chapters.length) this.goToChapter(i + 1);
    else this.seek(this.duration, 'chapter');
  }

  prevChapter() {
    const i = this.chapterIndex;
    const c = this.chapters[i];
    if (this.time - c.start > RESTART_GRACE || i === 0) this.goToChapter(i);
    else this.goToChapter(i - 1);
  }

  setSpeed(s) {
    this.speed = s;
    this.emit('speed');
  }

  cycleSpeed() {
    const i = SPEEDS.indexOf(this.speed);
    this.setSpeed(SPEEDS[(i + 1) % SPEEDS.length]);
  }

  beginScrub() {
    if (this.scrubbing) return;
    this.scrubbing = true;
    this.resumeAfterScrub = this.direction;
    this.direction = 0;
    this.emit('scrub-start');
  }

  endScrub() {
    if (!this.scrubbing) return;
    this.scrubbing = false;
    const resume = this.resumeAfterScrub;
    this.resumeAfterScrub = 0;
    if (resume > 0 && this.time < this.duration) this.direction = 1;
    else if (resume < 0 && this.time > 0) this.direction = -1;
    this.emit('scrub-end');
  }

  /** Advance by real elapsed seconds. Returns true when the playhead moved. */
  tick(dt) {
    if (!this.direction || this.scrubbing || !(dt > 0)) return false;
    const step = Math.min(dt, 0.1) * this.speed * this.direction; // clamp long frames (tab switches)
    const next = clamp(this.time + step, 0, this.duration);
    const moved = next !== this.time;
    this.time = next;
    if ((this.direction > 0 && next >= this.duration) || (this.direction < 0 && next <= 0)) {
      this.direction = 0;
      this.emit('ended');
    } else if (moved) {
      this.emit('tick');
    }
    return moved;
  }
}

export function formatTime(t) {
  const s = Math.max(0, Math.floor(t + 1e-6));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

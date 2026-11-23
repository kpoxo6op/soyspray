// Rendered film over the 3D stage. A beat may carry `film: { src, from }`: while that beat is on screen, a <video>
// covers the stage and shows the clip from `from` seconds plus the beat's local time, kept in step with the player
// (play, pause, scrub). Beats without a film show the live 3D scene as before. Clips are rendered in Blender
// (~/code/pearl-solder-film) at the beat durations, so no retiming is needed.

export function createFilm({ container, base = '' }) {
  const video = document.createElement('video');
  video.className = 'film';
  video.muted = true;
  video.playsInline = true;
  video.preload = 'auto';
  video.setAttribute('aria-hidden', 'true');
  video.hidden = true;
  container.appendChild(video);
  let src = '';
  let lastVT = -1;
  return {
    /** Seconds the video itself advanced since the last call, or null when it is not the clock (hidden, paused,
     *  buffering, just seeked). The guide's player follows this while a film plays, so a slow TV never makes the
     *  player run ahead and force a seek, which restarts the hardware decoder and stutters (Sony TV, 23 Nov). */
    advance() {
      if (video.hidden || video.paused || video.seeking || video.readyState < 3) { lastVT = -1; return null; }
      const t = video.currentTime;
      const d = lastVT < 0 ? null : t - lastVT;
      lastVT = t;
      return d !== null && d >= 0 && d < 0.25 ? d : null;
    },
    /** Call once per frame with the beat on screen, its local time in seconds and whether the player is playing. */
    update(beat, local, playing) {
      const f = beat && beat.film;
      if (!f) {
        if (!video.hidden) {
          video.pause();
          video.hidden = true;
          document.body.classList.remove('has-film');
        }
        return false;
      }
      const want = base + f.src;
      if (src !== want) {
        src = want;
        video.src = want;
      }
      if (video.hidden) {
        video.hidden = false;
        document.body.classList.add('has-film');
      }
      const target = (f.from || 0) + local;
      if (video.readyState >= 1 && Math.abs(video.currentTime - target) > (playing ? 0.6 : 0.04)) {
        video.currentTime = target;
        lastVT = -1;
      }
      if (playing && video.paused) video.play().catch(() => {});
      if (!playing && !video.paused) video.pause();
      return true;
    },
    video,
  };
}

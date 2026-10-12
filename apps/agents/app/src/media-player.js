// One session owns the native player and visual-description narration. Every
// visible Pause/Resume control and the OS media controls act on this session.
export function createMediaPlayer(video, audio, { pack, base, descriptionsEnabled, update, save }) {
    let cue = null;
    let description = null;
    let userPaused = false;
    let startingAudio = false;
    let continueVideo = false;
    let internalPauses = 0;
    let lastTime = 0;
    let lastSavedAt = 0;
    let pendingSeek = null;
    let pendingHost = null;
    const narrated = new Set();

    const session = {
        get description() { return description; },
        get describing() { return cue !== null; },
        get playing() {
            return !video.paused || !!(cue && !userPaused && (!audio.paused || startingAudio));
        },
        pause,
        resume,
        seek,
        move,
        cancelDescription,
        clearDescription() { if (!cue) description = null; changed(); },
    };

    function changed() {
        if (navigator.mediaSession) {
            navigator.mediaSession.playbackState = session.playing ? "playing" : "paused";
        }
        update(session);
    }
    function savePlayback() {
        if (video.readyState < 1) return;
        save(video.currentTime);
        lastSavedAt = performance.now();
    }
    function pauseVideo() {
        if (!video.paused) { internalPauses++; video.pause(); }
    }
    function pause() {
        userPaused = true;
        if (cue) audio.pause();
        pauseVideo();
        savePlayback();
        changed();
    }
    async function resume() {
        userPaused = false;
        try {
            if (cue) {
                startingAudio = true;
                changed();
                await audio.play();
            } else await video.play();
        } catch { userPaused = true; }
        finally { startingAudio = false; changed(); }
    }
    function cancelDescription() {
        cue = null;
        description = null;
        startingAudio = false;
        continueVideo = false;
        audio.pause();
        if (audio.readyState > 0) audio.currentTime = 0;
        changed();
    }
    function seek(seconds, play = false) {
        const requested = Number(seconds);
        if (!Number.isFinite(requested)) return;
        pendingSeek = { seconds: Math.max(0, requested), play };
        const wasDescribing = cue !== null;
        cancelDescription();
        if (wasDescribing) pauseVideo();
        narrated.clear();
        if (video.readyState < 1) { changed(); return; }
        const start = Math.min(pendingSeek.seconds, video.duration);
        pendingSeek = null;
        lastTime = start;
        video.currentTime = start;
        if (play) resume();
        changed();
    }
    async function describe(next) {
        cue = next;
        description = { start: next.start, text: next.text };
        narrated.add(next.id);
        continueVideo = !video.paused;
        userPaused = false;
        startingAudio = true;
        pauseVideo();
        audio.volume = video.volume;
        audio.muted = video.muted;
        audio.src = `${base()}/${next.audio}`;
        changed();
        try { await audio.play(); }
        catch { if (cue === next && !userPaused) descriptionError(next); }
        finally { startingAudio = false; changed(); }
    }
    function descriptionError(failed) {
        if (cue !== failed) return;
        cue = null;
        continueVideo = false;
        description = { start: failed.start, text: `${failed.text} Audio unavailable; resume playback when ready.` };
        changed();
    }
    audio.addEventListener("ended", () => {
        if (!cue) return;
        const shouldContinue = continueVideo && !userPaused;
        cue = null;
        continueVideo = false;
        if (shouldContinue) resume();
        changed();
    });
    audio.addEventListener("error", () => { if (cue) descriptionError(cue); });
    for (const event of ["playing", "pause"]) audio.addEventListener(event, changed);
    video.addEventListener("loadedmetadata", () => {
        if (pendingSeek) seek(pendingSeek.seconds, pendingSeek.play);
        lastTime = video.currentTime;
        changed();
    });
    video.addEventListener("seeking", () => {
        if (cue) { cancelDescription(); pauseVideo(); }
        lastTime = video.currentTime;
        changed();
    });
    video.addEventListener("seeked", () => { lastTime = video.currentTime; changed(); });
    video.addEventListener("play", () => {
        if (cue) {
            const audioWasPlaying = !userPaused && (!audio.paused || startingAudio);
            pauseVideo();
            if (audioWasPlaying) pause(); else resume();
        }
        else userPaused = false;
        changed();
    });
    video.addEventListener("pause", () => {
        if (internalPauses) internalPauses--;
        else if (cue) { userPaused = true; audio.pause(); }
        savePlayback();
        changed();
    });
    video.addEventListener("ended", changed);
    video.addEventListener("volumechange", () => { audio.volume = video.volume; audio.muted = video.muted; });
    video.addEventListener("timeupdate", () => {
        if (video.readyState < 1) return;
        if (session.playing && performance.now() - lastSavedAt >= 5000) savePlayback();
        if (!video.paused && !video.seeking && !cue && pack() && descriptionsEnabled()) {
            const next = pack().narrationCues.find(item => !narrated.has(item.id) &&
                lastTime < item.start && video.currentTime >= item.start);
            if (next) describe(next);
        }
        lastTime = video.currentTime;
        changed();
    });
    window.addEventListener("pagehide", savePlayback);

    function move(host) {
        if (!host || video.parentElement === host) { pendingHost = null; return true; }
        if (video.contains(document.activeElement) || document.fullscreenElement === video ||
            document.fullscreenElement?.contains(video)) {
            pendingHost = host;
            return false;
        }
        pendingHost = null;
        const state = { time: video.currentTime, playing: !video.paused,
            rate: video.playbackRate, volume: video.volume, muted: video.muted,
            captions: [...video.textTracks].map(track => track.mode) };
        if (host.moveBefore) host.moveBefore(video, null);
        else host.appendChild(video);
        video.playbackRate = state.rate;
        video.volume = state.volume;
        video.muted = state.muted;
        [...video.textTracks].forEach((track, i) => track.mode = state.captions[i]);
        if (video.readyState > 0 && video.currentTime !== state.time) video.currentTime = state.time;
        if (state.playing && video.paused) video.play().catch(() => {});
        changed();
        return true;
    }
    document.addEventListener("focusout", () => queueMicrotask(() => { if (pendingHost) move(pendingHost); }));
    document.addEventListener("fullscreenchange", () => { if (pendingHost) move(pendingHost); });
    if (navigator.mediaSession) {
        if (typeof MediaMetadata !== "undefined") {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: "Earning trust in coding agents · the recording", artist: "Lauren Tan",
            });
        }
        navigator.mediaSession.setActionHandler("play", resume);
        navigator.mediaSession.setActionHandler("pause", pause);
    }
    return session;
}

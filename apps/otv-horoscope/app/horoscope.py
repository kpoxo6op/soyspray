"""Record the ОТВ Прим horoscope from the live stream and send it to Telegram.

The channel does not list the horoscope in its programme guide. One process
keeps a short rolling video buffer of the live stream, transcribes each
finished minute of audio, and recognises the horoscope by the twelve zodiac
signs being read in order. It then cuts the episode from the buffer with a
lead-in, shrinks it under Telegram's bot upload limit and sends it.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import re
import subprocess
import threading
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG = logging.getLogger("otv-horoscope")
VLAT = timezone(timedelta(hours=10))
SEGMENT_NAME = re.compile(r"^(\d{8}T\d{6})Z\.ts$")
MONTHS = (
    "января февраля марта апреля мая июня июля августа сентября октября ноября декабря"
).split()

# Stems of the twelve signs in broadcast order, matched on lower-cased words.
# Besides the case forms, they accept the slips whisper made on the 2026-11-05
# airing ("Раком", "Левы", "Девом", "у рыб", "Фильцам" for "Тельцам").
SIGNS = (
    ("Овен", r"ов(?:ен|н\w*)"),
    ("Телец", r"(?:тел(?:ец|ьц\w*)|фил?ьц\w*)"),
    ("Близнецы", r"близнец\w*"),
    ("Рак", r"рак(?:и|ам|ами|ах|ов|у|е|ом)?"),
    ("Лев", r"(?:лев(?:ы|ам|ов)?|льв\w*)"),
    ("Дева", r"дев(?:а|ы|ам|ами|е|у|ой|ом)?"),
    ("Весы", r"вес(?:ы|ам|ах|ов)"),
    ("Скорпион", r"скорпион\w*"),
    ("Стрелец", r"стрел(?:ец|ьц\w*)"),
    ("Козерог", r"козерог\w*"),
    ("Водолей", r"водоле\w*"),
    ("Рыбы", r"рыб(?:ы|ам|ах|е|у)?"),
)
SIGN_PATTERNS = [re.compile(rf"(?<!\w){stem}(?!\w)", re.I) for _, stem in SIGNS]
TITLE = re.compile(r"гороскоп", re.I)


@dataclass(frozen=True)
class Phrase:
    """One transcribed phrase with its wall-clock start time (UTC epoch seconds)."""

    at: float
    text: str


@dataclass
class Settings:
    stream_url: str
    work: Path
    token: str
    chat_ids: list[str]
    segment_seconds: int = 60
    buffer_minutes: int = 90
    lead_in: float = 45.0
    tail: float = 60.0
    min_signs: int = 7
    sign_gap: float = 150.0
    dedup_hours: float = 10.0
    max_upload_bytes: int = 48 * 1024 * 1024
    whisper_model: str = "/models/small"
    whisper_threads: int = 2
    port: int = 8080
    chat_ids_file: Path | None = None

    def recipients(self) -> list[str]:
        """Chat ids to send to now; a mounted Secret file is re-read so new recipients
        take effect without restarting the recorder and losing its buffer."""
        if self.chat_ids_file is not None:
            try:
                return split_ids(self.chat_ids_file.read_text())
            except OSError:
                LOG.exception("could not read the chat list; using the one from start-up")
        return self.chat_ids

    @classmethod
    def from_env(cls, env=os.environ) -> Settings:
        return cls(
            stream_url=env["STREAM_URL"],
            work=Path(env.get("WORK_DIR", "/work")),
            token=env.get("TELEGRAM_BOT_TOKEN", ""),
            chat_ids=split_ids(env.get("TELEGRAM_CHAT_IDS", "")),
            segment_seconds=int(env.get("SEGMENT_SECONDS", 60)),
            buffer_minutes=int(env.get("BUFFER_MINUTES", 90)),
            lead_in=float(env.get("LEAD_IN_SECONDS", 45)),
            tail=float(env.get("TAIL_SECONDS", 60)),
            min_signs=int(env.get("MIN_SIGNS", 7)),
            sign_gap=float(env.get("SIGN_GAP_SECONDS", 150)),
            dedup_hours=float(env.get("DEDUP_HOURS", 10)),
            whisper_model=env.get("WHISPER_MODEL", "/models/small"),
            whisper_threads=int(env.get("WHISPER_THREADS", 2)),
            port=int(env.get("HTTP_PORT", 8080)),
            chat_ids_file=Path(env["TELEGRAM_CHAT_IDS_FILE"])
            if env.get("TELEGRAM_CHAT_IDS_FILE")
            else None,
        )


def split_ids(text: str) -> list[str]:
    return [c.strip() for c in text.split(",") if c.strip()]


def signs_in(text: str) -> list[int]:
    """Return the indices of the zodiac signs mentioned in a phrase, in text order."""
    found = []
    for index, pattern in enumerate(SIGN_PATTERNS):
        match = pattern.search(text)
        if match:
            found.append((match.start(), index))
    return [index for _, index in sorted(found)]


@dataclass
class Episode:
    first_sign_at: float
    last_sign_at: float
    signs: list[int] = field(default_factory=list)
    title_at: float | None = None

    @property
    def start(self) -> float:
        return self.title_at if self.title_at is not None else self.first_sign_at


class Detector:
    """Find a run of zodiac signs read in order, tolerant of a few missed words."""

    # A run may skip up to this many unheard signs between two recognised ones.
    MAX_SKIP = 3

    def __init__(self, min_signs: int = 7, sign_gap: float = 150.0):
        self.min_signs = min_signs
        self.sign_gap = sign_gap
        self.candidate: Episode | None = None
        self.last_title: float | None = None

    def feed(self, phrase: Phrase) -> None:
        if TITLE.search(phrase.text):
            self.last_title = phrase.at
        for sign in signs_in(phrase.text):
            run = self.candidate
            active = run is not None and phrase.at - run.last_sign_at <= self.sign_gap
            if active and run.signs[-1] < sign <= run.signs[-1] + 1 + self.MAX_SKIP:
                run.signs.append(sign)
                run.last_sign_at = phrase.at
            elif sign <= self.MAX_SKIP - 1 and (not active or len(run.signs) < 3):
                if active and run.signs[0] <= sign:
                    continue  # the same opening sign said again inside its paragraph
                title = self.last_title
                if title is not None and not 0 <= phrase.at - title <= 120:
                    title = None
                self.candidate = Episode(phrase.at, phrase.at, [sign], title)

    def complete(self, now: float) -> Episode | None:
        """Return a finished episode once its last sign is followed by quiet time."""
        run = self.candidate
        if not run or len(set(run.signs)) < self.min_signs or run.signs[-1] < 10:
            if run and now - run.last_sign_at > self.sign_gap:
                self.candidate = None
            return None
        if run.signs[-1] != 11 and now - run.last_sign_at <= self.sign_gap:
            return None
        self.candidate = None
        return run


def clip_window(episode: Episode, lead_in: float, tail: float) -> tuple[float, float]:
    return episode.start - lead_in, episode.last_sign_at + tail


def segment_start(path: Path) -> float | None:
    match = SEGMENT_NAME.match(path.name)
    if not match:
        return None
    moment = datetime.strptime(match.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return moment.timestamp()


def segments(directory: Path) -> list[tuple[float, Path]]:
    found = []
    for path in directory.glob("*.ts"):
        start = segment_start(path)
        if start is not None:
            found.append((start, path))
    return sorted(found)


def covering(segs: list[tuple[float, Path]], start: float, end: float) -> list[tuple[float, Path]]:
    """Pick the finished segments that overlap [start, end]; the newest one is still open."""
    chosen = []
    for index, (seg_start, path) in enumerate(segs[:-1]):
        seg_end = segs[index + 1][0]
        if seg_end > start and seg_start < end:
            chosen.append((seg_start, path))
    return chosen


def caption(episode: Episode) -> str:
    local = datetime.fromtimestamp(episode.start, VLAT)
    return f"Гороскоп ОТВ Прим, {local.day} {MONTHS[local.month - 1]}, эфир в {local:%H:%M} по Владивостоку"


def multipart(fields: dict[str, str], file_field: str, file_name: str, data: bytes):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_name}"\r\nContent-Type: video/mp4\r\n\r\n'
        ).encode()
        + data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def send_video(token: str, chat_id: str, video: Path, text: str, duration: int) -> None:
    body, content_type = multipart(
        {
            "chat_id": chat_id,
            "caption": text,
            "supports_streaming": "true",
            "duration": str(duration),
        },
        "video",
        video.name,
        video.read_bytes(),
    )
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendVideo",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError(f"Telegram refused the video: {result.get('description')}")


class State:
    """Remember sent episodes so a repeat airing or restart does not resend."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.data = json.loads(path.read_text())
        except (OSError, ValueError):
            self.data = {"sent": []}

    def recently_sent(self, at: float, hours: float) -> bool:
        return any(abs(at - sent) < hours * 3600 for sent in self.data["sent"])

    def mark(self, at: float) -> None:
        self.data["sent"] = [*self.data["sent"][-50:], at]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data))
        tmp.replace(self.path)


class Health:
    def __init__(self):
        self.lock = threading.Lock()
        self.values = {
            "last_segment": 0.0,
            "last_transcribed": 0.0,
            "episodes_found": 0,
            "episodes_sent": 0,
            "send_failures": 0,
            "last_episode": 0.0,
            "transcribe_seconds": 0.0,
        }

    def set(self, **values) -> None:
        with self.lock:
            self.values.update(values)

    def bump(self, key: str) -> None:
        with self.lock:
            self.values[key] += 1

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.values)


def serve(health: Health, port: int, now=time.time) -> http.server.ThreadingHTTPServer:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            values = health.snapshot()
            if self.path == "/healthz":
                fresh = now() - values["last_segment"] < 300
                self.send_response(200 if fresh else 503)
                self.end_headers()
                self.wfile.write(b"ok\n" if fresh else b"no recent live segment\n")
            elif self.path == "/metrics":
                body = "".join(f"otv_horoscope_{key} {value}\n" for key, value in values.items())
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                self.wfile.write(body.encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *_args):
            return

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def record_forever(settings: Settings, directory: Path) -> None:
    """Copy the live stream into minute-long MPEG-TS files named by their UTC start."""
    while True:
        command = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning",
            "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "30",
            "-rw_timeout", "30000000", "-i", settings.stream_url,
            "-map", "0:v:0", "-map", "0:a:0", "-c", "copy",
            "-f", "segment", "-segment_time", str(settings.segment_seconds),
            "-segment_format", "mpegts", "-reset_timestamps", "1", "-strftime", "1",
            str(directory / "%Y%m%dT%H%M%SZ.ts"),
        ]  # fmt: skip
        LOG.info("recording the live stream")
        result = subprocess.run(command, env={**os.environ, "TZ": "UTC"}, check=False)
        LOG.warning("recorder stopped with %s; restarting in 10 s", result.returncode)
        time.sleep(10)


def prune(directory: Path, keep_seconds: float, now: float) -> None:
    for start, path in segments(directory):
        if now - start > keep_seconds:
            path.unlink(missing_ok=True)


def audio_samples(path: Path):
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
         "-f", "f32le", "-"],
        check=True, capture_output=True,
    ).stdout  # fmt: skip
    return np.frombuffer(raw, np.float32)


def cut(settings: Settings, chosen, start: float, end: float, out: Path) -> int:
    """Join the buffer segments, trim to the window and fit the Telegram upload limit."""
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{path}'\n" for _, path in chosen))
    offset = max(0.0, start - chosen[0][0])
    duration = end - max(start, chosen[0][0])
    for height, video_kbps in ((720, 0), (480, 0), (360, 350)):
        if not video_kbps:
            budget = settings.max_upload_bytes * 8 / 1000 / duration - 96
            video_kbps = int(min(1800 if height == 720 else 900, budget * 0.92))
        if video_kbps < 200:
            continue
        subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-ss", f"{offset:.2f}", "-t", f"{duration:.2f}",
             "-vf", f"scale=-2:{height}", "-c:v", "libx264", "-preset", "veryfast",
             "-b:v", f"{video_kbps}k", "-maxrate", f"{video_kbps}k", "-bufsize", f"{2 * video_kbps}k",
             "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)],
            check=True,
        )  # fmt: skip
        if out.stat().st_size <= settings.max_upload_bytes:
            return int(duration)
    raise RuntimeError("The episode does not fit the Telegram upload limit.")


def deliver(settings: Settings, state: State, health: Health, episode: Episode, live: Path) -> None:
    health.bump("episodes_found")
    health.set(last_episode=episode.start)
    names = ", ".join(SIGNS[i][0] for i in episode.signs)
    LOG.info("horoscope at %s with %s", datetime.fromtimestamp(episode.start, VLAT), names)
    if state.recently_sent(episode.start, settings.dedup_hours):
        LOG.info("an airing within %s h was already sent; skipping", settings.dedup_hours)
        return
    start, end = clip_window(episode, settings.lead_in, settings.tail)
    give_up = time.time() + (end - start) + 900
    while True:
        segs = segments(live)
        if segs and segs[-1][0] >= end:
            break
        if time.time() > give_up:
            LOG.error("the live stream stopped before the episode ended; cutting what exists")
            segs = [*segs, (end, Path("/dev/null"))]
            break
        time.sleep(10)
    chosen = covering(segs, start, end)
    if not chosen:
        LOG.error("the buffer no longer holds this episode")
        return
    clips = settings.work / "clips"
    clips.mkdir(exist_ok=True)
    local = datetime.fromtimestamp(episode.start, VLAT)
    out = clips / f"goroskop-{local:%Y-%m-%d-%H%M}.mp4"
    duration = cut(settings, chosen, start, end, out)
    for chat_id in settings.recipients():
        try:
            send_video(settings.token, chat_id, out, caption(episode), duration)
            health.bump("episodes_sent")
        except Exception:  # noqa: BLE001 - keep recording after a delivery failure
            health.bump("send_failures")
            LOG.exception("could not send the horoscope to one chat")
    state.mark(episode.start)
    for old in sorted(clips.glob("*.mp4"))[:-5]:
        old.unlink(missing_ok=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    settings = Settings.from_env()
    live = settings.work / "live"
    live.mkdir(parents=True, exist_ok=True)
    health = Health()
    serve(health, settings.port)
    state = State(settings.work / "state.json")
    threading.Thread(target=record_forever, args=(settings, live), daemon=True).start()

    from faster_whisper import WhisperModel

    model = WhisperModel(
        settings.whisper_model, device="cpu", compute_type="int8",
        cpu_threads=settings.whisper_threads, local_files_only=True,
    )  # fmt: skip
    detector = Detector(settings.min_signs, settings.sign_gap)
    done: set[Path] = set()
    heard_until = 0.0
    while True:
        now = time.time()
        segs = segments(live)
        if segs:
            health.set(last_segment=segs[-1][0])
        for seg_start, path in segs[:-1]:
            if path in done:
                continue
            done.add(path)
            began = time.monotonic()
            try:
                pieces, _ = model.transcribe(
                    audio_samples(path), language="ru", vad_filter=True, beam_size=1
                )
                for piece in pieces:
                    phrase = Phrase(seg_start + piece.start, piece.text)
                    if signs_in(phrase.text) or TITLE.search(phrase.text):
                        local = datetime.fromtimestamp(phrase.at, VLAT)
                        LOG.info("heard at %s: %s", f"{local:%H:%M:%S}", phrase.text.strip())
                    detector.feed(phrase)
            except Exception:  # noqa: BLE001 - one bad segment must not stop detection
                LOG.exception("could not transcribe %s", path.name)
            LOG.debug("transcribed %s in %.1f s", path.name, time.monotonic() - began)
            health.set(transcribe_seconds=round(time.monotonic() - began, 1))
            heard_until = max(heard_until, seg_start + settings.segment_seconds)
            health.set(last_transcribed=seg_start)
        episode = detector.complete(heard_until)
        if episode:
            try:
                deliver(settings, state, health, episode, live)
            except Exception:  # noqa: BLE001
                health.bump("send_failures")
                LOG.exception("could not cut or send the horoscope")
        prune(live, settings.buffer_minutes * 60, now)
        done = {path for path in done if path.exists()}
        time.sleep(5)


if __name__ == "__main__":
    main()

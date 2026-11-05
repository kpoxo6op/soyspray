"""Behaviour of horoscope recognition, clipping and delivery helpers."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("horoscope", ROOT / "app/horoscope.py")
horoscope = importlib.util.module_from_spec(spec)
sys.modules["horoscope"] = horoscope
spec.loader.exec_module(horoscope)

READING = [
    "Гороскоп на шестое ноября.",
    "Овен. Овнам пора решить назревшие вопросы на работе и дома.",
    "Не принимайте решения поспешно, Овны.",
    "Телец. Сегодня удача на стороне Тельцов.",
    "Близнецам сегодня не стоит бороться с нежеланием работать.",
    "Ракам стоит отдохнуть.",
    "Львы получат хорошие новости.",
    "Девам лучше заняться мелкими делами.",
    "Весам советуют быть осторожнее с деньгами.",
    "Скорпионы встретят старого друга.",
    "Стрельцам звёзды обещают удачу.",
    "Козероги смогут продвинуться по службе.",
    "Водолеям стоит позвонить родным.",
    "Рыбам сегодня повезёт в любви.",
]


def feed(detector, lines, start=1000.0, step=20.0):
    for index, text in enumerate(lines):
        detector.feed(horoscope.Phrase(start + index * step, text))
    return start + (len(lines) - 1) * step


def test_sign_stems_cover_the_case_forms_used_on_air():
    assert horoscope.signs_in("Овнам пора, а Тельцам нет") == [0, 1]
    assert horoscope.signs_in("Львам и Девам") == [4, 5]
    assert horoscope.signs_in("Стрельцам, Козерогам и Водолеям") == [8, 9, 10]
    assert horoscope.signs_in("Рыбам повезёт") == [11]
    assert horoscope.signs_in("Хладнокровно и уверенно, левый фланг, весной") == []


def test_a_full_reading_is_one_episode_starting_at_its_title():
    detector = horoscope.Detector()
    last = feed(detector, ["Новости спорта: Адмирал победил."] + READING)
    episode = detector.complete(last + 5)
    assert episode is not None
    assert episode.signs == list(range(12))
    assert episode.start == 1020.0  # the "Гороскоп на ..." title, not the first sign
    assert episode.last_sign_at == last
    assert detector.complete(last + 500) is None


def test_missed_signs_are_tolerated_but_news_mentions_are_not_an_episode():
    detector = horoscope.Detector()
    patchy = [line for i, line in enumerate(READING) if i not in (3, 6, 9)]
    last = feed(detector, patchy)
    assert detector.complete(last + 5) is not None

    detector = horoscope.Detector()
    last = feed(detector, ["Рыбы пошли на нерест.", "Овны и Тельцы на выставке скота.", "Погода."])
    assert detector.complete(last + 1000) is None


def test_waits_for_the_reading_to_finish_when_pisces_was_not_heard():
    detector = horoscope.Detector()
    last = feed(detector, READING[:-1])
    assert detector.complete(last + 30) is None
    episode = detector.complete(last + 200)
    assert episode is not None and episode.signs[-1] == 10


def test_a_stray_late_sign_does_not_block_the_rest_of_the_reading():
    detector = horoscope.Detector()
    lines = READING[:3] + ["Рыбный рынок и рыбы."] + READING[3:]
    last = feed(detector, lines)
    episode = detector.complete(last + 5)
    assert episode is not None and len(set(episode.signs)) == 12


def test_clip_window_covers_the_lead_in_and_tail():
    episode = horoscope.Episode(first_sign_at=2000.0, last_sign_at=2300.0, signs=[0], title_at=1990)
    assert horoscope.clip_window(episode, 45, 60) == (1945.0, 2360.0)


def test_only_finished_buffer_segments_inside_the_window_are_used(tmp_path):
    names = ["20261105T100000Z.ts", "20261105T100100Z.ts", "20261105T100200Z.ts",
             "20261105T100300Z.ts", "junk.ts"]  # fmt: skip
    for name in names:
        (tmp_path / name).write_bytes(b"")
    segs = horoscope.segments(tmp_path)
    assert [path.name for _, path in segs] == names[:4]
    start = segs[0][0]
    chosen = horoscope.covering(segs, start + 90, start + 170)
    assert [path.name for _, path in chosen] == names[1:3]
    # The newest segment is still being written and is never used.
    assert horoscope.covering(segs, start + 185, start + 400) == []


def test_old_buffer_segments_are_pruned(tmp_path):
    for name in ("20261105T100000Z.ts", "20261105T110000Z.ts"):
        (tmp_path / name).write_bytes(b"")
    newest = horoscope.segment_start(tmp_path / "20261105T110000Z.ts")
    horoscope.prune(tmp_path, 1800, newest + 60)
    assert [p.name for p in tmp_path.iterdir()] == ["20261105T110000Z.ts"]


def test_caption_uses_vladivostok_time():
    episode = horoscope.Episode(1_793_930_400.0, 1_793_930_700.0, [0])  # 2026-11-06 02:00 UTC
    assert horoscope.caption(episode) == (
        "Гороскоп ОТВ Прим, 6 ноября, эфир в 12:00 по Владивостоку"
    )


def test_repeat_airings_are_sent_once_and_state_survives_restart(tmp_path):
    state = horoscope.State(tmp_path / "state.json")
    assert not state.recently_sent(10_000, 10)
    state.mark(10_000)
    again = horoscope.State(tmp_path / "state.json")
    assert again.recently_sent(10_000 + 9 * 3600, 10)
    assert not again.recently_sent(10_000 + 11 * 3600, 10)
    assert json.loads((tmp_path / "state.json").read_text())["sent"] == [10_000]


def test_telegram_upload_carries_caption_and_video_bytes():
    body, content_type = horoscope.multipart(
        {"chat_id": "42", "caption": "Гороскоп"}, "video", "clip.mp4", b"\x00\x01mp4"
    )
    boundary = content_type.split("boundary=")[1]
    assert body.endswith(f"--{boundary}--\r\n".encode())
    assert 'name="chat_id"\r\n\r\n42\r\n'.encode() in body
    assert "Гороскоп".encode() in body
    assert b'filename="clip.mp4"\r\nContent-Type: video/mp4\r\n\r\n\x00\x01mp4\r\n' in body


def test_settings_read_chat_list_and_defaults():
    settings = horoscope.Settings.from_env(
        {"STREAM_URL": "https://example.test/live.m3u8", "TELEGRAM_CHAT_IDS": "1, 2,,"}
    )
    assert settings.chat_ids == ["1", "2"]
    assert settings.segment_seconds == 60 and settings.lead_in == 45


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_cut_joins_buffer_minutes_into_one_upload_sized_clip(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    for minute in range(4):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=25",
             "-f", "lavfi", "-i", "sine=frequency=440", "-t", "6", "-c:v", "libx264",
             "-preset", "ultrafast", "-c:a", "aac", "-f", "mpegts",
             str(live / f"20261105T1000{minute * 6:02d}Z.ts")],
            check=True,
        )  # fmt: skip
    settings = horoscope.Settings("https://example.test", tmp_path, "", [], segment_seconds=6)
    segs = horoscope.segments(live)
    start, end = segs[0][0] + 3, segs[0][0] + 15
    chosen = horoscope.covering(segs, start, end)
    out = tmp_path / "clip.mp4"
    assert horoscope.cut(settings, chosen, start, end, out) == 12
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=height,codec_type",
         "-of", "json", str(out)],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    info = json.loads(probe.stdout)
    assert abs(float(info["format"]["duration"]) - 12) < 0.5
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    assert out.stat().st_size <= settings.max_upload_bytes

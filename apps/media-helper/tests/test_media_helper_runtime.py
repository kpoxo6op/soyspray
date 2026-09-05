"""Standard-library checks also run inside the immutable image without network access."""

import importlib.util
import os
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(
    os.environ.get("MEDIA_HELPER_SOURCE", Path(__file__).resolve().parents[1] / "app/app.py")
)


def load():
    spec = importlib.util.spec_from_file_location("runtime_under_check", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def programmes(helper):
    return {
        c["slug"]: [
            {
                "times": {"start": "20260901000000 +0000", "stop": "20260901010000 +0000"},
                "title": "Fixture",
            }
        ]
        for c in helper.epg_channels(helper.Handler.catalog)
    }


class RuntimeChecks(unittest.TestCase):
    def test_cold_and_stale_guide_reads_do_not_wait_for_the_upstream(self):
        for cached in (False, True):
            for path in ("/xmltv.xml", "/ready"):
                with self.subTest(cached=cached, path=path):
                    self.check_nonblocking(cached, path)

    def check_nonblocking(self, cached, endpoint):
        helper = load()
        good = programmes(helper)
        previous = helper.build_xmltv(helper.Handler.catalog, good) if cached else None
        helper.GUIDE_CACHE.update(xml=previous, programmes=good if cached else None)
        entered, release, returned = threading.Event(), threading.Event(), threading.Event()
        calls = []

        def fetch(_catalog):
            calls.append(True)
            entered.set()
            if not release.wait(5):
                raise TimeoutError("Fixture was not released")
            return good

        class Request:
            path = endpoint
            catalog = helper.Handler.catalog

            def send(self, status, body, content_type):
                self.response = status, body, content_type

        request = Request()

        def read():
            helper.Handler.do_GET(request)
            returned.set()

        reader = threading.Thread(target=read)
        with patch.object(helper, "fetch_epg_lite", fetch):
            try:
                helper.start_guide_refresh(helper.Handler.catalog)
                self.assertTrue(entered.wait(2))
                reader.start()
                self.assertTrue(returned.wait(2), "Guide read blocked behind its refresh")
                self.assertEqual(request.response[0], 200 if cached else 503)
                if cached:
                    self.assertEqual(
                        request.response[1],
                        previous.encode() if endpoint == "/xmltv.xml" else b"ok\n",
                    )
                for _ in range(20):
                    helper.start_guide_refresh(helper.Handler.catalog)
                self.assertEqual(len(calls), 1)
            finally:
                release.set()
                if reader.ident is not None:
                    reader.join(3)
                for thread in threading.enumerate():
                    if thread.name == "guide-refresh":
                        thread.join(3)
        self.assertFalse(helper.GUIDE_REFRESHING)
        self.assertEqual(
            helper.GUIDE_CACHE["xml"], helper.build_xmltv(helper.Handler.catalog, good)
        )

    def test_failed_or_truncated_refresh_keeps_the_complete_cache(self):
        for error in (OSError("offline"), EOFError("truncated gzip"), ValueError("invalid input")):
            with self.subTest(error=type(error).__name__):
                helper = load()
                with patch.object(helper, "fetch_epg_lite", return_value=programmes(helper)):
                    first = helper.guide_snapshot(helper.Handler.catalog, now=0)
                with patch.object(helper, "fetch_epg_lite", side_effect=error) as fetch:
                    self.assertEqual(
                        helper.guide_snapshot(helper.Handler.catalog, now=21601), first
                    )
                    self.assertEqual(
                        helper.guide_snapshot(helper.Handler.catalog, now=21602), first
                    )
                    self.assertEqual(fetch.call_count, 1)

    def test_fresh_cache_and_failure_backoff_start_no_worker(self):
        helper = load()
        for key in ("expires_at", "retry_at"):
            with self.subTest(key=key), patch.object(helper.threading, "Thread") as worker:
                helper.GUIDE_CACHE.update(expires_at=0, retry_at=0)
                helper.GUIDE_CACHE[key] = time.monotonic() + 300
                helper.start_guide_refresh(helper.Handler.catalog)
                worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()

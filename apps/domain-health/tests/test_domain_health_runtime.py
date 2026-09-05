"""Run the same standard-library checks locally and inside the immutable image."""

import importlib.util
import json
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

SOURCE = Path(
    os.environ.get(
        "DOMAIN_HEALTH_SOURCE",
        Path(__file__).resolve().parents[1] / "app/domain-health-exporter.py",
    )
)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(
            os.environ,
            {
                "DOMAIN_NAME": "example.test",
                "CLOUDFLARE_API_TOKEN": "synthetic-provider",
                "HEALTHCHECKS_PING_URL": "https://healthchecks.example/test",
                "EXPECTED_NAMESERVERS": "a.ns.example,b.ns.example",
                "CHECK_INTERVAL_SECONDS": "60",
            },
        ):
            spec = importlib.util.spec_from_file_location("domain_health_runtime", SOURCE)
            self.runtime = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.runtime)

    def test_expiry_supports_rdap_events_and_offsets(self):
        expected = self.runtime.parse_timestamp("2027-03-11T00:00:00Z")
        self.assertEqual(
            self.runtime.extract_rdap_expiry_timestamp(
                {
                    "events": [
                        {"eventAction": "expiration", "eventDate": "2027-03-11T12:00:00+12:00"}
                    ]
                }
            ),
            expected,
        )
        with self.assertRaises(RuntimeError):
            self.runtime.extract_rdap_expiry_timestamp({"events": []})
        with patch.object(
            self.runtime, "request_json", return_value={"expires": "2027-03-11T00:00:00Z"}
        ):
            self.runtime.check_rdap(expected + 1)
        self.assertIn(
            b'domain_health_rdap_expiry_days{domain="example.test"} -1.0',
            self.runtime.STATE.render_prometheus(),
        )

    def test_provider_facts_keep_missing_inactive_and_wrong_nameservers_visible(self):
        for result, expected in [
            ([], 'domain_health_cloudflare_zone_exists{domain="example.test"} 0.0'),
            (
                [
                    {
                        "name": "example.test",
                        "status": "pending",
                        "name_servers": ["A.NS.EXAMPLE.", "b.ns.example"],
                    }
                ],
                'domain_health_cloudflare_zone_active{domain="example.test"} 0.0',
            ),
            (
                [
                    {
                        "name": "example.test",
                        "status": "active",
                        "name_servers": ["other.ns.example"],
                    }
                ],
                'domain_health_cloudflare_nameservers_match{domain="example.test"} 0.0',
            ),
        ]:
            with (
                self.subTest(result=result),
                patch.object(
                    self.runtime, "request_json", return_value={"success": True, "result": result}
                ),
            ):
                self.runtime.check_cloudflare(time.time())
            self.assertIn(expected.encode(), self.runtime.STATE.render_prometheus())
        with patch.object(self.runtime, "request_json", return_value={"success": False}):
            with self.assertRaises(RuntimeError):
                self.runtime.check_cloudflare(time.time())

    def test_public_nameservers_are_normalized_and_mismatches_remain_visible(self):
        for names, expected in [(["B.NS.EXAMPLE.", "a.ns.example"], "1.0"), ([], "0.0")]:
            with patch.object(
                self.runtime,
                "request_json",
                return_value={"Answer": [{"data": name} for name in names]},
            ):
                self.runtime.check_public_dns(time.time())
            self.assertIn(
                f'domain_health_public_dns_nameservers_match{{domain="example.test"}} {expected}'.encode(),
                self.runtime.STATE.render_prometheus(),
            )

    def test_failed_check_keeps_the_previous_success_timestamp(self):
        self.runtime.update_check_status("rdap", True, 100)
        self.runtime.update_check_status("rdap", False, 200)
        metrics = self.runtime.STATE.render_prometheus()
        self.assertIn(
            b'domain_health_check_success{check="rdap",domain="example.test"} 0.0', metrics
        )
        self.assertIn(
            b'domain_health_last_check_timestamp_seconds{check="rdap",domain="example.test"} 200.0',
            metrics,
        )
        self.assertIn(
            b'domain_health_last_success_timestamp_seconds{check="rdap",domain="example.test"} 100.0',
            metrics,
        )

    def test_http_probe_detects_initial_failure_success_and_stale_checks(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), self.runtime.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(url + "/healthz", timeout=3)
            self.assertEqual(error.exception.code, 503)
            self.runtime.STATE.finish_run(True)
            with urlopen(url + "/healthz", timeout=3) as response:
                self.assertEqual(response.read(), b"ok\n")
            with urlopen(url + "/metrics", timeout=3) as response:
                self.assertTrue(response.headers["Content-Type"].startswith("text/plain"))
            with patch.object(self.runtime.time, "time", return_value=time.time() + 121):
                self.assertFalse(self.runtime.STATE.get_health())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_json_requests_work_without_third_party_packages(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"accept": self.headers["Accept"]}).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(
                self.runtime.request_json(f"http://127.0.0.1:{server.server_port}"),
                {"accept": "application/json"},
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_scheduled_failure_reports_to_the_existing_check_and_marks_unhealthy(self):
        with (
            patch.object(self.runtime, "check_rdap", side_effect=RuntimeError("synthetic outage")),
            patch.object(self.runtime, "check_cloudflare"),
            patch.object(self.runtime, "check_public_dns"),
            patch.object(self.runtime, "ping_healthchecks") as ping,
            patch.object(self.runtime.time, "sleep", side_effect=StopIteration),
            self.assertRaises(StopIteration),
        ):
            self.runtime.run_checks_forever()
        ping.assert_called_once_with("/fail")
        self.assertFalse(self.runtime.STATE.get_health())


if __name__ == "__main__":
    unittest.main()

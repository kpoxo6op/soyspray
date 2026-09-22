import importlib.util
import sys
import unittest
from pathlib import Path

APP = Path(__file__).parents[1] / "app"
sys.path.insert(0, str(APP))
SPEC = importlib.util.spec_from_file_location("cluster_diagnosis_telegram", APP / "telegram.py")
telegram = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(telegram)


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, payload, timeout):
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        response = self.responses.pop(0) if self.responses else (200, {"ok": True})
        if isinstance(response, Exception):
            raise response
        return response


class SendTests(unittest.TestCase):
    def test_a_message_is_sent_as_plain_text_to_the_fixed_chat(self):
        transport = Transport([(200, {"ok": True, "result": {"message_id": 1}})])
        result = telegram.Telegram("token", "336642153", transport=transport).send("hello")
        self.assertEqual(result["status"], "sent")
        payload = transport.calls[0]["payload"]
        self.assertEqual(payload["chat_id"], "336642153")
        self.assertEqual(payload["text"], "hello")
        self.assertTrue(payload["disable_web_page_preview"])
        self.assertNotIn("parse_mode", payload)

    def test_the_token_appears_only_in_the_request_url(self):
        transport = Transport([(200, {"ok": True})])
        telegram.Telegram("123:secret", "1", transport=transport).send("hello")
        self.assertIn("123:secret", transport.calls[0]["url"])

    def test_a_rejection_is_reported_without_delivering(self):
        result = telegram.Telegram(
            "token",
            "1",
            transport=Transport([(400, {"ok": False, "description": "chat not found"})]),
        ).send("hello")
        self.assertEqual(result["status"], "unavailable")
        self.assertIn("chat not found", result["cause"])

    def test_a_network_fault_is_reported(self):
        result = telegram.Telegram("token", "1", transport=Transport([OSError("offline")])).send(
            "x"
        )
        self.assertEqual(result["cause"], "network")

    def test_missing_credentials_never_attempt_a_send(self):
        transport = Transport([(200, {"ok": True})])
        client = telegram.Telegram("", "1", transport=transport)
        self.assertFalse(client.healthy())
        self.assertEqual(client.send("x")["cause"], "no-credentials")
        self.assertEqual(transport.calls, [])

    def test_a_long_message_is_trimmed_on_a_line_boundary(self):
        message = "\n".join(f"line {index}" for index in range(2000))
        fitted = telegram.fit_message(message)
        self.assertLessEqual(len(fitted), telegram.MAX_MESSAGE_CHARS)
        self.assertTrue(fitted.endswith("... (truncated)"))

    def test_a_short_message_is_unchanged(self):
        self.assertEqual(telegram.fit_message("short"), "short")

    def test_an_oversized_response_is_not_parsed(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size=None):
                return b"x" * (size or 0)

        original = telegram.urlopen
        telegram.urlopen = lambda request, timeout: Response()
        try:
            status, payload = telegram.default_transport("https://example.test", {}, 5.0)
        finally:
            telegram.urlopen = original
        self.assertEqual(status, 200)
        self.assertIsNone(payload)


class OutboxTests(unittest.TestCase):
    def test_the_outbox_is_bounded_in_count(self):
        outbox = []
        for index in range(telegram.MAX_OUTBOX + 5):
            outbox = telegram.enqueue(outbox, {"message": f"m{index}", "queued_at": 0})
        self.assertEqual(len(outbox), telegram.MAX_OUTBOX)
        self.assertEqual(outbox[-1]["message"], f"m{telegram.MAX_OUTBOX + 4}")

    def test_an_old_entry_is_expired(self):
        entry = {"message": "m", "queued_at": 1000.0}
        self.assertFalse(telegram.expired(entry, 1000.0 + 60))
        self.assertTrue(telegram.expired(entry, 1000.0 + telegram.MAX_OUTBOX_AGE_SECONDS + 1))

    def test_an_entry_without_a_time_is_expired(self):
        self.assertTrue(telegram.expired({"message": "m"}, 0.0))


if __name__ == "__main__":
    unittest.main()

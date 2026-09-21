import importlib.util
import json
import unittest
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

MODULE_PATH = Path(__file__).parents[1] / "app" / "classify.py"
SPEC = importlib.util.spec_from_file_location("cluster_diagnosis_classify", MODULE_PATH)
classify = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(classify)

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def body(labels, model="jev-1.13.0", **extra):
    return {
        "tier": "fast",
        "model": model,
        "modelsUsed": [model],
        "results": [
            {
                "label": label,
                "confidence": confidence,
                "scores": {name: 0.0 for name in classify.LABELS} | {label: confidence},
                "model": model,
                "escalated": False,
            }
            for label, confidence in labels
        ],
        "usage": {"classifications": len(labels), "escalated": 0, "ms": 120},
        **extra,
    }


class ClientStub:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, payload, timeout):
        self.calls.append(payload)
        response = self.responses.pop(0) if self.responses else (0, None)
        if isinstance(response, Exception):
            raise response
        return response


class EchoClient:
    """Answer every request with one result per input, in input order."""

    def __init__(self, label=classify.NORMAL, confidence=0.9, model="jev-1.13.0"):
        self.label = label
        self.confidence = confidence
        self.model = model
        self.calls = []

    def __call__(self, payload, timeout):
        self.calls.append(payload)
        return 200, body(
            [(self.label, self.confidence) for _ in payload["inputs"]], model=self.model
        )


def classifier(client, state=None, **kwargs):
    return classify.Classifier(
        state if state is not None else {},
        client=client,
        now=lambda: NOW,
        sleep=lambda _seconds: None,
        **kwargs,
    )


class SuccessTests(unittest.TestCase):
    def test_labels_and_model_are_reported(self):
        client = ClientStub([(200, body([(classify.STORAGE_FAILURE, 0.98)]))])
        report = classifier(client).classify(["failed to mount volume"])
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["model"], "jev-1.13.0")
        self.assertEqual(report["results"][0]["label"], classify.STORAGE_FAILURE)
        self.assertEqual(report["counts"], {classify.STORAGE_FAILURE: 1})
        self.assertEqual(report["classifications"], 1)

    def test_request_follows_the_published_contract(self):
        client = ClientStub([(200, body([(classify.UNKNOWN, 0.9)]))])
        classifier(client).classify(["something happened"])
        payload = client.calls[0]
        self.assertEqual(payload["tier"], "fast")
        self.assertEqual(payload["labels"], list(classify.LABELS))
        self.assertGreaterEqual(len(payload["labels"]), 2)
        self.assertLessEqual(len(payload["labels"]), 100)
        self.assertIn("unknown", payload["instructions"].lower())
        self.assertEqual(payload["inputs"], ["something happened"])

    def test_duplicate_texts_are_sent_once(self):
        client = ClientStub([(200, body([(classify.NORMAL, 0.9)]))])
        report = classifier(client).classify(["same line", "same   line", "same line"])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["inputs"], ["same line"])
        self.assertEqual(report["classifications"], 1)

    def test_cache_prevents_a_second_request(self):
        state = {}
        client = ClientStub([(200, body([(classify.NETWORK_FAILURE, 0.91)]))])
        first = classifier(client, state).classify(["lookup db on 10.233.0.3:53 failed"])
        second = classifier(client, state).classify(["lookup db on 10.233.0.3:53 failed"])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(second["status"], "cached")
        self.assertEqual(second["results"][0]["source"], "cache")
        self.assertEqual(first["counts"], second["counts"])

    def test_batch_is_split_but_bounded(self):
        client = EchoClient()
        texts = [
            f"line {index}" for index in range(classify.BATCH_MAX * classify.REQUESTS_PER_RUN + 5)
        ]
        report = classifier(client, {}).classify(texts)
        self.assertEqual(len(client.calls), classify.REQUESTS_PER_RUN)
        self.assertEqual(report["skipped"], 5)
        self.assertEqual(report["cause"], "batch-limit")
        self.assertEqual(report["classifications"], classify.BATCH_MAX * classify.REQUESTS_PER_RUN)

    def test_batches_are_sequential_and_bounded_per_call(self):
        client = EchoClient()
        texts = [f"line {index}" for index in range(classify.BATCH_MAX + 3)]
        classifier(client).classify(texts)
        self.assertEqual([len(call["inputs"]) for call in client.calls], [classify.BATCH_MAX, 3])


class UncertaintyTests(unittest.TestCase):
    def test_low_confidence_becomes_unknown_with_the_hint_kept(self):
        client = ClientStub([(200, body([(classify.STORAGE_FAILURE, 0.4)]))])
        report = classifier(client).classify(["maybe a volume problem"])
        item = report["results"][0]
        self.assertEqual(item["label"], classify.UNKNOWN)
        self.assertEqual(item["hint"], classify.STORAGE_FAILURE)
        self.assertEqual(report["unknown"], 1)

    def test_unscored_response_becomes_unknown(self):
        payload = body([(classify.NORMAL, 1.0)])
        payload["results"][0]["unscored"] = "input is not natural language"
        payload["results"][0]["confidence"] = None
        client = ClientStub([(200, payload)])
        report = classifier(client).classify(["### ?? 12"])
        self.assertEqual(report["results"][0]["label"], classify.UNKNOWN)
        self.assertEqual(report["results"][0]["source"], "fallback")

    def test_null_confidence_becomes_unknown(self):
        payload = body([(classify.NORMAL, 0.9)])
        payload["results"][0]["confidence"] = None
        report = classifier(ClientStub([(200, payload)])).classify(["a line"])
        self.assertEqual(report["results"][0]["label"], classify.UNKNOWN)

    def test_label_outside_the_requested_set_becomes_unknown(self):
        payload = body([("root cause found", 0.99)])
        report = classifier(ClientStub([(200, payload)])).classify(["a line"])
        self.assertEqual(report["results"][0]["label"], classify.UNKNOWN)
        self.assertEqual(report["results"][0]["source"], "fallback")

    def test_summary_is_a_hint_and_never_an_authority(self):
        client = ClientStub([(200, body([(classify.NORMAL, 0.97)]))])
        report = classifier(client).classify(["recovered"])
        value = classify.summarize(report)
        self.assertEqual(value["authority"], "hint-only")
        self.assertEqual(value["dominant"], classify.NORMAL)

    def test_summary_reports_unknown_when_every_label_is_unknown(self):
        client = ClientStub([(200, body([(classify.UNKNOWN, 0.95)]))])
        value = classify.summarize(classifier(client).classify(["???"]))
        self.assertEqual(value["dominant"], classify.UNKNOWN)
        self.assertEqual(value["unknown"], 1)
        self.assertEqual(value["dominant_confidence"], 0.95)


class FailureTests(unittest.TestCase):
    def test_malformed_response_is_unavailable_and_unknown(self):
        report = classifier(ClientStub([(200, {"results": []})])).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["cause"], "malformed")
        self.assertEqual(report["results"][0]["label"], classify.UNKNOWN)

    def test_non_json_body_is_unavailable(self):
        report = classifier(ClientStub([(200, "not json")])).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["results"][0]["source"], "fallback")

    def test_retry_after_429_then_success(self):
        client = ClientStub(
            [
                (429, {"error": "rate limited", "retry_after": 0.1}),
                (200, body([(classify.NORMAL, 0.9)])),
            ]
        )
        report = classifier(client).classify(["a line"])
        self.assertEqual(report["status"], "ok")
        self.assertEqual(len(client.calls), 2)

    def test_persistent_429_is_unavailable(self):
        client = ClientStub([(429, {})] * 6)
        report = classifier(client).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["cause"], "http-429")
        self.assertEqual(len(client.calls), classify.MAX_RETRIES + 1)

    def test_5xx_is_unavailable(self):
        client = ClientStub([(503, {})] * 6)
        report = classifier(client).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["cause"], "http-503")

    def test_network_outage_is_unavailable(self):
        client = ClientStub([URLError("offline")] * 6)
        report = classifier(client).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["cause"], "network")

    def test_client_error_is_not_retried(self):
        client = ClientStub([(422, {"error": "bad labels"})])
        report = classifier(client).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["cause"], "http-422")
        self.assertEqual(len(client.calls), 1)

    def test_no_request_when_the_daily_quota_is_spent(self):
        state = {"quota": {NOW.date().isoformat(): classify.DAILY_CLASSIFICATION_LIMIT}}
        client = ClientStub([(200, body([(classify.NORMAL, 0.9)]))])
        report = classifier(client, state).classify(["a line"])
        self.assertEqual(report["status"], "quota-exhausted")
        self.assertEqual(client.calls, [])
        self.assertEqual(report["results"][0]["label"], classify.UNKNOWN)

    def test_payload_limit_is_unavailable(self):
        client = ClientStub([(200, body([]))])
        with unittest.mock.patch.object(classify, "MAX_PAYLOAD_BYTES", 64):
            report = classifier(client).classify(["x" * 400])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["cause"], "payload-limit")
        self.assertEqual(client.calls, [])

    def test_model_substitution_is_flagged(self):
        client = ClientStub([(200, body([(classify.NORMAL, 0.9)], model="some-other-model"))])
        report = classifier(client).classify(["a line"])
        self.assertTrue(report["model_substitution"])
        self.assertEqual(report["model"], "some-other-model")

    def test_failure_does_not_raise(self):
        report = classifier(ClientStub([RuntimeError("boom")])).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["results"][0]["label"], classify.UNKNOWN)


class BoundTests(unittest.TestCase):
    """The advertised limits must be bounds, not estimates."""

    def test_quota_is_reserved_before_dispatch_and_trims_the_batch(self):
        limit = 5
        state = {"quota": {NOW.date().isoformat(): 2}}
        client = EchoClient()
        with unittest.mock.patch.object(classify, "DAILY_CLASSIFICATION_LIMIT", limit):
            report = classifier(client, state).classify([f"line {index}" for index in range(10)])
        self.assertEqual([len(call["inputs"]) for call in client.calls], [limit - 2])
        self.assertEqual(report["cause"], "quota-trimmed")
        self.assertLessEqual(state["quota"][NOW.date().isoformat()], limit)

    def test_an_ambiguous_completion_still_charges_the_reservation(self):
        state = {}
        client = ClientStub([(200, None)])
        with unittest.mock.patch.object(classify, "DAILY_CLASSIFICATION_LIMIT", 50):
            report = classifier(client, state).classify(["a line"])
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(state["quota"][NOW.date().isoformat()], 1)

    def test_an_oversized_response_is_not_parsed(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size=None):
                return b"x" * (size or 0)

        with unittest.mock.patch.object(classify, "urlopen", lambda request, timeout: Response()):
            status, payload = classify.default_client({}, 5.0)
        self.assertEqual(status, 200)
        self.assertIsNone(payload)

    def test_the_wall_clock_stops_a_second_batch(self):
        clock = {"now": 0.0}

        def monotonic():
            clock["now"] += 10.0
            return clock["now"]

        client = EchoClient()
        with unittest.mock.patch.object(classify.time, "monotonic", monotonic):
            report = classifier(client, {}, budget_seconds=25.0).classify(
                [f"line {index}" for index in range(classify.BATCH_MAX + 1)]
            )
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(report["status"], "partial")

    def test_partial_keeps_the_results_it_already_has(self):
        report = classifier(ClientStub([(200, body([(classify.NORMAL, 0.9)]))])).classify(
            ["a line"]
        )
        self.assertEqual(report["counts"], {classify.NORMAL: 1})


class BookkeepingTests(unittest.TestCase):
    def test_quota_counts_only_provider_classifications(self):
        state = {}
        client = ClientStub([(200, body([(classify.NORMAL, 0.9), (classify.NORMAL, 0.9)]))])
        engine = classifier(client, state)
        engine.classify(["one", "two"])
        engine.classify(["one", "two"])
        self.assertEqual(state["quota"][NOW.date().isoformat()], 2)

    def test_cache_is_pruned_to_the_bound(self):
        state = {}
        client = ClientStub([(200, body([(classify.NORMAL, 0.9)] * 10))])
        with unittest.mock.patch.object(classify, "MAX_CACHE_ENTRIES", 4):
            classifier(client, state).classify([f"line {index}" for index in range(10)])
        self.assertEqual(len(state["classifier_cache"]), 4)

    def test_metrics_record_failures_and_unknowns(self):
        state = {}
        classifier(ClientStub([(500, {})] * 6), state).classify(["a line"])
        self.assertEqual(state["metrics"]["classifier_failure_total"], 1)
        self.assertEqual(state["metrics"]["classifier_unknown_total"], 1)

    def test_text_is_normalized_and_bounded(self):
        self.assertEqual(classify.normalize_text("a\n\tb   c"), "a b c")
        self.assertEqual(len(classify.normalize_text("x" * 5000)), classify.MAX_TEXT_CHARS)
        self.assertNotIn("\x00", classify.normalize_text("a\x00b"))

    def test_empty_texts_are_ignored(self):
        client = ClientStub([])
        report = classifier(client).classify(["", "   ", "\n"])
        self.assertEqual(client.calls, [])
        self.assertEqual(report["results"], [])


class TransportTests(unittest.TestCase):
    def test_default_client_sends_a_real_user_agent_and_json(self):
        captured = {}

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, _size=None):
                return json.dumps(body([(classify.NORMAL, 0.9)])).encode()

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        with unittest.mock.patch.object(classify, "urlopen", fake_urlopen):
            status, payload = classify.default_client({"labels": ["a", "b"], "inputs": ["x"]}, 5.0)
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"][0]["label"], classify.NORMAL)
        headers = {key.lower(): value for key, value in captured["request"].headers.items()}
        self.assertEqual(headers["user-agent"], classify.USER_AGENT)
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(captured["request"].method, "POST")

    def test_default_client_reads_an_error_body(self):
        def fake_urlopen(request, timeout):
            raise HTTPError(
                classify.JEV_URL,
                429,
                "Too Many Requests",
                {},
                io_bytes(b'{"error":"rate limited"}'),
            )

        with unittest.mock.patch.object(classify, "urlopen", fake_urlopen):
            status, payload = classify.default_client({}, 5.0)
        self.assertEqual(status, 429)
        self.assertEqual(payload["error"], "rate limited")

    def test_default_client_tolerates_an_unreadable_error_body(self):
        def fake_urlopen(request, timeout):
            raise HTTPError(classify.JEV_URL, 502, "Bad Gateway", {}, io_bytes(b"<html>"))

        with unittest.mock.patch.object(classify, "urlopen", fake_urlopen):
            status, payload = classify.default_client({}, 5.0)
        self.assertEqual(status, 502)
        self.assertIsNone(payload)

    def test_endpoint_is_the_published_https_route(self):
        self.assertEqual(classify.JEV_URL, "https://classifier.dev")
        self.assertIn("soyspray", classify.USER_AGENT)


def io_bytes(value):
    import io

    return io.BytesIO(value)


if __name__ == "__main__":
    unittest.main()

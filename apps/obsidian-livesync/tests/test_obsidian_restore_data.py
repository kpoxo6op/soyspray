import copy
import importlib

import pytest

check = importlib.import_module("apps.obsidian-livesync.check_restore")


def payload(*docs):
    return {"rows": [{"id": doc["_id"], "doc": doc} for doc in docs]}


def note(name="note", **changes):
    return {
        "_id": name,
        "_rev": "1-note",
        "type": "plain",
        "path": "note.md",
        "size": len("Привет\n".encode()),
        "children": ["chunk"],
        **changes,
    }


def chunk():
    return {"_id": "chunk", "type": "leaf", "data": "Привет\n"}


def test_plain_notes_use_utf8_bytes_and_legacy_eden_chunks():
    record = note(children=["eden"], eden={"eden": {"data": "Привет\n"}})
    report, incomplete = check.inspect_documents(payload(record, note("second"), chunk()))
    assert not incomplete
    assert report["readable_plain_notes"] == 2
    assert report["readable_plain_bytes"] == 2 * len("Привет\n".encode())
    assert report["complete_note_recovery"]["value"] == "passed"
    assert report["attachment_recovery"]["value"] == "unknown"
    assert "Привет" not in str(report)


@pytest.mark.parametrize(
    "change",
    [
        {"size": 2},
        {"size": -1},
        {"children": "chunk"},
        {"children": [None]},
        {"eden": []},
        {"path": None},
    ],
)
def test_invalid_content_cannot_pass(change):
    with pytest.raises(ValueError):
        check.inspect_documents(payload(note(**change), chunk()))


def test_deleted_notes_and_binary_documents_do_not_count_as_verified_plain_notes():
    report, _ = check.inspect_documents(
        payload(
            note(),
            chunk(),
            note("deleted", deleted=True),
            note("binary", type="newnote"),
            note("old", type="notes"),
        )
    )
    assert report["readable_plain_notes"] == 1
    assert report["active_binary_documents"] == report["legacy_note_documents"] == 1
    assert (
        report["complete_note_recovery"]["value"]
        == report["attachment_recovery"]["value"]
        == "unknown"
    )


def test_only_the_same_incomplete_live_revision_can_explain_missing_chunks():
    incomplete = note("broken", children=["missing"])
    restored = payload(note(), chunk(), incomplete)
    report, missing = check.inspect_documents(restored)
    assert report["readable_plain_notes"] == report["unreadable_plain_notes"] == 1
    assert report["complete_note_recovery"]["value"] == "unknown"
    assert check.verify_existing_gaps(missing, restored, restored) == 1
    for live in (
        payload(note(), chunk()),
        payload(note(), chunk(), {**incomplete, "_rev": "2-new"}),
        payload(note(), chunk(), incomplete, {"_id": "missing", "data": "exists"}),
    ):
        with pytest.raises(ValueError):
            check.verify_existing_gaps(missing, restored, live)


def test_metadata_only_or_incomplete_snapshots_do_not_prove_note_recovery():
    for data in (
        payload(),
        payload(note("broken", children=["missing"])),
        payload(note("attachment", type="newnote"), chunk()),
    ):
        with pytest.raises(ValueError, match="readable"):
            check.inspect_documents(data)


def test_duplicate_or_incomplete_couchdb_rows_are_rejected():
    for data in (
        payload(note(), note()),
        {"rows": [{"id": "missing", "doc": None}]},
        {"rows": [{"id": "wrong", "doc": note()}]},
    ):
        with pytest.raises(ValueError):
            check.inspect_documents(data)


def test_readable_chunks_must_contain_text():
    invalid = copy.deepcopy(chunk())
    invalid["data"] = None
    with pytest.raises(ValueError, match="unreadable"):
        check.inspect_documents(payload(note(), invalid))


@pytest.mark.parametrize(
    "failure", [None, "forward", "identity", "changed", "lost-chunk", "known-gap"]
)
def test_authenticated_reads_use_only_the_bound_port_and_stop_the_forward(
    tmp_path, monkeypatch, failure
):
    import io
    import json
    from urllib.parse import urlparse

    calls = []
    stopped = []
    good = payload(note(), chunk())
    broken = note("broken", children=["missing"])
    restored = payload(note(), chunk(), broken) if failure in {"lost-chunk", "known-gap"} else good

    class Forward:
        def poll(self):
            return 1 if failure == "forward" else None

        def terminate(self):
            stopped.append(True)

        def wait(self, timeout):
            return 0

    def start(args, **kwargs):
        assert args[-1] == ":5984"
        assert "--address=127.0.0.1" in args
        if failure != "forward":
            kwargs["stdout"].write("Forwarding from 127.0.0.1:37931 -> 5984\n")
            kwargs["stdout"].flush()
        return Forward()

    class Client:
        def open(self, request, timeout):
            calls.append(request.full_url)
            address = urlparse(request.full_url)
            assert request.get_header("Authorization").startswith("Basic ")
            assert address.netloc in {"127.0.0.1:37931", "obsidian.soyspray.vip"}
            if address.netloc == "obsidian.soyspray.vip":
                response = (
                    restored
                    if failure == "known-gap"
                    else payload(note(), chunk(), broken, {"_id": "missing", "data": "exists"})
                )
            elif address.path == "/_session":
                response = {
                    "userCtx": {"name": None if failure == "identity" else "synthetic-user"}
                }
            elif address.path.endswith("_all_docs"):
                response = restored
            else:
                response = {
                    "update_seq": "changed"
                    if failure == "changed" and len(calls) > 3
                    else "original"
                }
            return io.StringIO(json.dumps(response))

    monkeypatch.setattr(check.subprocess, "Popen", start)
    monkeypatch.setattr(check.urllib.request, "build_opener", lambda *args: Client())
    inputs = {"adminUsername": "synthetic-user", "adminPassword": "synthetic-password"}
    if failure not in {None, "known-gap"}:
        with pytest.raises(ValueError):
            check.check_restored_notes("restore-test", tmp_path, {}, inputs)
    else:
        result = check.check_restored_notes("restore-test", tmp_path, {}, inputs)
        assert result["couchdb_authenticated_read"]
        assert result["readable_plain_notes"] == 1
        if failure == "known-gap":
            assert result["pre_existing_missing_chunks"] == 1
    assert stopped == [True]
    if failure == "forward":
        assert calls == []
    assert "synthetic-password" not in (tmp_path / "port-forward.log").read_text()

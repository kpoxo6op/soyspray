"""Read restored CouchDB notes without changing the live vault or writing note content."""

import base64
import json
import re
import subprocess
import time
import urllib.request

from scripts.restore_common import require


def documents(payload):
    rows = payload.get("rows", [])
    require(isinstance(rows, list), "CouchDB returned invalid document rows.")
    result = {}
    for row in rows:
        document = row.get("doc")
        require(
            isinstance(document, dict)
            and row.get("id") == document.get("_id")
            and row["id"] not in result,
            "CouchDB returned incomplete or duplicate documents.",
        )
        result[row["id"]] = document
    return result


def missing_chunks(note, docs):
    return {key for key in note["children"] if key not in docs and key not in note.get("eden", {})}


def inspect_documents(payload):
    docs = documents(payload)
    active = [doc for doc in docs.values() if not doc.get("deleted") and not doc.get("_deleted")]
    notes = [doc for doc in active if doc.get("type") == "plain"]
    incomplete = []
    readable = 0
    byte_count = 0
    for note in notes:
        require(
            isinstance(note.get("children"), list)
            and all(isinstance(key, str) for key in note["children"])
            and isinstance(note.get("eden", {}), dict)
            and isinstance(note.get("path"), str)
            and isinstance(note.get("size"), int)
            and note["size"] >= 0,
            "A restored note has invalid content metadata.",
        )
        if missing_chunks(note, docs):
            incomplete.append(note)
            continue
        pieces = [docs[key] if key in docs else note["eden"][key] for key in note["children"]]
        require(
            all(isinstance(piece, dict) and isinstance(piece.get("data"), str) for piece in pieces),
            "A restored note has an unreadable content chunk.",
        )
        size = len("".join(piece["data"] for piece in pieces).encode("utf-8"))
        require(size == note["size"], "Restored note content has the wrong byte length.")
        readable += 1
        byte_count += size
    require(readable > 0, "This snapshot proves no readable plain notes.")
    attachments = sum(doc.get("type") == "newnote" for doc in active)
    legacy = sum(doc.get("type") == "notes" for doc in active)
    report = {
        "restored_documents": len(docs),
        "active_plain_notes": len(notes),
        "readable_plain_notes": readable,
        "readable_plain_bytes": byte_count,
        "unreadable_plain_notes": len(incomplete),
        "active_binary_documents": attachments,
        "legacy_note_documents": legacy,
        "attachment_recovery": {
            "value": "unknown",
            "cause": "This snapshot has no active binary attachment documents."
            if not attachments
            else "Binary attachment decoding is not covered by this plain-note check.",
        },
        "complete_note_recovery": {
            "value": "unknown",
            "cause": "Some active notes have missing chunks or use a legacy format.",
        }
        if incomplete or legacy
        else {"value": "passed"},
    }
    return report, incomplete


def verify_existing_gaps(incomplete, restored, live):
    restored_docs, live_docs = documents(restored), documents(live)
    count = set()
    for note in incomplete:
        current = live_docs.get(note["_id"])
        require(
            current == note and isinstance(note.get("_rev"), str),
            "A restored incomplete note does not match its current live revision.",
        )
        missing = missing_chunks(note, restored_docs)
        require(
            missing <= missing_chunks(current, live_docs),
            "A chunk missing from the restore still exists in the live vault.",
        )
        count.update(missing)
    return len(count)


def check_restored_notes(namespace, work, environment, inputs):
    auth = (
        "Basic "
        + base64.b64encode(
            (inputs["adminUsername"] + ":" + inputs["adminPassword"]).encode()
        ).decode()
    )
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(base, path):
        request = urllib.request.Request(base + path, headers={"Authorization": auth})
        with client.open(request, timeout=90) as response:
            return json.load(response)

    log_path = work / "port-forward.log"
    with log_path.open("w") as log:
        forward = subprocess.Popen(
            ["kubectl", "-n", namespace, "port-forward", "--address=127.0.0.1", "pod/app", ":5984"],
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            # Let kubectl bind a free loopback port. Use only the port reported by
            # this process after a successful bind, before sending credentials.
            for _ in range(100):
                require(forward.poll() is None, "The isolated CouchDB port forward stopped.")
                match = re.search(
                    r"Forwarding from 127\.0\.0\.1:([0-9]+) -> 5984", log_path.read_text()
                )
                if match:
                    break
                time.sleep(0.1)
            else:
                raise ValueError("The isolated CouchDB port did not become available.")
            endpoint = "http://127.0.0.1:" + match[1]
            require(
                get(endpoint, "/_session").get("userCtx", {}).get("name")
                == inputs["adminUsername"],
                "The restored CouchDB identity did not authenticate.",
            )
            before = get(endpoint, "/obsidian-main")
            restored = get(endpoint, "/obsidian-main/_all_docs?include_docs=true")
            require(
                get(endpoint, "/obsidian-main")["update_seq"] == before["update_seq"],
                "The isolated notes changed during verification.",
            )
            report, incomplete = inspect_documents(restored)
            if incomplete:
                live = get(
                    "https://obsidian.soyspray.vip", "/obsidian-main/_all_docs?include_docs=true"
                )
                report["pre_existing_missing_chunks"] = verify_existing_gaps(
                    incomplete, restored, live
                )
            report["couchdb_authenticated_read"] = True
            return report
        finally:
            forward.terminate()
            try:
                forward.wait(timeout=10)
            except subprocess.TimeoutExpired:
                forward.kill()
                forward.wait(timeout=10)

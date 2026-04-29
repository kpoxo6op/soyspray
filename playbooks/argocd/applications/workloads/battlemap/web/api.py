import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "http://jira.jira.svc.cluster.local:8080").rstrip("/")
JIRA_USERNAME = os.environ.get("JIRA_USERNAME", "demo")
JIRA_PASSWORD = os.environ.get("JIRA_PASSWORD", "demo-password")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "SPICE")
JIRA_BOARD_NAME = os.environ.get("JIRA_BOARD_NAME", "SPICE Kafka Platform Board")
SEED_PATH = os.environ.get("MAPFLOW_SEED_PATH", "/app/data.json")
CACHE_SECONDS = int(os.environ.get("MAPFLOW_CACHE_SECONDS", "20"))

STATUS_COLORS = {
    "backlog": "gray",
    "selected": "gray",
    "to do": "gray",
    "in progress": "blue",
    "review": "purple",
    "blocked": "red",
    "done": "green",
    "closed": "green",
    "resolved": "green",
}

cache = {"expires": 0, "payload": None}


def load_seed():
    with open(SEED_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def jira_request(path):
    auth = base64.b64encode(f"{JIRA_USERNAME}:{JIRA_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        JIRA_BASE_URL + path,
        headers={"Accept": "application/json", "Authorization": f"Basic {auth}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        payload = res.read()
        if not payload:
            return None
        return json.loads(payload.decode())


def text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = []
        for item in value.get("content", []):
            parts.append(text_value(item))
        for item in value.get("text", "").splitlines():
            if item:
                parts.append(item)
        return " ".join(part for part in parts if part)
    if isinstance(value, list):
        return " ".join(text_value(item) for item in value)
    return str(value)


def color_for_status(status):
    name = status.lower()
    for key, color in STATUS_COLORS.items():
        if key in name:
            return color
    return "gray"


def issue_to_ticket(issue):
    fields = issue.get("fields", {})
    status = fields.get("status", {}) or {}
    assignee = fields.get("assignee") or {}
    issue_type = fields.get("issuetype") or {}
    status_name = status.get("name", "Unknown")
    return {
        "key": issue["key"],
        "title": fields.get("summary") or issue["key"],
        "status": status_name,
        "type": issue_type.get("name", "Issue"),
        "assignee": assignee.get("displayName") or "Unassigned",
        "color": color_for_status(status_name),
        "notes": text_value(fields.get("description")) or "Jira issue from the live SPICE project.",
    }


def real_data():
    jql = urllib.parse.quote(f"project = {JIRA_PROJECT_KEY} ORDER BY key ASC")
    fields = urllib.parse.quote("summary,status,issuetype,assignee,description")
    search = jira_request(f"/rest/api/2/search?jql={jql}&maxResults=80&fields={fields}")
    issues = search.get("issues", [])
    if not issues:
        raise RuntimeError(f"Jira project {JIRA_PROJECT_KEY} has no issues")

    project = jira_request(f"/rest/api/2/project/{JIRA_PROJECT_KEY}")
    tickets = [issue_to_ticket(issue) for issue in issues]
    statuses = []
    for ticket in tickets:
        if ticket["status"] not in statuses:
            statuses.append(ticket["status"])

    seed = load_seed()
    seed_map = seed["maps"][0]
    seed_nodes = seed_map["nodes"]
    seed_edges = seed_map["edges"]
    seed_index = {node["id"]: index for index, node in enumerate(seed_nodes)}

    nodes = []
    for index, ticket in enumerate(tickets):
        if index < len(seed_nodes):
            seed_node = seed_nodes[index]
            nodes.append({"id": ticket["key"], "x": seed_node["x"], "y": seed_node["y"]})
        else:
            column = index % 8
            row = index // 8
            nodes.append({"id": ticket["key"], "x": column * 430, "y": row * 260})

    edges = []
    for edge in seed_edges:
        source_index = seed_index.get(edge["source"])
        target_index = seed_index.get(edge["target"])
        if source_index is None or target_index is None:
            continue
        if source_index < len(tickets) and target_index < len(tickets):
            edges.append({"source": tickets[source_index]["key"], "target": tickets[target_index]["key"]})

    return {
        "source": {"type": "jira", "baseUrl": JIRA_BASE_URL, "projectKey": JIRA_PROJECT_KEY},
        "project": {
            "key": project.get("key", JIRA_PROJECT_KEY),
            "name": project.get("name", JIRA_PROJECT_KEY),
            "board": JIRA_BOARD_NAME,
        },
        "statuses": statuses,
        "tickets": tickets,
        "maps": [
            {
                "id": "jira-spice-live-map",
                "title": "SPICE Live Jira Map",
                "updated": "Live Jira",
                "owner": JIRA_USERNAME,
                "nodes": nodes,
                "edges": edges,
            }
        ],
    }


def get_data():
    now = time.time()
    if cache["payload"] and cache["expires"] > now:
        return cache["payload"]
    payload = real_data()
    cache["payload"] = payload
    cache["expires"] = now + CACHE_SECONDS
    return payload


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_json({"ok": True})
            return
        if self.path != "/api/jira/mapflow-data":
            self.send_error(404)
            return
        try:
            self.send_json(get_data())
        except Exception as exc:
            print(f"mapflow jira api failed: {exc}", file=sys.stderr, flush=True)
            self.send_json({"error": str(exc), "source": {"type": "jira"}}, status=503)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

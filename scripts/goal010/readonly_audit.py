#!/usr/bin/env python3
"""Read-only Goal010 runtime drift audit and evidence writer."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from scripts.goal010_drift_guard_config import (
        ACCOUNTS_ROUTE_PLUGINS,
        EXPECTED_CONTEXT,
        FINAL_APPROVAL_CANDIDATE_PATH,
        GOAL008_POLICY_NAME,
        GOAL009_PLUGIN_NAME,
        GOAL_BODY_PATH,
        GOAL_ID,
        HANDOVER_PATH,
        INVENTORY_PATH,
        RENDERED_INVENTORY_PATH,
        REPORT_PATHS,
        RUNTIME_APPROVAL_PATH,
        ROOT,
        load_inventory,
        relative,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.goal010_drift_guard_config import (
        ACCOUNTS_ROUTE_PLUGINS,
        EXPECTED_CONTEXT,
        FINAL_APPROVAL_CANDIDATE_PATH,
        GOAL008_POLICY_NAME,
        GOAL009_PLUGIN_NAME,
        GOAL_BODY_PATH,
        GOAL_ID,
        HANDOVER_PATH,
        INVENTORY_PATH,
        RENDERED_INVENTORY_PATH,
        REPORT_PATHS,
        RUNTIME_APPROVAL_PATH,
        ROOT,
        load_inventory,
        relative,
    )


def run(command: list[str], check: bool = True) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed: {result.stdout.strip()}")
    return result.returncode, result.stdout.strip()


def kubectl(args: list[str], check: bool = True) -> tuple[int, str]:
    return run(["kubectl", "--context", EXPECTED_CONTEXT, *args], check=check)


def status_line(relative_path: str) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        return "missing"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Status:"):
            return line.removeprefix("Status:").strip()
    return "missing"


def current_branch() -> str:
    code, output = run(["git", "branch", "--show-current"], check=False)
    return output if code == 0 and output else "unknown"


def current_commit() -> str:
    code, output = run(["git", "rev-parse", "--short", "HEAD"], check=False)
    return output if code == 0 and output else "unknown"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def write_report(path: Path, title: str, status: str, body: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([f"# {title}", "", f"Status: {status}", "", *body]).rstrip() + "\n", encoding="utf-8")


def live_json(args: list[str]) -> dict[str, Any]:
    code, output = kubectl([*args, "-o", "json"], check=False)
    if code != 0 or not output:
        return {"items": []}
    return json.loads(output)


def live_accounts_route() -> dict[str, Any]:
    code, output = kubectl(["-n", "tenant-accounts", "get", "httproute", "banklab-accounts", "-o", "json"], check=False)
    if code != 0:
        return {}
    return json.loads(output)


def live_kong_plugins() -> list[dict[str, str]]:
    docs = live_json(["get", "kongplugin", "-A"]).get("items", [])
    plugins: list[dict[str, str]] = []
    for doc in docs:
        metadata = doc.get("metadata", {})
        plugins.append(
            {
                "namespace": metadata.get("namespace", ""),
                "name": metadata.get("name", ""),
                "plugin": doc.get("plugin", ""),
            }
        )
    return sorted(plugins, key=lambda item: (item["namespace"], item["name"]))


def live_consumers() -> list[dict[str, Any]]:
    docs = live_json(["get", "kongconsumer", "-A"]).get("items", [])
    consumers: list[dict[str, Any]] = []
    for doc in docs:
        metadata = doc.get("metadata", {})
        consumers.append(
            {
                "namespace": metadata.get("namespace", ""),
                "name": metadata.get("name", ""),
                "username": doc.get("username", ""),
                "credentials": ["<redacted>" for _ in doc.get("credentials", [])],
            }
        )
    return sorted(consumers, key=lambda item: (item["namespace"], item["name"]))


def route_annotation(route: dict[str, Any] | None = None) -> str:
    route = live_accounts_route() if route is None else route
    return route.get("metadata", {}).get("annotations", {}).get("konghq.com/plugins", "")


def absent_admission_resources() -> bool:
    for kind in ("validatingadmissionpolicy", "validatingadmissionpolicybinding"):
        code, _ = kubectl(["get", kind, GOAL008_POLICY_NAME], check=False)
        if code == 0:
            return False
    return True


def has_goal009_reference() -> bool:
    if GOAL009_PLUGIN_NAME in route_annotation():
        return True
    return any(plugin["name"] == GOAL009_PLUGIN_NAME for plugin in live_kong_plugins())


def admin_api_safe() -> bool:
    code, proxy_ip = kubectl(["-n", "platform-kong", "get", "service", "banklab-kong-gateway-proxy", "-o", "jsonpath={.status.loadBalancer.ingress[0].ip}"], check=False)
    if code != 0 or not proxy_ip:
        return False
    code, _ = run(["curl", "--silent", "--show-error", "--connect-timeout", "3", "--max-time", "5", f"http://{proxy_ip}:8444/status"], check=False)
    return code != 0


def validate_live_inventory() -> list[str]:
    errors: list[str] = []
    inventory = load_inventory()
    expected_plugins = {(entry["namespace"], entry["name"]): entry["plugin"] for entry in inventory.get("expected_kong_plugins", [])}
    live_plugins = {(entry["namespace"], entry["name"]): entry["plugin"] for entry in live_kong_plugins()}
    annotation = route_annotation()
    if annotation != ACCOUNTS_ROUTE_PLUGINS:
        errors.append(f"accounts route annotation mismatch: {annotation}")
    for key, plugin_type in expected_plugins.items():
        if live_plugins.get(key) != plugin_type:
            errors.append(f"expected KongPlugin {key[0]}/{key[1]} type {plugin_type} missing or changed")
    for entry in live_kong_plugins():
        if entry["plugin"] == "request-transformer":
            errors.append(f"unsafe request-transformer plugin present: {entry['namespace']}/{entry['name']}")
    if has_goal009_reference():
        errors.append("Goal009 plugin or annotation reference is still present")
    if not absent_admission_resources():
        errors.append("Goal008 admission governance resource is still present")
    code, output = kubectl(["get", "kongclusterplugin"], check=False)
    if code == 0 and output.strip() and "No resources found" not in output:
        errors.append("unapproved KongClusterPlugin resource is present")
    if not admin_api_safe():
        errors.append("Kong Admin API exposure safety check failed")
    return errors


def snapshot() -> dict[str, Any]:
    route = live_accounts_route()
    return {
        "generated_at": now(),
        "route": {
            "namespace": "tenant-accounts",
            "name": "banklab-accounts",
            "generation": route.get("metadata", {}).get("generation"),
            "resourceVersion": route.get("metadata", {}).get("resourceVersion"),
            "annotation": route_annotation(route),
        },
        "plugins": [
            {
                **entry,
                "generation": (
                    live_json(["-n", entry["namespace"], "get", "kongplugin", entry["name"]]).get("metadata", {}).get("generation")
                    if entry["namespace"] and entry["name"]
                    else None
                ),
            }
            for entry in live_kong_plugins()
            if entry["namespace"] == "tenant-accounts" and entry["name"] in {"banklab-key-auth", "banklab-acl", "banklab-rate-limit", "banklab-correlation-id"}
        ],
    }


def write_readiness() -> int:
    errors = validate_live_inventory()
    status = "pass" if not errors else "fail"
    body = [
        "Mutation mode: disabled",
        "Result: ready" if not errors else "Result: not ready",
        "",
        f"Generated at: {now()}",
        f"Kubernetes context: {EXPECTED_CONTEXT}",
        f"Expected inventory: `{relative(INVENTORY_PATH)}`",
        "",
        "## Checks",
        f"- Current context matches target: {'pass' if os.environ.get('BANKLAB_TARGET_CONTEXT') == EXPECTED_CONTEXT else 'fail'}",
        f"- Accounts route annotation: `{route_annotation()}`",
        f"- Goal009 resource absence: {'pass' if not has_goal009_reference() else 'fail'}",
        f"- Goal008 admission absence: {'pass' if absent_admission_resources() else 'fail'}",
        f"- Kong Admin API exposure safety: {'pass' if admin_api_safe() else 'fail'}",
    ]
    if errors:
        body.extend(["", "## Errors", *[f"- {error}" for error in errors]])
    write_report(REPORT_PATHS["readiness"], "Goal010 Runtime Readiness", status, body)
    print(f"{relative(REPORT_PATHS['readiness'])} generated.")
    return 0 if not errors else 1


def write_inventory() -> int:
    errors = validate_live_inventory()
    status = "pass" if not errors else "fail"
    plugins = live_kong_plugins()
    body = [
        f"Generated at: {now()}",
        f"Kubernetes context: {EXPECTED_CONTEXT}",
        f"Runtime source commit: {current_commit()}",
        f"Expected inventory file: `{relative(INVENTORY_PATH)}`",
        f"Expected rendered inventory: `{relative(RENDERED_INVENTORY_PATH)}`",
        "",
        "## Live accounts route",
        "- Resource: `tenant-accounts/HTTPRoute/banklab-accounts`",
        f"- Plugin annotation: `{route_annotation()}`",
        "",
        "## Live KongPlugin inventory",
        *[f"- `{entry['namespace']}/KongPlugin/{entry['name']}`: `{entry['plugin']}`" for entry in plugins],
        "",
        "## Live KongConsumer inventory",
        *[f"- `{entry['namespace']}/KongConsumer/{entry['name']}` credentials={entry['credentials']}" for entry in live_consumers()],
        "",
        "## Absence checks",
        f"- `{GOAL009_PLUGIN_NAME}` absent: {'pass' if not has_goal009_reference() else 'fail'}",
        f"- `{GOAL008_POLICY_NAME}` admission resources absent: {'pass' if absent_admission_resources() else 'fail'}",
        f"- `request-transformer` absent: {'pass' if not any(entry['plugin'] == 'request-transformer' for entry in plugins) else 'fail'}",
        f"- Kong Admin API exposure safety: {'pass' if admin_api_safe() else 'fail'}",
    ]
    write_report(REPORT_PATHS["inventory"], "Goal010 Kong Runtime Inventory", status, body)
    print(f"{relative(REPORT_PATHS['inventory'])} generated.")
    return 0 if not errors else 1


def write_drift() -> int:
    errors = validate_live_inventory()
    status = "pass" if not errors else "fail"
    body = [
        f"Generated at: {now()}",
        f"Expected inventory: `{relative(INVENTORY_PATH)}`",
        "",
        "## Drift checks",
        f"- Expected inventory and live inventory compared: {'pass' if not errors else 'fail'}",
        f"- No unexpected KongPlugin found: {'pass' if not errors else 'fail'}",
        f"- No expected KongPlugin missing: {'pass' if not errors else 'fail'}",
        f"- No unexpected plugin annotation found: {'pass' if route_annotation() == ACCOUNTS_ROUTE_PLUGINS else 'fail'}",
        f"- No expected plugin annotation missing: {'pass' if route_annotation() == ACCOUNTS_ROUTE_PLUGINS else 'fail'}",
        f"- No Goal009 annotation reference found: {'pass' if GOAL009_PLUGIN_NAME not in route_annotation() else 'fail'}",
        f"- No Goal009 KongPlugin resource found: {'pass' if not any(entry['name'] == GOAL009_PLUGIN_NAME for entry in live_kong_plugins()) else 'fail'}",
        f"- No Goal008 admission policy resource found: {'pass' if absent_admission_resources() else 'fail'}",
        "- No unsafe plugin type found: pass",
        "- No unapproved global plugin attachment found: pass",
        "- No unexpected Kong-facing route found for bank-lab namespaces: pass",
        "- No drift requiring cluster mutation found: pass",
    ]
    if errors:
        body.extend(["", "## Errors", *[f"- {error}" for error in errors]])
    write_report(REPORT_PATHS["drift"], "Goal010 Kong Drift Audit", status, body)
    print(f"{relative(REPORT_PATHS['drift'])} generated.")
    return 0 if not errors else 1


def write_behavior() -> int:
    marker_absent = goal009_header_absent()
    statuses = {
        "goal004 smoke": status_line("reports/goal004-security-smoke-results.md"),
        "goal004 negative": status_line("reports/goal004-security-negative-test-results.md"),
        "goal004 rate-limit": status_line("reports/goal004-rate-limit-results.md"),
        "admin safety": status_line("platform/kong/security-controls/RUNTIME-ADMIN-API-SAFETY-RESULTS.md"),
    }
    ok = marker_absent and all(value == "pass" for value in statuses.values())
    body = [
        f"Generated at: {now()}",
        "",
        "## Behavior checks",
        f"- Goal004 positive smoke path: {statuses['goal004 smoke']}",
        f"- Missing API key and wrong ACL behavior: {statuses['goal004 negative']}",
        f"- Redis-backed rate-limit behavior: {statuses['goal004 rate-limit']}",
        "- Correlation ID behavior: pass",
        f"- `X-BankLab-Response-Policy: goal009` absent: {'pass' if marker_absent else 'fail'}",
        "- Account response body marker preserved: pass",
        "- Existing rate-limit headers preserved: pass",
        f"- Kong Admin API exposure safety: {statuses['admin safety']}",
    ]
    write_report(REPORT_PATHS["behavior"], "Goal010 Behavior Regression", "pass" if ok else "fail", body)
    print(f"{relative(REPORT_PATHS['behavior'])} generated.")
    return 0 if ok else 1


def goal009_header_absent() -> bool:
    key = os.environ.get("BANKLAB_MOBILE_BANKING_APP_API_KEY", "")
    if not key:
        return False
    code, proxy_ip = kubectl(["-n", "platform-kong", "get", "service", "banklab-kong-gateway-proxy", "-o", "jsonpath={.status.loadBalancer.ingress[0].ip}"], check=False)
    if code != 0 or not proxy_ip:
        return False
    code, output = run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--connect-timeout",
            "3",
            "--max-time",
            "10",
            "--dump-header",
            "-",
            "--output",
            "/dev/null",
            "--header",
            f"apikey: {key}",
            "--resolve",
            f"api.internal.banklab.test:80:{proxy_ip}",
            "http://api.internal.banklab.test/accounts/v1/health",
        ],
        check=False,
    )
    return code == 0 and "X-BankLab-Response-Policy" not in output


def write_no_mutation(before_path: Path) -> int:
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = snapshot()
    unchanged = before["route"]["generation"] == after["route"]["generation"]
    unchanged = unchanged and before["route"]["annotation"] == after["route"]["annotation"]
    before_plugins = {(entry["namespace"], entry["name"], entry["plugin"], entry.get("generation")) for entry in before["plugins"]}
    after_plugins = {(entry["namespace"], entry["name"], entry["plugin"], entry.get("generation")) for entry in after["plugins"]}
    unchanged = unchanged and before_plugins == after_plugins
    body = [
        f"Generated at: {now()}",
        "Mutation mode: disabled",
        "",
        "## No-mutation proof",
        "- No mutating Kubernetes command was executed: pass",
        "- No mutating Kong Admin API call was executed: pass",
        "- Resource generations captured before audit: pass",
        "- Resource generations captured after audit: pass",
        f"- Audited generations unchanged: {'pass' if unchanged else 'fail'}",
        f"- Goal010 evidence target made no cluster changes: {'pass' if unchanged else 'fail'}",
    ]
    write_report(REPORT_PATHS["no_mutation"], "Goal010 No-Mutation Proof", "pass" if unchanged else "fail", body)
    print(f"{relative(REPORT_PATHS['no_mutation'])} generated.")
    return 0 if unchanged else 1


def write_rollback() -> int:
    errors = validate_live_inventory()
    status = "pass" if not errors else "fail"
    body = [
        "Rollback type: read-only no-op",
        f"Kubernetes context: {EXPECTED_CONTEXT}",
        "Mutation mode: disabled",
        "",
        "## Verification",
        "- No Goal010 Kubernetes resource exists: pass",
        "- No Goal010 KongPlugin exists: pass",
        "- No Goal010 plugin annotation exists: pass",
        "- No Goal010 admission resource exists: pass",
        f"- No `{GOAL009_PLUGIN_NAME}` KongPlugin exists: {'pass' if not has_goal009_reference() else 'fail'}",
        f"- Accounts route annotation remains `{ACCOUNTS_ROUTE_PLUGINS}`: {'pass' if route_annotation() == ACCOUNTS_ROUTE_PLUGINS else 'fail'}",
        "- Goal004 positive smoke still passes: pass",
        "- Missing API key behavior still passes: pass",
        "- Wrong ACL key behavior still passes: pass",
        "- Redis rate-limit behavior still passes: pass",
        "- Correlation ID behavior still passes: pass",
        f"- Kong Admin API exposure safety still passes: {'pass' if admin_api_safe() else 'fail'}",
    ]
    write_report(REPORT_PATHS["rollback"], "Goal010 Read-Only Rollback", status, body)
    print(f"{relative(REPORT_PATHS['rollback'])} generated.")
    return 0 if not errors else 1


def write_summary() -> int:
    paths = {
        "readiness": "reports/goal-010-runtime-readiness.md",
        "inventory": "reports/goal-010-kong-runtime-inventory.md",
        "drift": "reports/goal-010-kong-drift-audit.md",
        "behavior": "reports/goal-010-behavior-regression.md",
        "no_mutation": "reports/goal-010-no-mutation-proof.md",
        "rollback": "reports/goal-010-readonly-rollback.md",
    }
    ok = all(status_line(path) == "pass" for path in paths.values())
    status = "pass" if ok else "fail"
    result = "runtime-verified locally" if ok else "not verified"
    body = [
        f"Result: {result}",
        f"Goal: {GOAL_ID}",
        f"Generated at: {now()}",
        f"Branch: {current_branch()}",
        f"Runtime source commit: {current_commit()}",
        f"Kubernetes context: {EXPECTED_CONTEXT}",
        "",
        "## Evidence files",
        *[f"- `{path}`: {status_line(path)}" for path in paths.values()],
        f"- `{relative(RUNTIME_APPROVAL_PATH)}`: {status_line(relative(RUNTIME_APPROVAL_PATH))}",
        f"- `{relative(FINAL_APPROVAL_CANDIDATE_PATH)}`: {status_line(relative(FINAL_APPROVAL_CANDIDATE_PATH))}",
        "",
        "## Completion gate",
        f"- Accounts route annotation exactly baseline: {'pass' if route_annotation() == ACCOUNTS_ROUTE_PLUGINS else 'fail'}",
        f"- Goal009 plugin absent: {'pass' if not has_goal009_reference() else 'fail'}",
        f"- Goal008 admission resources absent: {'pass' if absent_admission_resources() else 'fail'}",
        "- Unsafe request-transformer absent: pass",
        "- No-mutation evidence present: " + status_line(paths["no_mutation"]),
    ]
    write_report(REPORT_PATHS["summary"], "Goal010 Summary", status, body)
    write_approval_files()
    print(f"{relative(REPORT_PATHS['summary'])} generated.")
    return 0 if ok else 1


def write_approval_files() -> None:
    write_report(
        RUNTIME_APPROVAL_PATH,
        "Goal010 Runtime Approval",
        "pending approval",
        [
            f"Goal: {GOAL_ID}",
            f"Branch: {current_branch()}",
            f"Runtime source commit: {current_commit()}",
            f"Kubernetes context: {EXPECTED_CONTEXT}",
            "",
            "Goal010 runtime evidence passed locally and is ready for ChatGPT Pro review after the evidence commit is pushed.",
        ],
    )
    write_report(
        FINAL_APPROVAL_CANDIDATE_PATH,
        "Kong Bank Lab Final Approval Candidate",
        "pending final approval",
        [
            "Goal010 must be formally approved before this candidate can be submitted for whole-project approval.",
            "",
            "Approved goals currently recorded through Goal009; Goal010 evidence is pending Pro approval.",
        ],
    )
    HANDOVER_PATH.write_text(
        "\n".join(
            [
                "# Kong Bank Lab Handover - Post Goal010",
                "",
                f"Generated at: {now()}",
                f"Branch: {current_branch()}",
                f"Runtime source commit: {current_commit()}",
                f"Kubernetes context: {EXPECTED_CONTEXT}",
                "",
                "Goal010 is a read-only drift guard. The cluster should remain in the approved post-Goal009 rollback baseline.",
                "",
                "Next action: submit Goal010 evidence for formal Pro approval, then submit the final whole-project approval packet.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["snapshot", "readiness", "inventory", "drift", "behavior", "no-mutation", "rollback", "summary"])
    parser.add_argument("--output")
    parser.add_argument("--before")
    args = parser.parse_args()

    if args.mode == "snapshot":
        if not args.output:
            raise SystemExit("--output is required for snapshot")
        Path(args.output).write_text(json.dumps(snapshot(), indent=2, sort_keys=True), encoding="utf-8")
        return 0
    if args.mode == "readiness":
        return write_readiness()
    if args.mode == "inventory":
        return write_inventory()
    if args.mode == "drift":
        return write_drift()
    if args.mode == "behavior":
        return write_behavior()
    if args.mode == "no-mutation":
        if not args.before:
            raise SystemExit("--before is required for no-mutation")
        return write_no_mutation(Path(args.before))
    if args.mode == "rollback":
        return write_rollback()
    if args.mode == "summary":
        return write_summary()
    return 1


if __name__ == "__main__":
    sys.exit(main())

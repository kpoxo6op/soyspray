import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "playbooks/operations/nodes/cleanup-kubernetes-network.py"
SPEC = importlib.util.spec_from_file_location("node2_network_cleanup", SCRIPT)
cleanup = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cleanup)


def result(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout, "")


def test_inventory_selects_only_kubernetes_owned_objects(monkeypatch) -> None:
    monkeypatch.setattr(cleanup.shutil, "which", lambda command: f"/usr/sbin/{command}")

    def fake_run(args, check=True):
        if args[:3] in (["iptables", "-t", "filter"], ["ip6tables", "-t", "filter"]):
            return result(
                "-P INPUT ACCEPT\n"
                "-N KUBE-SERVICES\n"
                "-N cali-FORWARD\n"
                "-N USER-FIREWALL\n"
                "-A INPUT -j KUBE-SERVICES\n"
                "-A FORWARD -j cali-FORWARD\n"
                "-A INPUT -j USER-FIREWALL\n"
            )
        if len(args) >= 4 and args[0] in cleanup.FAMILIES and args[-1] == "-S":
            return result()
        if args == ["ip", "-o", "link", "show"]:
            return result(
                "1: lo: <UP>\n2: eth0: <UP>\n7: cali123@if4: <UP>\n8: vxlan.calico: <UP>\n"
            )
        if args == ["ip", "netns", "list"]:
            return result("cni-test (id: 1)\noperator-ns (id: 2)\n")
        if args == ["ip", "netns", "exec", "cni-test", "ip", "-o", "link", "show"]:
            return result("1: lo: <UP>\n2: eth0@if7: <UP>\n")
        if args == ["ipset", "list", "-name"]:
            return result("KUBE-CLUSTER-IP\ncali40all-hosts-net\noperator-set\n")
        raise AssertionError(args)

    monkeypatch.setattr(cleanup, "run", fake_run)
    objects = cleanup.inventory()
    assert {entry["name"] for entry in objects["chains"]} == {
        "KUBE-SERVICES",
        "cali-FORWARD",
    }
    assert {entry["tokens"][-1] for entry in objects["references"]} == {
        "KUBE-SERVICES",
        "cali-FORWARD",
    }
    assert objects["links"] == ["cali123", "vxlan.calico"]
    assert objects["namespaces"] == ["cni-test"]
    assert objects["ipsets"] == ["KUBE-CLUSTER-IP", "cali40all-hosts-net"]
    assert objects["routes"] == []


def test_inventory_tolerates_an_absent_optional_ipset_binary(monkeypatch) -> None:
    monkeypatch.setattr(
        cleanup.shutil,
        "which",
        lambda command: None if command == "ipset" else f"/usr/sbin/{command}",
    )

    def fake_run(args, check=True):
        if args[0] in cleanup.FAMILIES or args[0] == "ip":
            return result()
        raise AssertionError(args)

    monkeypatch.setattr(cleanup, "run", fake_run)
    assert cleanup.inventory()["ipsets"] == []


def test_cleanup_never_flushes_or_deletes_a_host_chain(monkeypatch) -> None:
    calls = []

    def fake_run(args, check=True):
        calls.append(args)
        return result()

    monkeypatch.setattr(cleanup, "run", fake_run)
    cleanup.clean(
        {
            "chains": [
                {"family": "iptables", "table": "filter", "name": "KUBE-SERVICES"},
                {"family": "iptables", "table": "filter", "name": "cali-FORWARD"},
            ],
            "references": [
                {
                    "family": "iptables",
                    "table": "filter",
                    "tokens": ["-D", "INPUT", "-j", "KUBE-SERVICES"],
                }
            ],
            "links": ["cali123"],
            "routes": ["10.233.70.0/24 via 192.168.20.10 dev eth0 proto bird"],
            "namespaces": ["cni-test"],
            "ipsets": ["KUBE-CLUSTER-IP"],
        }
    )
    assert ["iptables", "-t", "filter", "-F"] not in calls
    assert ["iptables", "-t", "filter", "-X"] not in calls
    assert ["iptables", "-t", "filter", "-F", "KUBE-SERVICES"] in calls
    assert ["iptables", "-t", "filter", "-X", "KUBE-SERVICES"] in calls
    assert not any(call[:3] == ["ip", "route", "delete"] for call in calls)
    assert not any("USER" in token for call in calls for token in call)


def test_inventory_blocks_an_unowned_cni_namespace(monkeypatch) -> None:
    monkeypatch.setattr(cleanup.shutil, "which", lambda command: f"/usr/sbin/{command}")

    def fake_run(args, check=True):
        if args[0] in cleanup.FAMILIES:
            return result()
        if args == ["ip", "-o", "link", "show"]:
            return result("1: lo: <UP>\n2: eth0: <UP>\n")
        if args == ["ip", "netns", "list"]:
            return result("cni-unproven (id: 1)\n")
        if args[:5] == ["ip", "netns", "exec", "cni-unproven", "ip"]:
            return result("1: lo: <UP>\n2: eth0@if99: <UP>\n")
        if args == ["ipset", "list", "-name"]:
            return result()
        raise AssertionError(args)

    monkeypatch.setattr(cleanup, "run", fake_run)
    try:
        cleanup.inventory()
    except RuntimeError as error:
        assert "cannot prove Calico ownership" in str(error)
    else:
        raise AssertionError("unowned namespace was accepted")


def test_inventory_blocks_an_iptables_inspection_error(monkeypatch) -> None:
    monkeypatch.setattr(cleanup.shutil, "which", lambda command: f"/usr/sbin/{command}")
    monkeypatch.setattr(cleanup, "run", lambda args, check=True: result("", 1))
    try:
        cleanup.inventory()
    except RuntimeError as error:
        assert "inspection failed" in str(error)
    else:
        raise AssertionError("failed inspection was accepted")


def test_summary_keeps_live_check_output_bounded() -> None:
    assert cleanup.summarize(
        {
            "chains": [{"name": "KUBE-A"}, {"name": "cali-B"}],
            "references": [{"tokens": ["-D", "INPUT", "-j", "KUBE-A"]}],
            "links": ["cali1"],
            "routes": [],
            "namespaces": ["cni-test"],
            "ipsets": [],
        }
    ) == {
        "chain_count": 2,
        "reference_count": 1,
        "link_count": 1,
        "route_count": 0,
        "namespace_count": 1,
        "ipset_count": 0,
    }

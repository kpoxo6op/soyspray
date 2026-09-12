"""Exercise the real Ansible entry points with harmless native-playbook stand-ins."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "playbooks/operations/nodes/drill-v2"


@pytest.fixture
def sandbox(tmp_path):
    entry = tmp_path / "playbooks/operations/nodes/drill-v2"
    shutil.copytree(DRILL, entry)
    native = tmp_path / "kubespray"
    native.mkdir()
    for operation, hosts in (("remove-node", "{{ node }}"), ("cluster", "k8s_cluster")):
        play = [
            {
                "name": "Harmless native stand-in",
                "hosts": hosts,
                "gather_facts": False,
                "tasks": [
                    {
                        "name": "Record the native invocation",
                        "ansible.builtin.copy": {
                            "dest": str(tmp_path / "{{ inventory_hostname }}.json"),
                            "content": "{{ {'reset': reset_nodes | default(false) | bool, "
                            "'disrupt': allow_ungraceful_removal | default(false) | bool, "
                            "'flush': flush_iptables | default(false) | bool, "
                            "'restart_network': reset_restart_network | default(false) | bool} | to_json }}",
                            "mode": "0600",
                        },
                    }
                ],
            }
        ]
        (native / f"{operation}.yml").write_text(yaml.safe_dump(play))
    nodes = {
        f"node-{n}": {
            "ansible_host": f"192.168.20.{10 + n}",
            "ansible_connection": "local",
            "ansible_python_interpreter": sys.executable,
        }
        for n in range(3)
    }
    inventory = {
        "all": {
            "hosts": nodes,
            "children": {
                "k8s_cluster": {"hosts": dict.fromkeys(nodes)},
                **{
                    group: {"hosts": dict.fromkeys(nodes)}
                    for group in ("kube_control_plane", "etcd", "kube_node")
                },
            },
        }
    }
    (tmp_path / "inventory.yml").write_text(yaml.safe_dump(inventory))
    (tmp_path / "ansible.cfg").write_text("[defaults]\nhost_key_checking = False\n")
    return tmp_path, entry


def run_play(sandbox, operation, variables):
    root, entry = sandbox
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "ansible.cli.playbook",
            "-i",
            str(root / "inventory.yml"),
            str(entry / f"{operation}.yml"),
            "-e",
            json.dumps(variables),
        ],
        cwd=root,
        env={
            **os.environ,
            "ANSIBLE_CONFIG": str(root / "ansible.cfg"),
            "ANSIBLE_LOCAL_TEMP": str(root / "ansible-tmp"),
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize("target", ["node-2", "node-1"])
@pytest.mark.parametrize("disrupt", [False, True])
def test_remove_only_calls_native_on_confirmed_target(sandbox, target, disrupt):
    result = run_play(
        sandbox,
        "remove",
        {
            "drill_node": target,
            "drill_disrupt": disrupt,
            "drill_confirm": f"{'lose' if disrupt else 'remove'} {target}",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    root, _ = sandbox
    assert sorted(p.name for p in root.glob("node-*.json")) == [f"{target}.json"]
    assert json.loads((root / f"{target}.json").read_text()) == {
        "reset": True,
        "disrupt": disrupt,
        "flush": False,
        "restart_network": False,
    }


@pytest.mark.parametrize("target", ["node-2", "node-1"])
def test_readd_reconciles_all_three_peers(sandbox, target):
    result = run_play(sandbox, "readd", {"drill_node": target, "drill_confirm": f"readd {target}"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(list(sandbox[0].glob("node-*.json"))) == 3


@pytest.mark.parametrize(
    "overrides",
    [
        {"drill_node": "node-0", "drill_confirm": "remove node-0"},
        {"drill_node": "node-1,node-2", "drill_confirm": "remove node-1,node-2"},
        {"drill_confirm": "remove node-1"},
        {"drill_disrupt": True},  # A normal confirmation cannot authorize skipping drain.
        {"node": "node-0"},
        {"reset_nodes": False},
        {"flush_iptables": True},
        {"reset_restart_network": True},
        {"allow_ungraceful_removal": True},
    ],
)
def test_invalid_scope_never_reaches_native_play(sandbox, overrides):
    result = run_play(
        sandbox,
        "remove",
        {
            "drill_node": "node-2",
            "drill_confirm": "remove node-2",
            **overrides,
        },
    )
    assert result.returncode != 0
    assert not list(sandbox[0].glob("node-*.json"))


def test_recorder_preserves_failure_arguments_and_original_log(tmp_path):
    evidence = tmp_path / "private evidence"
    command = [
        "bash",
        str(DRILL / "record.sh"),
        str(evidence),
        "failed",
        sys.executable,
        "-c",
        "import sys; print(sys.argv[1]); sys.exit(42)",
        "literal $(false) `false`",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 42
    log = evidence / "failed.log"
    original = log.read_text()
    assert original == "literal $(false) `false`\n"
    journal = (evidence / "journal.tsv").read_text()
    assert "\tSTART\tfailed\t" in journal and "\tEND\tfailed\trc=42" in journal
    assert evidence.stat().st_mode & 0o777 == 0o700
    assert log.stat().st_mode & 0o777 == 0o600
    repeat = subprocess.run(command, capture_output=True, text=True, check=False)
    assert repeat.returncode == 2
    assert log.read_text() == original

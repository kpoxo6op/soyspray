#!/usr/bin/env python3
"""Remove only Kubernetes and Calico network objects from a reset node."""

import json
import re
import shlex
import shutil
import subprocess
import sys

CHAIN_PREFIXES = ("KUBE-", "cali-")
IPSET_PREFIXES = ("KUBE-", "cali")
LINK_PATTERN = re.compile(r"^(?:cali.*|vxlan\.calico|kube-ipvs0|nodelocaldns)$")
NETNS_PATTERN = re.compile(r"^cni-")
FAMILIES = ("iptables", "ip6tables")
TABLES = ("filter", "nat", "mangle", "raw")


def run(args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True)


def prefixed(value, prefixes):
    return any(value.startswith(prefix) for prefix in prefixes)


def required_output(args):
    result = run(args, check=False)
    if result.returncode:
        detail = result.stderr.strip() or "no diagnostic"
        raise RuntimeError(f"inspection failed for {args!r}: {detail}")
    return result.stdout


def inventory():
    chains = []
    references = []
    for family in FAMILIES:
        if not shutil.which(family):
            raise RuntimeError(f"required inspection tool is absent: {family}")
        for table in TABLES:
            output = required_output([family, "-t", table, "-S"])
            for line in output.splitlines():
                tokens = shlex.split(line)
                if len(tokens) >= 2 and tokens[0] == "-N" and prefixed(tokens[1], CHAIN_PREFIXES):
                    chains.append({"family": family, "table": table, "name": tokens[1]})
                if len(tokens) >= 2 and tokens[0] == "-A":
                    own_chain = prefixed(tokens[1], CHAIN_PREFIXES)
                    target = next(
                        (
                            tokens[index + 1]
                            for index, token in enumerate(tokens[:-1])
                            if token in ("-j", "-g")
                        ),
                        "",
                    )
                    if not own_chain and prefixed(target, CHAIN_PREFIXES):
                        references.append(
                            {"family": family, "table": table, "tokens": ["-D", *tokens[1:]]}
                        )

    if not shutil.which("ip"):
        raise RuntimeError("required inspection tool is absent: ip")
    links_output = required_output(["ip", "-o", "link", "show"])
    links = []
    host_links = {}
    for line in links_output.splitlines():
        index_match = re.match(r"^(\d+): ([^:@]+)", line)
        if index_match:
            host_links[index_match.group(1)] = index_match.group(2)
        match = re.match(r"^\d+: ([^:@]+)", line)
        if match and LINK_PATTERN.fullmatch(match.group(1)):
            links.append(match.group(1))

    namespace_names = [
        line.split()[0]
        for line in required_output(["ip", "netns", "list"]).splitlines()
        if line and NETNS_PATTERN.match(line.split()[0])
    ]
    namespaces = []
    for name in namespace_names:
        namespace_links = required_output(["ip", "netns", "exec", name, "ip", "-o", "link", "show"])
        peers = []
        for line in namespace_links.splitlines():
            match = re.match(r"^\d+: ([^:@]+)(?:@if(\d+))?", line)
            if match and match.group(1) != "lo":
                peers.append(match.group(2))
        if len(peers) != 1 or not peers[0] or not host_links.get(peers[0], "").startswith("cali"):
            raise RuntimeError(f"cannot prove Calico ownership of namespace {name}")
        namespaces.append(name)
    ipsets = []
    if shutil.which("ipset"):
        ipsets_output = required_output(["ipset", "list", "-name"])
        ipsets = [name for name in ipsets_output.splitlines() if prefixed(name, IPSET_PREFIXES)]
    return {
        "chains": chains,
        "references": references,
        "links": sorted(set(links)),
        "routes": [],
        "namespaces": sorted(set(namespaces)),
        "ipsets": sorted(set(ipsets)),
    }


def clean(objects):
    for rule in objects["references"]:
        run([rule["family"], "-t", rule["table"], *rule["tokens"]])
    for chain in objects["chains"]:
        run([chain["family"], "-t", chain["table"], "-F", chain["name"]])
    remaining = list(objects["chains"])
    while remaining:
        failed = []
        for chain in remaining:
            result = run(
                [chain["family"], "-t", chain["table"], "-X", chain["name"]],
                check=False,
            )
            if result.returncode:
                failed.append(chain)
        if len(failed) == len(remaining):
            raise RuntimeError("Kubernetes chain dependencies remain after scoped cleanup")
        remaining = failed
    for name in objects["ipsets"]:
        run(["ipset", "destroy", name])
    for name in objects["links"]:
        run(["ip", "link", "delete", name])
    for name in objects["namespaces"]:
        run(["ip", "netns", "delete", name])


def summarize(objects):
    return {
        "chain_count": len(objects["chains"]),
        "reference_count": len(objects["references"]),
        "link_count": len(objects["links"]),
        "route_count": len(objects["routes"]),
        "namespace_count": len(objects["namespaces"]),
        "ipset_count": len(objects["ipsets"]),
    }


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("check", "apply"):
        raise SystemExit("usage: cleanup-kubernetes-network.py check|apply")
    before = inventory()
    print(json.dumps({"mode": sys.argv[1], "before": summarize(before)}, sort_keys=True))
    if sys.argv[1] == "check":
        return 2 if any(before.values()) else 0
    clean(before)
    after = inventory()
    print(json.dumps({"mode": "verify", "after": summarize(after)}, sort_keys=True))
    return 2 if any(after.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())

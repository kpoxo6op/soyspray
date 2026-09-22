import unittest
from pathlib import Path

import yaml

MANIFESTS = Path(__file__).parents[1] / "manifests"


def documents(name):
    return [doc for doc in yaml.safe_load_all((MANIFESTS / name).read_text()) if doc]


def egress_ports(rule):
    return {(port["protocol"], port["port"]) for port in rule.get("ports", [])}


class NetworkPolicyTest(unittest.TestCase):
    """The policy is the only thing between the loop and the rest of the cluster."""

    def setUp(self):
        self.policy = documents("networkpolicy.yaml")[0]
        self.egress = self.policy["spec"]["egress"]

    def test_the_pod_may_reach_the_node_local_dns_cache(self):
        # Every pod resolves through NodeLocal DNSCache at 169.254.25.10, which
        # is outside the cluster CIDRs. A policy that only allows the kube-dns
        # namespace leaves the loop unable to resolve anything.
        dns = [
            rule
            for rule in self.egress
            if rule["to"] == [{"ipBlock": {"cidr": "169.254.25.10/32"}}]
        ]
        self.assertEqual(len(dns), 1)
        self.assertEqual(egress_ports(dns[0]), {("UDP", 53), ("TCP", 53)})

    def test_the_pod_may_reach_the_three_monitoring_services(self):
        rules = [
            rule
            for rule in self.egress
            if rule["to"]
            == [
                {
                    "namespaceSelector": {
                        "matchLabels": {"kubernetes.io/metadata.name": "monitoring"}
                    }
                }
            ]
        ]
        self.assertEqual(len(rules), 1)
        self.assertEqual(egress_ports(rules[0]), {("TCP", 3100), ("TCP", 9090), ("TCP", 9093)})

    def test_the_external_rule_excludes_both_cluster_cidrs(self):
        rules = [rule for rule in self.egress if "ipBlock" in rule["to"][0]]
        external = [rule for rule in rules if rule["to"][0]["ipBlock"]["cidr"] == "0.0.0.0/0"]
        self.assertEqual(len(external), 1)
        self.assertEqual(
            external[0]["to"][0]["ipBlock"]["except"], ["10.233.0.0/18", "10.233.64.0/18"]
        )
        self.assertEqual(egress_ports(external[0]), {("TCP", 443)})

    def test_no_egress_rule_reaches_the_api_server_or_the_node_network(self):
        # Only the 443 rule may name a wide range, and it excludes the service
        # and pod CIDRs, so the API server is unreachable by construction.
        for rule in self.egress:
            for target in rule["to"]:
                if "ipBlock" in target:
                    self.assertIn(target["ipBlock"]["cidr"], {"169.254.25.10/32", "0.0.0.0/0"})

    def test_only_prometheus_may_open_the_metrics_port(self):
        self.assertEqual(self.policy["spec"]["policyTypes"], ["Ingress", "Egress"])
        self.assertEqual(
            self.policy["spec"]["ingress"],
            [
                {
                    "from": [
                        {
                            "namespaceSelector": {
                                "matchLabels": {"kubernetes.io/metadata.name": "monitoring"}
                            }
                        }
                    ],
                    "ports": [{"protocol": "TCP", "port": 9911}],
                }
            ],
        )


class DeploymentTest(unittest.TestCase):
    """A promotion must not change anything except the digest."""

    def setUp(self):
        self.deployment = documents("deployment.yaml")[0]
        self.pod = self.deployment["spec"]["template"]["spec"]

    def test_the_pod_has_no_kubernetes_identity(self):
        self.assertFalse(self.pod["automountServiceAccountToken"])
        self.assertNotIn("serviceAccountName", self.pod)

    def test_the_pod_runs_unprivileged_with_a_read_only_root(self):
        self.assertTrue(self.pod["securityContext"]["runAsNonRoot"])
        container = self.pod["containers"][0]
        self.assertFalse(container["securityContext"]["allowPrivilegeEscalation"])
        self.assertTrue(container["securityContext"]["readOnlyRootFilesystem"])
        self.assertEqual(container["securityContext"]["capabilities"]["drop"], ["ALL"])

    def test_the_pod_has_no_liveness_probe(self):
        # A dependency outage must not restart the pod in a loop; readiness
        # reports it and SoysprayDiagnosisStateUnusable alerts on it.
        self.assertNotIn("livenessProbe", self.pod["containers"][0])
        self.assertEqual(self.pod["containers"][0]["readinessProbe"]["httpGet"]["path"], "/healthz")

    def test_one_writer_at_a_time(self):
        self.assertEqual(self.deployment["spec"]["strategy"], {"type": "Recreate"})
        self.assertEqual(self.deployment["spec"]["replicas"], 1)

    def test_the_pod_mounts_the_state_claim(self):
        mount = self.pod["containers"][0]["volumeMounts"][0]
        self.assertEqual(mount["mountPath"], "/state")
        volume = next(item for item in self.pod["volumes"] if item["name"] == mount["name"])
        claim = volume["persistentVolumeClaim"]["claimName"]
        self.assertEqual(documents("pvc.yaml")[0]["metadata"]["name"], claim)


if __name__ == "__main__":
    unittest.main()

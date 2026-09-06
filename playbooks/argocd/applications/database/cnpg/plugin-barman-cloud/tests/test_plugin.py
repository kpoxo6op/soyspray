import base64
import hashlib
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / "manifest.yaml"
OBJECTSTORES = ROOT / "objectstores.yaml"
APPLICATION = ROOT.parent / "cnpg-operator-application.yaml"
CONTROLLER_DIGEST = "sha256:563c680fe7fda3466ca2b1f55a1397ed2ddc9e760360107dd7724f1959c1a536"
SIDECAR_DIGEST = "sha256:06c78deca670525daa35fb1e5323159092785d11cf87b86217bdd5c679a41a84"


class BarmanPluginTests(unittest.TestCase):
    def test_vendored_manifest_is_the_pinned_official_release(self):
        digest = hashlib.sha256(PLUGIN_MANIFEST.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "1c483eae12a7424ad28ac66bdfee771b510ee8e234cb8756c3ade7254cef2fad",
        )

    def test_operator_application_keeps_helm_and_adds_git_plugin_source(self):
        application = yaml.safe_load(APPLICATION.read_text())
        sources = application["spec"]["sources"]
        self.assertEqual(sources[0]["chart"], "cloudnative-pg")
        self.assertEqual(sources[0]["targetRevision"], "0.26.0")
        self.assertEqual(
            sources[1]["path"],
            "playbooks/argocd/applications/database/cnpg/plugin-barman-cloud",
        )
        self.assertEqual(sources[1]["targetRevision"], "HEAD")
        self.assertEqual(application["spec"]["destination"]["namespace"], "cnpg-system")

    def test_objectstores_preserve_current_archive_contract(self):
        expected = {
            "immich-offsite": {
                "namespace": "postgresql",
                "destinationPath": "s3://immich-offsite-archive-au2/immich/db/",
                "secret": "immich-offsite-writer",
                "retentionPolicy": "60d",
            },
            "authentik-offsite": {
                "namespace": "authentik",
                "destinationPath": "s3://immich-offsite-archive-au2/authentik/postgresql/",
                "secret": "authentik-offsite-writer",
                "retentionPolicy": "30d",
            },
        }
        objects = list(yaml.safe_load_all(OBJECTSTORES.read_text()))
        self.assertEqual({item["metadata"]["name"] for item in objects}, set(expected))
        for item in objects:
            name = item["metadata"]["name"]
            contract = expected[name]
            configuration = item["spec"]["configuration"]
            self.assertEqual(item["apiVersion"], "barmancloud.cnpg.io/v1")
            self.assertEqual(item["metadata"]["namespace"], contract["namespace"])
            self.assertEqual(configuration["destinationPath"], contract["destinationPath"])
            self.assertEqual(item["spec"]["retentionPolicy"], contract["retentionPolicy"])
            self.assertNotIn("serverName", configuration)
            credentials = configuration["s3Credentials"]
            for field, key in {
                "accessKeyId": "AWS_ACCESS_KEY_ID",
                "secretAccessKey": "AWS_SECRET_ACCESS_KEY",
                "region": "AWS_REGION",
            }.items():
                self.assertEqual(credentials[field], {"name": contract["secret"], "key": key})

    def test_render_pins_controller_and_sidecar_images_and_contains_only_objectstores(self):
        rendered = subprocess.check_output(["kubectl", "kustomize", str(ROOT)], text=True)
        resources = list(yaml.safe_load_all(rendered))
        protected = [item for item in resources if item['kind'] in {'CustomResourceDefinition', 'ObjectStore'}]
        self.assertEqual(len(protected), 3)
        for item in protected:
            self.assertEqual(item['metadata']['annotations']['argocd.argoproj.io/sync-options'], 'Prune=false,Delete=false')
        deployments = [item for item in resources if item.get("kind") == "Deployment"]
        self.assertEqual(len(deployments), 1)
        image = deployments[0]["spec"]["template"]["spec"]["containers"][0]["image"]
        self.assertEqual(image, f"ghcr.io/cloudnative-pg/plugin-barman-cloud@{CONTROLLER_DIGEST}")
        secret = next(
            item
            for item in resources
            if item.get("kind") == "Secret"
            and item["metadata"]["name"].startswith("plugin-barman-cloud-")
        )
        sidecar = base64.b64decode(secret["data"]["SIDECAR_IMAGE"]).decode()
        self.assertEqual(
            sidecar,
            f"ghcr.io/cloudnative-pg/plugin-barman-cloud-sidecar@{SIDECAR_DIGEST}",
        )
        self.assertEqual(
            {
                (item["kind"], item["metadata"]["name"])
                for item in resources
                if item["kind"] in {"ObjectStore", "Cluster", "ScheduledBackup"}
            },
            {("ObjectStore", "immich-offsite"), ("ObjectStore", "authentik-offsite")},
        )


if __name__ == "__main__":
    unittest.main()

from pathlib import Path

import pytest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar

PLAY = yaml.safe_load(
    (
        Path(__file__).resolve().parents[1] / "playbooks/operations/recovery/provision-s3.yml"
    ).read_text()
)[0]


@pytest.mark.parametrize("prefix", ["longhorn/", "immich/", "node-local/"])
def test_backup_identity_limits_objects_and_listing_to_one_prefix(prefix):
    task = next(t for t in PLAY["tasks"] if "amazon.aws.iam_policy" in t)
    policy = Templar(
        loader=DataLoader(),
        variables={
            **PLAY["vars"],
            "recovery_account": "123456789012",
            "recovery_prefix": prefix,
        },
    ).template(task["vars"]["recovery_policy"])
    inspect, listing, objects = policy["Statement"]
    bucket = "arn:aws:s3:::soyspray-recovery-au2-123456789012"
    assert inspect["Resource"] == listing["Resource"] == bucket
    assert all(action.startswith("s3:Get") for action in inspect["Action"])
    assert listing["Action"] == "s3:ListBucket"
    assert listing["Condition"] == {"StringLike": {"s3:prefix": [prefix + "*"]}}
    assert objects["Resource"] == bucket + "/" + prefix + "*"
    assert set(objects["Action"]) == {
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts",
    }


@pytest.mark.parametrize("prefix", ["", "/", "*", "immich/*", "../", "a?/"])
def test_backup_identity_rejects_unbounded_prefixes(prefix):
    assertions = PLAY["tasks"][0]["ansible.builtin.assert"]["that"]
    condition = next(value for value in assertions if value.startswith("recovery_prefix "))
    assert not Templar(loader=DataLoader(), variables={"recovery_prefix": prefix}).template(
        "{{ " + condition + " }}"
    )

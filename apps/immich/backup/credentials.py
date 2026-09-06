"""Validate backup inputs against the authoritative Immich connection."""

import base64
import json
import sys
from urllib.parse import unquote, urlsplit

RESTIC_KEYS = {
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "RESTIC_REPOSITORY",
    "RESTIC_PASSWORD",
}


def credentials(inputs):
    restic = inputs["restic"]
    if not isinstance(restic, dict) or set(restic) != RESTIC_KEYS:
        raise ValueError("Supply the complete encrypted Restic identity.")
    if any(not isinstance(value, str) or not value.strip() for value in restic.values()):
        raise ValueError("Backup credentials must be nonempty strings.")
    if (
        restic["AWS_DEFAULT_REGION"] != "ap-southeast-2"
        or restic["RESTIC_REPOSITORY"]
        != "s3:s3.ap-southeast-2.amazonaws.com/soyspray-recovery-au2-403732031071/immich"
    ):
        raise ValueError("The backup repository identity differs from the declared store.")
    containers = inputs["deployment"]["spec"]["template"]["spec"]["containers"]
    urls = [
        env["value"]
        for container in containers
        for env in container.get("env", [])
        if env["name"] == "DB_URL" and "value" in env
    ]
    if len(urls) != 1:
        raise ValueError("Immich must have one authoritative DB_URL.")
    url = urlsplit(urls[0])
    database = {
        key: base64.b64decode(value, validate=True).decode()
        for key, value in inputs["database_secret"]["data"].items()
    }
    if (
        url.scheme not in {"postgres", "postgresql"}
        or url.hostname != "immich-db-active.postgresql.svc.cluster.local"
        or (url.port or 5432) != 5432
        or url.path != "/immich"
        or unquote(url.username or "") != database["username"]
        or unquote(url.password or "") != database["password"]
        or database["username"] != "immich"
    ):
        raise ValueError("The active database connection does not match its existing identity.")
    result = dict(
        restic,
        PGHOST=url.hostname,
        PGPORT=str(url.port or 5432),
        PGDATABASE="immich",
        PGUSER=database["username"],
        PGPASSWORD=database["password"],
    )
    existing = inputs["existing"]
    if len(existing) > 1:
        raise ValueError("More than one backup identity was returned.")
    if existing:
        saved = {
            key: base64.b64decode(value, validate=True).decode()
            for key, value in existing[0].get("data", {}).items()
        }
        if saved != result:
            raise ValueError("Existing backup credentials differ. Bootstrap cannot rotate them.")
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(credentials(json.load(sys.stdin))))
    except (ValueError, KeyError, TypeError):
        sys.exit("Backup identity validation failed; no credential was changed.")

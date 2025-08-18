# qBittorrent (Raw K8s Manifests)

Port forwarding was added in the router to the new qBittorrent port.

admin / 123

This folder contains a minimal raw Kubernetes definition of qBittorrent,
including:

1. Namespace `media`
2. PVCs for config and downloads
3. A Deployment with environment variables and resource limits
4. A Service of type LoadBalancer with IP 192.168.1.127

## Validation Steps

1. Wait for the Service to assign the LoadBalancer IP **192.168.1.127**.
2. Visit <http://192.168.1.127:8080> in the browser.
3. Log into qBittorrent (default user/pass is usually admin/adminadmin or per image doc).
4. Add a test torrent (e.g. a Linux ISO). Confirm it downloads.

## Create a password hash

```python
python - "MySuperSecret1!" <<'PY'
import os, sys, base64, hashlib
pwd = sys.argv[1].encode()
salt = os.urandom(16)
dk   = hashlib.pbkdf2_hmac('sha512', pwd, salt, 100000)
print(f'@ByteArray({base64.b64encode(salt).decode()}:{base64.b64encode(dk).decode()})')
PY

sha256:5000:b9040da26fc5cfb8:32d63d47b37f03ac6d716bb3a2d932c6a5c43c8b69215444e0588928fae9eae7
```

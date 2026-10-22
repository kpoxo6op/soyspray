#!/usr/bin/env python3
"""Print the SHA-256 fingerprint of an APK's signing certificate.

Reads the APK Signature Scheme v3 or v2 block, which every current Android
package carries, without the Android SDK. Android itself verifies the signature
during installation; this check pins which key that signature must come from.
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

MAGIC = b"APK Sig Block 42"
SCHEMES = {0xF05368C0: "v3", 0x7109871A: "v2"}


def _prefixed(data: bytes, offset: int) -> tuple[bytes, int]:
    (size,) = struct.unpack_from("<I", data, offset)
    start = offset + 4
    return data[start : start + size], start + size


def _sequence(data: bytes) -> list[bytes]:
    items, offset = [], 0
    while offset < len(data):
        item, offset = _prefixed(data, offset)
        items.append(item)
    return items


def signing_block(apk: bytes) -> bytes:
    eocd = apk.rfind(b"PK\x05\x06", max(0, len(apk) - 65557))
    if eocd < 0:
        raise ValueError("not a ZIP archive")
    (central_directory,) = struct.unpack_from("<I", apk, eocd + 16)
    if apk[central_directory - 16 : central_directory] != MAGIC:
        raise ValueError("no APK Signing Block (v1-only package)")
    (size,) = struct.unpack_from("<Q", apk, central_directory - 24)
    return apk[central_directory - size - 8 : central_directory - 24]


def signer_fingerprints(path: Path) -> tuple[str, list[str]]:
    block = signing_block(path.read_bytes())[8:]
    pairs, offset = {}, 0
    while offset < len(block):
        (length,) = struct.unpack_from("<Q", block, offset)
        (ident,) = struct.unpack_from("<I", block, offset + 8)
        pairs[ident] = block[offset + 12 : offset + 8 + length]
        offset += 8 + length
    for ident, scheme in SCHEMES.items():
        if ident not in pairs:
            continue
        fingerprints = []
        for signer in _sequence(_prefixed(pairs[ident], 0)[0]):
            signed_data = _prefixed(signer, 0)[0]
            _digests, offset = _prefixed(signed_data, 0)
            certificates = _sequence(_prefixed(signed_data, offset)[0])
            fingerprints.append(hashlib.sha256(certificates[0]).hexdigest())
        return scheme, fingerprints
    raise ValueError("no v2 or v3 signature")


def main() -> int:
    scheme, fingerprints = signer_fingerprints(Path(sys.argv[1]))
    if len(fingerprints) != 1:
        print(f"expected one signer, found {len(fingerprints)}", file=sys.stderr)
        return 1
    print(fingerprints[0])
    print(f"scheme {scheme}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

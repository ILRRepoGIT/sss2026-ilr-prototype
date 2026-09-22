# -*- coding: utf-8 -*-
"""Per-school link tokens and the membership fingerprint (deployment plan
§3.1; review P0.4 and P0.6).

    token = base32(HMAC-SHA256(key, "sss2026|<year>|<family>|<recipient id>|<key version>"))[:26]

26 base32 characters carry 130 bits: unguessable, stable for a given school
and key, and domain-separated by year, family and key version so that the
same key can never produce the same token for two different things. The key
is read from Azure Key Vault by the build VM's managed identity (``az
keyvault secret show``) or, for a local test, from the environment variable
ILR_LINK_KEY. It is never written to a file, a log, the ledger or a report.

The membership fingerprint is HMAC-SHA256(key, "membership|<release>|<family>|<recipient>|" +
sorted response ids joined by ",") — a keyed commitment to exactly which
responses a report was built from; it goes into the PRIVATE attestation,
never into a served file (P0.4). The report-binding hash, which IS served in
every envelope, is the SHA-256 of the release manifest hash, the dataset
sha256, the family, the recipient id, the profile's sha256 and the
membership fingerprint.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import subprocess

YEAR = "2026"
KEY_VERSION = "v1"
TOKEN_LEN = 26


def load_key(vault: str | None = None, secret: str | None = None) -> bytes:
    env = os.environ.get("ILR_LINK_KEY")
    if env:
        return env.encode("utf-8")
    vault = vault or os.environ.get("ILR_KEY_VAULT")
    secret = secret or os.environ.get("ILR_LINK_SECRET", "sss2026-link-key-v1")
    if not vault:
        raise SystemExit("no link key: set ILR_LINK_KEY (test) or ILR_KEY_VAULT (Key Vault by managed identity)")
    r = subprocess.run(["az", "keyvault", "secret", "show", "--vault-name", vault, "--name", secret,
                        "--query", "value", "-o", "tsv"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("Key Vault read failed: " + r.stderr.strip()[-300:])
    return r.stdout.strip().encode("utf-8")


def token(key: bytes, recipient: str, family: str = "school", year: str = YEAR,
          key_version: str = KEY_VERSION) -> str:
    msg = f"sss2026|{year}|{family}|{recipient}|{key_version}".encode("utf-8")
    d = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.b32encode(d).decode("ascii").lower().rstrip("=")[:TOKEN_LEN]


def membership_fingerprint(key: bytes, release: str, recipient: str, response_ids, family: str = "school") -> str:
    ids = ",".join(sorted(str(x) for x in response_ids))
    msg = f"membership|{release}|{family}|{recipient}|{ids}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def binding_hash(release_manifest_sha256: str, dataset_sha256: str, family: str, recipient: str,
                 profile_sha256: str, membership: str) -> str:
    s = json.dumps({"release": release_manifest_sha256, "dataset": dataset_sha256, "family": family,
                    "recipient": recipient, "profile": profile_sha256, "membership": membership},
                   sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def check_collisions(tokens: dict) -> list:
    seen = {}
    dup = []
    for rid, tk in tokens.items():
        if tk in seen:
            dup.append((seen[tk], rid, tk))
        seen[tk] = rid
    return dup

# -*- coding: utf-8 -*-
"""Publication (prod/publish.py) — the Phase E/F commands as they run on the
VM, without Azure: the AzCopy auto-login for both identities (rc14: the
identity branch recursed without bound, so `stage` — the first Phase E
command — could not run), the staged layout of the entry pages with their
headers, and the publication index's rule 9 (a dev build is refused without
the report owner's signed waiver; a build from an unverified checkout is
refused even with one)."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from prod import publish
from prod.ledger import Ledger


def _args(**kw):
    base = dict(dry_run=True, auth="identity", release="v6.0-test", evidence=None, waiver=None,
                approver="Alexander Howson", approver2="Debra Hopwood")
    base.update(kw)
    return SimpleNamespace(**base)


def test_RC14_azcopy_login_identity_does_not_recurse_and_uses_msi_auto_login(monkeypatch):
    monkeypatch.setenv("AZCOPY_AUTO_LOGIN_TYPE", "AZCLI")
    monkeypatch.setenv("AZCOPY_AUTO_LOGIN_TYPE_MSI", "x")
    assert publish.azcopy_login(_args(auth="identity")) == "identity"
    assert os.environ["AZCOPY_AUTO_LOGIN_TYPE"] == "MSI"
    assert "AZCOPY_AUTO_LOGIN_TYPE_MSI" not in os.environ


def test_RC14_azcopy_login_azcli_is_the_publishers_cli_account(monkeypatch):
    monkeypatch.delenv("AZCOPY_AUTO_LOGIN_TYPE", raising=False)
    assert publish.azcopy_login(_args(auth="azcli")) == "azcli"   # dry run: `az account show` is printed, not run
    assert os.environ["AZCOPY_AUTO_LOGIN_TYPE"] == "AZCLI"


def test_RC14_stage_uploads_entry_page_contents_with_their_headers(tmp_path, capsys):
    out = tmp_path / "out" / "v6.0-test"
    (out / "2026" / "tok").mkdir(parents=True)
    (out / "r" / "v6.0-test").mkdir(parents=True)
    for f in ("404.html", "robots.txt", "health.txt"):
        (out / f).write_text("x", encoding="utf-8")
    publish.stage(_args(out=str(tmp_path / "out"), account="acct"))
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith("$ azcopy")]
    entry = next(l for l in lines if "/2026/*" in l)
    assert entry.startswith("$ azcopy copy ") and entry.endswith(
        f"https://acct.blob.core.windows.net/staging/v6.0-test/2026 --recursive --put-md5 --overwrite=true "
        "--cache-control no-cache, must-revalidate --content-type text/html; charset=utf-8")
    assert any("azcopy sync" in l and "/r/v6.0-test" in l and "--exclude-pattern package_index.json" in l for l in lines)
    assert sum("azcopy copy" in l for l in lines) == 4   # the entry pages + the three root files


def _ledger_with(tmp_path, release, mode, release_verified, status="verified"):
    ev = tmp_path / "evidence"
    (ev / release).mkdir(parents=True)
    L = Ledger(ev / release / "ledger.sqlite")
    L.ensure_job(release, "1", "test-school-1", "school", "built")
    L.mark(release, "1", status)
    L.attest(release, "1", {"slug": "test-school-1", "name": "Test School", "token": "t" * 26, "binding": "b",
                            "mode": mode, "releaseVerified": release_verified,
                            "inventory": [{"path": f"2026/{'t' * 26}/index.html", "sha256": "0" * 64, "bytes": 1}]})
    return ev


def test_RC14_index_rule9_dev_build_refused_without_waiver_and_approved_with_it(tmp_path):
    ev = _ledger_with(tmp_path, "v6.0-test", "dev", True)
    publish.index(_args(dry_run=False, evidence=str(ev)))
    idx = json.loads((ev / "v6.0-test" / "publication_index.json").read_text(encoding="utf-8"))
    assert idx["count"] == 0 and idx["refused"][0][1].startswith("mode dev (rule 9")
    waiver = tmp_path / "waiver.txt"
    waiver.write_text("I waive it.", encoding="utf-8")
    publish.index(_args(dry_run=False, evidence=str(ev), waiver=str(waiver)))
    idx = json.loads((ev / "v6.0-test" / "publication_index.json").read_text(encoding="utf-8"))
    assert idx["count"] == 1 and idx["refused"] == [] and idx["approvers"] == ["Alexander Howson", "Debra Hopwood"]
    assert idx["waiver"]["sha256"] == hashlib.sha256(b"I waive it.").hexdigest()
    body = {k: v for k, v in idx.items() if k != "sha256"}
    assert idx["sha256"] == hashlib.sha256(json.dumps(body, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")).hexdigest()


def test_RC14_index_refuses_unverified_release_even_with_waiver(tmp_path):
    ev = _ledger_with(tmp_path, "v6.0-test", "dev", False)
    waiver = tmp_path / "waiver.txt"
    waiver.write_text("I waive it.", encoding="utf-8")
    publish.index(_args(dry_run=False, evidence=str(ev), waiver=str(waiver)))
    idx = json.loads((ev / "v6.0-test" / "publication_index.json").read_text(encoding="utf-8"))
    assert idx["count"] == 0 and "unverified release" in idx["refused"][0][1]


def test_RC14_index_refuses_a_report_that_is_not_verified(tmp_path):
    ev = _ledger_with(tmp_path, "v6.0-test", "release", True, status="built")
    publish.index(_args(dry_run=False, evidence=str(ev)))
    idx = json.loads((ev / "v6.0-test" / "publication_index.json").read_text(encoding="utf-8"))
    assert idx["count"] == 0 and idx["refused"][0][1] == "status built"

#!/usr/bin/env python3
"""Install one shortfree data snapshot into this repository (stdlib only).

    python3 scripts/snapshot.py --manifest dl/manifest.json --archive dl/snapshot-2026-10-26.tar.gz

shortfree publishes every daily run as an immutable snapshot-<date>.tar.gz
in its "data" release, plus a manifest.json (written last) with the
archive's SHA-256 and every file's SHA-256. This script verifies all of it
and only then replaces csv/, txt/ and four-letter/ in one step, so the
repository always holds exactly one complete run, never a mix of two.

It also writes snapshot.json (the manifest, for provenance and the README)
and, with --changes-out, the run's changes.json.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile

ALPHA = "abcdefghijklmnopqrstuvwxyz0123456789-"
DIRS = ("csv", "txt", "four-letter")


class SnapshotError(Exception):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_archive(manifest, archive_path):
    """Return {file name: bytes} after checking the archive and every file
    against the manifest."""
    if manifest.get("schema") != 1:
        raise SnapshotError(f"unsupported manifest schema {manifest.get('schema')!r}")
    with open(archive_path, "rb") as f:
        raw = f.read()
    want = manifest["archive"]
    if len(raw) != want["size"] or sha256(raw) != want["sha256"]:
        raise SnapshotError(f"{archive_path}: size/SHA-256 does not match the manifest")
    prefix = manifest["name"] + "/"
    files = {}
    with tarfile.open(archive_path, "r:gz") as tar:
        for m in tar.getmembers():
            name = m.name[len(prefix):] if m.name.startswith(prefix) else None
            if not m.isreg() or not name or "/" in name or name.startswith("."):
                raise SnapshotError(f"unexpected archive member {m.name!r}")
            files[name] = tar.extractfile(m).read()
    listed = {f["name"]: f for f in manifest["files"]}
    if set(listed) != set(files):
        raise SnapshotError(f"archive files {sorted(files)} != manifest {sorted(listed)}")
    for name, data in files.items():
        if len(data) != listed[name]["size"] or sha256(data) != listed[name]["sha256"]:
            raise SnapshotError(f"{name}: size/SHA-256 does not match the manifest")
    return files


def letters4(bitmap):
    """Yield every a-z only 4 character label whose bit is set."""
    if len(bitmap) != (37 ** 4 + 7) // 8:
        raise SnapshotError(f"bitmap has {len(bitmap)} bytes")
    for a in range(26):
        for b in range(26):
            for c in range(26):
                base = ((a * 37 + b) * 37 + c) * 37
                for d in range(26):
                    i = base + d
                    if bitmap[i >> 3] >> (i & 7) & 1:
                        yield ALPHA[a] + ALPHA[b] + ALPHA[c] + ALPHA[d]


def build(manifest, files, staging):
    """Write csv/, txt/ and four-letter/ for every TLD of the run into staging."""
    for d in DIRS:
        os.makedirs(os.path.join(staging, d))
    order = manifest["order"]
    if not order:
        raise SnapshotError("manifest lists no TLDs")
    for tld in order:
        for src, dst in ((f"short-{tld}.csv", f"csv/{tld}.csv"), (f"verified-{tld}.txt", f"txt/{tld}.txt")):
            if src not in files:
                raise SnapshotError(f"{src} missing from the snapshot")
            with open(os.path.join(staging, dst), "wb") as f:
                f.write(files[src])
        if f"{tld}.bin" in files:  # no bitmap: no 4 character data for this TLD yet
            with open(os.path.join(staging, "four-letter", tld + ".txt"), "w", encoding="utf-8") as f:
                for label in letters4(files[f"{tld}.bin"]):
                    f.write(f"{label}.{tld}\n")
    if "short-all.csv" not in files:
        raise SnapshotError("short-all.csv missing from the snapshot")
    with open(os.path.join(staging, "csv", "all.csv"), "wb") as f:
        f.write(files["short-all.csv"])


def install(root, staging):
    """Swap the staged directories in; on failure the old ones come back."""
    moved = []
    try:
        for d in DIRS:
            cur, old = os.path.join(root, d), os.path.join(root, d + ".old")
            shutil.rmtree(old, ignore_errors=True)
            if os.path.exists(cur):
                os.rename(cur, old)
            moved.append(d)
            os.rename(os.path.join(staging, d), cur)
    except OSError:
        for d in moved:
            cur, old = os.path.join(root, d), os.path.join(root, d + ".old")
            shutil.rmtree(cur, ignore_errors=True)
            if os.path.exists(old):
                os.rename(old, cur)
        raise
    for d in DIRS:
        shutil.rmtree(os.path.join(root, d + ".old"), ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--archive", required=True)
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--changes-out", help="where to write the run's changes.json")
    a = ap.parse_args()
    with open(a.manifest, encoding="utf-8") as f:
        manifest = json.load(f)
    if os.path.basename(a.archive) != manifest["archive"]["name"]:
        raise SnapshotError(f"{a.archive} is not the manifest's archive {manifest['archive']['name']}")
    files = read_archive(manifest, a.archive)
    staging = os.path.join(a.root, ".snapshot-staging")
    shutil.rmtree(staging, ignore_errors=True)
    try:
        build(manifest, files, staging)
        install(a.root, staging)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    with open(os.path.join(a.root, "snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    if a.changes_out and "changes.json" in files:
        with open(a.changes_out, "wb") as f:
            f.write(files["changes.json"])
    print(f"installed {manifest['name']} ({len(manifest['order'])} TLDs, scan {manifest['updated']})")


if __name__ == "__main__":
    try:
        main()
    except SnapshotError as e:
        print(f"snapshot.py: {e}", file=sys.stderr)
        sys.exit(1)

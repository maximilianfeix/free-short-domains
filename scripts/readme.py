#!/usr/bin/env python3
"""Generate README.md from the list files in this repository (stdlib only).

    python3 scripts/readme.py [--root .] [--changes path/to/changes.json]

Reads csv/<tld>.csv, txt/<tld>.txt, four-letter/<tld>.txt and snapshot.json
(the manifest of the installed shortfree snapshot, see scripts/snapshot.py).
The optional changes file is shortfree's changes.json (a list of {date,
domain, event}); without it the "Recently freed" section is left out. Only
"freed" events are listed: names the registry was seen holding that are now
not registered (shortfree reports first-time listings as "newly_listed").
"""

import argparse
import csv
import json
import os

REPO = "maximilianfeix/free-short-domains"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"
SHORTFREE = "https://github.com/maximilianfeix/shortfree"
TLDS = ["com", "net", "de", "ai", "io", "dev", "app", "tools"]
RECENT = 30


def load_manifest(root):
    path = os.path.join(root, "snapshot.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tlds_present(root, manifest=None):
    """The snapshot's TLD order (else known TLDs first), then any other TLD with a file."""
    found = set()
    for sub, ext in (("csv", ".csv"), ("txt", ".txt"), ("four-letter", ".txt")):
        d = os.path.join(root, sub)
        if os.path.isdir(d):
            found |= {f[: -len(ext)] for f in os.listdir(d) if f.endswith(ext)}
    found.discard("all")
    order = (manifest or {}).get("order") or TLDS
    return [t for t in order if t in found] + sorted(found - set(order))


def count_lines(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def short_counts(root, tld):
    """Free (status=available) 1-3 character names per length, plus the
    newest check time. Falls back to txt/<tld>.txt if there is no CSV."""
    counts, newest = {1: 0, 2: 0, 3: 0}, ""
    path = os.path.join(root, "csv", tld + ".csv")
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                newest = max(newest, row.get("checked_at") or "")
                if row.get("status") == "available":
                    n = int(row["length"])
                    counts[n] = counts.get(n, 0) + 1
        return counts, newest
    path = os.path.join(root, "txt", tld + ".txt")
    if not os.path.exists(path):
        return None, newest
    with open(path, encoding="utf-8") as f:
        for line in f:
            label = line.strip().rsplit(".", 1)[0]
            if label:
                counts[len(label)] = counts.get(len(label), 0) + 1
    return counts, newest


def load_changes(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if isinstance(data, dict):
        data = data.get("changes", [])
    return data if isinstance(data, list) else None


def fmt(n):
    return f"{n:,}"


def link(n, path):
    return f"[{fmt(n)}]({path})"


def render(root, changes_path=None):
    manifest = load_manifest(root)
    tlds = tlds_present(root, manifest)
    rows, newest, totals = [], "", {1: 0, 2: 0, 3: 0, 4: 0}
    for tld in tlds:
        counts, checked = short_counts(root, tld)
        newest = max(newest, checked)
        txt = f"txt/{tld}.txt"
        cells = []
        for n in (1, 2, 3):
            if counts is None:
                cells.append("–")
            else:
                totals[n] += counts.get(n, 0)
                cells.append(link(counts.get(n, 0), txt))
        four = count_lines(os.path.join(root, "four-letter", tld + ".txt"))
        if four is None:
            cells.append("–")
        else:
            totals[4] += four
            cells.append(link(four, f"four-letter/{tld}.txt"))
        files = []
        if os.path.exists(os.path.join(root, "csv", tld + ".csv")):
            files.append(f"[csv](csv/{tld}.csv)")
        if os.path.exists(os.path.join(root, txt)):
            files.append(f"[txt]({txt})")
        rows.append(f"| `.{tld}` | " + " | ".join(cells) + " | " + " · ".join(files) + " |")

    out = []
    w = out.append
    w("# Free short domains\n")
    w(
        "Every **1–3 character** domain on "
        + " ".join(f"`.{t}`" for t in (tlds or TLDS))
        + " that the registry reports as not registered, plus all **4-letter** names not in the zone. Plain CSV and TXT, generated daily by "
        + f"[shortfree]({SHORTFREE}).\n"
    )
    w(
        f"[![last update](https://img.shields.io/github/last-commit/{REPO}?label=last%20update)](https://github.com/{REPO}/commits/main)"
        " [![license: CC0-1.0](https://img.shields.io/badge/license-CC0--1.0-lightgrey)](LICENSE)\n"
    )

    has_all = os.path.exists(os.path.join(root, "csv", "all.csv"))
    txts = [t for t in tlds if os.path.exists(os.path.join(root, "txt", t + ".txt"))]
    if not rows:
        w("> The first daily update has not run yet. The lists appear here after the next scan.\n")
    else:
        dl = []
        if has_all:
            dl.append(f"[**all.csv**]({RAW}csv/all.csv)")
        dl += [f"[{t}.txt]({RAW}txt/{t}.txt)" for t in txts]
        w("**Raw downloads:** " + " · ".join(dl) + "\n")
        if has_all:
            w("```sh\ncurl -sL " + RAW + "csv/all.csv\n```\n")

    w("## Counts\n")
    if manifest:
        oldest = [t.get("oldest_check") for t in manifest.get("tlds", {}).values() if t.get("oldest_check")]
        line = f"_Scan of {manifest['updated'][:16].replace('T', ' ')} UTC (snapshot `{manifest['name']}`)."
        if oldest:
            line += f" Oldest registry check behind a listed name: {min(oldest)[:10]}; checks older than {manifest.get('max_evidence_age_days', 14):g} days are not listed."
        w(line + " Click a number to open the list._\n")
        weak = [f"`.{t}` {c['coverage']}" for t, c in manifest.get("tlds", {}).items() if c.get("coverage") not in (None, "complete")]
        if weak:
            w("Coverage is not complete for " + ", ".join(weak) + " (partial: some names not checked yet; stale: the latest scan failed; held: the latest scan looked implausible and was not used). Unchecked names are not counted as taken.\n")
        if manifest.get("missing"):
            w("No data yet for " + " ".join(f"`.{t}`" for t in manifest["missing"]) + ".\n")
    elif newest:
        w(f"_Data as of {newest[:10]} (newest registry check, UTC). Click a number to open the list._\n")
    w("| TLD | 1 char | 2 chars | 3 chars | 4 letters¹ | files |")
    w("|---|--:|--:|--:|--:|---|")
    if rows:
        out.extend(rows)
        w(f"| **all** | {fmt(totals[1])} | {fmt(totals[2])} | {fmt(totals[3])} | {fmt(totals[4])} | "
          + ("[csv](csv/all.csv)" if has_all else "") + " |")
    else:
        w("| – | – | – | – | – | |")
    w("")
    w(
        f"¹ a–z only, not in the zone (DNS check, not RDAP-verified). "
        + ("Some 4 character shards have not been swept yet, so these counts are partial. " if manifest and any(t.get("four_unscanned") for t in manifest.get("tlds", {}).values()) else "")
        + 
        f"Full 4 character lists with digits and hyphens: [shortfree data release]({SHORTFREE}/releases/tag/data).\n"
    )

    changes = load_changes(changes_path)
    if changes:
        freed = [c for c in changes if isinstance(c, dict) and c.get("event") == "freed"][:RECENT]
        if freed:
            w("## Recently freed\n")
            w("Names the registry reported as registered or dropping that it now reports as not registered.\n")
            w(" · ".join(f"`{c['domain']}`" for c in freed) + "\n")

    w("## Files\n")
    w("| Path | Content |")
    w("|---|---|")
    w("| `csv/all.csv` | every 1–3 character domain with a current RDAP answer \"not registered\", on all TLDs |")
    w("| `csv/<tld>.csv` | 1–3 character names with status `available` (not registered), `dropping` (redemption / pending delete), `unverified` (no current RDAP answer) or `unknown` (no DNS answer) |")
    w("| `txt/<tld>.txt` | RDAP-verified (not registered) 1–3 character domains, one per line |")
    w("| `four-letter/<tld>.txt` | 4-letter names (a–z) not in the zone, one per line (DNS check only) |")
    w("| `snapshot.json` | manifest of the shortfree snapshot these files come from: checksums, counts, coverage, source run |")
    w("")
    w("CSV columns: `domain,tld,length,kind,status,first_seen,checked_at,verification,evidence_age_days` (`kind` = letters, digits or mixed; `verification` = rdap_verified, stale or pending; dates in UTC).\n")

    w("## Method\n")
    w(
        f"The lists come from [shortfree]({SHORTFREE}), which queries every candidate name directly at the TLD's "
        "authoritative name servers and confirms each 1–3 character name in the registry's RDAP service "
        "(`404` = not registered; answers older than 14 days are not listed as verified). 4-letter names are "
        "DNS-checked only. Not registered does not mean registrable: registries reserve some names or sell them at "
        "premium prices, which RDAP does not show, so check at your registrar. Only ASCII names are covered (no IDN). "
        "A name can be taken minutes after the scan. Every update installs one complete, checksum-verified snapshot. "
        f"Details: [accuracy]({SHORTFREE}/blob/main/docs/accuracy.md). Also available as a "
        f"[JSON/CSV API]({SHORTFREE}/blob/main/docs/api.md).\n"
    )
    w("If these lists save you time, a star helps other people find them.\n")
    w("Data: [CC0 1.0](LICENSE), no attribution required.")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--changes", help="shortfree changes.json (optional)")
    ap.add_argument("--out", default="README.md", help="output file, relative to --root")
    a = ap.parse_args()
    text = render(a.root, a.changes)
    with open(os.path.join(a.root, a.out), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()

# Free short domains

Every unregistered **1–3 character** domain on `.com` `.net` `.de` `.ai` `.io` `.dev` `.app` `.tools`, plus all free **4-letter** names. Plain CSV and TXT, verified against the registries, updated daily.

[![last update](https://img.shields.io/github/last-commit/maximilianfeix/free-short-domains?label=last%20update)](https://github.com/maximilianfeix/free-short-domains/commits/main) [![license: CC0-1.0](https://img.shields.io/badge/license-CC0--1.0-lightgrey)](LICENSE)

> The first daily update has not run yet. The lists appear here after the next scan.

## Counts

| TLD | 1 char | 2 chars | 3 chars | 4 letters¹ | files |
|---|--:|--:|--:|--:|---|
| – | – | – | – | – | |

¹ a–z only, not in the zone (DNS check, not RDAP-verified). Full 4 character lists with digits and hyphens: [shortfree data release](https://github.com/maximilianfeix/shortfree/releases/tag/data).

## Files

| Path | Content |
|---|---|
| `csv/all.csv` | every RDAP-verified free 1–3 character domain on all TLDs |
| `csv/<tld>.csv` | 1–3 character names with status `available`, `dropping` (redemption / pending delete) or `unverified` (RDAP check pending) |
| `txt/<tld>.txt` | verified free 1–3 character domains, one per line |
| `four-letter/<tld>.txt` | free 4-letter names (a–z), one per line |

CSV columns: `domain,tld,length,kind,status,first_seen,checked_at` (`kind` = letters, digits or mixed; dates in UTC).

## Method

The lists come from [shortfree](https://github.com/maximilianfeix/shortfree), which queries every candidate name directly at the TLD's authoritative name servers and confirms each 1–3 character name in the registry's RDAP service (`404` = not registered). 4-letter names are DNS-checked only. Free does not mean cheap: registries reserve some names or sell them at premium prices, which RDAP does not show, so check the price at your registrar. A name can be taken minutes after the scan. Also available as a [JSON/CSV API](https://github.com/maximilianfeix/shortfree/blob/main/docs/api.md).

If these lists save you time, a star helps other people find them.

Data: [CC0 1.0](LICENSE), no attribution required.

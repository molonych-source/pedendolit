"""
Rebuild comprehensive_raw.json from every raw PubMed record on disk.

Why this exists
---------------
comprehensive_raw.json is the canonical cumulative source that
`build_dataset.py --rebuild` reclassifies from. It was originally assembled by an
ad-hoc script that was never saved (the runbook points at "session history"), and
the version it produced had lost most of its abstracts: 1053 records but only 93
abstracts. Meanwhile the original per-batch MCP fetches in _tmp_batches/ still had
full text, citation blocks, and PMC ids.

The consequence was that 74% of the store was classified on title alone, which is
why two-thirds of articles ended up typed "Other" with no clinical bottom line.

This script merges every local source, keeping the BEST value for each field per
PMID, so the classifier gets the richest text available. It makes no network calls.

Merge rules
-----------
- abstract: longest wins (some copies were condensed by a subagent during fetch)
- authors / mesh_terms / keywords / article_types: longest list wins
- citation, identifiers: filled field by field, first non-empty wins
- everything else: first non-empty wins

Usage:
  python3 merge_raw_sources.py [--dry-run] [--out comprehensive_raw.json]
"""
import json, os, glob, argparse

HERE = os.path.dirname(os.path.abspath(__file__))

# Explicit sources first (most trusted last-write), then every batch file.
NAMED_SOURCES = [
    "comprehensive_raw.json",
    "raw_articles.prev.json",
    "raw_articles.json",
    "raw_articles_apem_backfill.json",
    "pilot_raw.json",
    "backfill_inline_supplement.json",
    "raw_supplement_jes.json",
]

LONGEST_STR_FIELDS = ("abstract", "title")
LONGEST_LIST_FIELDS = ("authors", "mesh_terms", "keywords", "article_types")
NESTED_DICT_FIELDS = ("identifiers", "journal", "publication_date", "citation")


def load_source(path):
    """Return a list of raw records from a JSON file, tolerating wrapper dicts."""
    try:
        with open(path) as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(d, dict):
        for k in ("articles", "records", "results", "data"):
            if isinstance(d.get(k), list):
                d = d[k]
                break
    return d if isinstance(d, list) else []


def pmid_of(rec):
    ids = rec.get("identifiers") or {}
    return str(ids.get("pmid") or rec.get("pmid") or "").strip()


def merge_into(dst, src):
    """Fold src into dst, keeping whichever value carries more information."""
    for k, v in src.items():
        if v in (None, "", [], {}):
            continue
        cur = dst.get(k)
        if k in NESTED_DICT_FIELDS and isinstance(v, dict):
            sub = dict(cur) if isinstance(cur, dict) else {}
            for sk, sv in v.items():
                if sv not in (None, "", [], {}) and sub.get(sk) in (None, "", [], {}):
                    sub[sk] = sv
            dst[k] = sub
        elif k in LONGEST_LIST_FIELDS and isinstance(v, list):
            if not isinstance(cur, list) or len(v) > len(cur):
                dst[k] = v
        elif k in LONGEST_STR_FIELDS and isinstance(v, str):
            if not isinstance(cur, str) or len(v) > len(cur):
                dst[k] = v
        elif cur in (None, "", [], {}):
            dst[k] = v
    return dst


def collect_sources():
    paths = []
    for name in NAMED_SOURCES:
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            paths.append(p)
    paths += sorted(glob.glob(os.path.join(HERE, "_tmp_batches", "*.json")))
    return paths


def store_as_raw(store_path):
    """Reverse-map the classified store back into raw-record shape.

    45 articles in pedendolit-data.json exist in NO raw file on disk — including
    both Practice-Altering Endocrine Society guidelines. Rebuilding purely from
    raw sources would silently delete them. Folding the store in first makes the
    rebuild non-destructive; real raw records still win on every field, because
    they are merged afterwards and carry longer abstracts and author lists.
    """
    try:
        with open(store_path) as f:
            arts = json.load(f).get("articles", [])
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for a in arts:
        pmid = str(a.get("pmid") or "").strip()
        if not pmid:
            continue
        authors = []
        for s in (a.get("authors") or []):
            parts = str(s).rsplit(" ", 1)
            authors.append({"last_name": parts[0], "initials": parts[1] if len(parts) > 1 else ""})
        y, m_, d_ = (str(a.get("pub_date") or "").split("-") + ["", ""])[:3]
        out.append({
            "identifiers": {"pmid": pmid, "doi": a.get("doi") or ""},
            "title": a.get("title") or "",
            "abstract": a.get("abstract") or "",
            "journal": {"title": a.get("journal") or "",
                        "iso_abbreviation": a.get("journal_abbr") or ""},
            "authors": authors,
            "publication_date": {"year": y, "month": m_, "day": d_},
            "article_types": a.get("pub_types") or [],
            "mesh_terms": a.get("mesh_terms") or [],
            "keywords": a.get("keywords") or [],
        })
    return out


def stats(records):
    def n(pred):
        return sum(1 for r in records if pred(r))
    return {
        "records": len(records),
        "abstract": n(lambda r: r.get("abstract")),
        "authors": n(lambda r: r.get("authors")),
        "doi": n(lambda r: (r.get("identifiers") or {}).get("doi") or r.get("doi")),
        "article_types": n(lambda r: r.get("article_types")),
        "citation": n(lambda r: (r.get("citation") or {}).get("volume")),
        "pmc": n(lambda r: (r.get("identifiers") or {}).get("pmc")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, do not write")
    ap.add_argument("--out", default="comprehensive_raw.json")
    ap.add_argument("--no-store", action="store_true",
                    help="do not seed from pedendolit-data.json (rebuild becomes destructive)")
    a = ap.parse_args()

    out_path = os.path.join(HERE, a.out)
    before = stats(load_source(out_path))

    merged, skipped = {}, 0

    # Seed from the existing store first so nothing already published can be lost,
    # then let the real raw records overwrite/extend those fields.
    store_seed = [] if a.no_store else store_as_raw(os.path.join(HERE, "pedendolit-data.json"))
    for rec in store_seed:
        merged[pmid_of(rec)] = dict(rec)
    seeded = len(merged)

    paths = collect_sources()
    for p in paths:
        for rec in load_source(p):
            if not isinstance(rec, dict):
                continue
            pmid = pmid_of(rec)
            if not pmid:
                skipped += 1
                continue
            if pmid in merged:
                merge_into(merged[pmid], rec)
            else:
                merged[pmid] = dict(rec)

    records = [merged[k] for k in sorted(merged)]
    after = stats(records)

    print(f"seeded {seeded} PMIDs from the existing store, "
          f"scanned {len(paths)} source files, {len(merged)} unique PMIDs total"
          + (f", {skipped} records skipped (no pmid)" if skipped else ""))
    print(f"{'field':<15}{'before':>9}{'after':>9}")
    for k in after:
        print(f"{k:<15}{before.get(k, 0):>9}{after[k]:>9}")

    if a.dry_run:
        print("\n--dry-run: nothing written")
        return
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()

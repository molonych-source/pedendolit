"""
Coverage audit: does the pipeline actually hold every article the monitored-journal
queries return?

Runs the same per-journal queries as weekly_fetch.py over a window, by BOTH Entrez date
and publication date, and diffs the result against every PMID the pipeline has ever
seen (the store plus every raw file, which also covers articles the classifier
excluded). Anything left over was never fetched.

This is the check that would have caught the 2026-10-13 finding: ~600 articles from
2026 never fetched because their year-only publication date kept them out of the old
publication-date window. Exits 1 when anything is missing, so it can gate the weekly run.

Usage:
  python3 audit_coverage.py                     # last 90 days
  python3 audit_coverage.py --since 2026-01-01
  python3 audit_coverage.py --since 2026-01-01 --write-missing missing_pmids.json
"""
import json, os, sys, glob, argparse, datetime, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("weekly_fetch", os.path.join(HERE, "weekly_fetch.py"))
wf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(wf)


def seen_pmids():
    seen = {str(a["pmid"]) for a in json.load(open(os.path.join(HERE, "pedendolit-data.json")))["articles"]}
    try:
        seen |= set(json.load(open(os.path.join(HERE, "excluded_pmids.json")))["excluded"])
    except (ValueError, OSError, KeyError):
        pass
    paths = glob.glob(os.path.join(HERE, "*raw*.json")) + glob.glob(os.path.join(HERE, "_tmp_batches", "*.json"))
    for p in paths:
        try:
            data = json.load(open(p))
        except (ValueError, OSError):
            continue
        for r in (data if isinstance(data, list) else []):
            if isinstance(r, dict):
                pm = (r.get("identifiers") or {}).get("pmid") or r.get("pmid")
                if pm:
                    seen.add(str(pm))
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD (default: 90 days ago)")
    ap.add_argument("--write-missing")
    a = ap.parse_args()
    today = datetime.date.today()
    since = a.since or (today - datetime.timedelta(days=90)).isoformat()
    mn, mx = since.replace("-", "/"), today.strftime("%Y/%m/%d")
    found = {}
    for dt in ("edat", "pdat"):
        for abbr, ids in wf.search_journals(mn, mx, dt).items():
            found.setdefault(abbr, set()).update(ids)
    seen = seen_pmids()
    missing = {abbr: sorted(ids - seen) for abbr, ids in found.items() if ids - seen}
    total = sum(len(v) for v in found.values())
    n_missing = sum(len(v) for v in missing.values())
    print(f"coverage audit {since} to {today}: {total} PMIDs from the journal queries, {n_missing} never fetched")
    for abbr, ids in sorted(missing.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(ids):4d}  {abbr}")
    if a.write_missing:
        allm = sorted({p for v in missing.values() for p in v})
        json.dump(allm, open(a.write_missing, "w"))
        print(f"wrote {len(allm)} PMIDs -> {a.write_missing}")
    if n_missing:
        print("FAIL: fetch these with  python3 weekly_fetch.py --pmids <file> --out <raw file>")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

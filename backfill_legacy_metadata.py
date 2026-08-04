"""
One-off maintenance script: refresh in-place the ~946 legacy articles (all from the
2026-06-28 backfill) that are missing abstract/authors/doi/journal_abbr/pub_types/
mesh_terms/keywords, and re-run the classifier on the corrected data.

Unlike build_dataset.py's normal merge (which SKIPS existing PMIDs) or --rebuild
(which discards anything not in the raw source), this UPDATES matching PMIDs in place:
  - Overwrites: title, abstract, journal, journal_abbr, authors, doi, pub_date,
    pub_types, mesh_terms, keywords, url, doi_url, and all classifier-derived fields
    (topic, subtopic, study_type, impact, board_relevant, tags, impact_rationale).
  - Preserves untouched: pmid, review_date, review_period, is_new, is_archived.

Usage:
  python3 backfill_legacy_metadata.py --raw legacy_refetch_raw.json [--dry-run]
"""
import json, os, sys, argparse, importlib.util
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "pedendolit-data.json")

# reuse map_raw + classifier from build_dataset.py / classifier.py (same pattern
# build_dataset.py itself uses to load classifier.py)
_spec_bd = importlib.util.spec_from_file_location("bd", os.path.join(HERE, "build_dataset.py"))
bd = importlib.util.module_from_spec(_spec_bd); _spec_bd.loader.exec_module(bd)
clf = bd.clf  # classifier module, already loaded by build_dataset.py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="JSON array of raw PubMed-MCP metadata records")
    ap.add_argument("--dry-run", action="store_true", help="report what would change, don't write")
    args = ap.parse_args()

    with open(DATA) as f:
        store = json.load(f)
    by_pmid = {a["pmid"]: a for a in store["articles"] if a.get("pmid")}

    with open(args.raw) as f:
        raw_list = json.load(f)

    before_impact = Counter(a.get("impact") for a in store["articles"])
    before_study = Counter(a.get("study_type") for a in store["articles"])

    updated, not_found, impact_changed = 0, [], []
    for raw in raw_list:
        rec = bd.map_raw(raw)
        pmid = rec["pmid"]
        if not pmid or pmid not in by_pmid:
            not_found.append(pmid)
            continue
        existing = by_pmid[pmid]
        c = clf.classify(rec)
        if c.get("excluded"):
            # Shouldn't happen for articles already accepted once, but don't silently
            # drop a previously-included article over a reclassification quirk.
            print(f"WARNING: PMID {pmid} would now be excluded ({c.get('exclude_reason')}) "
                  f"— leaving existing record untouched.")
            continue
        old_impact = existing.get("impact")
        new_impact = c["impact"]
        if old_impact != new_impact:
            impact_changed.append((pmid, old_impact, new_impact, rec["title"][:80]))
        # Preserve lifecycle fields; overwrite everything else.
        preserved = {k: existing[k] for k in
                     ("review_date", "review_period", "is_new", "is_archived")
                     if k in existing}
        merged = {**rec, **c, **preserved}
        by_pmid[pmid] = merged
        updated += 1

    store["articles"] = list(by_pmid.values())
    after_impact = Counter(a.get("impact") for a in store["articles"])
    after_study = Counter(a.get("study_type") for a in store["articles"])

    print(f"=== backfill_legacy_metadata ===")
    print(f"raw fetched: {len(raw_list)}  updated: {updated}  not_found_in_store: {len(not_found)}")
    if not_found:
        print(f"  not_found PMIDs (first 20): {not_found[:20]}")
    print(f"impact tier BEFORE: {dict(before_impact)}")
    print(f"impact tier AFTER:  {dict(after_impact)}")
    print(f"study_type BEFORE: {dict(before_study)}")
    print(f"study_type AFTER:  {dict(after_study)}")
    print(f"articles with impact CHANGED: {len(impact_changed)}")
    for pmid, old, new, title in impact_changed[:40]:
        print(f"  PMID {pmid}: {old} -> {new}  | {title}")
    if len(impact_changed) > 40:
        print(f"  ... and {len(impact_changed) - 40} more")

    if args.dry_run:
        print("\nDRY RUN — no file written.")
        return

    with open(DATA, "w") as f:
        json.dump(store, f, indent=1, ensure_ascii=False)
    print(f"\nwrote {DATA}")


if __name__ == "__main__":
    main()

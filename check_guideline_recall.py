"""
Recall test for the guideline sweep's PubMed search (guideline_fetch.py).

Known set: every guideline a physician APPROVED in guideline_decisions.json whose
store pub_date falls inside the test window. Those are confirmed in-scope guidelines,
so the sweep's query should find them. The test re-runs the query over the window and
fails if any known guideline is missing, except PMIDs already acknowledged in
guideline_recall_baseline.json (misses that existed when this test was written).

Run it after ANY change to the queries in guideline_fetch.py. It needs network access
(NCBI E-utilities) and takes under a minute.

To acknowledge a new miss as acceptable (rare: say why in the reason), add it with:
    python3 check_guideline_recall.py --accept PMID "reason"

Usage:
  python3 check_guideline_recall.py [--mindate 2024-01-01]
"""
import json, os, sys, argparse, datetime, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "guideline_recall_baseline.json")


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mindate", default="2024-01-01")
    ap.add_argument("--accept", nargs=2, metavar=("PMID", "REASON"))
    a = ap.parse_args()

    base = json.load(open(BASELINE)) if os.path.exists(BASELINE) else {"accepted_misses": {}}
    if a.accept:
        base["accepted_misses"][a.accept[0]] = {"reason": a.accept[1],
                                                "accepted_on": datetime.date.today().isoformat()}
        json.dump(base, open(BASELINE, "w"), indent=1)
        print(f"accepted {a.accept[0]}"); return 0

    dec = json.load(open(os.path.join(HERE, "guideline_decisions.json")))["decisions"]
    approved = {p for p, e in dec.items() if e.get("decision") == "approved"}
    store = {str(x["pmid"]): x for x in json.load(open(os.path.join(HERE, "pedendolit-data.json")))["articles"]}
    known = {p for p in approved if p in store and (store[p].get("pub_date") or "") >= a.mindate}

    gf = _load("guideline_fetch", "guideline_fetch.py")
    # Search by publication date, widened a year back: an article's stored pub_date is
    # its e-publication date, which can precede the issue date PubMed indexes on.
    lo = str(int(a.mindate[:4]) - 1) + "/01/01"
    hi = datetime.date.today().strftime("%Y/%m/%d")
    arms = gf.search_arms(lo, hi, "pdat")
    found = set().union(*arms.values())

    missed = sorted(known - found)
    acked = set(base["accepted_misses"])
    new = [p for p in missed if p not in acked]
    print(f"known approved guidelines since {a.mindate}: {len(known)} | found by query: "
          f"{len(known) - len(missed)} | recall {100 * (len(known) - len(missed)) / max(1, len(known)):.0f}%")
    if missed:
        print(f"missed: {len(missed)} ({len(missed) - len(new)} already acknowledged in the baseline)")
    if new:
        print("FAIL: the query no longer finds these approved guidelines:")
        for p in new:
            print(f"  !!  {p}: {(store[p].get('title') or '')[:80]}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

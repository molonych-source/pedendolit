"""
Apply the approvals downloaded from guideline_review.html.

Reads approved_pmids.json (the file the review page downloads) and:
  1. writes guideline_approved_raw.json — only the approved raw records,
  2. records EVERY decision (approved and rejected) in guideline_decisions.json, so the
     next sweep skips them instead of asking again,
  3. prints the merge commands rather than running them.

Step 3 is deliberate: mutating the store stays on the existing, understood path
(build_dataset.py --raw), so there is one way articles enter the datastore, not two.

Idempotent — re-running with the same file rewrites the same outputs and adds no
duplicate decisions.

Usage:
  python3 apply_approvals.py [--approvals ~/Downloads/approved_pmids.json]
"""
import json, os, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_APPROVALS = os.path.expanduser("~/Downloads/approved_pmids.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approvals", default=DEFAULT_APPROVALS,
                    help="the file downloaded by the review page")
    ap.add_argument("--candidates", default="guideline_candidates.json")
    ap.add_argument("--verdicts", default="guideline_verdicts.json")
    ap.add_argument("--decisions", default="guideline_decisions.json")
    ap.add_argument("--out", default="guideline_approved_raw.json")
    args = ap.parse_args()

    apath = args.approvals if os.path.isabs(args.approvals) else os.path.join(HERE, args.approvals)
    if not os.path.exists(apath):
        raise SystemExit(f"no approvals file at {apath}\n"
                         f"Open guideline_review.html, tick your choices, click Submit.")

    sub = json.load(open(apath))
    approved = set(str(p) for p in sub.get("approved", []))
    rejected = set(str(p) for p in sub.get("rejected", []))

    cands = json.load(open(os.path.join(HERE, args.candidates)))
    vpath = os.path.join(HERE, args.verdicts)
    verdicts = json.load(open(vpath)).get("verdicts", {}) if os.path.exists(vpath) else {}

    by_pmid = {}
    for rec in cands:
        pm = str((rec.get("identifiers") or {}).get("pmid"))
        if pm and pm != "None":
            by_pmid[pm] = rec

    unknown = sorted(p for p in (approved | rejected) if p not in by_pmid)
    keep = [by_pmid[p] for p in by_pmid if p in approved]

    outp = os.path.join(HERE, args.out)
    json.dump(keep, open(outp, "w"), indent=1)

    # Decision memory. Keyed by PMID so re-running simply overwrites the same entries.
    dpath = os.path.join(HERE, args.decisions)
    doc = {"comment": "PMIDs already ruled on in a guideline sweep. guideline_sweep.py "
                      "skips these so declined articles do not resurface every month.",
           "decisions": {}}
    if os.path.exists(dpath):
        existing = json.load(open(dpath))
        doc["decisions"] = existing.get("decisions", {})
    today = datetime.date.today().isoformat()
    for pm in sorted(approved | rejected):
        rec = by_pmid.get(pm) or {}
        doc["decisions"][pm] = {
            "decision": "approved" if pm in approved else "rejected",
            "decided_on": today,
            "agent_verdict": (verdicts.get(pm) or {}).get("verdict"),
            "title": (rec.get("title") or "")[:160],
        }
    json.dump(doc, open(dpath, "w"), indent=1)

    print(f"approvals: {len(approved)} approved, {len(rejected)} rejected "
          f"({len(doc['decisions'])} total decisions on record)")
    if unknown:
        print(f"  WARNING: {len(unknown)} pmid(s) not in {args.candidates}: {', '.join(unknown[:8])}")
    print(f"  wrote {outp}")
    print(f"  wrote {dpath}")
    if keep:
        print("\nNow merge them the normal way:")
        print(f"  python3 build_dataset.py --raw {os.path.basename(outp)}")
        print( "  python3 merge_raw_sources.py")
        print( "  python3 build_dashboard.py")
    else:
        print("\nNothing approved — no merge needed.")


if __name__ == "__main__":
    main()

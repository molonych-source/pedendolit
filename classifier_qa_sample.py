"""
Classifier QA sweep — sampling stage.

Reads the live store and produces a stratified sample of already-classified
articles for a judge (Sonnet subagent) to re-evaluate: is the assigned topic
actually correct? This is a companion to guideline_sweep.py, but solves a
different problem — that pipeline decides whether a PMID should be ADDED to
the store; this one re-checks whether a PMID already in the store has the
RIGHT topic.

No network calls, no raw fetch: this only re-judges classifications the
pipeline already made, from pedendolit-data.json itself.

Re-eligibility, not a flat skip-list: classifier_qa_decisions.json (written by
apply_classifier_qa.py) records each PMID's topic_at_review. A PMID is only
excluded from a fresh sample if its ledger entry's topic_at_review still
matches its CURRENT store topic AND the recorded verdict was "correct" — once
a classifier.py fix changes that PMID's topic, it becomes eligible again
automatically, which is what lets a later round confirm the fix. A PMID ruled
"wrong" whose topic hasn't moved yet is force-included every round as
pending_fix, regardless of its stratum's quota, so it can't quietly drop out
of a broad sample.

Usage:
  python3 classifier_qa_sample.py --topic Diabetes --study-type "Guideline/Consensus"
  python3 classifier_qa_sample.py --n-per-topic 20 --exhaustive-below 30
"""
import json, os, argparse, random

HERE = os.path.dirname(os.path.abspath(__file__))


def load_decisions(path):
    if not os.path.exists(path):
        return {}
    try:
        return (json.load(open(path)) or {}).get("decisions", {})
    except (ValueError, OSError):
        print(f"  note: {os.path.basename(path)} unreadable — treating as empty")
        return {}


def eligible(pmid, current_topic, decisions):
    """False only if the ledger already confirmed this exact topic as correct."""
    entry = decisions.get(pmid)
    if not entry:
        return True
    if entry.get("topic_at_review") == current_topic and entry.get("verdict") == "correct":
        return False
    return True


def pending_fix(pmid, current_topic, decisions):
    """True if a prior round flagged this PMID wrong and the topic hasn't moved yet.
    residual_accepted (an explicit, dated, reasoned ledger note — see
    CLASSIFIER_QA_RUNBOOK.md's Definition of done) closes this out deliberately: some
    known-wrong classifications have no keyword-based fix without worse collateral
    damage, so they shouldn't force-include forever waiting for one."""
    entry = decisions.get(pmid)
    if not entry:
        return False
    if entry.get("residual_accepted"):
        return False
    return entry.get("verdict") == "wrong" and entry.get("topic_at_review") == current_topic


def item_payload(a):
    return {
        "pmid": str(a.get("pmid")),
        "title": a.get("title") or "",
        "abstract": a.get("abstract") or "",
        "current_topic": a.get("topic"),
        "current_subtopic": a.get("subtopic"),
        "study_type": a.get("study_type"),
        "journal_abbr": a.get("journal_abbr"),
        "pub_date": a.get("pub_date"),
        "url": a.get("url"),
        "mesh_terms": a.get("mesh_terms") or [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--decisions", default="classifier_qa_decisions.json")
    ap.add_argument("--topic", action="append", default=[],
                     help="restrict to this topic (repeatable)")
    ap.add_argument("--study-type", action="append", default=[],
                     help="restrict to this study_type (repeatable)")
    ap.add_argument("--n-per-topic", type=int, default=20)
    ap.add_argument("--exhaustive-below", type=int, default=30,
                     help="topics with <= this many eligible articles are sampled 100%%")
    ap.add_argument("--force-pmid", action="append", default=[])
    ap.add_argument("--force-pmids-file", default=None,
                     help="text file, one PMID per line, or a JSON list")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="classifier_qa_sample.json")
    args = ap.parse_args()

    store_path = os.path.join(HERE, args.store)
    dec_path = os.path.join(HERE, args.decisions)

    store = json.load(open(store_path))
    decisions = load_decisions(dec_path)

    forced_in = set(str(p) for p in args.force_pmid)
    if args.force_pmids_file:
        raw = open(args.force_pmids_file).read().strip()
        try:
            forced_in |= set(str(p) for p in json.loads(raw))
        except ValueError:
            forced_in |= set(l.strip() for l in raw.splitlines() if l.strip())

    topic_filter = set(args.topic)
    study_type_filter = set(args.study_type)

    active = [a for a in store.get("articles", [])
              if not a.get("excluded") and not a.get("is_archived")]
    if topic_filter:
        active = [a for a in active if a.get("topic") in topic_filter]
    if study_type_filter:
        active = [a for a in active if a.get("study_type") in study_type_filter]

    by_topic = {}
    for a in active:
        by_topic.setdefault(a.get("topic"), []).append(a)

    rng = random.Random(args.seed)
    strata, chosen_pmids, items, forced_pmids = {}, set(), [], set()

    for topic, arts in by_topic.items():
        # Sort by PMID first so sampling is deterministic regardless of JSON/dict order.
        arts = sorted(arts, key=lambda a: str(a.get("pmid")))
        pool = [a for a in arts if eligible(str(a.get("pmid")), topic, decisions)]
        pending = [a for a in arts if pending_fix(str(a.get("pmid")), topic, decisions)]

        take_all = len(pool) <= args.exhaustive_below
        sample = pool if take_all else rng.sample(pool, min(args.n_per_topic, len(pool)))

        strata[topic] = {"pool_size": len(pool), "sampled": len(sample),
                          "exhaustive": len(sample) == len(pool)}

        for a in sample:
            pmid = str(a.get("pmid"))
            if pmid not in chosen_pmids:
                chosen_pmids.add(pmid)
                items.append(item_payload(a))
        for a in pending:
            pmid = str(a.get("pmid"))
            forced_pmids.add(pmid)
            if pmid not in chosen_pmids:
                chosen_pmids.add(pmid)
                items.append(item_payload(a))

    # Explicit --force-pmid / --force-pmids-file: pull from the FULL store (not just
    # `active`), since a forced PMID may sit outside the current --topic/--study-type
    # filter (e.g. carrying forward a regression from an unrelated stratum).
    by_pmid_all = {str(a.get("pmid")): a for a in store.get("articles", [])}
    for pmid in forced_in:
        forced_pmids.add(pmid)
        if pmid not in chosen_pmids and pmid in by_pmid_all:
            chosen_pmids.add(pmid)
            items.append(item_payload(by_pmid_all[pmid]))

    out_doc = {
        "generated": store.get("generated"),
        "seed": args.seed,
        "filters": {"topic": sorted(topic_filter), "study_type": sorted(study_type_filter)},
        "strata": strata,
        "forced_pmids": sorted(forced_pmids),
        "items": items,
    }

    out_path = os.path.join(HERE, args.out)
    json.dump(out_doc, open(out_path, "w"), indent=1)

    print(f"classifier QA sample: {len(items)} articles across {len(strata)} topic(s) "
          f"({len(forced_pmids)} forced/pending)")
    for topic, s in sorted(strata.items()):
        tag = "exhaustive" if s["exhaustive"] else f"sampled {s['sampled']}/{s['pool_size']}"
        print(f"  {topic}: {tag}")
    print(f"  wrote {out_path}")


if __name__ == "__main__":
    main()

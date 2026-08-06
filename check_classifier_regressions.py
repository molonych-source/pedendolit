"""
Classifier regression check — the deterministic, zero-cost layer of classifier QA.

Compares the LAST PUBLISHED store (git HEAD) against the CURRENT working-tree store
and fails if any article changed topic without something having predicted it. This is
the check that would have caught, automatically, the near-miss during the 2026-08-05
QA sweep: a thalassemia guard that looked correct but quietly moved an
already-correctly-classified Puberty article.

Why git rather than a snapshot file: `git show HEAD:pedendolit-data.json` is always
available, needs no discipline to maintain, and gives exactly the comparison worth
making — last published vs. just rebuilt. A snapshot file you must remember to write
before every rebuild is a check that silently disables itself the first time someone
forgets.

What fails vs. what only informs:
  * topic changed with no ledger entry predicting it  -> FAIL
  * an article disappeared from the store             -> FAIL (a classifier change can
    make exclusion rules newly fire and silently drop content)
  * study_type / impact changed                       -> reported, never fails. These
    legitimately shift whenever classification improves and no ledger records intent
    for them, so failing on them would cry wolf on every real improvement. But a
    study_type flip moves an article's impact tier and therefore what lands on the
    front page, so the counts are worth seeing.

A topic change counts as PREDICTED when `classifier_qa_decisions.json` holds an entry
for that PMID whose `target_topic` equals the article's new topic. That covers both
routes by which a topic is meant to move: a reviewed `wrong` verdict that a
classifier.py fix then implements, and a `residual_accepted` override that
build_dataset.apply_topic_overrides() writes directly.

Blessing an intended-but-unpredicted change is one command, deliberately, because the
friction of hand-editing the ledger is what makes a future session ignore a red exit
code instead:

    python3 check_classifier_regressions.py --bless 41482637 "diazoxide-choline for PWS hyperphagia, not congenital HI"

Usage:
  python3 check_classifier_regressions.py [--ref HEAD] [--store pedendolit-data.json]
  python3 check_classifier_regressions.py --bless PMID "reason" [--bless PMID "reason" ...]
"""
import json, os, sys, argparse, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# Changed values in these fields are reported but never fail the check — see the
# module docstring for why intent can't be verified for them.
INFO_FIELDS = ("study_type", "impact")


# Taxonomy renames: {old topic: new topic}. An article whose topic changed only because
# its label was renamed has not been reclassified, so it must not read as a regression.
# Add a row here whenever a topic is renamed or merged, in the same commit as the change.
TOPIC_RENAMES = {
    # 2026-08-06 merge — one clinical domain that had been split in two. See DECISIONS.md.
    "Bone/Calcium": "Bone/Mineral",
    "Calcium/Parathyroid": "Bone/Mineral",
}


def load_ref_store(ref, store_name):
    """The store as of a git ref, or None if it isn't there (e.g. first commit)."""
    try:
        out = subprocess.run(["git", "show", f"{ref}:{store_name}"],
                             cwd=HERE, capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        return json.loads(out.stdout)
    except ValueError:
        return None


def index_by_pmid(store):
    return {str(a.get("pmid")): a for a in store.get("articles", []) if a.get("pmid")}


def load_ledger(path):
    if not os.path.exists(path):
        return {}
    try:
        return (json.load(open(path)) or {}).get("decisions", {})
    except (ValueError, OSError):
        return {}


def bless(ledger_path, items, after_by_pmid):
    """Record each PMID's CURRENT topic as reviewed-correct, so it stops being flagged.

    Writes into the same ledger apply_classifier_qa.py owns, merging onto any existing
    entry so a residual_accepted flag or prior reasoning is never clobbered.
    """
    doc = {"comment": "PMIDs already ruled on in a classifier QA round. A PMID is "
                      "re-eligible for sampling once the store's topic for it changes "
                      "away from topic_at_review — see classifier_qa_sample.py.",
           "decisions": {}}
    if os.path.exists(ledger_path):
        existing = json.load(open(ledger_path))
        doc["decisions"] = existing.get("decisions", {})
        if existing.get("comment"):
            doc["comment"] = existing["comment"]

    today = datetime.date.today().isoformat()
    for pmid, reason in items:
        art = after_by_pmid.get(pmid)
        if not art:
            raise SystemExit(f"--bless {pmid}: that PMID is not in the current store.")
        topic = art.get("topic")
        entry = dict(doc["decisions"].get(pmid, {}))
        entry.update({
            "topic_at_review": topic,
            "verdict": "correct",
            "target_topic": topic,
            "decided_on": today,
            "decided_by": "regression-bless",
            "bless_reason": reason,
            "title": (art.get("title") or "")[:160],
        })
        doc["decisions"][pmid] = entry
        print(f"  blessed {pmid} as {topic} — {reason}")

    json.dump(doc, open(ledger_path, "w"), indent=1)
    print(f"  wrote {os.path.basename(ledger_path)} ({len(doc['decisions'])} decisions on record)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="HEAD",
                    help="git ref to treat as the 'before' state (default HEAD)")
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--decisions", default="classifier_qa_decisions.json")
    ap.add_argument("--bless", nargs=2, action="append", default=[],
                    metavar=("PMID", "REASON"),
                    help="record a PMID's current topic as reviewed-correct. Repeatable.")
    ap.add_argument("--limit", type=int, default=25,
                    help="max examples to print per section (default 25)")
    args = ap.parse_args()

    store_path = os.path.join(HERE, args.store)
    ledger_path = os.path.join(HERE, args.decisions)

    after = json.load(open(store_path))
    after_by_pmid = index_by_pmid(after)

    if args.bless:
        bless(ledger_path, args.bless, after_by_pmid)
        print("\nRe-run without --bless to confirm the check is clean.")
        return 0

    before = load_ref_store(args.ref, args.store)
    if before is None:
        print(f"no {args.store} at git {args.ref} — nothing to compare against.")
        print("(First commit, or the store isn't tracked yet. Not a failure.)")
        return 0

    before_by_pmid = index_by_pmid(before)
    ledger = load_ledger(ledger_path)

    # target_topic is the single "this article is meant to be X" signal, covering both
    # a reviewed wrong-verdict later fixed in classifier.py and a residual_accepted
    # override applied at build time.
    predicted = {pm: e.get("target_topic") for pm, e in ledger.items() if e.get("target_topic")}

    moved_ok, moved_bad, renamed, info_changed = [], [], [], {f: [] for f in INFO_FIELDS}
    for pmid, a_art in after_by_pmid.items():
        b_art = before_by_pmid.get(pmid)
        if not b_art:
            continue
        b_topic, a_topic = b_art.get("topic"), a_art.get("topic")
        if b_topic != a_topic:
            row = (pmid, b_topic, a_topic, (a_art.get("title") or "")[:70])
            if TOPIC_RENAMES.get(b_topic) == a_topic:
                # A taxonomy rename, not a reclassification. The article did not move;
                # the label it already had was renamed underneath it. Without this, every
                # article in a merged topic reads as an unexplained change — and worse,
                # any still-pending fix in that topic looks like a fresh regression.
                renamed.append(row)
            else:
                (moved_ok if predicted.get(pmid) == a_topic else moved_bad).append(row)
        for f in INFO_FIELDS:
            if b_art.get(f) != a_art.get(f):
                info_changed[f].append((pmid, b_art.get(f), a_art.get(f),
                                        (a_art.get("title") or "")[:70]))

    removed = sorted(set(before_by_pmid) - set(after_by_pmid))
    added = sorted(set(after_by_pmid) - set(before_by_pmid))

    print(f"=== classifier regression check (vs. git {args.ref}) ===")
    print(f"before: {len(before_by_pmid)} articles | after: {len(after_by_pmid)} articles")
    print()

    if renamed:
        print(f"Topic renamed by a taxonomy change: {len(renamed)} "
              f"(informational — the article did not move)")
        for pmid, b, a, title in renamed[:5]:
            print(f"  --  {pmid}: {b} -> {a}  | {title}")
        if len(renamed) > 5:
            print(f"  ... and {len(renamed) - 5} more")
        print()

    if moved_ok:
        print(f"Topic changed as predicted: {len(moved_ok)}")
        for pmid, b, a, title in moved_ok[:args.limit]:
            print(f"  ok  {pmid}: {b} -> {a}  | {title}")
        if len(moved_ok) > args.limit:
            print(f"  ... and {len(moved_ok) - args.limit} more")
        print()

    for f in INFO_FIELDS:
        rows = info_changed[f]
        if not rows:
            continue
        print(f"{f} changed: {len(rows)} (informational — never fails)")
        for pmid, b, a, title in rows[:5]:
            print(f"  --  {pmid}: {b} -> {a}  | {title}")
        if len(rows) > 5:
            print(f"  ... and {len(rows) - 5} more")
        print()

    if added:
        print(f"New articles: {len(added)} (informational)")
        print()

    failures = 0

    if moved_bad:
        failures += len(moved_bad)
        print(f"UNEXPLAINED topic changes: {len(moved_bad)}")
        print("Nothing in the ledger predicted these. Each is either a real regression")
        print("or a correct change nobody recorded — decide which, then either fix")
        print("classifier.py or bless it:")
        for pmid, b, a, title in moved_bad[:args.limit]:
            want = predicted.get(pmid)
            note = f"  (ledger wanted {want})" if want else ""
            print(f"  !!  {pmid}: {b} -> {a}{note}  | {title}")
        if len(moved_bad) > args.limit:
            print(f"  ... and {len(moved_bad) - args.limit} more")
        print()
        print("  python3 check_classifier_regressions.py --bless <PMID> \"<why it's right>\"")
        print()

    if removed:
        failures += len(removed)
        print(f"DISAPPEARED from the store: {len(removed)}")
        print("A classifier change can make exclusion rules newly fire and silently drop")
        print("content. Confirm each was meant to go:")
        for pmid in removed[:args.limit]:
            b = before_by_pmid[pmid]
            print(f"  !!  {pmid}: was {b.get('topic')} | {(b.get('title') or '')[:70]}")
        if len(removed) > args.limit:
            print(f"  ... and {len(removed) - args.limit} more")
        print()

    if failures:
        print(f"FAIL — {failures} change(s) need a human decision.")
        return 1

    print("PASS — every topic change was predicted, and nothing disappeared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

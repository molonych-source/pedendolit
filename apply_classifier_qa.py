"""
Apply the decisions downloaded from classifier_qa_review.html.

Reads classifier_qa_review.json (the file the review page downloads) and:
  1. records EVERY reviewed PMID in classifier_qa_decisions.json (the ledger), so the
     next sample run knows what's already settled and what's still pending_fix,
  2. writes classifier_qa_report.md — the root-cause artifact, grouping confirmed-wrong
     cases by (current_topic -> target_topic) with a title-vs-abstract trigger-location
     signal per PMID (via classifier.classify_topic(art, trace=True), the real waterfall,
     not a parallel reimplementation that could drift out of sync),
  3. prints the rebuild commands rather than running them.

This script never edits classifier.py and never runs --rebuild itself — same discipline
apply_approvals.py already follows for build_dataset.py: mutating the classifier or the
store stays on an understood, human-reviewed path.

Idempotent — re-running with the same input file rewrites the same fields on the same
ledger entries (MERGED onto whatever was already there, never replaced wholesale — a PMID
carrying residual_accepted from an earlier round must keep it through a later round's
re-decision, or the accepted-residual escape hatch silently breaks the next time that PMID
gets sampled).

Some flagged-wrong PMIDs have no code fix without worse collateral damage than the bug
itself (see CLASSIFIER_QA_RUNBOOK.md's Definition of done). Mark one as an accepted
residual — closing it out of pending_fix without touching classifier.py — with:
  python3 apply_classifier_qa.py --accept-residual 38828931 "tested a title-only guard, it misroutes 8 other genuinely diabetes articles"
This only annotates a PMID that already has a ledger entry (from this run or a prior one).

Usage:
  python3 apply_classifier_qa.py [--decisions-in ~/Downloads/classifier_qa_review.json]
  python3 apply_classifier_qa.py --accept-residual PMID "reason"
"""
import json, os, argparse, datetime, importlib.util
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.expanduser("~/Downloads/classifier_qa_review.json")


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


classifier = _load("classifier", "classifier.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions-in", default=DEFAULT_INPUT,
                     help="the file downloaded by classifier_qa_review.html")
    ap.add_argument("--sample", default="classifier_qa_sample.json")
    ap.add_argument("--verdicts", default="classifier_qa_verdicts.json")
    ap.add_argument("--decisions", default="classifier_qa_decisions.json",
                     help="the ledger")
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--out", default="classifier_qa_report.md")
    ap.add_argument("--accept-residual", nargs=2, action="append", default=[],
                     metavar=("PMID", "REASON"),
                     help="mark a PMID (must already have a ledger entry) as an accepted "
                          "residual — no classifier.py fix without worse collateral damage. "
                          "The sampler stops force-including it. Repeatable.")
    args = ap.parse_args()

    dpath = os.path.join(HERE, args.decisions)
    ledger = {"comment": "PMIDs already ruled on in a classifier QA round. A PMID is "
                         "re-eligible for sampling once the store's topic for it changes "
                         "away from topic_at_review — see classifier_qa_sample.py. "
                         "residual_accepted (see apply_classifier_qa.py --accept-residual) "
                         "closes a PMID out of pending_fix without a code change.",
              "decisions": {}}
    if os.path.exists(dpath):
        existing = json.load(open(dpath))
        ledger["decisions"] = existing.get("decisions", {})

    today = datetime.date.today().isoformat()
    unknown = []
    correct_n, wrong_n = 0, 0
    wrong_groups = defaultdict(list)  # (current, target) -> [(pmid, title, matched_in)]

    inp = args.decisions_in if os.path.isabs(args.decisions_in) else os.path.join(HERE, args.decisions_in)
    if not os.path.exists(inp) and not args.accept_residual:
        raise SystemExit(f"no decisions file at {inp}\n"
                          f"Open classifier_qa_review.html, adjust topics, click Submit.\n"
                          f"(Or pass --accept-residual PMID REASON with no decisions file "
                          f"to just annotate an already-reviewed PMID.)")

    if os.path.exists(inp):
        sub = json.load(open(inp))
        human_decisions = sub.get("decisions", {})  # pmid -> {verdict, target_topic}

        sample = json.load(open(os.path.join(HERE, args.sample)))
        items_by_pmid = {i["pmid"]: i for i in sample["items"]}
        vpath = os.path.join(HERE, args.verdicts)
        agent_verdicts = json.load(open(vpath)).get("verdicts", {}) if os.path.exists(vpath) else {}

        for pmid, dec in human_decisions.items():
            item = items_by_pmid.get(pmid)
            if not item:
                unknown.append(pmid)
                continue
            current_topic = item.get("current_topic")
            target_topic = dec.get("target_topic") or current_topic
            verdict = "correct" if target_topic == current_topic else "wrong"
            agent_v = (agent_verdicts.get(pmid) or {}).get("verdict")
            agent_conf = (agent_verdicts.get(pmid) or {}).get("confidence")

            # Merge onto whatever was already there — never replace wholesale — so a prior
            # round's residual_accepted/residual_reason survives a re-decision instead of
            # silently vanishing (that PMID would otherwise go back to force-included
            # pending_fix forever, defeating the point of accepting it as a residual).
            entry = dict(ledger["decisions"].get(pmid, {}))
            entry.update({
                "topic_at_review": current_topic,
                "verdict": verdict,
                "target_topic": target_topic,
                "agent_verdict": agent_v,
                "confidence": agent_conf,
                "decided_on": today,
                "decided_by": "human",
                "title": (item.get("title") or "")[:160],
            })
            # Reviewer's free-text note from the review page. Only overwrite when this
            # round supplied one, so clearing the box doesn't erase an earlier round's
            # reasoning.
            if dec.get("note"):
                entry["note"] = dec["note"]
            ledger["decisions"][pmid] = entry

            if verdict == "correct":
                correct_n += 1
            else:
                wrong_n += 1
                art = {"title": item.get("title"), "abstract": item.get("abstract")}
                # Traces against the CURRENT classifier.py — if this is a re-run after a
                # fix already landed, the trigger location reflects the fix, not the
                # original bug. Run apply before patching classifier.py, not after.
                _, _, trace = classifier.classify_topic(art, trace=True)
                wrong_groups[(current_topic, target_topic)].append(
                    (pmid, item.get("title") or "", trace["matched_in"], trace["matched"]))

    for pmid, reason in args.accept_residual:
        if pmid not in ledger["decisions"]:
            raise SystemExit(f"--accept-residual {pmid}: no ledger entry for this PMID yet — "
                              f"it must be reviewed (via the normal decisions-in flow) at "
                              f"least once first.")
        ledger["decisions"][pmid]["residual_accepted"] = True
        ledger["decisions"][pmid]["residual_reason"] = reason
        ledger["decisions"][pmid]["residual_decided_on"] = today

    json.dump(ledger, open(dpath, "w"), indent=1)

    # Global pending tally: ledger entries still marked wrong whose topic hasn't moved,
    # across the WHOLE ledger (not just this round) — these need a code fix + rebuild
    # before they'll stop resurfacing.
    store = json.load(open(os.path.join(HERE, args.store))) if os.path.exists(os.path.join(HERE, args.store)) else {"articles": []}
    current_topic_by_pmid = {str(a.get("pmid")): a.get("topic") for a in store.get("articles", [])}
    pending = [pm for pm, e in ledger["decisions"].items()
               if e.get("verdict") == "wrong" and not e.get("residual_accepted")
               and current_topic_by_pmid.get(pm) == e.get("topic_at_review")]
    residuals = [pm for pm, e in ledger["decisions"].items() if e.get("residual_accepted")]

    # Report.
    lines = ["# Classifier QA report", "",
              f"Generated {today}. {correct_n} correct, {wrong_n} wrong (this round), "
              f"{len(pending)} pending fix (whole ledger).", ""]

    if wrong_groups:
        lines.append("## Confirmed-wrong groups (current → target)")
        lines.append("")
        lines.append("| current → target | count | trigger location | example PMIDs (titles) |")
        lines.append("|---|---|---|---|")
        for (cur, tgt), rows in sorted(wrong_groups.items(), key=lambda kv: -len(kv[1])):
            locs = sorted(set(r[2] for r in rows))
            examples = "; ".join(f"{pm} ({title[:70]}{'…' if len(title) > 70 else ''})"
                                  for pm, title, _, _ in rows[:5])
            lines.append(f"| {cur} → {tgt} | {len(rows)} | {', '.join(locs)} | {examples} |")
        lines.append("")
        lines.append("### Matched literals per article")
        lines.append("")
        for (cur, tgt), rows in sorted(wrong_groups.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"**{cur} → {tgt}**")
            for pm, title, loc, matched in rows:
                lines.append(f"- {pm} — matched `{matched}` in **{loc}** — {title[:100]}")
            lines.append("")
    else:
        lines.append("No confirmed-wrong verdicts this round.")
        lines.append("")

    if pending:
        lines.append(f"## Still pending fix (whole ledger): {len(pending)}")
        lines.append("These stay force-included in the next sample until a classifier.py fix "
                      "moves their topic.")
        lines.append("")
        for pm in sorted(pending):
            e = ledger["decisions"][pm]
            lines.append(f"- {pm} — {e.get('topic_at_review')} → {e.get('target_topic')} — "
                          f"{e.get('title','')}")
        lines.append("")

    if residuals:
        lines.append(f"## Accepted residuals (whole ledger): {len(residuals)}")
        lines.append("Known-wrong, deliberately NOT fixed — every code-level guard tried "
                      "caused worse collateral damage than the bug itself. The sampler no "
                      "longer force-includes these; see `residual_reason` for why.")
        lines.append("")
        for pm in sorted(residuals):
            e = ledger["decisions"][pm]
            lines.append(f"- {pm} — {e.get('topic_at_review')} → {e.get('target_topic')} — "
                          f"{e.get('title','')}. **Why not fixed:** {e.get('residual_reason','')}")
        lines.append("")

    noted = {pm: e for pm, e in ledger["decisions"].items() if e.get("note")}
    if noted:
        lines.append(f"## Reviewer notes ({len(noted)})")
        lines.append("Free-text reasoning captured on the review page. These are the calls "
                      "where a topic dropdown alone did not carry the argument — read them "
                      "before writing a general rule for the group they sit in.")
        lines.append("")
        for pm in sorted(noted):
            e = noted[pm]
            arrow = (f"{e.get('topic_at_review')} → {e.get('target_topic')}"
                     if e.get("verdict") == "wrong" else f"kept as {e.get('topic_at_review')}")
            lines.append(f"- **{pm}** ({arrow}) — {e.get('title','')[:90]}")
            lines.append(f"  > {e['note']}")
        lines.append("")

    lines.append("## Next steps")
    lines.append("")
    lines.append("This script never edits `classifier.py` or the store. After root-causing "
                  "the groups above into a fix:")
    lines.append("```")
    lines.append("python3 merge_raw_sources.py")
    lines.append(f"python3 build_dataset.py --run-date {today} --raw comprehensive_raw.json --rebuild")
    lines.append("python3 build_dashboard.py")
    lines.append("```")
    lines.append("Then snapshot {pmid: topic} before/after the rebuild and diff it — every "
                  "changed PMID should match a `verdict: wrong` ledger entry with that exact "
                  "`target_topic`; anything else is a regression.")

    outp = os.path.join(HERE, args.out)
    open(outp, "w").write("\n".join(lines))

    print(f"classifier QA apply: {correct_n} correct, {wrong_n} wrong "
          f"({len(wrong_groups)} groups), {len(pending)} pending fix, "
          f"{len(residuals)} accepted residuals on the whole ledger")
    if args.accept_residual:
        print(f"  marked residual_accepted for: {', '.join(pm for pm, _ in args.accept_residual)}")
    if unknown:
        print(f"  WARNING: {len(unknown)} pmid(s) not in {args.sample}: {', '.join(unknown[:8])}")
    print(f"  wrote {dpath}")
    print(f"  wrote {outp}")


if __name__ == "__main__":
    main()

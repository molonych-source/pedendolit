"""
Find articles whose clinical_bottom_line is not a real takeaway.

classifier.clinical_bottom_line() is extractive: it looks for a CONCLUSIONS-style
section marker and takes the following sentences, else falls back to the last two
sentences of the abstract. On a structured abstract that works well. On an
unstructured one the fallback can land on the opening sentences, which is how 182
articles ended up with the abstract's first words as their "bottom line".

Read-only. Writes a report and the target list; changes nothing.

Usage: python3 audit_bottom_lines.py [--store pedendolit-data.json]
"""
import json, os, re, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def has_no_usable_source(a):
    """Returns True if article has no abstract or only [Abstract not available]."""
    ab = _norm(a.get("abstract"))
    return not ab or ab.startswith("[Abstract not available]")


def classify_weakness(a):
    """(is_weak, reason_code). See the module docstring for why each rule exists."""
    bl = _norm(a.get("clinical_bottom_line"))
    ab = _norm(a.get("abstract"))

    if not ab:
        return True, "no_abstract"
    if not bl or bl.startswith("[Abstract not available]"):
        return True, "placeholder"
    if len(bl) < 60:
        return True, "too_short"
    # Extractive: the bottom line is how the abstract begins, so it is background
    # rather than a finding.
    head = bl.split("...")[0][:50]
    if head and ab.startswith(head):
        return True, "extractive"
    # Ends mid-sentence with no terminal punctuation — a truncation, not a sentence.
    if not re.search(r"[.!?]['\")\]]?$", bl):
        return True, "truncated_midsentence"
    return False, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--report", default="bottom_line_audit.md")
    ap.add_argument("--targets", default="bottom_line_targets.json")
    args = ap.parse_args()

    store = json.load(open(os.path.join(HERE, args.store)))
    arts = [a for a in store.get("articles", []) if not a.get("excluded")]

    reasons = collections.Counter()
    targets, examples = [], collections.defaultdict(list)
    for a in arts:
        weak, why = classify_weakness(a)
        reasons[why] += 1
        if weak:
            targets.append(str(a["pmid"]))
            if len(examples[why]) < 5:
                examples[why].append((str(a["pmid"]),
                                      _norm(a.get("title"))[:70],
                                      _norm(a.get("clinical_bottom_line"))[:110]))

    weak_n = len(targets)
    # Count articles with no usable source text by testing the abstract field directly
    # (more robust than deriving from reason codes, which could drift if abstracts are backfilled)
    by_pmid = {str(a["pmid"]): a for a in arts}
    no_source_targets = [p for p in targets if has_no_usable_source(by_pmid[p])]
    no_source = len(no_source_targets)
    real_abstract_targets = weak_n - no_source

    # Robustness check: assert the two groups account for all targets
    assert no_source + real_abstract_targets == weak_n, \
        f"no-source ({no_source}) + real-abstract ({real_abstract_targets}) must sum to targets ({weak_n})"

    L = ["# Bottom-line audit", "",
         f"{len(arts)} articles checked. **{weak_n} need regeneration "
         f"({100*weak_n/len(arts):.1f}%)**; {reasons['ok']} are fine.", "",
         f"Of the targets, **{no_source} have no usable source text** (no abstract or",
         "`[Abstract not available]`), so they cannot be regenerated without manual",
         f"intervention or fabrication risk. The remaining {real_abstract_targets} have a real abstract but a",
         "weak bottom line (extractive, truncated, or too short).", "",
         "These are mechanical rules. They catch bottom lines that are structurally",
         "wrong (missing, truncated, or the abstract's opening). They cannot catch one",
         "that is a well-formed sentence but a poor takeaway — task 2's judge sees a",
         "random sample of the `ok` group to estimate that residual.", "",
         "| Reason | Articles | What it means |", "|---|---|---|"]
    meanings = {
        "no_abstract": "No abstract indexed in PubMed — nothing to extract from",
        "placeholder": "Literally `[Abstract not available]` or empty",
        "too_short": "Under 60 characters — a fragment, not a takeaway",
        "extractive": "Repeats how the abstract opens, i.e. background not findings",
        "truncated_midsentence": "Ends without terminal punctuation — cut off",
        "ok": "Passes every mechanical check",
    }
    for why, n in reasons.most_common():
        L.append(f"| {why} | {n} | {meanings[why]} |")

    for why in [w for w in reasons if w != "ok"]:
        L += ["", f"## {why} — examples", ""]
        for pmid, title, bl in examples[why]:
            L += [f"- **{pmid}** — {title}", f"  > {bl}"]

    open(os.path.join(HERE, args.report), "w").write("\n".join(L) + "\n")
    json.dump(sorted(targets), open(os.path.join(HERE, args.targets), "w"), indent=1)
    print(f"{weak_n} of {len(arts)} need regeneration")
    for why, n in reasons.most_common():
        print(f"  {n:5d}  {why}")
    print(f"wrote {args.report} and {args.targets}")


if __name__ == "__main__":
    main()

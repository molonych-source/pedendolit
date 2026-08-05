"""
PedsEndoBrief monthly guideline sweep — triage stage.

The normal pipeline is journal-scoped: it only ever sees the 19 journals in
journals.json. That is correct for routine surveillance but structurally blind to
a guideline published somewhere else — and societies do publish outside those 19
(Endocrine Society in JCEM, yes, but also DSD guidelines in Endocrine Journal, the
Female Athlete Triad consensus in Sports Medicine, national CAH guidelines in
Problems of Endocrinology, and so on).

This script is the safety net. The agent runs a publication-type-scoped PubMed
search across ALL journals (query in WEEKLY_REFRESH_RUNBOOK.md), saves the metadata,
and points this script at it. The script classifies each candidate, drops anything
already in the store, and writes a review queue for a human to approve.

It deliberately does NOT write to pedendolit-data.json. That wide query runs about
35% precision — the rest is dermatology, urology, nephrology, ophthalmology — and
auto-merging would put off-topic guidelines on the live site. Approved PMIDs go in
through the normal merge path:

    python3 build_dataset.py --raw guideline_candidates.json

No network calls: like every other script here, it reads what the agent fetched.

Usage:
  python3 guideline_sweep.py --raw sweep_raw.json [--out-prefix guideline]
"""
import json, os, argparse, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Reuse the real classifier and the real raw->article mapper. Reimplementing either
# here would let the review queue drift away from what the store would actually do
# with the same article.
classifier = _load("classifier", "classifier.py")
dataset = _load("build_dataset", "build_dataset.py")


def load_raw(path):
    """Accept either a bare list of MCP records or a {'articles': [...]} response."""
    d = json.load(open(path))
    if isinstance(d, dict):
        d = d.get("articles") or []
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="sweep_raw.json",
                    help="PubMed MCP metadata for the sweep results")
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--decisions", default="guideline_decisions.json")
    ap.add_argument("--out-prefix", default="guideline")
    args = ap.parse_args()

    raw_path = args.raw if os.path.isabs(args.raw) else os.path.join(HERE, args.raw)
    store_path = os.path.join(HERE, args.store)
    dec_path = os.path.join(HERE, args.decisions)

    raw = load_raw(raw_path)
    store = json.load(open(store_path))
    # PMIDs are strings in the store; the MCP nests its pmid under identifiers and
    # a top-level .get("pmid") silently returns None. map_raw() already handles that
    # — go through it rather than reading the field directly.
    known = set(str(a.get("pmid")) for a in store.get("articles", []))

    # Articles already ruled on in a previous sweep — approved OR rejected. Without
    # this the same declined guidelines resurface every month asking to be declined
    # again. Written by apply_approvals.py.
    # Tolerate a missing/empty/garbled decisions file — the sweep should still run and
    # simply show everything, rather than dying. (--decisions /dev/null is a legitimate
    # way to ask for "ignore memory, rebuild the full candidate list".)
    decided = {}
    if os.path.exists(dec_path):
        try:
            decided = (json.load(open(dec_path)) or {}).get("decisions", {})
        except (ValueError, OSError):
            print(f"  note: {os.path.basename(dec_path)} unreadable — treating as empty")

    kept, already, excluded, seen_before = [], 0, 0, 0
    for rec in raw:
        art = dataset.map_raw(rec)
        if not art.get("pmid"):
            continue
        if str(art["pmid"]) in known:
            already += 1
            continue
        if str(art["pmid"]) in decided:
            seen_before += 1
            continue
        res = classifier.classify(art)
        # The classifier's own exclusion rules (adult-only, errata, off-topic) are
        # the first filter; a human reviews whatever survives.
        if res.get("excluded"):
            excluded += 1
            continue
        # classify() returns only the classification fields — the caller merges them
        # onto the article, same as build_dataset does. Without this the queue has
        # topics but no titles.
        kept.append({"raw": rec, "art": {**art, **res}})

    # Guidelines first, then most recent — the reviewer's attention should land on
    # the real guidelines before the maybes.
    kept.sort(key=lambda k: (k["art"].get("study_type") != "Guideline/Consensus",
                             (k["art"].get("pub_date") or "")), reverse=False)

    cand_path = os.path.join(HERE, f"{args.out_prefix}_candidates.json")
    json.dump([k["raw"] for k in kept], open(cand_path, "w"), indent=1)

    md_path = os.path.join(HERE, f"{args.out_prefix}_review_queue.md")
    with open(md_path, "w") as f:
        f.write("# Guideline sweep — review queue\n\n")
        f.write(f"{len(kept)} candidates ({already} already in the store, "
                f"{seen_before} decided in a previous sweep, {excluded} excluded by the "
                f"classifier).\n\n")
        f.write("This markdown file is a quick text view. The real review surface is the\n"
                "checkbox page — see the monthly sweep section of "
                "`WEEKLY_REFRESH_RUNBOOK.md`:\n\n")
        f.write("```\n# agent writes guideline_verdicts.json, then:\n"
                "python3 build_review_page.py   # -> guideline_review.html\n```\n\n")
        f.write("| # | Type | Topic | Society | Date | Journal | Title |\n")
        f.write("|---|------|-------|---------|------|---------|-------|\n")
        for i, k in enumerate(kept, 1):
            a = k["art"]
            soc = ", ".join(a.get("society") or []) or "—"
            title = (a.get("title") or "").replace("|", "\\|")
            f.write(f"| {i} | {a.get('study_type','')} | {a.get('topic','')} | {soc} | "
                    f"{a.get('pub_date','')} | {a.get('journal_abbr','')} | "
                    f"[{title}]({a.get('url','')}) |\n")

    print(f"sweep: {len(raw)} fetched | {already} already in store | "
          f"{seen_before} previously decided | {excluded} classifier-excluded | "
          f"{len(kept)} for review")
    print(f"  wrote {md_path}")
    print(f"  wrote {cand_path}")


if __name__ == "__main__":
    main()

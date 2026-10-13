"""
AI labeling, step 2 of 2: validate a labeled batch and merge it into ai_labels/labels.json.

The labeler (a Claude routine session, or a subagent) reads ai_labels/PROMPT.md and
ai_labels/queue.json and writes its answers to ai_labels/batch_out.json. This script:
  1. checks every answer against the schema in PROMPT.md (fails on any error, writing
     nothing, so a bad batch can simply be redone),
  2. checks the answers cover exactly the queued PMIDs,
  3. stamps each with the model, prompt version and date, and merges it in.
Existing labels are never overwritten unless --replace is given, so re-running is safe.

labels.json is a side file, like pub_dates.json: nothing reads it into the site until a
separate, reviewed step applies it.

Usage:
  python3 ai_label_apply.py --model claude-haiku-5-5
  python3 ai_label_apply.py --model claude-haiku-5-5 --input path/to/out.json --queue path/to/queue.json
  python3 ai_label_apply.py --validate-only --input _work/pilot/labels_haiku_v2.json --queue _work/pilot/articles.json
"""
import json, os, re, sys, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "ai_labels")

SUBTOPICS = {
    "Diabetes": {"T1D", "T1D·Stage", "T2D", "Technology", "MODY/Monogenic", "CFRD", "GDM", "Steroid-induced", "General"},
    "Growth": {"GH deficiency & therapy", "Syndromic short stature", "Short stature evaluation", "General"},
    "Puberty": {"Precocious puberty", "Delayed puberty & hypogonadism", "Pubertal timing & physiology", "General"},
    "Thyroid": {"Nodules & cancer", "Congenital hypothyroidism", "Hyperthyroidism & Graves",
                "Autoimmune & acquired hypothyroidism", "General"},
    "Adrenal": {"CAH", "Adrenal tumors & Cushing", "Adrenal insufficiency", "Mineralocorticoid & aldosterone", "General"},
    "Pituitary": {"Pituitary tumors", "Hypopituitarism", "Water balance", "General"},
    "Bone/Mineral": {"Phosphate/FGF23", "Skeletal Fragility", "PTH/Calcium", "Vitamin D/Rickets"},
}
TOPICS = set(SUBTOPICS) | {"Obesity/Metabolic", "Hyperinsulinism", "PCOS", "DSD", "Gender Medicine", "Lipids",
                           "Cancer Late Effects", "Genetics", "General Endocrinology"}
STUDY_TYPES = {"Guideline/Consensus", "Meta-analysis", "Systematic Review", "Scoping Review", "RCT",
               "Clinical Trial", "Observational/Cohort", "Prospective Study", "Real-World Study",
               "Registry/Database", "Case-Control", "Cross-Sectional", "Survey/Questionnaire", "Case Series",
               "Review", "Editorial/Commentary", "Letter/Correspondence", "Health Economics", "Pilot Study", "Other"}
ENUMS = {"primary_outcome_met": {"yes", "no", "mixed", "not_applicable", "unclear"},
         "pediatric": {"yes", "partly", "no"}, "human": {"yes", "no"},
         "endocrine_subject": {"yes", "partly", "no"}, "confidence": {"high", "medium", "low"}}
FIELDS = {"pmid", "topic", "subtopic", "study_type", "participants", "primary_outcome_met", "pediatric",
          "human", "endocrine_subject", "takeaway", "confidence"}


def no_abstract(a):
    t = (a.get("abstract") or "").strip()
    return len(t) < 40 or t.lower().startswith("[abstract not available")


def validate(out, queue):
    errs = []
    q = {str(a["pmid"]): a for a in queue}
    seen = set()
    for x in out:
        p = str(x.get("pmid"))
        tag = f"pmid {p}"
        if p in seen: errs.append(f"{tag}: duplicate")
        seen.add(p)
        if p not in q: errs.append(f"{tag}: not in the queue"); continue
        if set(x) != FIELDS: errs.append(f"{tag}: fields {sorted(set(x) ^ FIELDS)}")
        t = x.get("topic")
        if t not in TOPICS: errs.append(f"{tag}: topic {t!r}")
        elif x.get("subtopic") not in SUBTOPICS.get(t, {"General"}): errs.append(f"{tag}: subtopic {x.get('subtopic')!r} for {t}")
        if x.get("study_type") not in STUDY_TYPES: errs.append(f"{tag}: study_type {x.get('study_type')!r}")
        for k, ok in ENUMS.items():
            if x.get(k) not in ok: errs.append(f"{tag}: {k} {x.get(k)!r}")
        n = x.get("participants")
        if n is not None and not (isinstance(n, int) and n >= 0): errs.append(f"{tag}: participants {n!r}")
        tk = x.get("takeaway")
        if no_abstract(q[p]):
            if tk is not None: errs.append(f"{tag}: takeaway given but no abstract")
        elif not tk or len(tk.split()) > 35: errs.append(f"{tag}: takeaway missing or over 35 words")
    missing = set(q) - seen
    if missing: errs.append(f"{len(missing)} queued PMIDs have no answer, e.g. {sorted(missing)[:3]}")
    return errs


def prompt_version():
    m = re.search(r"PROMPT_VERSION:\s*(\S+)", open(os.path.join(D, "PROMPT.md")).read())
    return m.group(1) if m else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(D, "batch_out.json"))
    ap.add_argument("--queue", default=os.path.join(D, "queue.json"))
    ap.add_argument("--model")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    a = ap.parse_args()
    out, queue = json.load(open(a.input)), json.load(open(a.queue))
    errs = validate(out, queue)
    if errs:
        print(f"INVALID: {len(errs)} problem(s); nothing written")
        for e in errs[:30]: print("  ", e)
        return 1
    print(f"valid: {len(out)} labels")
    if a.validate_only:
        return 0
    if not a.model:
        print("--model is required to merge"); return 1
    path = os.path.join(D, "labels.json")
    try:
        led = json.load(open(path))
    except (OSError, ValueError):
        led = {"comment": "AI labels per PMID (see ai_labels/PROMPT.md). Side file: not applied to the site "
                          "until a reviewed step does so.", "labels": {}}
    stamp = {"model": a.model, "prompt_version": prompt_version(), "labeled_on": datetime.date.today().isoformat()}
    added = kept = 0
    for x in out:
        p = str(x["pmid"])
        if p in led["labels"] and not a.replace:
            kept += 1; continue
        led["labels"][p] = {**{k: v for k, v in x.items() if k != "pmid"}, **stamp}
        added += 1
    json.dump(led, open(path, "w"), ensure_ascii=False, indent=0, sort_keys=True)
    print(f"merged {added} new, kept {kept} existing; labels.json now holds {len(led['labels'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

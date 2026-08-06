"""
Rules-based misclassification-suspicion scoring (roadmap item F2, prototype).

Read-only. Scores every article in the store for how likely its topic is wrong,
using signals the classifier already exposes via classify_topic(trace=True) plus
NLM-curated MeSH terms, which are independent of the classifier's own keywords.

The point is to concentrate expensive judge attention: Diabetes alone is 720 of
1406 articles, so a flat stratified sample covers ~3% of it. A ranked suspicion
list turns that into a targeted 3%.

Nothing here decides anything. It emits a ranked report and, optionally, a PMID
list to feed classifier_qa_sample.py --force-pmids-file.

Usage:
  python3 suspicion_score.py [--store pedendolit-data.json]
                             [--out suspicion_report.md]
                             [--pmids-out suspicion_pmids.json]
                             [--top N] [--topic T] [--min-score S]
"""
import json, os, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
import classifier

TOPICS = (
    "Diabetes", "Growth", "Puberty", "Thyroid", "Adrenal", "Obesity/Metabolic",
    "General Endocrinology", "Bone/Mineral", "Pituitary", "Hyperinsulinism",
    "Genetics", "DSD", "PCOS", "Gender Medicine",
    "Cancer Late Effects", "Lipids",
)

# MeSH substring -> topic. Deliberately conservative: only terms that pin a topic
# unambiguously. A term that could sit under two topics is left out entirely,
# because a false disagreement signal costs judge attention on a correct article.
MESH_TOPIC = {
    "diabetes mellitus, type 1": "Diabetes",
    "diabetes mellitus, type 2": "Diabetes",
    "diabetic ketoacidosis": "Diabetes",
    "insulin infusion systems": "Diabetes",
    "blood glucose self-monitoring": "Diabetes",
    "glycated hemoglobin": "Diabetes",
    "congenital hyperinsulinism": "Hyperinsulinism",
    "hyperinsulinism": "Hyperinsulinism",
    "nesidioblastosis": "Hyperinsulinism",
    "growth hormone": "Growth",
    "human growth hormone": "Growth",
    "dwarfism, pituitary": "Growth",
    "body height": "Growth",
    "turner syndrome": "Growth",
    "prader-willi syndrome": "Growth",
    "achondroplasia": "Growth",
    "puberty, precocious": "Puberty",
    "puberty, delayed": "Puberty",
    "hypogonadism": "Puberty",
    "kallmann syndrome": "Puberty",
    "menarche": "Puberty",
    "thyroid": "Thyroid",
    "hypothyroidism": "Thyroid",
    "hyperthyroidism": "Thyroid",
    "graves disease": "Thyroid",
    "thyroiditis": "Thyroid",
    "goiter": "Thyroid",
    "adrenal hyperplasia, congenital": "Adrenal",
    "adrenal insufficiency": "Adrenal",
    "addison disease": "Adrenal",
    "cushing syndrome": "Adrenal",
    "pheochromocytoma": "Adrenal",
    "hyperaldosteronism": "Adrenal",
    "pediatric obesity": "Obesity/Metabolic",
    "obesity, morbid": "Obesity/Metabolic",
    "metabolic syndrome": "Obesity/Metabolic",
    "non-alcoholic fatty liver disease": "Obesity/Metabolic",
    "bariatric surgery": "Obesity/Metabolic",
    "bone density": "Bone/Mineral",
    "osteoporosis": "Bone/Mineral",
    "diphosphonates": "Bone/Mineral",
    "familial hypophosphatemic rickets": "Bone/Mineral",
    "craniopharyngioma": "Pituitary",
    "pituitary neoplasms": "Pituitary",
    "hypopituitarism": "Pituitary",
    "acromegaly": "Pituitary",
    "diabetes insipidus": "Pituitary",
    "inappropriate adh syndrome": "Pituitary",
    "hyperparathyroidism": "Bone/Mineral",
    "hypoparathyroidism": "Bone/Mineral",
    "parathyroid hormone": "Bone/Mineral",
    "vitamin d deficiency": "Bone/Mineral",
    "rickets": "Bone/Mineral",
    "hypocalcemia": "Bone/Mineral",
    "hypercalcemia": "Bone/Mineral",
    "disorders of sex development": "DSD",
    "gonadal dysgenesis": "DSD",
    "46, xy disorders of sex development": "DSD",
    "polycystic ovary syndrome": "PCOS",
    "transgender persons": "Gender Medicine",
    "gender dysphoria": "Gender Medicine",
    "gender-affirming care": "Gender Medicine",
    "cancer survivors": "Cancer Late Effects",
    "hyperlipoproteinemia type ii": "Lipids",
    "hypercholesterolemia": "Lipids",
    "anticholesteremic agents": "Lipids",
}


def mesh_topics(mesh_terms):
    """Topics the article's MeSH headings unambiguously point at."""
    found = set()
    for m in mesh_terms or []:
        ml = m.lower()
        for key, topic in MESH_TOPIC.items():
            if key in ml:
                found.add(topic)
    return found


def score_article(art):
    """Returns (score, [reasons]). Higher score = more worth a judge's time."""
    topic = art.get("topic")
    reasons = []
    score = 0

    _, _, tr = classifier.classify_topic(art, trace=True)
    branch = tr.get("branch")
    matched = tr.get("matched") or []
    where = tr.get("matched_in")

    # S1 — the round-1 failure mode: a topic decided by a single literal that
    # appears only in the abstract, i.e. plausibly an incidental comorbidity
    # mention rather than the article's subject.
    if where == "abstract" and len(matched) <= 1:
        score += 4
        lit = matched[0] if matched else "?"
        reasons.append(f"decided on a single abstract-only literal ({lit!r})")
    elif where == "abstract" and len(matched) == 2:
        score += 2
        reasons.append("decided on abstract-only evidence (2 literals)")

    # S2 — the catch-all. classify_topic cannot say "I don't know", so branch 25
    # is where uncertainty actually lands.
    if branch == "25":
        score += 3
        reasons.append("fell through to the General Endocrinology catch-all")

    # S3 — MeSH disagreement. NLM indexers are independent of this classifier,
    # so a clean disagreement is the strongest single signal available.
    mt = mesh_topics(art.get("mesh_terms"))
    if mt:
        if topic not in mt:
            score += 5
            reasons.append("MeSH points to " + "/".join(sorted(mt)) + f", classifier said {topic}")
        elif len(mt) > 1:
            score += 1
            reasons.append("MeSH spans " + "/".join(sorted(mt)))

    # S4 — no abstract means the decision rested on a title alone.
    if not (art.get("abstract") or "").strip():
        score += 2
        reasons.append("no abstract; classified on title alone")

    # S5 — a guideline is high-visibility on the dashboard, so a mislabel there
    # costs more than the same error on a case report. Not evidence of error,
    # a weight on its consequence.
    if art.get("study_type") == "Guideline/Consensus":
        score += 1
        reasons.append("guideline (high visibility if wrong)")

    return score, reasons, branch, where


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--out", default="suspicion_report.md")
    ap.add_argument("--pmids-out", default="suspicion_pmids.json")
    ap.add_argument("--top", type=int, default=150,
                    help="how many PMIDs to write to --pmids-out")
    ap.add_argument("--topic", action="append", default=[],
                    help="restrict the PMID list to this topic (repeatable)")
    ap.add_argument("--min-score", type=int, default=5)
    args = ap.parse_args()

    store = json.load(open(os.path.join(HERE, args.store)))
    arts = [a for a in store.get("articles", []) if not a.get("excluded")]

    scored = []
    for a in arts:
        s, reasons, branch, where = score_article(a)
        if s > 0:
            scored.append({
                "pmid": str(a.get("pmid")), "score": s, "reasons": reasons,
                "topic": a.get("topic"), "title": a.get("title") or "",
                "branch": branch, "matched_in": where,
                "study_type": a.get("study_type"),
            })
    scored.sort(key=lambda r: (-r["score"], r["topic"], r["pmid"]))

    by_topic = collections.Counter(r["topic"] for r in scored if r["score"] >= args.min_score)
    dist = collections.Counter(r["score"] for r in scored)

    lines = ["# Classifier suspicion report (F2 prototype)", ""]
    lines.append(f"Scored {len(arts)} articles; {len(scored)} carry at least one suspicion signal; "
                 f"{sum(1 for r in scored if r['score'] >= args.min_score)} score >= {args.min_score}.")
    lines.append("")
    lines.append("Higher score = more worth a judge's time. This ranks *uncertainty*, "
                 "not error — a high score on a correct article is expected and fine.")
    lines.append("")
    lines.append("## Score distribution")
    lines.append("")
    lines.append("| Score | Articles |")
    lines.append("|---|---|")
    for s in sorted(dist, reverse=True):
        lines.append(f"| {s} | {dist[s]} |")
    lines.append("")
    lines.append(f"## Where the score >= {args.min_score} articles sit")
    lines.append("")
    lines.append("| Topic | Suspicious |")
    lines.append("|---|---|")
    for t, n in by_topic.most_common():
        lines.append(f"| {t} | {n} |")
    lines.append("")
    lines.append("## Ranked list (top 100)")
    lines.append("")
    for r in scored[:100]:
        lines.append(f"### {r['score']} — {r['pmid']} — {r['topic']}")
        lines.append(f"*{r['title'][:200]}*")
        lines.append("")
        for reason in r["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")

    out = os.path.join(HERE, args.out)
    open(out, "w").write("\n".join(lines) + "\n")

    pool = [r for r in scored if r["score"] >= args.min_score]
    if args.topic:
        pool = [r for r in pool if r["topic"] in set(args.topic)]
    pmids = [r["pmid"] for r in pool[:args.top]]
    json.dump(pmids, open(os.path.join(HERE, args.pmids_out), "w"), indent=1)

    print(f"scored {len(arts)} articles, {len(scored)} with signal")
    print(f"wrote {out}")
    print(f"wrote {len(pmids)} PMIDs to {args.pmids_out}"
          + (f" (topics: {', '.join(args.topic)})" if args.topic else ""))


if __name__ == "__main__":
    main()

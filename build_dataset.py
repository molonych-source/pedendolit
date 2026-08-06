"""
PedEndoLit dataset builder.

Reads raw fetched articles (raw_articles.json — produced by the agent calling the
PubMed MCP), runs the classifier, applies dedup + 60-day archive + is_new logic,
and writes pedendolit-data.json (the datastore the dashboard reads).

Re-runnable and idempotent: existing PMIDs are never re-classified or duplicated;
new articles are merged in. Pass --run-date YYYY-MM-DD to override 'today' (testing).

Usage:
  python3 build_dataset.py [--run-date YYYY-MM-DD] [--raw raw_articles.json]
"""
import json, os, sys, argparse, datetime, importlib.util, html as _html, re as _re

HERE = os.path.dirname(os.path.abspath(__file__))

# Days after an article's review_date before it is hidden from the dashboard.
# None = never archive (current behavior). See the archive block in build().
ARCHIVE_AFTER_DAYS = None


def _clean(s):
    """Decode HTML/XML character entities from PubMed text (e.g. &#xa0; -> nbsp,
    &#xb1; -> +/-, &#x3b1; -> alpha) and normalize odd whitespace to plain spaces
    so abstracts render correctly. Safe to run repeatedly (idempotent)."""
    if not s:
        return s
    s = _html.unescape(s)
    # collapse non-breaking / thin / narrow spaces to a normal space
    s = s.replace(" ", " ").replace(" ", " ").replace(" ", " ").replace(" ", " ")
    # tidy doubled spaces introduced by the above
    s = _re.sub(r"[ \t]{2,}", " ", s)
    return s
DATA = os.path.join(HERE, "pedendolit-data.json")

# load classifier module
_spec = importlib.util.spec_from_file_location("clf", os.path.join(HERE, "classifier.py"))
clf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(clf)


def load_store():
    if os.path.exists(DATA):
        with open(DATA) as f:
            return json.load(f)
    return {"generated": None, "review_period": None, "articles": []}


def apply_pub_dates(store):
    """Re-apply corrected publication dates from pub_dates.json.

    `pub_date` as built from the raw feed is unreliable: the feed supplies one merged
    date dict, so when a journal issue carries only year+month the day is taken from the
    e-publication date and glued on, producing a date in neither source. 344 of 1,406
    were wrong that way (see pub_date_audit.md). fix_pub_dates.py resolves them properly
    against PubMed and records the result here; this re-applies it on every build so a
    --rebuild cannot restore the fabricated values.
    """
    path = os.path.join(HERE, "pub_dates.json")
    if not os.path.exists(path):
        return 0
    try:
        dates = (json.load(open(path)) or {}).get("dates", {})
    except (ValueError, OSError):
        return 0
    applied = 0
    for a in store["articles"]:
        rec = dates.get(str(a.get("pmid")))
        if not rec:
            continue
        a["pub_date"] = rec["pub_date"]
        a["pub_date_precision"] = rec["precision"]
        a["pub_date_source"] = rec.get("source")
        applied += 1
    return applied


def apply_topic_overrides(store):
    """Per-PMID topic corrections for classifier QA residuals with no rule-based fix.

    See CLASSIFIER_QA_RUNBOOK.md's "Accepting a residual": some flagged-wrong
    classifications have no classifier.py guard that fixes them without misrouting more
    genuinely-correct articles than it fixes (round 1: a Vitamin D guideline, an MASLD
    guideline — every keyword/title guard tried broke other Diabetes articles). Rather
    than force a bad general rule, `apply_classifier_qa.py --accept-residual` records the
    correct target_topic for that one PMID in classifier_qa_decisions.json, and THIS
    function applies it here, at build time, to every article regardless of whether it's
    new or already in the store — so it survives both a normal merge run and a --rebuild.

    Recomputes every field that actually depends on topic (subtopic/diabetes_subtype,
    tags, impact_rationale) via the real classifier functions, not by hand — a bare
    a["topic"] = new_topic would leave a stale #Diabetes tag on an article that no longer
    filters as Diabetes.
    """
    dpath = os.path.join(HERE, "classifier_qa_decisions.json")
    if not os.path.exists(dpath):
        return 0
    try:
        decisions = (json.load(open(dpath)) or {}).get("decisions", {})
    except (ValueError, OSError):
        return 0
    overrides = {pm: e["target_topic"] for pm, e in decisions.items()
                 if e.get("residual_accepted") and e.get("target_topic")}
    if not overrides:
        return 0
    applied = 0
    for a in store["articles"]:
        new_topic = overrides.get(str(a.get("pmid")))
        if not new_topic or a.get("topic") == new_topic:
            continue
        text = ((a.get("title") or "") + " " + (a.get("abstract") or "")).lower()
        title_l = (a.get("title") or "").lower()
        a["topic"] = new_topic
        # Subtopic must be recomputed, not blanked: Bone/Mineral carries subdomains too,
        # so blanking would strip them from every overridden article in that topic.
        a["subtopic"] = (clf.bone_mineral_subtopic(title_l, text)
                         if new_topic == "Bone/Mineral" else None)
        a["diabetes_subtype"] = clf.diabetes_subtype(text) if new_topic == "Diabetes" else None
        a["tags"] = clf.generate_tags(a, new_topic, a["subtopic"], a.get("study_type"),
                                       a.get("impact"), a.get("board_relevant"), text, title_l)
        a["impact_rationale"] = clf.impact_rationale(a.get("impact"), a.get("study_type"),
                                                       a.get("journal"), new_topic,
                                                       a.get("sample_n"), a.get("society"))
        applied += 1
    return applied


def map_raw(raw):
    """Map a PubMed-MCP metadata record to the classifier's expected input shape."""
    ids = raw.get("identifiers", {}) or {}
    j = raw.get("journal", {}) or {}
    pd = raw.get("publication_date", {}) or {}
    # Keep every author. This used to truncate at 6, which made a citation export
    # impossible: 174 records sat at exactly 6 names, so "complete" and "truncated"
    # were indistinguishable. The dashboard still shows only the first 3 + "et al.";
    # truncating for display is the renderer's job, not the store's.
    authors = []
    for a in (raw.get("authors") or []):
        ln = a.get("last_name", "") or ""
        ini = a.get("initials", "") or (a.get("fore_name", "")[:1] if a.get("fore_name") else "")
        authors.append(_clean((ln + " " + ini).strip()))
    pub_date = ""
    if pd.get("year"):
        pub_date = pd["year"]
        if pd.get("month"): pub_date += "-" + str(pd["month"]).zfill(2)
        if pd.get("day"):   pub_date += "-" + str(pd["day"]).zfill(2)
    doi = ids.get("doi") or raw.get("doi") or ""
    pmid = ids.get("pmid") or raw.get("pmid") or ""
    # PubMed returns these but they were never mapped, which is why no proper
    # citation (or PMC full-text link) could be produced.
    cit = raw.get("citation", {}) or {}
    pmc = ids.get("pmc") or ""
    return {
        "pmid": pmid,
        "title": _clean((raw.get("title") or "").strip()),
        "abstract": _clean((raw.get("abstract") or "").strip()),
        "journal": _clean(j.get("title") or ""),
        "journal_abbr": _clean(j.get("iso_abbreviation") or ""),
        "authors": authors,
        "doi": doi,
        "pub_date": pub_date,
        "pub_types": raw.get("article_types") or [],
        "mesh_terms": raw.get("mesh_terms") or [],
        "keywords": raw.get("keywords") or [],
        "volume": _clean(cit.get("volume") or ""),
        "issue": _clean(cit.get("issue") or ""),
        "pages": _clean(cit.get("pages") or ""),
        "pmc": pmc,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "doi_url": f"https://doi.org/{doi}" if doi else "",
        "pmc_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc}/" if pmc else "",
    }


def build(run_date=None, raw_path=None, verbose=True, rebuild=False):
    run_date = run_date or datetime.date.today().isoformat()
    raw_path = raw_path or os.path.join(HERE, "raw_articles.json")
    if rebuild:
        # Reclassify everything from raw; discard prior classifications.
        # Preserves review_date per PMID if known, so archive logic stays correct.
        prior = load_store()
        prior_dates = {a["pmid"]: a.get("review_date") for a in prior["articles"] if a.get("pmid")}
        store = {"generated": None, "review_period": None, "articles": [], "_prior_dates": prior_dates}
        existing = set()
    else:
        store = load_store()
        store.pop("_prior_dates", None)
        existing = {a["pmid"] for a in store["articles"] if a.get("pmid")}

    with open(raw_path) as f:
        raw_list = json.load(f)

    stats = {"fetched": len(raw_list), "new": 0, "dup_skipped": 0, "excluded": 0,
             "by_topic": {}, "by_impact": {}, "by_study": {}, "exclude_reasons": {}}

    for raw in raw_list:
        rec = map_raw(raw)
        pmid = rec["pmid"]
        if not pmid:
            continue
        if pmid in existing:
            stats["dup_skipped"] += 1
            continue
        existing.add(pmid)
        c = clf.classify(rec)
        if c.get("excluded"):
            stats["excluded"] += 1
            r = c.get("exclude_reason", "?")
            stats["exclude_reasons"][r] = stats["exclude_reasons"].get(r, 0) + 1
            continue
        article = {**rec, **c}
        # On rebuild, keep the article's original review_date so archive math is stable.
        rd = run_date
        if rebuild:
            rd = store.get("_prior_dates", {}).get(pmid) or run_date
        article["review_date"] = rd
        article["review_period"] = datetime.datetime.strptime(rd, "%Y-%m-%d").strftime("%B %Y")
        article["is_new"] = True
        article["is_archived"] = False
        store["articles"].append(article)
        stats["new"] += 1
        stats["by_topic"][c["topic"]] = stats["by_topic"].get(c["topic"], 0) + 1
        stats["by_impact"][c["impact"]] = stats["by_impact"].get(c["impact"], 0) + 1
        stats["by_study"][c["study_type"]] = stats["by_study"].get(c["study_type"], 0) + 1

    # Archive + is_new reset (applied to whole store).
    #
    # Archiving is OFF. It used to hide anything whose review_date was more than
    # ARCHIVE_AFTER_DAYS old, but review_date is when an article was ADDED to the
    # store, not when it was published. The whole historical backfill shares one
    # date (2026-06-28, 1029 articles), so every one of them would have crossed a
    # 60-day cutoff on the same weekly run — the site would have dropped from 1287
    # articles to 258 on 2026-08-30 and to 35 by late September.
    #
    # The dashboard is a searchable corpus, not a rolling window, so nothing ages
    # out. "What's new" is answered per-user from a last-seen timestamp instead of
    # by hiding articles from everyone. Set ARCHIVE_AFTER_DAYS to an int to
    # re-enable; leave it None to keep every article visible.
    for a in store["articles"]:
        a["is_new"] = (a.get("review_date") == run_date)  # True only for articles added this run
        if ARCHIVE_AFTER_DAYS is None:
            a["is_archived"] = False
        else:
            cutoff = (datetime.datetime.strptime(run_date, "%Y-%m-%d")
                      - datetime.timedelta(days=ARCHIVE_AFTER_DAYS)).date().isoformat()
            a["is_archived"] = a.get("review_date", "9999") < cutoff

    overrides_applied = apply_topic_overrides(store)
    dates_applied = apply_pub_dates(store)

    store["generated"] = datetime.datetime.now().isoformat(timespec="seconds")
    store["review_period"] = datetime.datetime.strptime(run_date, "%Y-%m-%d").strftime("%B %Y")
    store["last_run_date"] = run_date
    store.pop("_prior_dates", None)

    with open(DATA, "w") as f:
        json.dump(store, f, indent=1, ensure_ascii=False)

    if verbose:
        active = sum(1 for a in store["articles"] if not a["is_archived"])
        print(f"=== build_dataset {run_date} ===")
        print(f"fetched={stats['fetched']} new={stats['new']} dup_skipped={stats['dup_skipped']} excluded={stats['excluded']}")
        print(f"store total={len(store['articles'])} active={active} archived={len(store['articles'])-active}")
        print("by_topic:", dict(sorted(stats['by_topic'].items(), key=lambda x:-x[1])))
        print("by_impact:", stats['by_impact'])
        print("by_study:", dict(sorted(stats['by_study'].items(), key=lambda x:-x[1])))
        if stats['exclude_reasons']:
            print("exclude_reasons:", dict(sorted(stats['exclude_reasons'].items(), key=lambda x:-x[1])))
        if overrides_applied:
            print(f"topic_overrides applied: {overrides_applied} (see classifier_qa_decisions.json)")
        if dates_applied:
            print(f"pub_dates applied: {dates_applied} (see pub_dates.json)")
    stats["overrides_applied"] = overrides_applied
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date")
    ap.add_argument("--raw")
    ap.add_argument("--rebuild", action="store_true",
                    help="reclassify all raw articles, discarding prior classifications")
    a = ap.parse_args()
    build(run_date=a.run_date, raw_path=a.raw, rebuild=a.rebuild)

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


def map_raw(raw):
    """Map a PubMed-MCP metadata record to the classifier's expected input shape."""
    ids = raw.get("identifiers", {}) or {}
    j = raw.get("journal", {}) or {}
    pd = raw.get("publication_date", {}) or {}
    authors = []
    for a in (raw.get("authors") or [])[:6]:
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
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "doi_url": f"https://doi.org/{doi}" if doi else "",
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

    # 60-day archive + is_new reset (applied to whole store)
    cutoff = (datetime.datetime.strptime(run_date, "%Y-%m-%d") - datetime.timedelta(days=60)).date().isoformat()
    for a in store["articles"]:
        a["is_new"] = (a.get("review_date") == run_date)  # True only for articles added this run
        if a.get("review_date", "9999") < cutoff:
            a["is_archived"] = True

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
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-date")
    ap.add_argument("--raw")
    ap.add_argument("--rebuild", action="store_true",
                    help="reclassify all raw articles, discarding prior classifications")
    a = ap.parse_args()
    build(run_date=a.run_date, raw_path=a.raw, rebuild=a.rebuild)

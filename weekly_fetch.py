"""
Weekly refresh, fetch stage: search the monitored journals in journals.json directly on
PubMed (NCBI E-utilities) and write raw_articles.json for build_dataset.py.

Replaces steps 1-5 of the weekly procedure, which searched through the PubMed MCP with
a 14-day PUBLICATION-date window. That window structurally missed every article whose
PubMed publication date is year-only (online-first journals such as Front Endocrinol
and J Diabetes Sci Technol): PubMed files those as Jan 1, so they never fall inside a
recent window. A coverage audit on 2026-10-13 found ~600 such 2026 articles never
fetched. This script windows by ENTREZ date (when the record entered PubMed), which
every record has, and overlaps runs (21 days by default) so nothing falls between them.

Records are written in the PubMed MCP shape, so build_dataset.map_raw() reads them
unchanged. Fetching and parsing reuse guideline_fetch.py.

Usage:
  python3 weekly_fetch.py                                   # last 21 days -> raw_articles.json
  python3 weekly_fetch.py --days 30
  python3 weekly_fetch.py --mindate 2026/01/01 --maxdate 2026/10/13 --out backfill_raw.json
  python3 weekly_fetch.py --pmids PMIDS.json --out x.json  # fetch an explicit PMID list
Set NCBI_API_KEY in the environment to raise the rate limit (optional).
"""
import json, os, time, argparse, datetime, importlib.util
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("guideline_fetch", os.path.join(HERE, "guideline_fetch.py"))
gf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(gf)


def journal_queries():
    """One PubMed query per monitored journal, exactly as the runbook defines them."""
    cfg = json.load(open(os.path.join(HERE, "journals.json")))
    peds = cfg["peds_terms"]
    return [(j["abbr"], f'"{j["abbr"]}"[Journal]' + (f" AND {peds}" if j.get("peds_filter") else ""))
            for j in cfg["journals"]]


def search_journals(mindate, maxdate, datetype="edat"):
    """{journal abbr: set of PMIDs} for the window."""
    out = {}
    for abbr, q in journal_queries():
        ids, _ = gf.esearch(q, mindate, maxdate, datetype)
        out[abbr] = set(ids)
        time.sleep(0.35)
    return out


def fetch_records(pmids):
    recs = []
    pmids = sorted(pmids)
    for i in range(0, len(pmids), 200):
        root = ET.fromstring(gf.get(gf.EU + "efetch.fcgi",
                                    {"db": "pubmed", "id": ",".join(pmids[i:i + 200]), "retmode": "xml"}))
        recs += [gf.parse(x) for x in root.findall("PubmedArticle")]
        time.sleep(0.35)
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=21)
    ap.add_argument("--mindate"); ap.add_argument("--maxdate")
    ap.add_argument("--pmids", help="JSON list of PMIDs to fetch instead of searching")
    ap.add_argument("--out", default="raw_articles.json")
    a = ap.parse_args()
    if a.pmids:
        ids = set(json.load(open(a.pmids)))
        print(f"fetching {len(ids)} listed PMIDs")
    else:
        today = datetime.date.today()
        mx = a.maxdate or today.strftime("%Y/%m/%d")
        mn = a.mindate or (today - datetime.timedelta(days=a.days)).strftime("%Y/%m/%d")
        per = search_journals(mn, mx)
        ids = set().union(*per.values())
        print(f"window {mn} to {mx} (Entrez date): {len(ids)} PMIDs across {sum(1 for v in per.values() if v)} journals")
    recs = fetch_records(ids)
    out = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
    json.dump(recs, open(out, "w"), ensure_ascii=False)
    print(f"{len(recs)} records -> {out}")
    if len(recs) < len(ids):
        print(f"note: {len(ids) - len(recs)} PMIDs returned no PubmedArticle (book chapters or retracted records)")


if __name__ == "__main__":
    main()

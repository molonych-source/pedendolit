"""
Monthly guideline sweep, fetch stage: search PubMed directly (NCBI E-utilities) and
write sweep_raw.json for guideline_sweep.py.

Replaces the agent-run MCP search in the runbook. Two arms, because one is not enough:
  A  publication type (Practice Guideline / Guideline / Consensus ...): what PubMed
     has already tagged. New records often wait weeks for that tag.
  B  title wording (guideline, consensus, position statement, Delphi, ...): catches
     the untagged ones. 25 of the 70 guidelines found missing on 2026-10-13 were
     reachable only this way. Low precision (~12%); the review step handles that.
Both are ANDed with pediatric and endocrine terms.

The window is by ENTREZ date (when the record entered PubMed), not publication date:
online-first journals publish with a year-only date, which PubMed files as Jan 1, so
a recent publication-date window never contains them.

Records come out in the same shape as the PubMed MCP output, so build_dataset.map_raw()
and guideline_sweep.py read them unchanged. Also stamps guideline_sweep_state.json,
which check_classifier_regressions.py reads to fail when the sweep is overdue.

Usage:
  python3 guideline_fetch.py                        # last 60 days (overlapping runs)
  python3 guideline_fetch.py --days 90
  python3 guideline_fetch.py --mindate 2024/01/01 --maxdate 2026/10/13
  python3 guideline_fetch.py --pmids-only           # print PMIDs, write nothing (recall test)
Set NCBI_API_KEY in the environment to raise the rate limit (optional).
"""
import sys, json, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET

import os, argparse, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
TOOL = "pedsendobrief-guideline-sweep"
API_KEY = os.environ.get("NCBI_API_KEY", "")

PEDS = '(child[MeSH] OR adolescent[MeSH] OR infant[MeSH] OR pediatric[tiab] OR paediatric[tiab] OR children[tiab] OR adolescents[tiab] OR youth[tiab])'
ENDO = ('(endocrin*[tiab] OR diabetes[tiab] OR thyroid*[tiab] OR puberty[tiab] OR "growth hormone"[tiab] '
        'OR "short stature"[tiab] OR adrenal[tiab] OR obesity[tiab] OR calcium[tiab] OR "vitamin d"[tiab] '
        'OR "bone density"[tiab] OR osteoporosis[tiab] OR rickets[tiab] OR pituitary[tiab] OR "sex development"[tiab] '
        'OR hypoglycemia[tiab] OR hyperinsulinism[tiab] OR "polycystic ovary"[tiab] OR "gender dysphoria"[tiab] '
        'OR "turner syndrome"[tiab] OR "prader-willi"[tiab] OR lipid*[tiab] OR cholesterol*[tiab] OR "insulin"[tiab])')
ARMS = {
    "A_pubtype": f'(Practice Guideline[pt] OR Guideline[pt] OR Consensus Development Conference[pt] OR Consensus Statement[pt]) AND {PEDS} AND {ENDO}',
    "B_title": (f'(guideline*[ti] OR consensus[ti] OR "position statement"[ti] OR "position paper"[ti] '
                f'OR recommendation*[ti] OR "standards of care"[ti] OR "standards of medical care"[ti] '
                f'OR "clinical report"[ti] OR "expert opinion"[ti] OR delphi[ti] OR "practice parameter"[ti]) AND {PEDS} AND {ENDO}'),
}

def get(url, params):
    params = dict(params, tool=TOOL)
    if API_KEY:
        params["api_key"] = API_KEY
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=60) as r:
                return r.read()
        except Exception as e:
            time.sleep(2 + attempt * 3)
            err = e
    raise err

def esearch(term, mindate, maxdate, datetype="edat"):
    ids, start = [], 0
    while True:
        x = json.loads(get(EU + "esearch.fcgi", {"db": "pubmed", "term": term, "retmode": "json",
            "retmax": 9999, "retstart": start, "datetype": datetype, "mindate": mindate, "maxdate": maxdate}))
        r = x["esearchresult"]; ids += r["idlist"]
        if len(ids) >= int(r["count"]) or not r["idlist"]:
            return ids, int(r["count"])
        start = len(ids); time.sleep(0.4)

MON = {m: i for i, m in enumerate(["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"], 1)}
def txt(el): return "".join(el.itertext()).strip() if el is not None else ""

def parse(art):
    mc = art.find("MedlineCitation"); a = mc.find("Article"); pmid = mc.findtext("PMID")
    abst = []
    for t in a.findall("Abstract/AbstractText"):
        lab = t.get("Label"); s = txt(t)
        if s: abst.append(f"{lab}: {s}" if lab else s)
    j = a.find("Journal"); ji = j.find("JournalIssue"); pd = ji.find("PubDate")
    y = pd.findtext("Year") or (pd.findtext("MedlineDate") or "")[:4]
    m = pd.findtext("Month") or ""; m = str(MON.get(m[:3].lower(), m)) if m else ""
    ids = {"pmid": pmid, "doi": "", "pmc": ""}
    for i in art.findall("PubmedData/ArticleIdList/ArticleId"):
        if i.get("IdType") == "doi": ids["doi"] = i.text or ""
        if i.get("IdType") == "pmc": ids["pmc"] = i.text or ""
    return {
        "identifiers": ids, "title": txt(a.find("ArticleTitle")), "abstract": "\n".join(abst),
        "journal": {"title": j.findtext("Title") or "", "iso_abbreviation": j.findtext("ISOAbbreviation") or ""},
        "authors": [{"last_name": au.findtext("LastName") or au.findtext("CollectiveName") or "",
                     "initials": au.findtext("Initials") or ""} for au in a.findall("AuthorList/Author")],
        "publication_date": {"year": y, "month": m, "day": pd.findtext("Day") or ""},
        "article_types": [t.text for t in a.findall("PublicationTypeList/PublicationType")],
        "mesh_terms": [d.text for d in mc.findall("MeshHeadingList/MeshHeading/DescriptorName")],
        "keywords": [k.text for k in mc.findall("KeywordList/Keyword") if k.text],
        "citation": {"volume": ji.findtext("Volume") or "", "issue": ji.findtext("Issue") or "",
                     "pages": a.findtext("Pagination/MedlinePgn") or ""},
        "language": [l.text for l in a.findall("Language")],
        "indexing_status": mc.get("Status"),
    }

def search_arms(mindate, maxdate, datetype="edat"):
    arm_ids = {}
    for name, q in ARMS.items():
        arm_ids[name], _ = esearch(q, mindate, maxdate, datetype)
        time.sleep(0.4)
    return arm_ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--mindate"); ap.add_argument("--maxdate")
    ap.add_argument("--datetype", default="edat", choices=["edat", "pdat"])
    ap.add_argument("--out", default="sweep_raw.json")
    ap.add_argument("--pmids-only", action="store_true")
    a = ap.parse_args()
    today = datetime.date.today()
    mx = a.maxdate or today.strftime("%Y/%m/%d")
    mn = a.mindate or (today - datetime.timedelta(days=a.days)).strftime("%Y/%m/%d")
    arm_ids = search_arms(mn, mx, a.datetype)
    allids = sorted(set().union(*arm_ids.values()))
    if a.pmids_only:
        print(json.dumps(allids)); return
    for k, v in arm_ids.items():
        print(f"{k}: {len(v)} hits")
    recs = []
    for i in range(0, len(allids), 200):
        root = ET.fromstring(get(EU + "efetch.fcgi", {"db": "pubmed", "id": ",".join(allids[i:i+200]), "retmode": "xml"}))
        recs += [parse(x) for x in root.findall("PubmedArticle")]
        time.sleep(0.4)
    out = a.out if os.path.isabs(a.out) else os.path.join(HERE, a.out)
    json.dump(recs, open(out, "w"), ensure_ascii=False)
    state = {"last_fetch": today.isoformat(), "window": [mn, mx], "datetype": a.datetype,
             "candidates_fetched": len(recs)}
    json.dump(state, open(os.path.join(HERE, "guideline_sweep_state.json"), "w"), indent=1)
    print(f"{len(allids)} PMIDs, {len(recs)} records -> {out}")
    print("next: python3 guideline_sweep.py --raw " + os.path.basename(out))


if __name__ == "__main__":
    main()

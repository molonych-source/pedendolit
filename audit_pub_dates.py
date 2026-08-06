"""
Audit stored pub_date against PubMed (read-only, no writes to the store).

Motivation: a spot check on 2026-08-05 found stored dates like 2026-09-09 where
PubMed's ArticleDate is 2024-09-09 and only the *journal issue* carries 2026 —
i.e. the year came from one field and the month/day from another. Any time-based
UI (the "since date" catch-up mode, a "last 30 days" view, newest-first sorting)
rests on this field, so its true error rate is worth knowing before designing on it.

Fetches in batches of 200 via efetch, compares, writes a markdown report.

Usage:
  python3 audit_pub_dates.py [--store pedendolit-data.json] [--sample N|all]
                             [--out pub_date_audit.md]
"""
import json, os, argparse, random, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TOOL, EMAIL = "pedendolit", "molonych@gmail.com"

MONTHS = {m: f"{i:02d}" for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def norm(y, m, d):
    """Normalize a (year, month, day) triple to a sortable string, or None."""
    if not y:
        return None
    m = MONTHS.get(m, m) if m else None
    if m and not m.isdigit():
        return y
    parts = [y]
    if m:
        parts.append(m.zfill(2))
        if d and d.isdigit():
            parts.append(d.zfill(2))
    return "-".join(parts)


def node_date(node):
    if node is None:
        return None
    return norm(node.findtext("Year"), node.findtext("Month"), node.findtext("Day"))


def fetch(pmids):
    """Returns {pmid: {"article_date":..., "journal_date":..., "title":...}}."""
    data = urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
        "tool": TOOL, "email": EMAIL,
    }).encode()
    with urllib.request.urlopen(EFETCH, data=data, timeout=120) as r:
        xml = r.read()
    out = {}
    for art in ET.fromstring(xml).findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID")
        out[pmid] = {
            "article_date": node_date(art.find(".//Article/ArticleDate")),
            "journal_date": node_date(art.find(".//Journal/JournalIssue/PubDate")),
            "title": (art.findtext(".//ArticleTitle") or "")[:90],
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--sample", default="all",
                    help="'all' or an integer sample size")
    ap.add_argument("--out", default="pub_date_audit.md")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    store = json.load(open(os.path.join(HERE, args.store)))
    arts = [a for a in store.get("articles", []) if not a.get("excluded")]
    by_pmid = {str(a["pmid"]): a for a in arts}

    pmids = sorted(by_pmid)
    if args.sample != "all":
        random.Random(args.seed).shuffle(pmids)
        pmids = sorted(pmids[:int(args.sample)])

    live = {}
    for i in range(0, len(pmids), 200):
        chunk = pmids[i:i + 200]
        live.update(fetch(chunk))
        print(f"  fetched {min(i+200, len(pmids))}/{len(pmids)}")
        time.sleep(0.4)          # stay under the 3 req/sec unauthenticated cap

    rows = []
    for p in pmids:
        stored = (by_pmid[p].get("pub_date") or "").strip()
        ref = live.get(p)
        if not ref:
            rows.append((p, stored, None, None, "not returned by PubMed"))
            continue
        ad, jd = ref["article_date"], ref["journal_date"]
        issue = None
        if not stored:
            issue = "empty in store"
        # A fabricated date: the journal issue gives only year-month, so the day
        # was taken from ArticleDate and glued on. The result matches neither
        # source and points at a day the article was never associated with.
        elif (jd and len(jd) == 7 and ad and len(stored) == 10
              and stored[:7] == jd and stored[8:10] == ad[8:10] and stored[:7] != ad[:7]):
            issue = "FABRICATED (journal year-month + day borrowed from ArticleDate)"
        elif len(stored) != 10:
            issue = "not a sortable ISO date"
        # Dated to the journal issue rather than to e-publication. Not invented,
        # but it presents an article that appeared online in year X as year Y —
        # which is what a "what's new" reader actually sees.
        elif jd and stored == jd and ad and ad[:4] != jd[:4]:
            issue = "issue-dated, not e-pub dated (shown newer than it is)"
        elif ad and stored[:4] != ad[:4] and not (jd and stored[:4] == jd[:4]):
            issue = "year matches neither ArticleDate nor JournalDate"
        if issue:
            rows.append((p, stored, ad, jd, issue))

    by_issue = {}
    for r in rows:
        by_issue.setdefault(r[4], []).append(r)

    L = ["# pub_date audit", ""]
    L.append(f"Checked **{len(pmids)}** stored articles against PubMed "
             f"({'full store' if args.sample == 'all' else 'sample'}). "
             f"**{len(rows)}** have a problem ({100*len(rows)/max(1,len(pmids)):.1f}%).")
    L += ["", "| Problem | Articles |", "|---|---|"]
    for k, v in sorted(by_issue.items(), key=lambda kv: -len(kv[1])):
        L.append(f"| {k} | {len(v)} |")
    L.append("")
    L.append("`pub_date` is what any date filter, newest-first sort, or "
             "\"since <date>\" query reads. Every row below sorts to the wrong place.")
    for k, v in sorted(by_issue.items(), key=lambda kv: -len(kv[1])):
        L += ["", f"## {k} ({len(v)})", "",
              "| PMID | stored | PubMed ArticleDate | PubMed JournalDate |", "|---|---|---|---|"]
        for p, stored, ad, jd, _ in v[:60]:
            L.append(f"| {p} | `{stored}` | `{ad}` | `{jd}` |")
        if len(v) > 60:
            L.append(f"| … | *+{len(v)-60} more* | | |")

    out = os.path.join(HERE, args.out)
    open(out, "w").write("\n".join(L) + "\n")
    print(f"\n{len(rows)} of {len(pmids)} problematic")
    for k, v in sorted(by_issue.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(v):5d}  {k}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

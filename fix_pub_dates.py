"""
Repair `pub_date` from PubMed, and record how precise it actually is.

The bug (found 2026-08-06, see `pub_date_audit.md`): the raw feed hands the pipeline a
single merged `publication_date` dict. When the journal issue carries only a year and
month, the day is taken from a *different* field — the article's e-publication date —
and glued on, producing a date that exists in neither source. 165 of 1,406 store dates
were fabricated this way, 110 more were unsortable (`2018-Oct`, bare `2018`), and 69
showed a paper that appeared online in 2024 as 2026.

## The rule this applies

PubMed carries two dates and they routinely disagree by 1-3 years:

  * `Article/ArticleDate`          — when it actually appeared online (e-publication)
  * `Journal/JournalIssue/PubDate` — the formal issue it was later bound into

For a keep-up brief, **e-publication is what "published" means**: it is when a reader
could first have seen the paper. Dating by issue makes a 2024 paper look like 2026 news,
which is precisely the failure a "what's new since X" view must not have.

Fallback order, and never invent a day:

  1. `ArticleDate`                    -> precision "day"
  2. `JournalIssue/PubDate`, full     -> precision "day"
  3. `JournalIssue/PubDate`, yyyy-mm  -> `yyyy-mm-01`, precision "month"
  4. `JournalIssue/PubDate`, yyyy     -> `yyyy-01-01`, precision "year"

Cases 3 and 4 still need *a* sortable value, so they pin to the first of the period —
but they say so in `pub_date_precision`, so the UI can render "March 2018" or "2018"
instead of a false "1 March 2018". That is the difference between a placeholder and a
fabrication: this one is deterministic, documented, and labelled.

## Weekly use

Re-runnable and idempotent. With `--only-missing` it repairs just the articles that have
no `pub_date_precision` yet, which after this first pass means only newly ingested ones —
about 35 a week, one request. Wire that into the weekly run so the bug cannot creep back
via the raw feed.

Usage:
  python3 fix_pub_dates.py --dry-run          # default: report, write nothing
  python3 fix_pub_dates.py --apply
  python3 fix_pub_dates.py --apply --only-missing
"""
import json, os, argparse, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
TOOL, EMAIL = "pedendolit", "molonych@gmail.com"

MONTHS = {m: f"{i:02d}" for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def _parts(node):
    """(year, month, day) from a PubMed date node, months normalised to numbers."""
    if node is None:
        return None, None, None
    y = node.findtext("Year")
    m = node.findtext("Month")
    d = node.findtext("Day")
    if m:
        m = MONTHS.get(m[:3].title(), m)
        if not m.isdigit():
            m = None
    if d and not d.isdigit():
        d = None
    # A MedlineDate like "2018 Oct-Dec" has no Year element; take its leading year.
    if not y:
        md = node.findtext("MedlineDate") or ""
        if md[:4].isdigit():
            y = md[:4]
    return y, m, d


def resolve(article_date, journal_date):
    """Apply the fallback order. Returns (pub_date, precision, source)."""
    ay, am, ad = article_date
    if ay and am and ad:
        return f"{ay}-{am.zfill(2)}-{ad.zfill(2)}", "day", "article"
    jy, jm, jd = journal_date
    if jy and jm and jd:
        return f"{jy}-{jm.zfill(2)}-{jd.zfill(2)}", "day", "journal"
    if jy and jm:
        return f"{jy}-{jm.zfill(2)}-01", "month", "journal"
    if jy:
        return f"{jy}-01-01", "year", "journal"
    # An ArticleDate missing its day is still better than nothing.
    if ay and am:
        return f"{ay}-{am.zfill(2)}-01", "month", "article"
    if ay:
        return f"{ay}-01-01", "year", "article"
    return None, None, None


def fetch(pmids):
    data = urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
        "tool": TOOL, "email": EMAIL,
    }).encode()
    with urllib.request.urlopen(EFETCH, data=data, timeout=120) as r:
        xml = r.read()
    out = {}
    for art in ET.fromstring(xml).findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID")
        out[pmid] = (_parts(art.find(".//Article/ArticleDate")),
                     _parts(art.find(".//Journal/JournalIssue/PubDate")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--apply", action="store_true", help="write; otherwise dry-run")
    ap.add_argument("--only-missing", action="store_true",
                    help="only articles with no pub_date_precision yet (weekly use)")
    ap.add_argument("--report", default="pub_date_fix_report.md")
    args = ap.parse_args()

    path = os.path.join(HERE, args.store)
    store = json.load(open(path))
    arts = store.get("articles", [])
    by_pmid = {str(a.get("pmid")): a for a in arts if a.get("pmid")}

    targets = ([p for p, a in by_pmid.items() if not a.get("pub_date_precision")]
               if args.only_missing else sorted(by_pmid))
    if not targets:
        print("nothing to do — every article already has pub_date_precision.")
        return 0

    live = {}
    for i in range(0, len(targets), 200):
        live.update(fetch(targets[i:i + 200]))
        print(f"  fetched {min(i+200, len(targets))}/{len(targets)}")
        time.sleep(0.4)

    changed, unchanged, missing = [], 0, []
    prec_counts, month_moves = {}, 0
    for p in targets:
        ref = live.get(p)
        if not ref:
            missing.append(p)
            continue
        new_date, precision, source = resolve(*ref)
        if not new_date:
            missing.append(p)
            continue
        prec_counts[precision] = prec_counts.get(precision, 0) + 1
        a = by_pmid[p]
        old = (a.get("pub_date") or "").strip()
        if old != new_date:
            if old[:7] != new_date[:7]:
                month_moves += 1
            changed.append((p, old, new_date, precision, source,
                            (a.get("title") or "")[:70]))
        else:
            unchanged += 1
        if args.apply:
            a["pub_date"] = new_date
            a["pub_date_precision"] = precision
            a["pub_date_source"] = source

    print(f"\nchecked {len(targets)} | changed {len(changed)} | already correct {unchanged} "
          f"| no usable date {len(missing)}")
    print(f"  of the changes, {month_moves} move to a different month bucket")
    print("  precision: " + ", ".join(f"{k}={v}" for k, v in sorted(prec_counts.items())))

    L = ["# pub_date repair", "",
         f"{'APPLIED' if args.apply else 'DRY RUN — nothing written'}. "
         f"Checked {len(targets)}, changed {len(changed)}, already correct {unchanged}, "
         f"no usable date {len(missing)}.", "",
         f"{month_moves} articles move to a different month bucket, which is what any "
         f"date filter or newest-first sort reads.", "",
         "| precision | articles |", "|---|---|"]
    for k, v in sorted(prec_counts.items()):
        L.append(f"| {k} | {v} |")
    L += ["", "## Changes (first 80)", "",
          "| PMID | old | new | precision | source | title |", "|---|---|---|---|---|---|"]
    for p, old, new, prec, src, title in changed[:80]:
        L.append(f"| {p} | `{old}` | `{new}` | {prec} | {src} | {title} |")
    if len(changed) > 80:
        L.append(f"| … | *+{len(changed)-80} more* | | | | |")
    open(os.path.join(HERE, args.report), "w").write("\n".join(L) + "\n")
    print(f"  wrote {args.report}")

    if args.apply:
        json.dump(store, open(path, "w"), indent=1)
        print(f"  wrote {args.store}")

        # Durability. `build_dataset.py --rebuild` regenerates pub_date from the raw
        # feed, which is where the bug comes from — so writing only to the store would
        # be silently undone by the next rebuild. This side file is the corrected record,
        # and build_dataset.apply_pub_dates() re-applies it on EVERY build, exactly as
        # apply_topic_overrides() does for topics.
        cache_path = os.path.join(HERE, "pub_dates.json")
        cache = {}
        if os.path.exists(cache_path):
            cache = (json.load(open(cache_path)) or {}).get("dates", {})
        for p in targets:
            a = by_pmid.get(p)
            if a and a.get("pub_date_precision"):
                cache[p] = {"pub_date": a["pub_date"],
                            "precision": a["pub_date_precision"],
                            "source": a.get("pub_date_source")}
        json.dump({"comment": "Corrected publication dates, resolved from PubMed by "
                              "fix_pub_dates.py. Re-applied on every build by "
                              "build_dataset.apply_pub_dates(), because --rebuild would "
                              "otherwise restore the fabricated dates from the raw feed.",
                   "dates": cache}, open(cache_path, "w"), indent=1)
        print(f"  wrote pub_dates.json ({len(cache)} dates on record)")
    else:
        print("\n  dry run — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

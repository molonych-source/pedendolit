"""
PedEndoLit dashboard generator.
Reads pedendolit-data.json and writes a self-contained PedEndoLit-Dashboard.html
with the dataset embedded. Open the HTML directly in any browser — no server needed.

Layout: articles grouped into collapsible impact-tier sections (Practice-Altering,
High, Moderate, Low). Each article card collapses to a one-line header; an expand
chevron reveals the bottom line, the why-this-classification rationale, tags, and
the full abstract (revealed on press). Filters: search, topic, Diabetes-subtype,
age range, board-relevant, open-access, new-this-period.

Run after build_dataset.py. The weekly scheduled task runs both in sequence.
"""
import json, os, datetime, re, csv

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Feedback / bug-report form (Web3Forms).
# Get a free access key at https://web3forms.com (enter your email, no signup).
# Paste it below. The key is safe to expose in a public page — it can only
# SEND to your email, it cannot read anything. Until set, the Report button
# shows a "not configured" notice instead of failing silently.
WEB3FORMS_KEY = "bb727558-afe2-4799-9fda-90cd430b6a40"
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Phase 2: user accounts + personal saved-article lists (Supabase).
# Both values come from the Supabase dashboard -> Project Settings -> API.
# SUPABASE_ANON_KEY holds the "publishable" key (sb_publishable_...); the older
# "anon public" JWT starting with "eyJ" also works if this one ever needs swapping.
# The key is DESIGNED to be public in a web page. It grants no access on its
# own — Row-Level Security decides what each signed-in user may read or write.
# Never paste the "service_role" key here; that one bypasses RLS.
# While these are left empty, the dashboard builds exactly as before: no Sign in
# button, no Saved tab, no Save buttons.
SUPABASE_URL = "https://oiafndmmdplvitrttene.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_nPy9JRVfAiCN0HXhSHkckQ_XG4llewm"
# ---------------------------------------------------------------------------

# Optional entry-date override: Perplexity's export dates articles by PubMed ENTRY
# date (when the article entered the index), not print date. If the CSV is present,
# we adopt its dates so the month filter reflects entry-date (matching the source of
# truth) instead of print date. Articles not in the CSV keep their PubMed pub_date.
ENTRY_DATE_CSV = os.path.join(HERE, "all_articles_export.csv")

def load_entry_dates():
    if not os.path.exists(ENTRY_DATE_CSV):
        return {}
    out = {}
    with open(ENTRY_DATE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pmid = (row.get("pmid") or "").strip()
            pd = (row.get("pub_date") or "").strip()
            if pmid and pd:
                out[pmid] = pd
    return out

_MONTHS = {m: i for i, m in enumerate(
    ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], start=1)}
_MONTH_NAMES = ["", "January","February","March","April","May","June",
                "July","August","September","October","November","December"]

def month_key_label(pub_date):
    """Parse a date in any of these forms:
      YYYY-MM-DD, YYYY-Mon-DD, YYYY-Mon, YYYY-MM   (PubMed pub_date, hyphen)
      'YYYY Mon DD', 'YYYY Mon', 'YYYY'            (Perplexity CSV, space)
    Returns (sort_key, label). For a year with no resolvable month, returns
    ('YYYY-00', 'YYYY (month n/a)'). Returns (None,None) only if no year at all."""
    if not pub_date:
        return None, None
    s = pub_date.strip()
    # normalize separators: take year, then first non-year token as month
    tokens = re.split(r"[-\s]+", s)
    if not tokens or not re.match(r"^\d{4}$", tokens[0]):
        return None, None
    year = tokens[0]
    mnum = None
    if len(tokens) >= 2:
        mtok = tokens[1]
        if mtok.isdigit():
            mnum = int(mtok)
        else:
            mnum = _MONTHS.get(mtok[:3].title())
    if mnum and 1 <= mnum <= 12:
        return f"{year}-{mnum:02d}", f"{_MONTH_NAMES[mnum]} {year}"
    # year known, month not resolvable
    return f"{year}-00", f"{year} (month n/a)"
DATA = os.path.join(HERE, "pedendolit-data.json")
OUT_LOCAL = os.path.join(HERE, "PedEndoLit-Dashboard.html")
OUT_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "PedEndoLit-Dashboard.html"))
# The published copy must live inside this folder — it is the git repo GitHub
# Pages serves from. Writing it to the 01_Clinical_Research level would put it
# outside version control and it would never reach the live site.
OUT_INDEX = os.path.join(HERE, "index.html")


def build():
    with open(DATA) as f:
        store = json.load(f)
    active = [a for a in store["articles"] if not a.get("is_archived")]
    # stamp normalized month key/label onto each article, keyed on PUBLICATION date.
    # NB: we intentionally do NOT use the Perplexity CSV entry/index date here — that
    # is when an article entered the database, which mis-buckets (e.g. a Feb article
    # indexed in June showed under "June 2026"). The Month filter means "published in".
    months = {}
    for a in active:
        date_src = a.get("pub_date", "")
        k, lbl = month_key_label(date_src)
        a["month_key"] = k or ""
        a["month_label"] = lbl or ""
        if k:
            months[k] = lbl
    # sorted list of available months, newest first; the 'YYYY-00' (month n/a)
    # keys sort after that year's real months, which is the intended placement.
    month_list = [{"key": k, "label": months[k]} for k in sorted(months, reverse=True)]

    rank = {"PRACTICE-ALTERING": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    active.sort(key=lambda a: a.get("pub_date", ""), reverse=True)
    active.sort(key=lambda a: rank.get(a["impact"], 9))

    payload = {
        "generated": store.get("generated"),
        "review_period": store.get("review_period"),
        "last_run_date": store.get("last_run_date"),
        "count": len(active),
        "months": month_list,
        "articles": active,
    }
    data_json = json.dumps(payload, ensure_ascii=False)
    # Substitute config placeholders FIRST, then the dataset LAST, so that no
    # article text can ever be mistaken for a placeholder.
    html_doc = (HTML_TEMPLATE
                .replace("__WEB3FORMS_KEY__", WEB3FORMS_KEY)
                .replace("__SUPABASE_URL__", SUPABASE_URL)
                .replace("__SUPABASE_ANON_KEY__", SUPABASE_ANON_KEY)
                .replace("/*DATA*/", data_json))
    for out in (OUT_LOCAL, OUT_ROOT, OUT_INDEX):
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_doc)
    print(f"dashboard written: {len(active)} active articles")
    print(f"  {OUT_LOCAL}")
    print(f"  {OUT_ROOT}")
    print(f"  {OUT_INDEX}")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PedEndoLit — Pediatric Endocrinology Literature Dashboard</title>
<style>
:root{
  --bg:#faf9f5; --surface:#ffffff; --ink:#1f1e1c; --muted:#6b6a64; --line:#e6e4dc; --soft:#f4f2ec;
  --pa:#993c1d; --pa-bg:#faece7; --pa-dot:#d85a30;
  --high:#0c447c; --high-bg:#e6f1fb; --high-dot:#378add;
  --mod:#854f0b; --mod-bg:#faeeda; --mod-dot:#ba7517;
  --low:#5f5e5a; --low-bg:#f1efe8; --low-dot:#888780;
  --accent:#0f6e56; --accent-bg:#e1f5ee;
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#1a1916; --surface:#26241f; --ink:#ece9e1; --muted:#a3a098; --line:#3a382f; --soft:#2c2a25;
    --pa-bg:#3a1d12; --high-bg:#0c2438; --mod-bg:#3a2a10; --low-bg:#2c2a25;
    --pa:#f0997b; --high:#85b7eb; --mod:#ef9f27; --low:#b4b2a9; --accent:#5dcaa5; --accent-bg:#0f3a30;}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.5;font-size:15px}
.wrap{max-width:1180px;margin:0 auto;padding:24px 20px 80px}
header h1{font-size:22px;font-weight:600;margin:0 0 2px}
header .sub{color:var(--muted);font-size:13px}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:18px 0}
.metric{background:var(--surface);border:0.5px solid var(--line);border-radius:10px;padding:11px 13px}
.metric .lab{font-size:12px;color:var(--muted)}
.metric .val{font-size:23px;font-weight:600;margin-top:2px}
.tabs{display:flex;gap:4px;border-bottom:0.5px solid var(--line);margin:18px 0 4px}
.tab{border:none;background:none;color:var(--muted);font-size:14px;font-weight:500;padding:9px 16px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
.tab:hover{color:var(--ink)}
.tab.on{color:var(--accent);border-bottom-color:var(--accent)}
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:14px 0 16px}
@media(max-width:760px){.charts{grid-template-columns:1fr}}
.panel{background:var(--surface);border:0.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:16px}
.panel h2{font-size:14px;font-weight:600;margin:0 0 12px;color:var(--muted)}
.bar-row{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px}
.bar-row .name{width:150px;flex:none;color:var(--ink)}
.bar-track{flex:1;background:var(--low-bg);border-radius:6px;height:16px;overflow:hidden}
.bar-fill{height:100%;border-radius:6px}
.bar-row .num{width:40px;text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:16px 0 8px}
.controls input[type=search]{flex:1;min-width:220px;padding:9px 12px;border:0.5px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font-size:14px}
.chip{border:0.5px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:5px 12px;font-size:13px;cursor:pointer;user-select:none}
.chip.on{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.rowlabel{font-size:12px;color:var(--muted);align-self:center;margin-right:2px}
.msel{font-size:13px;padding:6px 28px 6px 12px;border:0.5px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);cursor:pointer;appearance:none;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b6a64' stroke-width='2'><path d='M6 9l6 6 6-6'/></svg>");background-repeat:no-repeat;background-position:right 9px center}
.msel:focus{outline:none;border-color:var(--accent)}
.count-line{color:var(--muted);font-size:13px;margin:8px 2px 14px}
/* tier group accordion */
.group{margin-bottom:14px;border:0.5px solid var(--line);border-radius:12px;overflow:hidden;background:var(--surface)}
.ghead{display:flex;align-items:center;gap:10px;padding:12px 16px;cursor:pointer;user-select:none}
.ghead:hover{background:var(--soft)}
.dot{width:13px;height:13px;border-radius:50%;flex:none}
.gname{font-weight:600;font-size:14px;padding:3px 10px;border-radius:6px}
.gname.pa{background:var(--pa-bg);color:var(--pa)} .gname.high{background:var(--high-bg);color:var(--high)}
.gname.mod{background:var(--mod-bg);color:var(--mod)} .gname.low{background:var(--low-bg);color:var(--low)}
.gcount{color:var(--muted);font-size:13px}
.gchev{margin-left:auto;color:var(--muted);transition:transform .15s;font-size:18px;line-height:1}
.group.collapsed .gchev{transform:rotate(-90deg)}
.group.collapsed .gbody{display:none}
.gbody{border-top:0.5px solid var(--line)}
/* article card */
.card{border-bottom:0.5px solid var(--line)}
.card:last-child{border-bottom:none}
.chead{display:flex;gap:10px;align-items:flex-start;padding:12px 16px;cursor:pointer}
.chead:hover{background:var(--soft)}
.cchev{color:var(--muted);font-size:16px;line-height:1.4;flex:none;transition:transform .15s}
.card.open .cchev{transform:rotate(90deg)}
.award{color:var(--accent);font-size:14px;flex:none;margin-top:2px}
.cmain{flex:1;min-width:0}
.ctitle{font-size:15px;font-weight:600;margin:0 0 3px}
.cmeta{font-size:13px;color:var(--muted)}
.cmeta .badge{margin-left:2px}
.badge{font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;letter-spacing:.02em;vertical-align:1px}
.b-pa{background:var(--pa-bg);color:var(--pa)} .b-high{background:var(--high-bg);color:var(--high)}
.b-mod{background:var(--mod-bg);color:var(--mod)} .b-low{background:var(--low-bg);color:var(--low)}
.subt{font-size:12px;color:var(--accent)}
.cbody{display:none;padding:0 16px 16px 42px}
.card.open .cbody{display:block}
.bl{font-size:13.5px;background:var(--soft);border-radius:8px;padding:10px 12px;margin:4px 0 8px}
.bl b{font-weight:600}
.why{font-size:12.5px;color:var(--muted);font-style:italic;margin:0 0 10px}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 10px}
.tag{font-size:11px;color:var(--muted);background:var(--low-bg);border-radius:5px;padding:2px 7px}
.abswrap{margin:4px 0 10px}
.absbtn{border:0.5px solid var(--line);background:var(--surface);color:var(--ink);border-radius:7px;padding:6px 12px;font-size:13px;cursor:pointer}
.absbtn:hover{background:var(--soft)}
.abshead{font-size:11px;font-weight:600;letter-spacing:.06em;color:var(--muted);margin:10px 0 4px}
.abstext{font-size:13.5px;color:var(--ink);line-height:1.6;white-space:pre-wrap}
.abstext.none{color:var(--muted);font-style:italic}
.links a{font-size:13px;color:var(--accent);text-decoration:none;margin-right:14px}
.links a:hover{text-decoration:underline}
.pmid{float:right;color:var(--muted);font-size:12px}
.foot{margin-top:30px;color:var(--muted);font-size:12px;border-top:0.5px solid var(--line);padding-top:14px}
.reportbtn{display:inline-block;border:0.5px solid var(--line);background:var(--surface);color:var(--ink);border-radius:7px;padding:6px 12px;font-size:13px;cursor:pointer}
.reportbtn:hover{background:var(--soft)}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center;z-index:50;padding:16px}
.modal-bg.show{display:flex}
.modal{background:var(--surface);border:0.5px solid var(--line);border-radius:12px;max-width:460px;width:100%;padding:18px 20px}
.modal h3{margin:0 0 4px;font-size:16px;font-weight:600}
.modal p{margin:0 0 12px;font-size:13px;color:var(--muted)}
.modal textarea{width:100%;min-height:120px;padding:10px 12px;border:0.5px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;font-size:14px;resize:vertical}
.modal .mrow{display:flex;gap:8px;justify-content:flex-end;margin-top:12px}
.modal button{border:0.5px solid var(--line);background:var(--surface);color:var(--ink);border-radius:8px;padding:8px 16px;font-size:14px;cursor:pointer}
.modal button.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
.modal button:hover{opacity:.9}
.modal .msg{font-size:13px;margin-top:10px;min-height:18px}
.modal .msg.ok{color:var(--accent)} .modal .msg.err{color:var(--pa)}
.hp{position:absolute;left:-9999px;top:-9999px}
.empty{text-align:center;color:var(--muted);padding:36px;font-size:14px}
/* ---- Phase 2: accounts + saved articles ---- */
.authbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.authwho{font-size:12px;color:var(--muted);max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.savebtn{flex:none;margin-top:1px;border:0.5px solid var(--line);background:var(--surface);color:var(--muted);border-radius:7px;padding:4px 10px;font-size:12px;cursor:pointer;white-space:nowrap}
.savebtn:hover:not(:disabled){background:var(--soft);color:var(--ink)}
.savebtn.on{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.savebtn:disabled{opacity:.4;cursor:not-allowed}
.modal input[type=email],.modal input[type=password]{width:100%;padding:9px 12px;margin-bottom:8px;border:0.5px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;font-size:14px}
.modal .mrow.split{justify-content:space-between}
.stubhead{display:flex;align-items:center;gap:10px;padding:12px 16px;background:var(--soft);border-bottom:0.5px solid var(--line)}
.stubrow{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:0.5px solid var(--line)}
.stubrow:last-child{border-bottom:none}
.stubrow .ctitle{color:var(--muted);font-style:italic;font-weight:500}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:8px;font-size:13px;z-index:60;opacity:0;pointer-events:none;transition:opacity .2s;max-width:90%}
.toast.show{opacity:.95}
.toast.err{background:var(--pa);color:#fff}
/* ---- Phase 3: notes, citations, "new since your last visit" ---- */
.notewrap{margin:10px 0 4px;position:relative}
.notelbl{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}
.notebox{width:100%;padding:8px 10px;border:0.5px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;font-size:13px;resize:vertical;min-height:44px}
.notebox:focus{outline:2px solid var(--accent);outline-offset:-1px}
.notestat{position:absolute;right:6px;bottom:8px;font-size:11px;color:var(--muted)}
.citebtn{margin-left:auto;background:none;border:0.5px solid var(--line);color:var(--muted);border-radius:6px;padding:5px 10px;font:inherit;font-size:12px;cursor:pointer;min-height:32px}
.citebtn:hover{color:var(--ink);border-color:var(--muted)}
.newdot{color:var(--accent);margin-right:6px;font-size:12px}
.savedbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.exportbtns{display:flex;gap:8px;flex-wrap:wrap}
.minibtn{background:var(--surface);border:0.5px solid var(--line);color:var(--ink);border-radius:8px;padding:8px 12px;font:inherit;font-size:12px;cursor:pointer;min-height:36px}
.minibtn:hover{border-color:var(--muted)}
/* ---- Phase 3C: phone ergonomics ---- */
.tabs{flex-wrap:wrap}
@media(max-width:760px){
  .chip{padding:9px 14px;font-size:13px}       /* was ~27px tall, under the 44px target */
  .savebtn,.citebtn,.minibtn{min-height:40px}
  .cbody{padding:0 14px 16px 16px}             /* the 42px indent ate a phone's width */
  .bar-row .name{width:110px}
  .controls input[type=search]{min-width:100%}
}
</style>
<!-- Supabase browser client (auth + saved lists). Loaded from CDN; if it fails
     to load the dashboard still works, just without accounts. Version is pinned
     so an upstream release cannot silently break sign-in; bump deliberately. -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.112.0"></script>
</head>
<body>
<div class="wrap">
  <header style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
    <div>
      <h1>PedEndoLit</h1>
      <div class="sub">Pediatric endocrinology literature dashboard · <span id="period"></span></div>
    </div>
    <div class="authbar">
      <span class="authwho" id="auth-who" style="display:none"></span>
      <button class="reportbtn" id="auth-btn" style="display:none">Sign in</button>
      <button class="reportbtn" id="open-report">Report a bug or leave a comment</button>
    </div>
  </header>

  <div class="metrics" id="metrics"></div>

  <div class="tabs">
    <button class="tab on" data-tab="feed">Feed</button>
    <button class="tab" data-tab="saved" id="tab-btn-saved" style="display:none">My Saved Articles</button>
    <button class="tab" data-tab="analytics">Analytics</button>
  </div>

  <div id="tab-feed">
    <div class="controls">
      <input type="search" id="q" placeholder="Search title, author, journal, takeaway…"/>
      <span class="chip" data-flag="since" id="chip-since" style="display:none">✦ New since your last visit</span>
      <span class="chip" data-flag="mine" id="chip-mine" style="display:none">★ Saved</span>
      <span class="chip" data-flag="guidelines">Guidelines</span>
      <span class="chip" data-flag="new">New this period</span>
      <span class="chip" data-flag="board">Board-relevant</span>
      <span class="chip" data-flag="open">Open access</span>
    </div>
    <div id="topic-chips" class="controls" style="margin-top:0"><span class="rowlabel">Topic:</span></div>
    <div id="dm-chips" class="controls" style="margin-top:0;display:none"><span class="rowlabel">Diabetes subtype:</span></div>
    <div id="age-chips" class="controls" style="margin-top:0"><span class="rowlabel">Age:</span></div>
    <div class="controls" style="margin-top:0">
      <span class="rowlabel">Month:</span>
      <select id="month-select" class="msel"><option value="All">All months</option></select>
    </div>

    <div class="count-line" id="count"></div>
    <div id="groups"></div>
  </div>

  <div id="tab-saved" style="display:none">
    <div class="savedbar">
      <div class="count-line" id="saved-count"></div>
      <div class="exportbtns">
        <button type="button" class="minibtn" id="export-txt" title="Copy all saved citations as plain text">Copy citations</button>
        <button type="button" class="minibtn" id="export-ris" title="Download as .ris for Zotero, EndNote or Mendeley">Export to Zotero (.ris)</button>
      </div>
    </div>
    <div id="saved-list"></div>
  </div>

  <div id="tab-analytics" style="display:none">
    <div class="charts">
      <div class="panel"><h2>Topic distribution</h2><div id="chart-topic"></div></div>
      <div class="panel"><h2>Evidence impact</h2><div id="chart-impact"></div></div>
    </div>
    <div class="panel"><h2>Articles by journal</h2><div id="chart-journal"></div></div>
  </div>

  <div class="foot">
    Data source: PubMed (NCBI E-utilities). Classified with PedEndoLit classifier v2.5.
    Generated <span id="gen"></span>. Article links open PubMed; DOI / Full Text open the publisher.
    This is a literature-surveillance aid, not medical advice.
  </div>
</div>

<div class="modal-bg" id="report-modal">
  <div class="modal">
    <h3>Report a bug or comment</h3>
    <p>Tell me what's wrong or share a suggestion. Submissions are emailed to the maintainer.</p>
    <form id="report-form">
      <textarea id="report-msg" placeholder="Describe the bug or your comment…" required></textarea>
      <input type="text" id="report-hp" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true"/>
      <div class="mrow">
        <button type="button" id="report-cancel">Cancel</button>
        <button type="submit" class="primary" id="report-send">Send</button>
      </div>
      <div class="msg" id="report-status"></div>
    </form>
  </div>
</div>

<div class="modal-bg" id="auth-modal">
  <div class="modal">
    <h3>Sign in to PedEndoLit</h3>
    <p>An account lets you save articles to your own list. Your list is private to you.</p>
    <form id="auth-form">
      <input type="email" id="auth-email" placeholder="you@example.com" autocomplete="email" required/>
      <input type="password" id="auth-pass" placeholder="Password (at least 6 characters)" autocomplete="current-password" required/>
      <div class="mrow split">
        <button type="button" id="auth-signup">Create account</button>
        <span>
          <button type="button" id="auth-cancel">Cancel</button>
          <button type="submit" class="primary" id="auth-signin">Sign in</button>
        </span>
      </div>
      <div class="msg" id="auth-status"></div>
    </form>
  </div>
</div>

<div class="toast" id="toast"></div>

<script id="data" type="application/json">/*DATA*/</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const ART=D.articles;

// ---- Phase 2 config (filled in by build_dashboard.py) ----
const SUPA_URL="__SUPABASE_URL__";
const SUPA_KEY="__SUPABASE_ANON_KEY__";
// Accounts are available only when both values are configured AND the Supabase
// library actually loaded. Otherwise the dashboard behaves exactly as in Phase 1.
const AUTH_ON = SUPA_URL.indexOf('http')===0 && SUPA_KEY.length>20
                && typeof window.supabase!=='undefined';
let SB=null;      // Supabase client
let USER=null;    // signed-in user, or null
document.getElementById('period').textContent=D.review_period||'';
document.getElementById('gen').textContent=(D.generated||'').replace('T',' ');

const TIERS=[
  {key:'PRACTICE-ALTERING',label:'Practice-Altering',cls:'pa',dot:'var(--pa-dot)'},
  {key:'HIGH',label:'High',cls:'high',dot:'var(--high-dot)'},
  {key:'MODERATE',label:'Moderate',cls:'mod',dot:'var(--mod-dot)'},
  {key:'LOW',label:'Low',cls:'low',dot:'var(--low-dot)'},
];
const impClass={'PRACTICE-ALTERING':'b-pa','HIGH':'b-high','MODERATE':'b-mod','LOW':'b-low'};
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const authorStr=a=>{const au=a.authors||[];if(!au.length)return '';return au.length<=3?au.join(', '):au.slice(0,3).join(', ')+' et al.';};
const _MON={jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};
// Format a PubMed pub_date as mm/dd/yyyy. Handles YYYY-MM-DD, YYYY-Mon-DD,
// and partial dates (no day -> mm/yyyy; year only -> yyyy) without inventing a day.
function fmtDate(s){
  if(!s)return '';
  const t=String(s).trim().split(/[-\s]+/);
  if(!/^\d{4}$/.test(t[0]))return esc(s);
  const y=t[0]; let mo=null,d=null;
  if(t[1]!==undefined){const x=t[1];mo=/^\d+$/.test(x)?parseInt(x,10):_MON[x.slice(0,3).toLowerCase()];}
  if(t[2]!==undefined&&/^\d+$/.test(t[2]))d=parseInt(t[2],10);
  if(mo&&mo>=1&&mo<=12&&d&&d>=1&&d<=31)
    return `${String(mo).padStart(2,'0')}/${String(d).padStart(2,'0')}/${y}`;
  if(mo&&mo>=1&&mo<=12)return `${String(mo).padStart(2,'0')}/${y}`;
  return y;
}

function metrics(){
  const n=ART.length;
  const m=[['Active articles',n],
    ['Practice-altering',ART.filter(a=>a.impact==='PRACTICE-ALTERING').length],
    ['High impact',ART.filter(a=>a.impact==='HIGH').length],
    ['Board-relevant',ART.filter(a=>a.board_relevant===1).length],
    ['New this period',ART.filter(a=>a.is_new).length]];
  document.getElementById('metrics').innerHTML=m.map(([l,v])=>
    `<div class="metric"><div class="lab">${l}</div><div class="val">${v}</div></div>`).join('');
}

// filter chip rows
const topics=[...new Set(ART.map(a=>a.topic))].sort();
document.getElementById('topic-chips').insertAdjacentHTML('beforeend',
  topics.map(t=>`<span class="chip" data-topic="${esc(t)}">${esc(t)}</span>`).join(''));
const DM_SUBS=['All','T1D','T1D·Stage','T2D','Technology','MODY/Monogenic','CFRD','GDM','Steroid-induced','General'];
document.getElementById('dm-chips').insertAdjacentHTML('beforeend',
  DM_SUBS.map(s=>`<span class="chip${s==='All'?' on':''}" data-dm="${esc(s)}">${esc(s)}</span>`).join(''));
const AGES=['All','Neonatal','Infant','Child','Adolescent','Transition'];
document.getElementById('age-chips').insertAdjacentHTML('beforeend',
  AGES.map(a=>`<span class="chip${a==='All'?' on':''}" data-age="${esc(a)}">${esc(a)}</span>`).join(''));

// month dropdown, populated from the publication months present in the data (newest first)
const MONTHS=D.months||[];
document.getElementById('month-select').insertAdjacentHTML('beforeend',
  MONTHS.map(m=>`<option value="${esc(m.key)}">${esc(m.label)}</option>`).join(''));

const state={q:'',flags:new Set(),topic:null,dm:'All',age:'All',month:'All'};
// LOW group collapsed by default; others open. Persists during session.
const collapsed={'PRACTICE-ALTERING':false,'HIGH':false,'MODERATE':false,'LOW':true};
const openCards=new Set();
// Abstracts need their own state Set for the same reason cards do: without it,
// any re-render (which now includes every keystroke) silently re-collapses every
// abstract the reader had opened.
const openAbstracts=new Set();

// Populated from user_prefs once signed in; null means "we don't know yet", which
// is different from "nothing is new".
let sinceLastVisit=null;
function isNewToMe(a){
  if(!sinceLastVisit)return false;
  const d=a.review_date||'';
  return d>sinceLastVisit;
}

function matches(a){
  if(state.topic&&a.topic!==state.topic)return false;
  if(state.topic==='Diabetes'&&state.dm!=='All'){
    if(state.dm==='Technology'){if(a.subtopic!=='Technology')return false;}
    else if(a.diabetes_subtype!==state.dm)return false;
  }
  if(state.age!=='All'&&!(a.age_range||[]).includes(state.age))return false;
  if(state.month!=='All'&&a.month_key!==state.month)return false;
  if(state.flags.has('board')&&a.board_relevant!==1)return false;
  if(state.flags.has('open')&&a.access!=='Open')return false;
  if(state.flags.has('new')&&!a.is_new)return false;
  if(state.flags.has('guidelines')&&a.study_type!=='Guideline/Consensus')return false;
  if(state.flags.has('mine')&&!savedPmids.has(a.pmid))return false;
  if(state.flags.has('since')&&!isNewToMe(a))return false;
  if(state.q){const q=state.q.toLowerCase();
    if(!(a.title+' '+(a.authors||[]).join(' ')+' '+a.journal+' '+(a.clinical_bottom_line||'')+' '+(a.tags||[]).join(' ')+' '+(a.abstract||'')).toLowerCase().includes(q))return false;}
  return true;
}

function cardHTML(a){
  const open=openCards.has(a.pmid)?' open':'';
  const award=a.impact==='PRACTICE-ALTERING'?`<span class="award" title="Practice-altering">&#9733;</span>`:`<span class="award" style="visibility:hidden">&#9733;</span>`;
  const sub=a.subtopic?` <span class="subt">${esc(a.subtopic)}</span>`:'';
  const tags=(a.tags||[]).slice(0,10).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
  const soc=(a.society&&a.society.length)?`<span class="tag">${a.society.map(esc).join(', ')}</span>`:'';
  const hasAbs=(a.abstract||'').trim().length>=40;
  // NB: no id= on the abstract body. The same card can be rendered twice (Feed and
  // My Saved Articles), and duplicate ids would make one copy toggle the other.
  const absOpen=openAbstracts.has(a.pmid);
  const ab  = hasAbs
    ? `<div class="abswrap"><button class="absbtn" data-abs="${a.pmid}">${absOpen?'Hide abstract':'Show abstract'}</button>
         <div class="absbody" style="display:${absOpen?'block':'none'}"><div class="abshead">ABSTRACT</div><div class="abstext">${esc(a.abstract)}</div></div></div>`
    : `<div class="abswrap"><div class="abshead">ABSTRACT</div><div class="abstext none">Abstract not available in PubMed for this record.</div></div>`;
  const doi=a.doi_url?`<a href="${esc(a.doi_url)}" target="_blank" rel="noopener">Full Text &#8599;</a>`:'';
  const pm=a.url?`<a href="${esc(a.url)}" target="_blank" rel="noopener">PubMed &#8599;</a>`:'';
  const isNew=isNewToMe(a)?`<span class="newdot" title="New since your last visit">&#10022;</span>`:'';
  // The note box only appears for articles this person has actually saved —
  // showing it on all ~1300 cards would be noise, and there is nothing to attach
  // a note to until a save row exists.
  const noteBox=(AUTH_ON&&USER&&savedPmids.has(a.pmid))
    ? `<div class="notewrap"><label class="notelbl">Your note</label>
         <textarea class="notebox" data-note="${esc(a.pmid)}" rows="2"
           placeholder="Why did you save this? (only you can see it)">${esc(noteFor(a.pmid))}</textarea>
         <span class="notestat" data-notestat="${esc(a.pmid)}"></span></div>`
    : '';
  return `<div class="card${open}" data-pmid="${a.pmid}">
    <div class="chead" data-card="${a.pmid}">
      <span class="cchev">&#9656;</span>${award}
      <div class="cmain">
        <div class="ctitle">${isNew}${esc(a.title)}</div>
        <div class="cmeta"><em>${esc(a.journal_abbr||a.journal)}</em> · ${fmtDate(a.pub_date)} · ${esc(authorStr(a))}
          · <span class="badge ${impClass[a.impact]}">${esc(a.impact)}</span>
          · ${esc(a.study_type)}${sub}</div>
      </div>
      ${AUTH_ON?`<button type="button" class="savebtn" data-save="${esc(a.pmid)}"></button>`:''}
    </div>
    <div class="cbody">
      ${a.clinical_bottom_line?`<div class="bl"><b>Bottom line:</b> ${esc(a.clinical_bottom_line)}</div>`:''}
      ${a.impact_rationale?`<div class="why"><b>Why ${esc(a.impact)}:</b> ${esc(a.impact_rationale)}</div>`:''}
      <div class="tags">${soc}${tags}</div>
      ${noteBox}
      ${ab}
      <div class="links">${pm}${doi}<span class="pmid">PMID: ${esc(a.pmid)}</span>
        <button type="button" class="citebtn" data-cite="${esc(a.pmid)}">Copy citation</button></div>
    </div>
  </div>`;
}

function render(){
  const shown=ART.filter(matches);
  document.getElementById('count').textContent=`${shown.length} of ${ART.length} articles`;
  const root=document.getElementById('groups');
  if(!shown.length){root.innerHTML='<div class="empty">No articles match the current filters.</div>';return;}
  let html='';
  for(const t of TIERS){
    const items=shown.filter(a=>a.impact===t.key);
    if(!items.length)continue;
    const col=collapsed[t.key]?' collapsed':'';
    html+=`<div class="group${col}" data-tier="${t.key}">
      <div class="ghead" data-tier="${t.key}">
        <span class="dot" style="background:${t.dot}"></span>
        <span class="gname ${t.cls}">${t.label}</span>
        <span class="gcount">${items.length} article${items.length===1?'':'s'}</span>
        <span class="gchev">&#9662;</span>
      </div>
      <div class="gbody">${items.map(cardHTML).join('')}</div>
    </div>`;
  }
  root.innerHTML=html;
  syncSaveButtons();
}

// event delegation — shared by the Feed and the My Saved Articles list
function cardClick(e){
  const sv=e.target.closest('.savebtn');
  if(sv){toggleSave(sv.dataset.save);return;}
  const gh=e.target.closest('.ghead');
  if(gh){const k=gh.dataset.tier;if(!k)return;collapsed[k]=!collapsed[k];
    gh.closest('.group').classList.toggle('collapsed',collapsed[k]);return;}
  const absBtn=e.target.closest('.absbtn');
  if(absBtn){const p=absBtn.dataset.abs;if(!p)return;
    // Record it in openAbstracts, then apply to every copy of this card, exactly
    // like the card-open toggle below. Driving this off inline style alone meant
    // the next render wiped it.
    const willOpen=!openAbstracts.has(p);
    if(willOpen)openAbstracts.add(p);else openAbstracts.delete(p);
    document.querySelectorAll('.card[data-pmid="'+p+'"]').forEach(c=>{
      const el=c.querySelector('.absbody');const bt=c.querySelector('.absbtn');
      if(el)el.style.display=willOpen?'block':'none';
      if(bt)bt.textContent=willOpen?'Hide abstract':'Show abstract';});
    return;}
  if(e.target.closest('.links'))return;
  const ch=e.target.closest('.chead');
  if(ch){const p=ch.dataset.card;if(!p)return;
    // An article can be on screen twice (Feed and My Saved Articles). Drive the
    // toggle off this card's own state, then keep every copy of it in step.
    const willOpen=!ch.closest('.card').classList.contains('open');
    if(willOpen)openCards.add(p);else openCards.delete(p);
    document.querySelectorAll('.card[data-pmid="'+p+'"]')
      .forEach(c=>c.classList.toggle('open',willOpen));}
}
document.getElementById('groups').addEventListener('click',cardClick);
document.getElementById('saved-list').addEventListener('click',cardClick);

// Debounced. render() re-filters ~1300 articles and rebuilds the whole list, so
// firing it on every keystroke made typing visibly janky on a phone.
let qTimer=null;
document.getElementById('q').addEventListener('input',e=>{
  state.q=e.target.value;
  clearTimeout(qTimer);
  qTimer=setTimeout(render,160);
});
document.querySelectorAll('.chip[data-flag]').forEach(c=>c.addEventListener('click',()=>{
  const f=c.dataset.flag;
  if(state.flags.has(f)){state.flags.delete(f);c.classList.remove('on');}
  else{state.flags.add(f);c.classList.add('on');}
  render();
}));
document.querySelectorAll('.chip[data-topic]').forEach(c=>c.addEventListener('click',()=>{
  const t=c.dataset.topic;
  document.querySelectorAll('.chip[data-topic]').forEach(x=>x.classList.remove('on'));
  if(state.topic===t){state.topic=null;}else{state.topic=t;c.classList.add('on');}
  const dmRow=document.getElementById('dm-chips');
  if(state.topic==='Diabetes')dmRow.style.display='flex';
  else{dmRow.style.display='none';state.dm='All';
    document.querySelectorAll('.chip[data-dm]').forEach(x=>x.classList.toggle('on',x.dataset.dm==='All'));}
  render();
}));
document.querySelectorAll('.chip[data-dm]').forEach(c=>c.addEventListener('click',()=>{
  document.querySelectorAll('.chip[data-dm]').forEach(x=>x.classList.remove('on'));
  c.classList.add('on');state.dm=c.dataset.dm;render();
}));
document.querySelectorAll('.chip[data-age]').forEach(c=>c.addEventListener('click',()=>{
  document.querySelectorAll('.chip[data-age]').forEach(x=>x.classList.remove('on'));
  c.classList.add('on');state.age=c.dataset.age;render();
}));
document.getElementById('month-select').addEventListener('change',e=>{
  state.month=e.target.value;render();
});

// ---- Analytics charts ----
function countBy(arr,key){const o={};arr.forEach(a=>{const v=a[key]||'—';o[v]=(o[v]||0)+1});return o;}
function distBar(containerId,counts,colorFor){
  const max=Math.max(1,...Object.values(counts));
  const rows=Object.entries(counts).sort((a,b)=>b[1]-a[1]);
  document.getElementById(containerId).innerHTML=rows.map(([k,v])=>{
    const w=Math.round(v/max*100);
    return `<div class="bar-row"><div class="name">${esc(k)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${w}%;background:${colorFor(k)}"></div></div>
      <div class="num">${v}</div></div>`;
  }).join('');
}
const impactDot={'PRACTICE-ALTERING':'var(--pa-dot)','HIGH':'var(--high-dot)','MODERATE':'var(--mod-dot)','LOW':'var(--low-dot)'};
let chartsDrawn=false;
function drawCharts(){
  if(chartsDrawn)return;
  distBar('chart-topic',countBy(ART,'topic'),()=>'#1d9e75');
  distBar('chart-impact',{
    'PRACTICE-ALTERING':ART.filter(a=>a.impact==='PRACTICE-ALTERING').length,
    'HIGH':ART.filter(a=>a.impact==='HIGH').length,
    'MODERATE':ART.filter(a=>a.impact==='MODERATE').length,
    'LOW':ART.filter(a=>a.impact==='LOW').length,
  },k=>impactDot[k]||'#888780');
  distBar('chart-journal',countBy(ART,'journal_abbr'),()=>'#1d9e75');
  chartsDrawn=true;
}

// ---- tab switching ----
document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>{
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  t.classList.add('on');
  const which=t.dataset.tab;
  ['feed','saved','analytics'].forEach(k=>{
    const el=document.getElementById('tab-'+k);
    if(el)el.style.display = (k===which?'block':'none');
  });
  if(which==='analytics')drawCharts();
  if(which==='saved')renderSaved();
}));

// ---- feedback / bug-report modal ----
const W3KEY="__WEB3FORMS_KEY__";
const rmodal=document.getElementById('report-modal');
const rstatus=document.getElementById('report-status');
function openReport(){rstatus.textContent='';rstatus.className='msg';rmodal.classList.add('show');document.getElementById('report-msg').focus();}
function closeReport(){rmodal.classList.remove('show');}
document.getElementById('open-report').addEventListener('click',openReport);
document.getElementById('report-cancel').addEventListener('click',closeReport);
rmodal.addEventListener('click',e=>{if(e.target===rmodal)closeReport();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeReport();});
document.getElementById('report-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const msg=document.getElementById('report-msg').value.trim();
  if(!msg)return;
  if(document.getElementById('report-hp').value){closeReport();return;} // honeypot: silently drop bots
  if(W3KEY==='YOUR_ACCESS_KEY'){
    rstatus.textContent='Reporting is not set up yet (no access key configured).';
    rstatus.className='msg err';return;
  }
  const btn=document.getElementById('report-send');
  btn.disabled=true;rstatus.textContent='Sending…';rstatus.className='msg';
  try{
    const res=await fetch('https://api.web3forms.com/submit',{
      method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},
      body:JSON.stringify({
        access_key:W3KEY,
        subject:'PedEndoLit dashboard — bug/comment',
        from_name:'PedEndoLit dashboard',
        message:msg,
        page_url:location.href
      })
    });
    const data=await res.json();
    if(data.success){
      rstatus.textContent='Thanks — your report was sent.';rstatus.className='msg ok';
      document.getElementById('report-msg').value='';
      setTimeout(closeReport,1500);
    }else{rstatus.textContent='Could not send: '+(data.message||'unknown error');rstatus.className='msg err';}
  }catch(err){rstatus.textContent='Network error — please try again.';rstatus.className='msg err';}
  btn.disabled=false;
});

// ===========================================================================
// Phase 2 — accounts (Supabase Auth) and personal saved-article lists.
// Only PMIDs are stored in the database. Article text is never copied there,
// so the weekly refresh stays the single source of truth for article content.
// ===========================================================================

// pmid lookup for the current week's dataset. Keys are strings: the dataset
// stores pmid as text, Postgres returns it as a number, so both sides are
// normalized to String() before they ever meet.
const BY_PMID=new Map(ART.map(a=>[String(a.pmid),a]));
const savedPmids=new Set();   // fast membership test for the Save buttons
let   savedOrder=[];          // display order, most recently saved first
const savedNotes=new Map();   // pmid -> note text
function noteFor(p){return savedNotes.get(String(p))||'';}

// ---- citations (RIS / plain text) ----
// Built entirely from the embedded dataset — nothing is fetched. Only worth
// having now that volume/issue/pages and full author lists actually exist.
function citationText(a){
  const au=(a.authors||[]);
  const names=au.length>6?au.slice(0,6).join(', ')+', et al.':au.join(', ');
  const yr=(a.pub_date||'').slice(0,4);
  const vip=[a.volume?a.volume:'',a.issue?'('+a.issue+')':'',a.pages?':'+a.pages:''].join('');
  return [names,a.title,[a.journal_abbr||a.journal,yr].filter(Boolean).join('. '),
          vip,a.doi?'doi:'+a.doi:'','PMID: '+a.pmid].filter(Boolean).join('. ').replace(/\.\./g,'.');
}
function risRecord(a){
  const L=[];
  const ty=(a.study_type==='Guideline/Consensus')?'STAND':'JOUR';
  L.push('TY  - '+ty);
  (a.authors||[]).forEach(n=>L.push('AU  - '+n));
  if(a.title)L.push('TI  - '+a.title);
  if(a.journal)L.push('JO  - '+a.journal);
  if(a.journal_abbr)L.push('J2  - '+a.journal_abbr);
  const yr=(a.pub_date||'').slice(0,4); if(yr)L.push('PY  - '+yr);
  if(a.pub_date)L.push('DA  - '+a.pub_date.replace(/-/g,'/'));
  if(a.volume)L.push('VL  - '+a.volume);
  if(a.issue)L.push('IS  - '+a.issue);
  if(a.pages)L.push('SP  - '+a.pages);
  if(a.abstract)L.push('AB  - '+a.abstract.replace(/\r?\n/g,' '));
  if(a.doi)L.push('DO  - '+a.doi);
  if(a.url)L.push('UR  - '+a.url);
  L.push('AN  - '+a.pmid);
  (a.tags||[]).forEach(t=>L.push('KW  - '+t.replace(/^#/,'')));
  L.push('ER  - ');
  return L.join('\n');
}
async function copyText(txt){
  try{await navigator.clipboard.writeText(txt);return true;}
  catch(e){
    // clipboard API needs a secure context; fall back so this still works locally
    try{const ta=document.createElement('textarea');ta.value=txt;ta.style.position='fixed';
      ta.style.opacity='0';document.body.appendChild(ta);ta.select();
      const ok=document.execCommand('copy');ta.remove();return ok;}catch(e2){return false;}
  }
}
function downloadFile(name,txt,mime){
  const b=new Blob([txt],{type:mime||'text/plain;charset=utf-8'});
  const u=URL.createObjectURL(b);const a=document.createElement('a');
  a.href=u;a.download=name;document.body.appendChild(a);a.click();
  a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000);
}

// ---- small toast for save/load errors ----
let toastTimer=null;
function toast(msg,isErr){
  const t=document.getElementById('toast');
  t.textContent=msg;
  t.className='toast show'+(isErr?' err':'');
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>{t.className='toast'+(isErr?' err':'');},4000);
}
function dbMsg(err){
  if(!err)return 'unknown error';
  if(err.code==='42P01'||err.code==='PGRST205')
    return 'the saved_articles table is missing — finish the Supabase setup';
  return err.message||String(err);
}

// ---- Save buttons ----
// Labels are set here rather than in cardHTML so there is exactly one place
// that decides how a Save button looks in each state.
function syncSaveButtons(){
  document.querySelectorAll('.savebtn').forEach(b=>{
    const p=b.dataset.save;
    const on=savedPmids.has(p);
    b.classList.toggle('on',on);
    b.disabled=!USER;
    b.innerHTML=on?'&#9733; Saved':'&#9734; Save';
    b.title=USER?(on?'Remove from My Saved Articles':'Save to My Saved Articles')
                :'Sign in to save articles';
  });
}

function addLocal(p){savedPmids.add(p);savedOrder=[p].concat(savedOrder.filter(x=>x!==p));}
function delLocal(p){savedPmids.delete(p);savedOrder=savedOrder.filter(x=>x!==p);}

async function toggleSave(pmid){
  if(!AUTH_ON)return;
  if(!USER){openAuth();return;}
  const wasSaved=savedPmids.has(pmid);
  // Update the UI first, then write. If the write fails we put it back.
  if(wasSaved)delLocal(pmid); else addLocal(pmid);
  syncSaveButtons();renderSaved();
  try{
    let error;
    if(wasSaved){
      ({error}=await SB.from('saved_articles').delete()
        .eq('user_id',USER.id).eq('pmid',Number(pmid)));
    }else{
      ({error}=await SB.from('saved_articles')
        .insert({user_id:USER.id,pmid:Number(pmid)}));
      if(error&&error.code==='23505')error=null; // already saved: not a failure
    }
    if(error)throw error;
  }catch(err){
    if(wasSaved)addLocal(pmid); else delLocal(pmid);
    syncSaveButtons();renderSaved();
    toast((wasSaved?'Could not remove that article: ':'Could not save that article: ')+dbMsg(err),true);
  }
}

async function loadSaved(){
  savedPmids.clear();savedOrder=[];savedNotes.clear();
  if(USER&&SB){
    const {data,error}=await SB.from('saved_articles')
      .select('pmid,saved_at,note').order('saved_at',{ascending:false});
    if(error)toast('Could not load your saved list: '+dbMsg(error),true);
    else (data||[]).forEach(r=>{const p=String(r.pmid);
      if(!savedPmids.has(p)){savedPmids.add(p);savedOrder.push(p);}
      if(r.note)savedNotes.set(p,r.note);});
  }
  syncSaveButtons();renderSaved();
  // The Feed needs re-rendering too: note boxes and the "Saved" filter both
  // depend on this data, and unlike Phase 2 the saved set now affects the Feed.
  render();
}

// ---- notes on saved articles ----
// Free text, so this is an upsert rather than the insert/delete used for saves.
// Debounced per article and fired on blur, so typing doesn't hammer the network.
const noteTimers=new Map();
async function saveNote(pmid,text){
  if(!AUTH_ON||!USER||!SB)return;
  const p=String(pmid);
  const val=(text||'').trim();
  if(val)savedNotes.set(p,val); else savedNotes.delete(p);
  const stat=document.querySelector('[data-notestat="'+p+'"]');
  if(stat)stat.textContent='Saving…';
  const {error}=await SB.from('saved_articles')
    .update({note:val||null}).eq('user_id',USER.id).eq('pmid',Number(p));
  if(stat){
    stat.textContent=error?'Not saved':'Saved';
    if(!error)setTimeout(()=>{if(stat)stat.textContent='';},1500);
  }
  if(error)toast('Could not save your note: '+dbMsg(error),true);
}

// ---- "since your last visit" ----
// Reads the previous visit marker, then stamps this visit. prev_seen_at is what
// the badge is computed from, so opening the page doesn't wipe the very marker
// the reader is looking at.
async function loadPrefs(){
  sinceLastVisit=null;
  if(!(USER&&SB))return;
  const {data,error}=await SB.from('user_prefs')
    .select('last_seen_at,prev_seen_at').eq('user_id',USER.id).maybeSingle();
  if(error&&error.code!=='PGRST116'){/* absent row is normal on first visit */}
  const nowIso=new Date().toISOString();
  if(data){
    sinceLastVisit=(data.last_seen_at||'').slice(0,10)||null;
    await SB.from('user_prefs')
      .update({prev_seen_at:data.last_seen_at,last_seen_at:nowIso,updated_at:nowIso})
      .eq('user_id',USER.id);
  }else{
    // First ever visit: nothing is "new to you" yet, by definition.
    await SB.from('user_prefs').insert({user_id:USER.id,last_seen_at:nowIso});
  }
  const chip=document.getElementById('chip-since');
  if(chip){
    const n=sinceLastVisit?ART.filter(isNewToMe).length:0;
    chip.style.display=(sinceLastVisit&&n>0)?'':'none';
    chip.textContent='✦ '+n+' new since your last visit';
  }
  const mine=document.getElementById('chip-mine');
  if(mine)mine.style.display=USER?'':'none';
}

// ---- My Saved Articles view ----
function renderSaved(){
  const host=document.getElementById('saved-list');
  const cnt=document.getElementById('saved-count');
  if(!host)return;
  cnt.textContent='';
  if(!AUTH_ON){host.innerHTML='<div class="empty">Accounts are not set up on this site yet.</div>';return;}
  if(!USER){host.innerHTML='<div class="empty">Sign in to start building your saved list.</div>';return;}
  if(!savedOrder.length){
    host.innerHTML='<div class="empty">No saved articles yet. Click &#9734; Save on any article in the Feed.</div>';return;}
  // An article you saved may be gone from this week's dataset (archived after
  // 60 days, or dropped by a source journal). Show it as a stub with a working
  // PubMed link instead of silently losing it.
  const present=savedOrder.filter(p=>BY_PMID.has(p));
  const missing=savedOrder.filter(p=>!BY_PMID.has(p));
  cnt.textContent=savedOrder.length+' saved article'+(savedOrder.length===1?'':'s')
    +(missing.length?' · '+missing.length+' no longer in the current list':'');
  let html='';
  if(present.length)
    html+='<div class="group"><div class="gbody">'
      +present.map(p=>cardHTML(BY_PMID.get(p))).join('')+'</div></div>';
  if(missing.length)
    html+='<div class="group"><div class="stubhead"><span class="gname low">Not in the current list</span>'
      +'<span class="gcount">'+missing.length+'</span></div><div class="gbody">'
      +missing.map(p=>'<div class="stubrow"><div class="cmain">'
        +'<div class="ctitle">[Article no longer in current list]</div>'
        +'<div class="cmeta">PMID '+esc(p)+' · <a href="https://pubmed.ncbi.nlm.nih.gov/'
        +esc(p)+'/" target="_blank" rel="noopener">View on PubMed &#8599;</a></div></div>'
        +'<button type="button" class="savebtn" data-save="'+esc(p)+'"></button></div>').join('')
      +'</div></div>';
  host.innerHTML=html;
  syncSaveButtons();
}

// ---- auth UI ----
const amodal=document.getElementById('auth-modal');
const astatus=document.getElementById('auth-status');
function openAuth(){
  astatus.textContent='';astatus.className='msg';
  amodal.classList.add('show');
  document.getElementById('auth-email').focus();
}
function closeAuth(){amodal.classList.remove('show');}
function updateAuthUI(){
  const btn=document.getElementById('auth-btn'),who=document.getElementById('auth-who');
  if(!AUTH_ON)return;
  btn.style.display='';
  document.getElementById('tab-btn-saved').style.display='';
  if(USER){
    who.textContent=USER.email||'Signed in';who.style.display='';
    btn.textContent='Sign out';
  }else{
    who.textContent='';who.style.display='none';
    btn.textContent='Sign in';
  }
}

async function doAuth(mode){
  const em=document.getElementById('auth-email').value.trim();
  const pw=document.getElementById('auth-pass').value;
  if(!em||!pw){astatus.textContent='Enter your email and a password.';astatus.className='msg err';return;}
  if(mode==='signup'&&pw.length<6){
    astatus.textContent='Password must be at least 6 characters.';astatus.className='msg err';return;}
  const b1=document.getElementById('auth-signin'),b2=document.getElementById('auth-signup');
  b1.disabled=b2.disabled=true;
  astatus.textContent=mode==='signup'?'Creating your account…':'Signing in…';
  astatus.className='msg';
  try{
    const {data,error}= mode==='signup'
      ? await SB.auth.signUp({email:em,password:pw})
      : await SB.auth.signInWithPassword({email:em,password:pw});
    if(error){astatus.textContent=error.message;astatus.className='msg err';}
    else if(mode==='signup'&&!data.session){
      // email confirmation is switched on for this project
      astatus.textContent='Account created. Check your email for a confirmation link, then sign in.';
      astatus.className='msg ok';
    }else{
      document.getElementById('auth-pass').value='';
      closeAuth();
      toast(mode==='signup'?'Account created. You are signed in.':'Signed in.');
    }
  }catch(err){
    astatus.textContent='Network error — please try again.';astatus.className='msg err';
  }
  b1.disabled=b2.disabled=false;
}

if(AUTH_ON){
  SB=window.supabase.createClient(SUPA_URL,SUPA_KEY);
  let authReady=false;
  const applySession=s=>{
    const u=s?s.user:null;
    const changed=(u?u.id:null)!==(USER?USER.id:null);
    USER=u;updateAuthUI();
    if(changed||!authReady){
      authReady=true;
      // Order matters: prefs first so the "new since your last visit" marker is
      // known before the Feed renders, then the saved list (which re-renders).
      loadPrefs().then(loadSaved).catch(()=>loadSaved());
    }
  };
  // fires immediately with the stored session, then on every sign-in/out/refresh
  SB.auth.onAuthStateChange((_evt,session)=>applySession(session));
  SB.auth.getSession().then(({data})=>applySession(data.session));

  document.getElementById('auth-btn').addEventListener('click',async()=>{
    if(USER){await SB.auth.signOut();toast('Signed out.');}
    else openAuth();
  });
  document.getElementById('auth-cancel').addEventListener('click',closeAuth);
  document.getElementById('auth-signup').addEventListener('click',()=>doAuth('signup'));
  document.getElementById('auth-form').addEventListener('submit',e=>{e.preventDefault();doAuth('signin');});
  amodal.addEventListener('click',e=>{if(e.target===amodal)closeAuth();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeAuth();});
}

// ---- notes: debounced typing + save on blur ----
// Delegated on document because note boxes are created and destroyed by render().
document.addEventListener('input',e=>{
  const ta=e.target.closest('.notebox');
  if(!ta)return;
  const p=ta.dataset.note;
  clearTimeout(noteTimers.get(p));
  noteTimers.set(p,setTimeout(()=>saveNote(p,ta.value),900));
});
document.addEventListener('blur',e=>{
  const ta=e.target.closest&&e.target.closest('.notebox');
  if(!ta)return;
  const p=ta.dataset.note;
  clearTimeout(noteTimers.get(p));
  saveNote(p,ta.value);
},true);
// Typing in a note must not bubble up and toggle the card open/closed.
document.addEventListener('click',e=>{if(e.target.closest('.notebox'))e.stopPropagation();},true);

// ---- copy a single citation ----
document.addEventListener('click',async e=>{
  const b=e.target.closest('.citebtn');
  if(!b)return;
  e.stopPropagation();
  const a=BY_PMID.get(String(b.dataset.cite));
  if(!a)return;
  const ok=await copyText(citationText(a));
  b.textContent=ok?'Copied':'Copy failed';
  setTimeout(()=>{b.textContent='Copy citation';},1400);
});

// ---- export the saved list ----
function savedArticlesInDataset(){
  return savedOrder.map(p=>BY_PMID.get(p)).filter(Boolean);
}
const expRis=document.getElementById('export-ris');
if(expRis)expRis.addEventListener('click',()=>{
  const arts=savedArticlesInDataset();
  if(!arts.length){toast('Nothing to export yet.',true);return;}
  downloadFile('pedendolit-saved.ris',arts.map(risRecord).join('\n'),'application/x-research-info-systems');
});
const expTxt=document.getElementById('export-txt');
if(expTxt)expTxt.addEventListener('click',async()=>{
  const arts=savedArticlesInDataset();
  if(!arts.length){toast('Nothing to export yet.',true);return;}
  const ok=await copyText(arts.map((a,i)=>(i+1)+'. '+citationText(a)).join('\n\n'));
  toast(ok?'Citations copied to the clipboard.':'Could not copy.',!ok);
});

metrics();render();renderSaved();
</script>
</body>
</html>"""

if __name__ == "__main__":
    build()

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

# Show the "Continue with Google" button. Leave False until the Google provider is
# actually enabled in Supabase (Authentication -> Sign In / Providers -> Google),
# otherwise clicking it just errors with "provider is not enabled".
# NOTE: the Google client SECRET is not like the key above — it is a real secret and
# lives only in the Supabase dashboard. It must never appear in this file or the repo.
GOOGLE_ENABLED = True
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
                .replace("__GOOGLE_ENABLED__", "true" if GOOGLE_ENABLED else "false")
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
<title>PedsEndoBrief: Pediatric Endocrinology Literature</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#faf9f5; --surface:#ffffff; --ink:#1f1e1c; --ink2:#45443f; --muted:#6b6a64; --line:#e6e4dc; --soft:#f4f2ec;
  --pa:#993c1d; --pa-bg:#faece7; --pa-dot:#d85a30;
  --high:#0c447c; --high-bg:#e6f1fb; --high-dot:#378add;
  --mod:#854f0b; --mod-bg:#faeeda; --mod-dot:#ba7517;
  --low:#5f5e5a; --low-bg:#f1efe8; --low-dot:#888780;
  --accent:#0f6e56; --accent-bg:#e1f5ee;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif;
  --sans:"Public Sans",system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#1a1916; --surface:#26241f; --ink:#ece9e1; --ink2:#cfccc3; --muted:#a3a098; --line:#3a382f; --soft:#2c2a25;
    --pa-bg:#3a1d12; --high-bg:#0c2438; --mod-bg:#3a2a10; --low-bg:#2c2a25;
    --pa:#f0997b; --high:#85b7eb; --mod:#ef9f27; --low:#b4b2a9; --accent:#5dcaa5; --accent-bg:#0f3a30;}
}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.5;font-size:15px}
a{color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 80px}

/* ---- top bar: brand, destinations, search, account ---- */
.top{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--line)}
.top-in{max-width:1180px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;gap:8px 18px;flex-wrap:wrap}
.brand{font-family:var(--serif);font-weight:600;font-size:22px;letter-spacing:-.01em;text-decoration:none;color:var(--ink)}
.nav{display:flex;gap:2px}
.nav a{padding:7px 12px;border-radius:8px;color:var(--muted);text-decoration:none;font-size:14px;font-weight:500}
.nav a:hover{color:var(--ink);background:var(--soft)}
.nav a[aria-current=page]{color:var(--accent);background:var(--accent-bg)}
.search{flex:1;min-width:180px;max-width:440px}
.search input{width:100%;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:inherit;font-size:14px}
.authbar{display:flex;gap:8px;align-items:center;margin-left:auto}
.authwho{font-size:12px;color:var(--muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ---- landing ---- */
.hero{padding:36px 0 4px}
.hero-q{font-family:var(--serif);font-size:30px;line-height:1.5;font-weight:400;margin:0;letter-spacing:-.005em}
.inl{font:inherit;color:var(--accent);background:transparent;border:0;border-bottom:2px solid var(--accent);border-radius:0;padding:0 2px;cursor:pointer;appearance:none;-webkit-appearance:none}
select.inl{padding-right:22px;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%230f6e56' stroke-width='2.5'><path d='M6 9l6 6 6-6'/></svg>");background-repeat:no-repeat;background-position:right 2px center}
input.inl{font-size:.82em}
.go{font:inherit;font-family:var(--sans);font-size:15px;font-weight:600;background:var(--accent);color:#fff;border:0;border-radius:8px;padding:9px 16px;cursor:pointer;margin-left:6px;vertical-align:middle}
.go:hover{opacity:.92}
.coverage{font-size:13.5px;color:var(--muted);max-width:70ch;border-left:3px solid var(--line);padding:2px 0 2px 12px;margin:18px 0 0}
.coverage.warn{color:var(--ink);background:var(--mod-bg);border-left-color:var(--mod-dot);padding:10px 14px;border-radius:0 8px 8px 0}
.statline{font-size:13px;color:var(--muted);margin:12px 0 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px;margin:26px 0 10px}
.tile{display:flex;flex-direction:column;gap:7px;padding:15px 16px 13px;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--rule,var(--line));border-radius:10px;text-decoration:none;color:var(--ink)}
.tile:hover{border-color:var(--muted);border-left-color:var(--rule,var(--muted))}
.t-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.t-name{font-weight:600;font-size:16px;line-height:1.3}
.spark{flex:none;color:var(--muted);margin-top:3px}
.t-new{font-size:13px;font-weight:600;color:var(--accent)}
.t-new.none{color:var(--muted);font-weight:400}
.t-lead{font-family:var(--serif);font-size:14.5px;line-height:1.42;margin:0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.t-foot{margin-top:auto;padding-top:4px;font-size:12px;color:var(--muted)}

/* ---- topic queue ---- */
.qhead{padding:22px 0 4px}
.back{font-size:13.5px;color:var(--muted);text-decoration:none}
.back:hover{color:var(--ink);text-decoration:underline}
.qtitle{font-family:var(--serif);font-size:34px;font-weight:600;margin:4px 0 2px;letter-spacing:-.01em;line-height:1.2}
.qsub{color:var(--muted);font-size:14px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center;margin:14px 0 14px}
.fld{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted)}
.fld select,.fld input{font:inherit;font-size:13px;padding:5px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink)}
.chip{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:999px;padding:5px 12px;font:inherit;font-size:13px;cursor:pointer}
.chip:hover{border-color:var(--muted)}
.chip.on{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.empty{text-align:center;color:var(--muted);padding:36px;font-size:14px}
/* tier group accordion: the tier is named once here, not on every row */
.group{margin-bottom:14px;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--surface)}
.ghead{display:flex;align-items:center;gap:10px;padding:12px 18px;cursor:pointer;user-select:none}
.ghead:hover{background:var(--soft)}
.dot{width:13px;height:13px;border-radius:50%;flex:none}
.gname{font-weight:600;font-size:14px;padding:3px 10px;border-radius:6px}
.gname.pa{background:var(--pa-bg);color:var(--pa)} .gname.high{background:var(--high-bg);color:var(--high)}
.gname.mod{background:var(--mod-bg);color:var(--mod)} .gname.low{background:var(--low-bg);color:var(--low)}
.gcount{color:var(--muted);font-size:13px}
.gchev{margin-left:auto;color:var(--muted);transition:transform .15s;font-size:18px;line-height:1}
.group.collapsed .gchev{transform:rotate(-90deg)}
.group.collapsed .gbody{display:none}
.gbody{border-top:1px solid var(--line)}
.morebtn{display:block;width:100%;border:0;border-top:1px solid var(--line);background:var(--soft);color:var(--ink);font:inherit;font-size:13.5px;padding:12px;cursor:pointer}
.morebtn:hover{background:var(--line)}

/* ---- article row: bottom line is the headline ---- */
.card{border-bottom:1px solid var(--line)}
.card:last-child{border-bottom:none}
.chead{display:flex;gap:14px;align-items:flex-start;padding:16px 18px;cursor:pointer}
.chead:hover{background:var(--soft)}
.cmain{flex:1;min-width:0}
.bl-head{font-family:var(--serif);font-size:18.5px;line-height:1.38;font-weight:500;margin:0 0 5px;color:var(--ink)}
.bl-head.is-title{font-weight:600}
.bl-head{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card.open .bl-head{display:block;-webkit-line-clamp:unset;overflow:visible}
.blrest{font-family:var(--serif);font-size:15px;line-height:1.55;color:var(--ink2);margin:0 0 12px;max-width:70ch}
.ctitle{font-size:13.5px;line-height:1.45;color:var(--ink2);margin:0 0 4px}
.cmeta{font-size:12.5px;color:var(--muted)}
.cact{display:flex;align-items:center;gap:6px;flex:none}
.cchev{color:var(--muted);font-size:15px;transition:transform .15s}
.card.open .cchev{transform:rotate(90deg)}
.tierpill{font-size:11px;font-weight:600;padding:1px 7px;border-radius:5px}
.subt{color:var(--accent)}
.cbody{display:none;padding:0 18px 18px}
.card.open .cbody{display:block}
.why{font-size:12.5px;color:var(--muted);font-style:italic;margin:0 0 10px}
.tags{display:flex;flex-wrap:wrap;gap:5px;margin:0 0 10px}
.tag{font-size:11px;color:var(--muted);background:var(--low-bg);border-radius:5px;padding:2px 7px}
.abswrap{margin:4px 0 10px}
.absbtn{border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:7px;padding:6px 12px;font-size:13px;cursor:pointer}
.absbtn:hover{background:var(--soft)}
.abshead{font-size:11px;font-weight:600;letter-spacing:.06em;color:var(--muted);margin:10px 0 4px}
.abstext{font-size:14px;color:var(--ink);line-height:1.6;white-space:pre-wrap;max-width:75ch}
.abstext.none{color:var(--muted);font-style:italic}
.links a{font-size:13px;color:var(--accent);text-decoration:none;margin-right:14px}
.links a:hover{text-decoration:underline}
.pmid{float:right;color:var(--muted);font-size:12px}

/* ---- analytics ---- */
.charts{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:20px 0 16px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:16px}
.panel h2{font-size:14px;font-weight:600;margin:0 0 12px;color:var(--muted)}
.bar-row{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px}
.bar-row .name{width:150px;flex:none;color:var(--ink)}
.bar-track{flex:1;background:var(--low-bg);border-radius:6px;height:16px;overflow:hidden}
.bar-fill{height:100%;border-radius:6px}
.bar-row .num{width:40px;text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}

.pagehead{padding:22px 0 4px}
.foot{margin-top:40px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:14px}
.foot .reportbtn{margin-top:10px}
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
.modal input[type=email],.modal input[type=password],.modal input.codein{width:100%;padding:9px 12px;margin-bottom:8px;border:0.5px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;font-size:14px}
.modal input.codein{letter-spacing:6px;text-align:center;font-variant-numeric:tabular-nums}
.modal button.linkbtn{background:none;border:0;padding:0;color:var(--muted);font-size:12px;text-decoration:underline;cursor:pointer}
.modal button.linkbtn:hover{color:var(--ink);opacity:1}
.modal .mrow.split{justify-content:space-between}
.stubhead{display:flex;align-items:center;gap:10px;padding:12px 16px;background:var(--soft);border-bottom:0.5px solid var(--line)}
.stubrow{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:0.5px solid var(--line)}
.stubrow:last-child{border-bottom:none}
.stubrow .ctitle{color:var(--muted);font-style:italic;font-weight:500}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:8px;font-size:13px;z-index:60;opacity:0;pointer-events:none;transition:opacity .2s;max-width:90%}
.toast.show{opacity:.95}
.toast.err{background:var(--pa);color:#fff}
/* ---- Google sign-in ---- */
#auth-google{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;
  padding:11px 16px;border:0.5px solid var(--line);border-radius:8px;background:var(--surface);
  color:var(--ink);font:inherit;font-size:14px;font-weight:500;cursor:pointer;min-height:44px}
#auth-google:hover{border-color:var(--muted)}
#auth-google:disabled{opacity:.6;cursor:not-allowed}
.authdiv{display:flex;align-items:center;gap:10px;margin:14px 0;color:var(--muted);font-size:12px}
.authdiv::before,.authdiv::after{content:"";flex:1;height:1px;background:var(--line)}
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
/* ---- phone ---- */
.tabs{display:none}
@media(max-width:700px){
  .top-in{padding:8px 14px;gap:8px 12px}
  .brand{order:1;font-size:20px}
  .authbar{order:2}
  .authwho{display:none}
  .search{order:3;flex-basis:100%;max-width:none}
  .nav{order:4;flex-basis:100%}
  .wrap{padding:0 14px 60px}
  .hero{padding-top:24px}
  .hero-q{font-size:22px}
  .go{margin:8px 0 0 0;display:block}
  .grid{grid-template-columns:1fr}
  .qtitle{font-size:27px}
  .bl-head{font-size:17px}
  .chead{padding:14px 12px;gap:10px}
  .cbody{padding:0 12px 16px}
  .chip{padding:9px 14px}
  .savebtn,.citebtn,.minibtn{min-height:40px}
  .charts{grid-template-columns:1fr}
  .bar-row .name{width:110px}
}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}
</style>
<!-- Supabase browser client (auth + saved lists). Loaded from CDN; if it fails
     to load the dashboard still works, just without accounts. Version is pinned
     so an upstream release cannot silently break sign-in; bump deliberately. -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.112.0"></script>
</head>
<body>
<header class="top">
  <div class="top-in">
    <a class="brand" href="#/" id="brand">PedsEndoBrief</a>
    <nav class="nav" aria-label="Main">
      <a href="#/" data-nav="home">Topics</a>
      <a href="#/saved" data-nav="saved" id="tab-btn-saved" style="display:none">Saved</a>
      <a href="#/analytics" data-nav="analytics">Analytics</a>
    </nav>
    <div class="search"><input type="search" id="q" placeholder="Search all articles" aria-label="Search all articles" autocomplete="off"/></div>
    <div class="authbar">
      <span class="authwho" id="auth-who" style="display:none"></span>
      <button class="reportbtn" id="auth-btn" style="display:none">Sign in</button>
    </div>
  </div>
</header>

<div class="wrap">
  <main id="main">

  <section id="v-home">
    <div class="hero">
      <p class="hero-q">What's new in
        <select id="c-topic" class="inl" aria-label="Topic"></select>
        since <input type="date" id="c-since" class="inl" aria-label="Since date"/>
        <button type="button" class="go" id="c-go">Show articles</button>
      </p>
      <div id="c-note" role="status"></div>
      <p class="statline" id="statline"></p>
    </div>
    <div class="grid" id="grid"></div>
  </section>

  <section id="v-queue" hidden>
    <div class="qhead" id="qhead"></div>
    <div class="toolbar" id="qtools">
      <label class="fld">Published since <input type="date" id="f-since"/></label>
      <label class="fld">Age
        <select id="f-age"><option>All</option><option>Neonatal</option><option>Infant</option><option>Child</option><option>Adolescent</option><option>Transition</option></select></label>
      <label class="fld" id="f-dm-wrap" hidden>Diabetes type
        <select id="f-dm"><option>All</option><option>T1D</option><option>T1D·Stage</option><option>T2D</option><option>Technology</option><option>MODY/Monogenic</option><option>CFRD</option><option>GDM</option><option>Steroid-induced</option><option>General</option></select></label>
      <button type="button" class="chip" data-flag="since" id="chip-since" style="display:none">New since your last visit</button>
      <button type="button" class="chip" data-flag="mine" id="chip-mine" style="display:none">Saved only</button>
      <button type="button" class="chip" data-flag="new">Added this week</button>
      <button type="button" class="chip" data-flag="guidelines">Guidelines</button>
      <button type="button" class="chip" data-flag="board">Board-relevant</button>
      <button type="button" class="chip" data-flag="open">Open access</button>
    </div>
    <div id="groups"></div>
  </section>

  <section id="v-saved" hidden>
    <div class="pagehead"><h1 class="qtitle">Saved articles</h1></div>
    <div class="toolbar">
      <div class="qsub" id="saved-count"></div>
      <span style="flex:1"></span>
      <button type="button" class="minibtn" id="export-txt" title="Copy all saved citations as plain text">Copy citations</button>
      <button type="button" class="minibtn" id="export-ris" title="Download as .ris for Zotero, EndNote or Mendeley">Export to Zotero (.ris)</button>
    </div>
    <div id="saved-list"></div>
  </section>

  <section id="v-analytics" hidden>
    <div class="pagehead"><h1 class="qtitle">Analytics</h1></div>
    <div class="charts">
      <div class="panel"><h2>Topic distribution</h2><div id="chart-topic"></div></div>
      <div class="panel"><h2>Evidence impact</h2><div id="chart-impact"></div></div>
    </div>
    <div class="panel"><h2>Articles by journal</h2><div id="chart-journal"></div></div>
  </section>

  </main>

  <div class="foot">
    Data source: PubMed (NCBI E-utilities). Classified with the PedsEndoBrief classifier v2.5.
    Generated <span id="gen"></span>. Article links open PubMed; DOI / Full Text open the publisher.
    This is a literature-surveillance aid, not medical advice.
    <div><button type="button" class="reportbtn" id="open-report">Report a bug or leave a comment</button></div>
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
    <h3 id="auth-title">Sign in to PedsEndoBrief</h3>
    <p id="auth-intro">An account lets you save articles to your own list. Your list is private to you.</p>
    <button type="button" id="auth-google" style="display:none">
      <svg viewBox="0 0 18 18" width="16" height="16" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/></svg>
      <span>Continue with Google</span>
    </button>
    <div class="authdiv" id="auth-div" style="display:none"><span>or</span></div>
    <form id="auth-form">
      <input type="email" id="auth-email" placeholder="you@example.com" autocomplete="email" required/>
      <input type="password" id="auth-pass" placeholder="Password (at least 6 characters)" autocomplete="current-password" required/>
      <div style="margin:-2px 0 4px"><button type="button" class="linkbtn" id="auth-forgot">Forgot password?</button></div>
      <div class="mrow split">
        <button type="button" id="auth-signup">Create account</button>
        <span>
          <button type="button" id="auth-cancel">Cancel</button>
          <button type="submit" class="primary" id="auth-signin">Sign in</button>
        </span>
      </div>
      <div class="msg" id="auth-status"></div>
    </form>
    <form id="reset-form" style="display:none">
      <p id="reset-hint"></p>
      <input type="email" id="reset-email" placeholder="you@example.com" autocomplete="email"/>
      <div id="reset-stage2" style="display:none">
        <input type="text" id="reset-code" class="codein" placeholder="6-digit code" inputmode="numeric" autocomplete="one-time-code" maxlength="6"/>
        <input type="password" id="reset-newpass" placeholder="New password (at least 6 characters)" autocomplete="new-password"/>
      </div>
      <div class="mrow split">
        <button type="button" class="linkbtn" id="reset-resend" style="display:none">Resend code</button>
        <span>
          <button type="button" id="reset-back">Back</button>
          <button type="submit" class="primary" id="reset-go">Email me a code</button>
        </span>
      </div>
      <div class="msg" id="reset-status"></div>
    </form>
    <form id="confirm-form" style="display:none">
      <p id="confirm-hint"></p>
      <input type="text" id="confirm-code" class="codein" placeholder="6-digit code" inputmode="numeric" autocomplete="one-time-code" maxlength="6"/>
      <div class="mrow split">
        <button type="button" class="linkbtn" id="confirm-resend">Resend code</button>
        <span>
          <button type="button" id="confirm-back">Back</button>
          <button type="submit" class="primary" id="confirm-go">Confirm email</button>
        </span>
      </div>
      <div class="msg" id="confirm-status"></div>
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
const GOOGLE_ON=__GOOGLE_ENABLED__;
// Accounts are available only when both values are configured AND the Supabase
// library actually loaded. Otherwise the dashboard behaves exactly as in Phase 1.
const AUTH_ON = SUPA_URL.indexOf('http')===0 && SUPA_KEY.length>20
                && typeof window.supabase!=='undefined';
let SB=null;      // Supabase client
let USER=null;    // signed-in user, or null
document.getElementById('gen').textContent=(D.generated||'').replace('T',' ');

const TIERS=[
  {key:'PRACTICE-ALTERING',label:'Practice-Altering',cls:'pa',dot:'var(--pa-dot)'},
  {key:'HIGH',label:'High',cls:'high',dot:'var(--high-dot)'},
  {key:'MODERATE',label:'Moderate',cls:'mod',dot:'var(--mod-dot)'},
  {key:'LOW',label:'Low',cls:'low',dot:'var(--low-dot)'},
];
const TIER_BY_KEY=Object.fromEntries(TIERS.map(t=>[t.key,t]));
const esc=s=>(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const authorStr=a=>{const au=a.authors||[];if(!au.length)return '';return au.length<=3?au.join(', '):au.slice(0,3).join(', ')+' et al.';};
const _MON={jan:1,feb:2,mar:3,apr:4,may:5,jun:6,jul:7,aug:8,sep:9,oct:10,nov:11,dec:12};
// Format a pub_date as mm/dd/yyyy, honouring how precise the date actually is.
// Since the 2026-08-06 repair, pub_date is ALWAYS a full sortable ISO date — a
// month-precision article stores YYYY-MM-01 so it can be sorted and filtered. Rendering
// that literally would put a fabricated day back on the page, which is the bug the
// repair removed. `prec` ('day' | 'month' | 'year') says how much of it is real.
function fmtDate(s, prec){
  if(!s)return '';
  const t=String(s).trim().split(/[-\s]+/);
  if(!/^\d{4}$/.test(t[0]))return esc(s);
  const y=t[0]; let mo=null,d=null;
  if(prec==='year')return y;
  if(t[1]!==undefined){const x=t[1];mo=/^\d+$/.test(x)?parseInt(x,10):_MON[x.slice(0,3).toLowerCase()];}
  if(t[2]!==undefined&&/^\d+$/.test(t[2])&&prec!=='month')d=parseInt(t[2],10);
  if(mo&&mo>=1&&mo<=12&&d&&d>=1&&d<=31)
    return `${String(mo).padStart(2,'0')}/${String(d).padStart(2,'0')}/${y}`;
  if(mo&&mo>=1&&mo<=12)return `${String(mo).padStart(2,'0')}/${y}`;
  return y;
}
const MONTH_NAMES=['January','February','March','April','May','June','July','August','September','October','November','December'];
function fmtLong(iso){   // 2026-07-01 -> "Jul 1, 2026"
  const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(iso||'');if(!m)return iso||'';
  return MONTH_NAMES[+m[2]-1].slice(0,3)+' '+(+m[3])+', '+m[1];
}
function monthLabel(key){const m=/^(\d{4})-(\d{2})/.exec(key||'');return m?MONTH_NAMES[+m[2]-1]+' '+m[1]:key;}
function prevMonth(key){let y=+key.slice(0,4),m=+key.slice(5,7)-1;if(m<1){m=12;y--;}return y+'-'+String(m).padStart(2,'0');}
function isoMinusDays(iso,n){const d=new Date(iso+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-n);return d.toISOString().slice(0,10);}

// ---------------------------------------------------------------------------
// Dataset-derived facts. Everything here is computed from ART at load, never typed
// in, so it stays true as the corpus grows.
// ---------------------------------------------------------------------------
const LASTRUN=(D.last_run_date||'').slice(0,10)||new Date().toISOString().slice(0,10);
const CUR_MONTH=LASTRUN.slice(0,7);
const TOPIC_ORDER=['Diabetes','Growth','Puberty','Thyroid','Adrenal','Obesity/Metabolic','Bone/Mineral','Pituitary',
  'Hyperinsulinism','PCOS','Genetics','DSD','Gender Medicine','Cancer Late Effects','Lipids','General Endocrinology'];
const TOPIC_SET=new Set(ART.map(a=>a.topic));
const TOPICS=TOPIC_ORDER.filter(t=>TOPIC_SET.has(t)).concat([...TOPIC_SET].filter(t=>!TOPIC_ORDER.includes(t)).sort());

// Coverage floor: the earliest month from which every complete month holds at least
// half the median of the last six complete months. Walks calendar months (a month
// with no articles counts as zero, it does not get skipped).
const MC={};ART.forEach(a=>{const k=(a.pub_date||'').slice(0,7);if(k)MC[k]=(MC[k]||0)+1;});
const COV=(function(){
  const recent=[];let k=prevMonth(CUR_MONTH);
  for(let i=0;i<6;i++){recent.push(MC[k]||0);k=prevMonth(k);}
  recent.sort((a,b)=>a-b);
  const med=(recent[2]+recent[3])/2, thr=med/2;
  let floor=null;k=prevMonth(CUR_MONTH);
  for(let i=0;i<240;i++){if((MC[k]||0)>=thr){floor=k;k=prevMonth(k);}else break;}
  if(!floor)return null;
  let sum=0,n=0;for(k=floor;k<CUR_MONTH;){sum+=MC[k]||0;n++;const y=+k.slice(0,4),m=+k.slice(5,7);k=m===12?(y+1)+'-01':y+'-'+String(m+1).padStart(2,'0');}
  const date=floor+'-01';
  const pre=ART.filter(a=>(a.pub_date||'')<date);
  return {floor,date,label:monthLabel(floor),avg:Math.round(sum/Math.max(1,n)),
          pre:pre.length,preGuidelines:pre.filter(a=>a.study_type==='Guideline/Consensus').length};
})();

// The same impact_rationale text appears verbatim on every guideline. Text that repeats
// that often carries no information about THIS article, so it is not shown.
const RAT_COUNT=new Map();
ART.forEach(a=>{if(a.impact_rationale)RAT_COUNT.set(a.impact_rationale,(RAT_COUNT.get(a.impact_rationale)||0)+1);});

// A bottom line is only fit to be a headline if it reads as a takeaway. Weak ones
// (empty, placeholder, a fragment, cut off mid-sentence, or just the abstract's
// opening words) fall back to the title rather than showing broken text at 18px.
// This is a stopgap for the real fix, generating proper bottom lines (PLAN_bottom_lines.md).
const _norm=s=>(s||'').toLowerCase().replace(/\s+/g,' ').trim();
function blInfo(a){
  if(a._bl)return a._bl;
  const bl=(a.clinical_bottom_line||'').trim();
  let weak=null;
  if(!bl)weak='empty';
  else if(/^\[/.test(bl))weak='placeholder';
  else if(bl.length<25)weak='short';
  else if(!/[.!?)"'”’%]$/.test(bl))weak='truncated';
  else if(/^(furthermore|moreover|additionally|notably|however|thus|therefore|in addition|also)\b/i.test(bl))weak='fragment';   // starts mid-argument, so it cannot stand alone
  else if(a.abstract){const b=_norm(bl),ab=_norm(a.abstract),n=Math.min(60,b.length);
    if(n>=25&&ab.startsWith(b.slice(0,n)))weak='extractive';}
  return (a._bl={text:bl,weak:weak});
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const state={topic:null,q:'',since:'',flags:new Set(),dm:'All',age:'All'};
const defaultCollapsed=()=>({'PRACTICE-ALTERING':false,'HIGH':false,'MODERATE':false,'LOW':true});
let collapsed=defaultCollapsed();
const openCards=new Set();
// Abstracts need their own state Set for the same reason cards do: without it,
// any re-render silently re-collapses every abstract the reader had opened.
const openAbstracts=new Set();
const PAGE=50, shownN={};      // rows rendered per tier before "Show more"
let viewNow='home';

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
  if(state.since&&(a.pub_date||'')<state.since)return false;
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

// ---------------------------------------------------------------------------
// Coverage notice. Adapts to what was asked: a date earlier than the corpus goes
// gets a statement of what the answer can and cannot see, before any articles.
// ---------------------------------------------------------------------------
function coverageHTML(since,topic){
  if(!COV)return '';
  if(since&&since<COV.date){
    const n=ART.filter(a=>a.pub_date>=since&&a.pub_date<COV.date&&(!topic||a.topic===topic)).length;
    return `<div class="coverage warn"><b>Coverage is thin before ${esc(COV.label)}.</b> From ${esc(fmtLong(since))} to then, the site holds ${n} ${topic?esc(topic)+' ':''}article${n===1?'':'s'}, against about ${COV.avg} a month since. Read the results as what we have, not everything published.</div>`;
  }
  return `<div class="coverage">Steady monthly coverage starts in ${esc(COV.label)}, at about ${COV.avg} articles a month. Before that the site holds ${COV.pre} articles in all (${COV.preGuidelines} of them guidelines), so an earlier start date returns a sample.</div>`;
}

// ---------------------------------------------------------------------------
// Landing: catch-up sentence + one tile per topic
// ---------------------------------------------------------------------------
function sparkSVG(topic){
  const keys=[];let k=CUR_MONTH;for(let i=0;i<12;i++){keys.unshift(k);k=prevMonth(k);}
  const c=keys.map(m=>ART.filter(a=>a.topic===topic&&(a.pub_date||'').slice(0,7)===m).length);
  const mx=Math.max(1,...c);
  const bars=c.map((v,i)=>{const h=v?Math.max(2,Math.round(v/mx*20)):1;
    return `<rect x="${i*6}" y="${22-h}" width="4" height="${h}" rx="1" fill="currentColor"${i===11?' opacity=".45"':''}/>`;}).join('');
  return `<svg class="spark" width="70" height="22" viewBox="0 0 70 22" role="img" aria-label="${esc(topic)} articles per month, ${esc(monthLabel(keys[0]))} to ${esc(monthLabel(keys[11]))}">${bars}</svg>`;
}
function renderHome(){
  const jr=new Set(ART.map(a=>a.journal_abbr||a.journal)).size;
  document.getElementById('statline').textContent=
    `${ART.length.toLocaleString()} articles from ${jr} journals. Updated ${fmtLong(LASTRUN)}.`;
  document.getElementById('grid').innerHTML=TOPICS.map(t=>{
    const arts=ART.filter(a=>a.topic===t);
    const fresh=arts.filter(a=>a.is_new);
    const lead=(fresh.length?fresh:arts)[0];     // ART is already ranked: impact tier, then newest
    const b=blInfo(lead);
    const rule=TIER_BY_KEY[lead.impact]?TIER_BY_KEY[lead.impact].dot:'var(--line)';
    return `<a class="tile" href="#/t/${encodeURIComponent(t)}" style="--rule:${rule}">
      <div class="t-head"><span class="t-name">${esc(t)}</span>${sparkSVG(t)}</div>
      <div class="t-new${fresh.length?'':' none'}">${fresh.length?fresh.length+' new this week':'Nothing new this week'}</div>
      <p class="t-lead">${esc(b.weak?lead.title:b.text)}</p>
      <div class="t-foot">${arts.length.toLocaleString()} article${arts.length===1?'':'s'}</div>
    </a>`;}).join('');
  updateCatchNote();
}
function catchTopic(){return document.getElementById('c-topic').value;}
function updateCatchNote(){
  document.getElementById('c-note').innerHTML=coverageHTML(document.getElementById('c-since').value,catchTopic());
}
(function initCatch(){
  const sel=document.getElementById('c-topic');
  sel.innerHTML='<option value="">any topic</option>'+TOPICS.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join('');
  const dt=document.getElementById('c-since');
  dt.max=LASTRUN;dt.value=isoMinusDays(LASTRUN,7);
  sel.addEventListener('change',updateCatchNote);
  dt.addEventListener('input',updateCatchNote);
  document.getElementById('c-go').addEventListener('click',()=>{
    const t=sel.value, s=dt.value;
    const qs=s?'?since='+encodeURIComponent(s):'';
    location.hash=(t?'#/t/'+encodeURIComponent(t):'#/all')+qs;
  });
})();

// ---------------------------------------------------------------------------
// Article row
// ---------------------------------------------------------------------------
function absText(a){
  return `<div class="abshead">ABSTRACT</div><div class="abstext">${esc(a.abstract)}</div>`;
}

function cardHTML(a,opt){
  opt=opt||{};
  const open=openCards.has(a.pmid);
  const b=blInfo(a);
  const sub=a.subtopic?` · <span class="subt">${esc(a.subtopic)}</span>`:'';
  const tags=(a.tags||[]).slice(0,8).map(t=>`<span class="tag">${esc(t)}</span>`).join('');
  const soc=(a.society&&a.society.length)?`<span class="tag">${a.society.map(esc).join(', ')}</span>`:'';
  const hasAbs=(a.abstract||'').trim().length>=40;
  // NB: no id= on the abstract body. The same card can be rendered twice (a topic
  // list and the Saved list), and duplicate ids would make one copy toggle the other.
  const absOpen=openAbstracts.has(a.pmid);
  // Abstract text is only put in the DOM once opened: it is the largest text on a
  // card and was most of the page's node count for content hidden by default.
  const ab  = hasAbs
    ? `<div class="abswrap"><button class="absbtn" data-abs="${a.pmid}">${absOpen?'Hide abstract':'Show abstract'}</button>
         <div class="absbody" style="display:${absOpen?'block':'none'}">${absOpen?absText(a):''}</div></div>`
    : `<div class="abswrap"><div class="abshead">ABSTRACT</div><div class="abstext none">Abstract not available in PubMed for this record.</div></div>`;
  const doi=a.doi_url?`<a href="${esc(a.doi_url)}" target="_blank" rel="noopener">Full Text &#8599;</a>`:'';
  const pm=a.url?`<a href="${esc(a.url)}" target="_blank" rel="noopener">PubMed &#8599;</a>`:'';
  const isNew=isNewToMe(a)?`<span title="New since your last visit" style="color:var(--accent)">&#10022; </span>`:'';
  const t=TIER_BY_KEY[a.impact];
  const tier=(opt.tier&&t)?`<span class="tierpill gname ${t.cls}">${t.label}</span> · `:'';
  // The note box only appears for articles this person has actually saved —
  // showing it on every card would be noise, and there is nothing to attach
  // a note to until a save row exists.
  const noteBox=(AUTH_ON&&USER&&savedPmids.has(a.pmid))
    ? `<div class="notewrap"><label class="notelbl">Your note</label>
         <textarea class="notebox" data-note="${esc(a.pmid)}" rows="2"
           placeholder="Why did you save this? (only you can see it)">${esc(noteFor(a.pmid))}</textarea>
         <span class="notestat" data-notestat="${esc(a.pmid)}"></span></div>`
    : '';
  // A bottom line over ~170 characters is a paragraph, not a headline: lead with its
  // first sentence and keep the remainder for when the row is opened.
  let headTxt=b.text, rest='';
  if(!b.weak&&b.text.length>170){
    const m=/^(.{25,}?[.!?])\s+(?=[A-Z])/.exec(b.text);
    if(m){headTxt=m[1];rest=b.text.slice(m[0].length);}
  }
  const why=(a.impact_rationale&&RAT_COUNT.get(a.impact_rationale)<5)
    ? `<div class="why">${esc(a.impact_rationale)}</div>`:'';
  const head=b.weak
    ? `<h3 class="bl-head is-title">${isNew}${esc(a.title)}</h3>`
    : `<h3 class="bl-head">${isNew}${esc(headTxt)}</h3><div class="ctitle">${esc(a.title)}</div>`;
  return `<div class="card${open?' open':''}" data-pmid="${a.pmid}">
    <div class="chead" data-card="${a.pmid}" role="button" tabindex="0" aria-expanded="${open}">
      <div class="cmain">
        ${head}
        <div class="cmeta">${tier}${[`<em>${esc(a.journal_abbr||a.journal)}</em>`,fmtDate(a.pub_date,a.pub_date_precision),esc(authorStr(a)),esc(a.study_type)].filter(Boolean).join(' · ')}${sub}</div>
      </div>
      <div class="cact">
        ${AUTH_ON?`<button type="button" class="savebtn" data-save="${esc(a.pmid)}"></button>`:''}
        <span class="cchev" aria-hidden="true">&#9656;</span>
      </div>
    </div>
    <div class="cbody">
      ${rest?`<p class="blrest">${esc(rest)}</p>`:''}
      ${why}
      <div class="tags">${soc}${tags}</div>
      ${noteBox}
      ${ab}
      <div class="links">${pm}${doi}<span class="pmid">PMID: ${esc(a.pmid)}</span>
        <button type="button" class="citebtn" data-cite="${esc(a.pmid)}">Copy citation</button></div>
    </div>
  </div>`;
}

// ---------------------------------------------------------------------------
// Queue: tier groups, ranked impact first then newest (ART is pre-sorted)
// ---------------------------------------------------------------------------
function rowsHTML(tierKey,items){
  const n=shownN[tierKey]||PAGE;
  const rest=items.length-n;
  return items.slice(0,n).map(a=>cardHTML(a)).join('')
    +(rest>0?`<button type="button" class="morebtn" data-more="${tierKey}">Show ${Math.min(PAGE,rest)} more (${rest} not shown)</button>`:'');
}
function queueTitle(){
  if(viewNow==='search')return state.q?`Search: ${state.q}`:'Search';
  return state.topic||'All topics';
}
function renderQueue(){
  const shown=ART.filter(matches);
  const fresh=shown.filter(a=>a.is_new).length;
  let sub=`${shown.length.toLocaleString()} article${shown.length===1?'':'s'}`;
  if(state.since)sub+=`, published since ${fmtLong(state.since)}`;
  if(fresh)sub+=`. ${fresh} added this week`;
  document.getElementById('qhead').innerHTML=
    `<a class="back" href="#/">&#8249; All topics</a>
     <h1 class="qtitle">${esc(queueTitle())}</h1>
     <div class="qsub">${sub}</div>
     ${(viewNow==='search')?'':coverageHTML(state.since,state.topic)}`;
  const root=document.getElementById('groups');
  if(!shown.length){root.innerHTML='<div class="empty">No articles match. Clear a filter or choose an earlier start date.</div>';return;}
  let html='';
  for(const t of TIERS){
    const items=shown.filter(a=>a.impact===t.key);
    if(!items.length)continue;
    const col=collapsed[t.key]?' collapsed':'';
    html+=`<div class="group${col}" data-tier="${t.key}">
      <div class="ghead" data-tier="${t.key}" role="button" tabindex="0">
        <span class="dot" style="background:${t.dot}"></span>
        <span class="gname ${t.cls}">${t.label}</span>
        <span class="gcount">${items.length} article${items.length===1?'':'s'}</span>
        <span class="gchev">&#9662;</span>
      </div>
      <div class="gbody" data-tier="${t.key}">${collapsed[t.key]?'':rowsHTML(t.key,items)}</div>
    </div>`;
  }
  root.innerHTML=html;
  syncSaveButtons();
}
function render(){
  if(viewNow==='queue'||viewNow==='search')renderQueue();
  else if(viewNow==='home')renderHome();
}

// Build a collapsed tier's rows the first time it is opened.
function fillGroup(tierKey,groupEl){
  const body=groupEl.querySelector('.gbody');
  if(!body||body.firstChild)return;
  body.innerHTML=rowsHTML(tierKey,ART.filter(a=>a.impact===tierKey&&matches(a)));
  syncSaveButtons();
}

// event delegation — shared by the topic list and the Saved list
function cardClick(e){
  const sv=e.target.closest('.savebtn');
  if(sv){toggleSave(sv.dataset.save);return;}
  const more=e.target.closest('.morebtn');
  if(more){const k=more.dataset.more;shownN[k]=(shownN[k]||PAGE)+PAGE;
    const body=more.closest('.gbody');
    body.innerHTML=rowsHTML(k,ART.filter(a=>a.impact===k&&matches(a)));
    syncSaveButtons();return;}
  const gh=e.target.closest('.ghead');
  if(gh){const k=gh.dataset.tier;if(!k)return;
    collapsed[k]=!collapsed[k];
    const grp=gh.closest('.group');
    grp.classList.toggle('collapsed',collapsed[k]);
    if(!collapsed[k])fillGroup(k,grp);   // built on first open, not up front
    return;}
  const absBtn=e.target.closest('.absbtn');
  if(absBtn){const p=absBtn.dataset.abs;if(!p)return;
    // Record it in openAbstracts, then apply to every copy of this card.
    const willOpen=!openAbstracts.has(p);
    if(willOpen)openAbstracts.add(p);else openAbstracts.delete(p);
    const art=BY_PMID.get(String(p));
    document.querySelectorAll('.card[data-pmid="'+p+'"]').forEach(c=>{
      const el=c.querySelector('.absbody');const bt=c.querySelector('.absbtn');
      if(el){
        if(willOpen&&!el.firstChild&&art)el.innerHTML=absText(art);  // fill on first open
        el.style.display=willOpen?'block':'none';
      }
      if(bt)bt.textContent=willOpen?'Hide abstract':'Show abstract';});
    return;}
  if(e.target.closest('.links'))return;
  const ch=e.target.closest('.chead');
  if(ch){const p=ch.dataset.card;if(!p)return;
    // An article can be on screen twice (a topic list and Saved). Drive the
    // toggle off this card's own state, then keep every copy of it in step.
    const willOpen=!ch.closest('.card').classList.contains('open');
    if(willOpen)openCards.add(p);else openCards.delete(p);
    document.querySelectorAll('.card[data-pmid="'+p+'"]').forEach(c=>{
      c.classList.toggle('open',willOpen);
      const h=c.querySelector('.chead');if(h)h.setAttribute('aria-expanded',willOpen);});}
}
function cardKey(e){
  if(e.key!=='Enter'&&e.key!==' ')return;
  const el=e.target;
  if(!(el.classList&&(el.classList.contains('chead')||el.classList.contains('ghead'))))return;
  e.preventDefault();cardClick({target:el});
}
['groups','saved-list'].forEach(id=>{
  const el=document.getElementById(id);
  el.addEventListener('click',cardClick);
  el.addEventListener('keydown',cardKey);
});

// ---------------------------------------------------------------------------
// Routing. The hash IS the state, so Back/Forward and shared links work.
//   #/                      landing
//   #/t/<Topic>?since=ISO   topic queue        #/all?since=ISO   every topic
//   #/search?q=text         search all         #/saved   #/analytics
// ---------------------------------------------------------------------------
function parseHash(){
  const h=location.hash.replace(/^#\/?/,'');
  const qi=h.indexOf('?');
  const path=qi<0?h:h.slice(0,qi), qs=qi<0?'':h.slice(qi+1);
  const seg=path.split('/');
  let arg='';try{arg=decodeURIComponent(seg.slice(1).join('/'));}catch(e){arg=seg.slice(1).join('/');}
  return {name:seg[0]||'home',arg,p:new URLSearchParams(qs)};
}
function setParam(k,v){
  const r=parseHash();
  if(v)r.p.set(k,v);else r.p.delete(k);
  const qs=r.p.toString();
  const base=location.hash.replace(/\?.*$/,'')||'#/';
  history.replaceState(null,'',base+(qs?'?'+qs:''));
  route(true);
}
let lastKey=null;
function setView(v){
  viewNow=v;
  const pane={home:'home',queue:'queue',search:'queue',saved:'saved',analytics:'analytics'}[v];
  ['home','queue','saved','analytics'].forEach(k=>{document.getElementById('v-'+k).hidden=(k!==pane);});
  const navFor={home:'home',queue:'home',search:'',saved:'saved',analytics:'analytics'}[v];
  document.querySelectorAll('.nav a').forEach(a=>{
    if(a.dataset.nav===navFor)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
}
function syncTools(){
  document.getElementById('f-since').value=state.since;
  document.getElementById('f-age').value=state.age;
  document.getElementById('f-dm').value=state.dm;
  document.getElementById('f-dm-wrap').hidden=(state.topic!=='Diabetes');
  document.querySelectorAll('#qtools .chip').forEach(c=>c.classList.toggle('on',state.flags.has(c.dataset.flag)));
}
function route(keepScroll){
  const r=parseHash();
  let v='home';
  state.topic=null;state.q='';
  if(r.name==='t'&&TOPIC_SET.has(r.arg)){v='queue';state.topic=r.arg;}
  else if(r.name==='all'){v='queue';}
  else if(r.name==='search'){v='search';state.q=(r.p.get('q')||'').trim();}
  else if(r.name==='saved'){v='saved';}
  else if(r.name==='analytics'){v='analytics';}
  state.since=(v==='queue')?(r.p.get('since')||''):'';
  const key=v+'|'+(state.topic||'')+'|'+state.q;
  if(key!==lastKey){      // a new list starts with clean filters
    state.flags.clear();state.dm='All';state.age='All';
    for(const k in shownN)delete shownN[k];
    collapsed=defaultCollapsed();
    if(v==='search')for(const k in collapsed)collapsed[k]=false;
    lastKey=key;
  }
  setView(v);
  const qbox=document.getElementById('q');
  if(v==='search'){if(document.activeElement!==qbox)qbox.value=state.q;}
  else if(document.activeElement!==qbox)qbox.value='';
  syncTools();
  document.title=(state.topic?state.topic+' · ':v==='saved'?'Saved · ':v==='analytics'?'Analytics · ':'')+'PedsEndoBrief: Pediatric Endocrinology Literature';
  if(v==='home')renderHome();
  else if(v==='queue'||v==='search')renderQueue();
  else if(v==='saved')renderSaved();
  else if(v==='analytics')drawCharts();
  if(!keepScroll)window.scrollTo(0,0);
}
window.addEventListener('hashchange',()=>route());

// Search lives in the header and always searches every article. While typing it
// rewrites the current history entry instead of adding one per keystroke.
let qTimer=null;
document.getElementById('q').addEventListener('input',e=>{
  const val=e.target.value.trim();
  clearTimeout(qTimer);
  qTimer=setTimeout(()=>{
    const onSearch=(viewNow==='search');
    if(!val){if(onSearch)location.hash='#/';return;}
    const h='#/search?q='+encodeURIComponent(val);
    if(onSearch){history.replaceState(null,'',h);route(true);}
    else location.hash=h;
  },200);
});

// queue toolbar
document.querySelectorAll('#qtools .chip[data-flag]').forEach(c=>c.addEventListener('click',()=>{
  const f=c.dataset.flag;
  if(state.flags.has(f))state.flags.delete(f);else state.flags.add(f);
  c.classList.toggle('on',state.flags.has(f));
  for(const k in shownN)delete shownN[k];
  render();
}));
document.getElementById('f-since').addEventListener('change',e=>setParam('since',e.target.value));
document.getElementById('f-age').addEventListener('change',e=>{state.age=e.target.value;for(const k in shownN)delete shownN[k];render();});
document.getElementById('f-dm').addEventListener('change',e=>{state.dm=e.target.value;for(const k in shownN)delete shownN[k];render();});

// ---- Analytics charts ----
function countBy(arr,key){const o={};arr.forEach(a=>{const v=a[key]||'—';o[v]=(o[v]||0)+1});return o;}
// keepOrder: preserve the caller's key order instead of sorting by count. Impact is an
// ORDINAL scale (practice-altering > high > moderate > low); sorting it by count rendered
// it as LOW, MODERATE, PRACTICE-ALTERING, HIGH, which reads as a ranking and isn't one.
// Topic and journal are nominal, so count-sorting them is correct and stays the default.
function distBar(containerId,counts,colorFor,keepOrder){
  const max=Math.max(1,...Object.values(counts));
  const rows=keepOrder?Object.entries(counts):Object.entries(counts).sort((a,b)=>b[1]-a[1]);
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
  },k=>impactDot[k]||'#888780',true);
  distBar('chart-journal',countBy(ART,'journal_abbr'),()=>'#1d9e75');
  chartsDrawn=true;
}

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
        subject:'PedsEndoBrief — bug/comment',
        from_name:'PedsEndoBrief',
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
    host.innerHTML='<div class="empty">No saved articles yet. Click &#9734; Save on any article.</div>';return;}
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
  authView('main');
  amodal.classList.add('show');
  document.getElementById('auth-email').focus();
}
function closeAuth(){amodal.classList.remove('show');}

// ---- modal views: sign-in / password reset / signup confirmation ----
let curView='main';
function authView(v){
  curView=v;
  const main=v==='main';
  document.getElementById('auth-form').style.display=main?'':'none';
  document.getElementById('auth-google').style.display=(main&&GOOGLE_ON)?'':'none';
  document.getElementById('auth-div').style.display=(main&&GOOGLE_ON)?'':'none';
  document.getElementById('auth-intro').style.display=main?'':'none';
  document.getElementById('reset-form').style.display=v==='reset'?'':'none';
  document.getElementById('confirm-form').style.display=v==='confirm'?'':'none';
  document.getElementById('auth-title').textContent=
    v==='reset'?'Reset your password':v==='confirm'?'Confirm your email':'Sign in to PedsEndoBrief';
}

// ---- password reset: email -> 6-digit code -> new password ----
// Deliberately a code, not a magic link: hospital mail scanners pre-click links
// and consume one-time tokens before the reader ever sees the email.
const pwstatus=document.getElementById('reset-status');
function rmsg(t,c){pwstatus.textContent=t;pwstatus.className='msg'+(c?' '+c:'');}
let otpOK=false; // a recovery code is single-use; don't re-verify after a failed password update
function setResetStage(n){
  document.getElementById('reset-stage2').style.display=n===2?'':'none';
  document.getElementById('reset-resend').style.display=n===2?'':'none';
  document.getElementById('reset-email').readOnly=n===2;
  document.getElementById('reset-go').textContent=n===2?'Set new password':'Email me a code';
  document.getElementById('reset-hint').textContent=n===2
    ?'Enter the 6-digit code from the email, then choose a new password.'
    :"Enter your account email and we'll email you a 6-digit code.";
}
function openReset(){
  authView('reset');setResetStage(1);rmsg('');otpOK=false;
  document.getElementById('reset-email').value=document.getElementById('auth-email').value.trim();
  document.getElementById('reset-code').value='';
  document.getElementById('reset-newpass').value='';
  document.getElementById('reset-email').focus();
}
async function sendResetCode(fromResend){
  const em=document.getElementById('reset-email').value.trim();
  if(!em){rmsg('Enter your email address.','err');return;}
  const b=document.getElementById('reset-go');b.disabled=true;
  rmsg('Sending code…');
  try{
    const {error}=await SB.auth.resetPasswordForEmail(em);
    if(error)rmsg(error.message,'err');
    else{
      setResetStage(2);otpOK=false;
      rmsg('If an account exists for that address, a 6-digit code is on its way.','ok');
      if(!fromResend)document.getElementById('reset-code').focus();
    }
  }catch(e){rmsg('Network error — please try again.','err');}
  b.disabled=false;
}
async function submitReset(){
  if(document.getElementById('reset-stage2').style.display==='none'){sendResetCode(false);return;}
  const em=document.getElementById('reset-email').value.trim();
  const code=document.getElementById('reset-code').value.trim();
  const pw=document.getElementById('reset-newpass').value;
  if(!/^\d{6}$/.test(code)){rmsg('Enter the 6-digit code from the email.','err');return;}
  if(pw.length<6){rmsg('Password must be at least 6 characters.','err');return;}
  const b=document.getElementById('reset-go');b.disabled=true;
  rmsg('Checking code…');
  try{
    if(!otpOK){
      const {error}=await SB.auth.verifyOtp({email:em,token:code,type:'recovery'});
      if(error){rmsg('That code is invalid or has expired. Use "Resend code" to get a new one.','err');b.disabled=false;return;}
      otpOK=true;
    }
    const {error:e2}=await SB.auth.updateUser({password:pw});
    if(e2){rmsg('Code accepted, but the password could not be set: '+e2.message,'err');}
    else{
      document.getElementById('reset-code').value='';
      document.getElementById('reset-newpass').value='';
      closeAuth();toast('Password updated. You are signed in.');
    }
  }catch(e){rmsg('Network error — please try again.','err');}
  b.disabled=false;
}

// ---- signup confirmation: 6-digit code (used only while email confirmation is ON) ----
const cstatus=document.getElementById('confirm-status');
function cmsg(t,c){cstatus.textContent=t;cstatus.className='msg'+(c?' '+c:'');}
let confirmEmail='';
function openConfirm(em){
  confirmEmail=em;authView('confirm');cmsg('');
  astatus.textContent='';astatus.className='msg'; // clear the "Creating your account…" left behind on the sign-in view
  document.getElementById('confirm-hint').textContent=
    'We emailed a 6-digit code to '+em+'. Enter it below to activate your account.';
  document.getElementById('confirm-code').value='';
  document.getElementById('confirm-code').focus();
}
async function submitConfirm(){
  const code=document.getElementById('confirm-code').value.trim();
  if(!/^\d{6}$/.test(code)){cmsg('Enter the 6-digit code from the email.','err');return;}
  const b=document.getElementById('confirm-go');b.disabled=true;
  cmsg('Checking code…');
  try{
    const {error}=await SB.auth.verifyOtp({email:confirmEmail,token:code,type:'signup'});
    if(error)cmsg('That code is invalid or has expired. Use "Resend code" to get a new one.','err');
    else{closeAuth();toast('Email confirmed. You are signed in.');}
  }catch(e){cmsg('Network error — please try again.','err');}
  b.disabled=false;
}
async function resendConfirm(){
  cmsg('Sending a new code…');
  try{
    const {error}=await SB.auth.resend({type:'signup',email:confirmEmail});
    cmsg(error?error.message:'New code sent.',error?'err':'ok');
  }catch(e){cmsg('Network error — please try again.','err');}
}

// ---- Sign in with Google ----
// Redirect flow: this page -> Supabase -> Google -> back here with the session in
// the URL hash. supabase-js picks the hash up on load (detectSessionInUrl), so no
// extra handling is needed for the success path — only for errors, below.
async function signInWithGoogle(){
  const b=document.getElementById('auth-google');
  if(!SB)return;
  b.disabled=true;
  astatus.textContent='Redirecting to Google…';astatus.className='msg';
  const {error}=await SB.auth.signInWithOAuth({
    provider:'google',
    // Strip any existing hash so we don't hand Google a URL with tokens in it.
    options:{redirectTo:location.href.split('#')[0]}
  });
  if(error){
    b.disabled=false;
    astatus.textContent='Could not start Google sign-in: '+(error.message||'unknown error');
    astatus.className='msg err';
  }
}

// ---- read the URL hash on load ----
// Both OAuth and (later) password recovery come back through the hash fragment,
// including failures. Without this an error just vanishes and the user sees a
// signed-out page with no explanation.
function consumeAuthHash(){
  const h=location.hash||'';
  if(h.length<2)return null;
  let p;
  try{p=new URLSearchParams(h.slice(1));}catch(e){return null;}
  const err=p.get('error_description')||p.get('error');
  const type=p.get('type');
  if(err){
    // Clear the hash so a refresh doesn't replay the same error.
    history.replaceState(null,'',location.pathname+location.search);
    toast('Sign-in failed: '+decodeURIComponent(err).replace(/\+/g,' '),true);
    return null;
  }
  if(p.get('access_token')){
    // supabase-js has already stored the session; tidy the address bar so tokens
    // aren't left sitting in history or copied out of the URL bar.
    history.replaceState(null,'',location.pathname+location.search);
  }
  return type||null;
}

function updateAuthUI(){
  const btn=document.getElementById('auth-btn'),who=document.getElementById('auth-who');
  if(!AUTH_ON)return;
  btn.style.display='';
  document.getElementById('tab-btn-saved').style.display='';
  // Only reveal the Google button once the provider is actually configured,
  // otherwise clicking it errors with "provider is not enabled". Skip while the
  // modal is on the reset/confirm view — verifyOtp fires an auth event mid-flow
  // and this would un-hide the button underneath that view.
  if(GOOGLE_ON&&curView==='main'){
    document.getElementById('auth-google').style.display='';
    document.getElementById('auth-div').style.display='';
  }
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
      openConfirm(em);
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
  document.getElementById('auth-google').addEventListener('click',signInWithGoogle);
  document.getElementById('auth-forgot').addEventListener('click',openReset);
  document.getElementById('reset-back').addEventListener('click',()=>authView('main'));
  document.getElementById('reset-form').addEventListener('submit',e=>{e.preventDefault();submitReset();});
  document.getElementById('reset-resend').addEventListener('click',()=>sendResetCode(true));
  document.getElementById('confirm-back').addEventListener('click',()=>authView('main'));
  document.getElementById('confirm-form').addEventListener('submit',e=>{e.preventDefault();submitConfirm();});
  document.getElementById('confirm-resend').addEventListener('click',resendConfirm);
  amodal.addEventListener('click',e=>{if(e.target===amodal)closeAuth();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeAuth();});
  // Runs before the session settles, so an OAuth error surfaces instead of the
  // page silently rendering as signed-out.
  consumeAuthHash();
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

route();
</script>
</body>
</html>"""

if __name__ == "__main__":
    build()

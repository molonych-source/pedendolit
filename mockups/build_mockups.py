"""
Build three UI-direction prototypes for the redesign brainstorm (roadmap item B).

These are THROWAWAY. They exist to be reacted to, not shipped. They deliberately
do not touch build_dashboard.py's HTML_TEMPLATE, do not write index.html, and are
not part of the pipeline. Each is a self-contained HTML file using real articles
from the live store so the density and wording are honest.

  1. the-brief.html      — an editorial weekly issue with an archive behind it
  2. triage-queue.html   — an inbox: one stream, unread state, keyboard-driven
  3. topic-catchup.html  — topic grid first, catch-up per topic with a coverage floor

Usage:  python3 mockups/build_mockups.py
"""
import json, os, html, collections, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "..", "pedendolit-data.json")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PALETTE = """
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
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.55;font-size:16px}
a{color:var(--accent)}
.wrap{max-width:760px;margin:0 auto;padding:28px 20px 90px}
.note{background:var(--soft);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:6px;padding:12px 14px;margin:0 0 26px;font-size:13.5px;color:var(--muted)}
.note b{color:var(--ink)}
"""

MOCK_BANNER = """
<div class="note"><b>Mockup — not the real site.</b> Built {when} for the redesign
brainstorm. Real articles, real counts, throwaway code. The point is the shape of the
page, not the pixels. {extra}</div>
"""


def esc(s):
    return html.escape(s or "")


def load():
    store = json.load(open(STORE))
    arts = [a for a in store.get("articles", []) if not a.get("excluded")]
    return store, arts


def bottom_line(a, n=240):
    t = (a.get("clinical_bottom_line") or "").strip()
    t = re.sub(r"\s+", " ", t)
    if len(t) > n:
        t = t[:n].rsplit(" ", 1)[0] + "…"
    return t


ORDER = {"PRACTICE-ALTERING": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}


def rank(arts):
    """Impact tier first, then newest. Only ISO dates sort meaningfully, which is
    itself part of the finding — see the design brief."""
    return sorted(arts, key=lambda a: (ORDER.get(a.get("impact"), 9),
                                       "0" if not ISO.match(str(a.get("pub_date") or ""))
                                       else "1" + str(a.get("pub_date"))), reverse=False)


def recent(arts, since="2026-06-01"):
    """Articles a weekly brief could plausibly lead with. Excludes non-ISO dates
    (they cannot be ordered) and the audit's known-bad future dates."""
    out = []
    for a in arts:
        p = str(a.get("pub_date") or "")
        if ISO.match(p) and since <= p <= "2026-08-06":
            out.append(a)
    return out


def real_bottom_line(a):
    """True where the bottom line is not simply the abstract's opening words."""
    bl = re.sub(r"\s+", " ", (a.get("clinical_bottom_line") or "")).strip()
    ab = re.sub(r"\s+", " ", (a.get("abstract") or "")).strip()
    if not bl or bl.startswith("[Abstract not available]"):
        return False
    return not (ab and ab.startswith(bl.split("...")[0][:50]))


# --------------------------------------------------------------------------
# 1. THE BRIEF — an editorial issue. Opens with a point of view.
# --------------------------------------------------------------------------
def build_brief(store, arts, out):
    pool = [a for a in recent(arts) if real_bottom_line(a)]
    pa = [a for a in pool if a.get("impact") in ("PRACTICE-ALTERING", "HIGH")]
    rest = [a for a in pool if a.get("impact") not in ("PRACTICE-ALTERING", "HIGH")]
    lead = rank(pa)[:5]
    also = rank(rest)[:6]

    items = []
    for i, a in enumerate(lead, 1):
        items.append(f"""
        <article class="lead">
          <div class="num">{i}</div>
          <div>
            <div class="kicker"><span class="dot" style="background:var(--pa-dot)"></span>
              {esc(a.get('topic'))} · {esc(a.get('study_type'))}</div>
            <h2>{esc(a.get('title'))}</h2>
            <p class="bl">{esc(bottom_line(a, 280))}</p>
            <div class="meta">{esc(a.get('journal_abbr'))} · {esc(a.get('pub_date'))}
              · <a href="{esc(a.get('url'))}">PubMed</a></div>
          </div>
        </article>""")

    rows = []
    for a in also:
        rows.append(f"""
        <div class="row">
          <div class="rdot" style="background:var(--high-dot)"></div>
          <div>
            <div class="rt">{esc(a.get('title'))}</div>
            <div class="rb">{esc(bottom_line(a, 150))}</div>
            <div class="meta">{esc(a.get('topic'))} · {esc(a.get('journal_abbr'))}</div>
          </div>
        </div>""")

    css = PALETTE + """
    header.issue{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:8px}
    .eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700}
    header.issue h1{font-size:34px;line-height:1.12;margin:6px 0 6px;letter-spacing:-.02em}
    header.issue .dek{color:var(--muted);font-size:15px;margin:0}
    .standfirst{font-size:18px;line-height:1.5;margin:22px 0 30px;padding-left:14px;
      border-left:3px solid var(--accent)}
    .sec{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
      font-weight:700;margin:34px 0 4px;border-top:1px solid var(--line);padding-top:14px}
    article.lead{display:grid;grid-template-columns:34px 1fr;gap:14px;padding:20px 0;
      border-bottom:1px solid var(--line)}
    .num{font-size:26px;font-weight:700;color:var(--line);line-height:1;padding-top:4px}
    .kicker{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;
      letter-spacing:.06em;display:flex;align-items:center;gap:7px}
    .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
    article.lead h2{font-size:20px;line-height:1.32;margin:7px 0 9px;letter-spacing:-.01em}
    .bl{margin:0 0 9px;font-size:15.5px;color:var(--ink)}
    .meta{font-size:12.5px;color:var(--muted)}
    .row{display:grid;grid-template-columns:9px 1fr;gap:12px;padding:13px 0;
      border-bottom:1px solid var(--line);align-items:start}
    .rdot{width:8px;height:8px;border-radius:50%;margin-top:7px}
    .rt{font-size:15px;font-weight:600;line-height:1.35}
    .rb{font-size:13.5px;color:var(--muted);margin:3px 0 3px}
    .archive{margin-top:40px;background:var(--soft);border:1px solid var(--line);
      border-radius:8px;padding:16px 18px}
    .archive h3{margin:0 0 8px;font-size:14px}
    .archive ul{margin:0;padding-left:18px;font-size:14px;color:var(--muted)}
    .searchlink{margin-top:26px;font-size:14px;color:var(--muted);text-align:center}
    """

    doc = f"""<!doctype html><meta charset="utf-8">
<title>Mockup 1 — The Brief</title><style>{css}</style>
<div class="wrap">
{MOCK_BANNER.format(when="2026-08-05", extra="Dates shown are the stored ones, which the audit found are wrong for ~24% of articles.")}
<header class="issue">
  <div class="eyebrow">PedsEndoBrief · Issue 31</div>
  <h1>What changed in pediatric endocrinology this week</h1>
  <p class="dek">Week of August 4, 2026 · {len(lead)} things worth your time · about 4 minutes</p>
</header>

<p class="standfirst">The page has an opinion: a few items lead, a few more are worth a glance,
and everything else stays in the archive unless you go looking. Nobody constructs a query
to find out what happened this week.</p>

<div class="note" style="border-left-color:var(--mod)"><b>What this mockup exposed.</b>
Across all of June–July 2026 the store holds <b>1</b> Practice-Altering and <b>11</b> High
articles. There is no week with five must-reads in it. Either the brief runs monthly, or it
leads with Moderate too, or it says "quiet week" out loud — but the editorial format promises
a volume of important news the specialty does not actually generate.</div>

<div class="sec">Lead — read these</div>
{''.join(items)}

<div class="sec">Also worth knowing</div>
{''.join(rows)}

<div class="archive">
  <h3>Earlier issues</h3>
  <ul>
    <li>Issue 30 — week of July 28 · 4 lead items</li>
    <li>Issue 29 — week of July 21 · 6 lead items</li>
    <li>Issue 28 — week of July 14 · 3 lead items</li>
  </ul>
</div>

<p class="searchlink">Looking for something specific?
<a href="#">Search all {len(arts):,} articles →</a></p>
</div>"""
    open(out, "w").write(doc)
    return len(lead) + len(also)


# --------------------------------------------------------------------------
# 2. TRIAGE QUEUE — an inbox. Optimized for clearing, not browsing.
# --------------------------------------------------------------------------
def build_queue(store, arts, out):
    pool = [a for a in arts if a.get("clinical_bottom_line")]
    pool = rank(pool)[:24]

    cards = []
    for i, a in enumerate(pool):
        imp = a.get("impact")
        cls = {"PRACTICE-ALTERING": "pa", "HIGH": "high",
               "MODERATE": "mod", "LOW": "low"}.get(imp, "low")
        cards.append(f"""
      <li class="item{' unread' if i < 9 else ''}" data-i="{i}" tabindex="0">
        <div class="bar" style="background:var(--{cls}-dot)"></div>
        <div class="body">
          <div class="bl">{esc(bottom_line(a, 200))}</div>
          <div class="ttl">{esc(a.get('title'))}</div>
          <div class="meta">
            <span class="tier t-{cls}">{esc(imp.title().replace('-',' ') if imp else '')}</span>
            <span>{esc(a.get('topic'))}</span><span>·</span>
            <span>{esc(a.get('journal_abbr'))}</span><span>·</span>
            <span>{esc(a.get('pub_date'))}</span>
          </div>
        </div>
        <div class="acts">
          <button class="act" title="Save">☆</button>
          <button class="act done" title="Mark read">✓</button>
        </div>
      </li>""")

    css = PALETTE + """
    .wrap{max-width:840px}
    header.q{display:flex;justify-content:space-between;align-items:baseline;
      border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:4px}
    header.q h1{font-size:20px;margin:0}
    .count{font-size:13px;color:var(--muted)}
    .hint{font-size:12.5px;color:var(--muted);margin:10px 0 18px}
    kbd{background:var(--soft);border:1px solid var(--line);border-bottom-width:2px;
      border-radius:4px;padding:1px 6px;font-size:11.5px;font-family:inherit}
    ul.queue{list-style:none;margin:0;padding:0}
    li.item{display:grid;grid-template-columns:4px 1fr auto;gap:14px;align-items:start;
      background:var(--surface);border:1px solid var(--line);border-radius:8px;
      padding:14px 14px 13px 0;margin-bottom:8px;overflow:hidden;outline:none}
    li.item:focus{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-bg)}
    li.item.read{opacity:.45}
    .bar{align-self:stretch;border-radius:0}
    .bl{font-size:15.5px;line-height:1.45;margin-bottom:5px}
    li.item.unread .bl{font-weight:600}
    .ttl{font-size:13px;color:var(--muted);line-height:1.4;margin-bottom:6px}
    .meta{font-size:12px;color:var(--muted);display:flex;gap:6px;flex-wrap:wrap;align-items:center}
    .tier{font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
      padding:2px 7px;border-radius:99px;margin-right:2px}
    .t-pa{background:var(--pa-bg);color:var(--pa)} .t-high{background:var(--high-bg);color:var(--high)}
    .t-mod{background:var(--mod-bg);color:var(--mod)} .t-low{background:var(--low-bg);color:var(--low)}
    .acts{display:flex;gap:4px;padding-top:2px}
    .act{background:none;border:1px solid var(--line);border-radius:6px;width:32px;height:32px;
      cursor:pointer;color:var(--muted);font-size:15px;line-height:1}
    .act:hover{border-color:var(--accent);color:var(--accent)}
    .done.on{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
    """

    js = """
    const items=[...document.querySelectorAll('.item')];
    let cur=0;
    function focus(i){cur=Math.max(0,Math.min(items.length-1,i));items[cur].focus();
      items[cur].scrollIntoView({block:'nearest'});}
    function toggleRead(el){el.classList.toggle('read');el.classList.remove('unread');
      el.querySelector('.done').classList.toggle('on');tally();}
    function tally(){document.getElementById('n').textContent=
      document.querySelectorAll('.item:not(.read)').length;}
    document.addEventListener('keydown',e=>{
      if(e.key==='j'){focus(cur+1);e.preventDefault();}
      if(e.key==='k'){focus(cur-1);e.preventDefault();}
      if(e.key==='e'||e.key==='Enter'){toggleRead(items[cur]);e.preventDefault();}
    });
    items.forEach((el,i)=>{el.addEventListener('click',ev=>{
      if(ev.target.closest('.done')){toggleRead(el);}
      cur=i;});});
    tally(); focus(0);
    """

    doc = f"""<!doctype html><meta charset="utf-8">
<title>Mockup 2 — Triage queue</title><style>{css}</style>
<div class="wrap">
{MOCK_BANNER.format(when="2026-08-05", extra="Keyboard works: try it.")}
<header class="q">
  <h1>Your queue</h1>
  <div class="count"><b id="n">0</b> unread · {len(arts):,} in archive</div>
</header>
<p class="hint"><kbd>j</kbd> / <kbd>k</kbd> to move · <kbd>e</kbd> to mark read ·
  ☆ to save. The bottom line is the headline; the paper's title is secondary.</p>
<ul class="queue">{''.join(cards)}</ul>
</div>
<script>{js}</script>"""
    open(out, "w").write(doc)
    return len(pool)


# --------------------------------------------------------------------------
# 3. TOPIC CATCH-UP — topic grid first; coverage floor stated up front.
# --------------------------------------------------------------------------
def build_catchup(store, arts, out):
    by_topic = collections.Counter(a.get("topic") for a in arts)
    # "since your last visit" is faked here at a plausible 2 weeks
    recent = collections.Counter(
        a.get("topic") for a in arts
        if ISO.match(str(a.get("pub_date") or "")) and str(a.get("pub_date")) >= "2026-07-01")

    tiles = []
    for topic, total in by_topic.most_common():
        n = recent.get(topic, 0)
        head = next((a for a in rank([x for x in arts if x.get("topic") == topic
                                      and x.get("clinical_bottom_line")])), None)
        tiles.append(f"""
      <button class="tile{' hot' if n else ''}">
        <div class="th">{esc(topic)}</div>
        <div class="tn">{'<b>'+str(n)+'</b> new' if n else '<span class=q>nothing new</span>'}
          <span class="tt">{total} total</span></div>
        <div class="tl">{esc(bottom_line(head, 95)) if head else ''}</div>
      </button>""")

    css = PALETTE + """
    .wrap{max-width:900px}
    header.c h1{font-size:24px;margin:0 0 4px}
    header.c .dek{color:var(--muted);font-size:14px;margin:0 0 4px}
    .floor{background:var(--mod-bg);border:1px solid var(--line);border-left:3px solid var(--mod);
      border-radius:6px;padding:12px 14px;margin:20px 0 26px;font-size:13.5px}
    .floor b{color:var(--mod)}
    .ask{display:flex;gap:8px;align-items:center;flex-wrap:wrap;background:var(--surface);
      border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:8px;font-size:15px}
    .ask select,.ask input{font:inherit;font-size:14px;padding:6px 9px;border-radius:6px;
      border:1px solid var(--line);background:var(--bg);color:var(--ink)}
    .ask button{font:inherit;font-size:14px;padding:7px 16px;border-radius:6px;border:1px solid var(--accent);
      background:var(--accent);color:#fff;cursor:pointer;font-weight:600}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-top:26px}
    .tile{text-align:left;background:var(--surface);border:1px solid var(--line);border-radius:10px;
      padding:13px 14px;cursor:pointer;font:inherit;color:inherit;transition:border-color .12s}
    .tile:hover{border-color:var(--accent)}
    .tile.hot{border-left:3px solid var(--accent)}
    .th{font-size:14.5px;font-weight:650;margin-bottom:3px}
    .tn{font-size:12.5px;color:var(--muted);margin-bottom:7px}
    .tn b{color:var(--accent);font-size:14px}
    .q{opacity:.6}
    .tt{float:right}
    .tl{font-size:12.5px;color:var(--muted);line-height:1.4;border-top:1px solid var(--line);padding-top:7px}
    .sec{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);
      font-weight:700;margin:30px 0 0}
    """

    doc = f"""<!doctype html><meta charset="utf-8">
<title>Mockup 3 — Topic catch-up</title><style>{css}</style>
<div class="wrap">
{MOCK_BANNER.format(when="2026-08-05", extra="")}
<header class="c">
  <h1>Catch me up</h1>
  <p class="dek">Pick a topic and a date. The answer states what it can and cannot see.</p>
</header>

<div class="ask">
  <span>What's new in</span>
  <select><option>Diabetes</option><option>Thyroid</option><option>Growth</option>
    <option>every topic</option></select>
  <span>since</span>
  <input type="date" value="2026-07-01">
  <button>Show me</button>
</div>

<div class="floor"><b>Coverage floor.</b> Dense coverage begins <b>January 2026</b>.
2025 holds about 118 articles and thins to 1–9 per month; 2018–2024 is essentially
guidelines only. Ask for "since March 2025" and you will get an honest but thin answer,
and this box will say so rather than letting three papers look like the whole story.</div>

<div class="sec">Or browse by topic</div>
<div class="grid">{''.join(tiles)}</div>
</div>"""
    open(out, "w").write(doc)
    return len(by_topic)


def main():
    store, arts = load()
    n1 = build_brief(store, arts, os.path.join(HERE, "the-brief.html"))
    n2 = build_queue(store, arts, os.path.join(HERE, "triage-queue.html"))
    n3 = build_catchup(store, arts, os.path.join(HERE, "topic-catchup.html"))
    print(f"the-brief.html      {n1} articles shown")
    print(f"triage-queue.html   {n2} articles shown")
    print(f"topic-catchup.html  {n3} topic tiles")
    print(f"(from {len(arts)} live articles; nothing in the pipeline was touched)")


if __name__ == "__main__":
    main()

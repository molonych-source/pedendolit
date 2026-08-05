"""
Build the guideline approval page.

Reads the sweep's candidates plus the review agent's verdicts and writes a single
self-contained HTML file: checkboxes, the agent's reasoning per article, and a
Submit button that downloads approved_pmids.json.

Same shape as build_dashboard.py — pure stdlib, no network, data embedded, opens by
double-click. The page never writes to the store; apply_approvals.py does that from
the downloaded file.

Usage:
  python3 build_review_page.py [--candidates guideline_candidates.json]
                               [--verdicts guideline_verdicts.json]
                               [--out guideline_review.html]
"""
import json, os, argparse, html, importlib.util, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


classifier = _load("classifier", "classifier.py")
dataset = _load("build_dataset", "build_dataset.py")

# MeSH headings are curated by NLM, which makes them far better specialty evidence
# than free-text matching. They are shown to corroborate the agent's verdict — they
# never decide it. (classifier.py ignores MeSH entirely.)
ENDO_MESH = (
    "diabetes", "insulin", "thyroid", "adrenal", "puberty", "growth hormone",
    "pituitary", "gonad", "testosterone", "estrogen", "androgen", "hypoglycemia",
    "obesity", "body mass index", "calcium", "parathyroid", "vitamin d", "bone density",
    "hyperplasia, congenital adrenal", "sex development", "endocrine", "hormone",
    "metabolic syndrome", "lipid", "cholesterol", "glucose", "somatotropin",
    "polycystic ovary", "menarche", "amenorrhea", "gender", "hyperinsulinism",
)
PEDS_MESH = ("child", "adolescent", "infant", "pediatr", "puberty", "neonat", "young adult")

BADGE = {"accept": ("Recommended", "ok"),
         "borderline": ("Your call", "mid"),
         "reject": ("Not relevant", "no")}


def mesh_evidence(mesh):
    endo = [m for m in mesh if any(k in m.lower() for k in ENDO_MESH)]
    peds = [m for m in mesh if any(k in m.lower() for k in PEDS_MESH)]
    return endo[:4], peds[:3]


CSS = """
:root{
  --bg:#faf9f5; --surface:#ffffff; --ink:#1f1e1c; --muted:#6b6a64; --line:#e6e4dc; --soft:#f4f2ec;
  --accent:#0f6e56; --accent-bg:#e1f5ee; --ok:#0f6e56; --mid:#b8791f; --no:#9a5c4a;
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#1a1916; --surface:#26241f; --ink:#ece9e1; --muted:#a3a098; --line:#3a382f; --soft:#2c2a25;
         --accent:#5dcaa5; --accent-bg:#0f3a30; --ok:#5dcaa5; --mid:#e0b060; --no:#f0997b;}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.5;font-size:15px}
.wrap{max-width:1100px;margin:0 auto;padding:28px 20px 120px}
h1{font-size:24px;margin:0 0 4px}
.sub{color:var(--muted);font-size:14px;margin-bottom:22px}
.sec{margin:26px 0 10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.sec h2{font-size:16px;margin:0}
.count{color:var(--muted);font-size:13px}
.mini{background:none;border:0;padding:0;color:var(--muted);font-size:12px;text-decoration:underline;cursor:pointer}
.mini:hover{color:var(--ink)}
.card{background:var(--surface);border:0.5px solid var(--line);border-radius:10px;
  padding:13px 15px;margin-bottom:9px;display:flex;gap:12px;align-items:flex-start}
.card.on{border-color:var(--accent);background:var(--accent-bg)}
.card input[type=checkbox]{margin-top:3px;width:17px;height:17px;flex:none;cursor:pointer;accent-color:var(--accent)}
.body{min-width:0;flex:1}
.title{font-weight:600;margin-bottom:3px}
.title a{color:inherit;text-decoration:none}
.title a:hover{text-decoration:underline}
.meta{color:var(--muted);font-size:12.5px;margin-bottom:7px}
.reason{font-size:13.5px;padding:7px 10px;border-left:2.5px solid var(--line);background:var(--soft);border-radius:0 6px 6px 0}
.reason .who{font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);display:block;margin-bottom:2px}
.ev{font-size:12px;color:var(--muted);margin-top:6px}
.ev code{background:var(--soft);border-radius:4px;padding:1px 5px;font-size:11.5px}
.badge{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:2px 8px;
  border-radius:20px;border:1px solid currentColor;white-space:nowrap}
.badge.ok{color:var(--ok)} .badge.mid{color:var(--mid)} .badge.no{color:var(--no)}
details.abs{margin-top:7px}
details.abs summary{cursor:pointer;font-size:12.5px;color:var(--muted)}
details.abs p{font-size:13.5px;margin:7px 0 0;color:var(--ink)}
details.grp>summary{cursor:pointer;color:var(--muted);font-size:13px;margin-bottom:10px}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:0.5px solid var(--line);
  padding:13px 20px;display:flex;align-items:center;gap:14px;justify-content:center;flex-wrap:wrap}
.bar b{font-size:15px}
button.go{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:10px 22px;
  font:inherit;font-size:15px;font-weight:600;cursor:pointer}
button.go:hover{opacity:.92}
button.alt{background:var(--surface);color:var(--ink);border:0.5px solid var(--line);
  border-radius:8px;padding:10px 16px;font:inherit;cursor:pointer}
.done{color:var(--accent);font-size:13.5px}
"""


def card_html(c):
    a, v = c["art"], c["verdict"]
    label, cls = BADGE.get(v["verdict"], ("?", "mid"))
    endo, peds = mesh_evidence(a.get("mesh_terms") or [])
    ev = []
    if endo:
        ev.append("endocrine MeSH: " + " ".join(f"<code>{html.escape(m)}</code>" for m in endo))
    if peds:
        ev.append("pediatric MeSH: " + " ".join(f"<code>{html.escape(m)}</code>" for m in peds))
    if c["monitored"]:
        ev.append("journal is already monitored")
    bits = [
        f'<div class="title"><a href="{html.escape(a.get("url") or "")}" target="_blank" '
        f'rel="noopener">{html.escape(a.get("title") or "")}</a></div>',
        f'<div class="meta">{html.escape(a.get("journal_abbr") or "")} · '
        f'{html.escape(a.get("pub_date") or "")} · PMID {html.escape(str(a.get("pmid")))} · '
        f'classifier: {html.escape(a.get("study_type") or "")} / {html.escape(a.get("topic") or "")}</div>',
        f'<div class="reason"><span class="who">Review agent · {html.escape(v.get("confidence","") )} confidence</span>'
        f'{html.escape(v.get("reason") or "")}</div>',
    ]
    if ev:
        bits.append(f'<div class="ev">{" &nbsp;·&nbsp; ".join(ev)}</div>')
    if a.get("abstract"):
        bits.append('<details class="abs"><summary>Abstract</summary><p>'
                    + html.escape(a["abstract"][:1600]) + '</p></details>')
    checked = " checked" if v["verdict"] == "accept" else ""
    return (f'<label class="card{" on" if checked else ""}">'
            f'<input type="checkbox" value="{html.escape(str(a.get("pmid")))}"{checked}>'
            f'<div class="body">{"".join(bits)}</div>'
            f'<span class="badge {cls}">{label}</span></label>')


def section(title, blurb, cards, collapsed=False):
    if not cards:
        return ""
    head = (f'<div class="sec"><h2>{html.escape(title)}</h2>'
            f'<span class="count">{len(cards)} · {html.escape(blurb)}</span>'
            f'<button type="button" class="mini" data-all>select all</button>'
            f'<button type="button" class="mini" data-none>select none</button></div>')
    body = "".join(cards)
    if collapsed:
        return (f'{head}<details class="grp"><summary>show {len(cards)} '
                f'(you can still tick any of these)</summary>{body}</details>')
    return head + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="guideline_candidates.json")
    ap.add_argument("--verdicts", default="guideline_verdicts.json")
    ap.add_argument("--out", default="guideline_review.html")
    args = ap.parse_args()

    cands = json.load(open(os.path.join(HERE, args.candidates)))
    verdicts = json.load(open(os.path.join(HERE, args.verdicts))).get("verdicts", {})
    monitored = set(j["abbr"] for j in
                    json.load(open(os.path.join(HERE, "journals.json")))["journals"])

    rows = []
    missing = []
    for rec in cands:
        art = dataset.map_raw(rec)
        pmid = str(art.get("pmid"))
        res = classifier.classify(art)
        art = {**art, **({} if res.get("excluded") else res)}
        v = verdicts.get(pmid)
        if not v:
            missing.append(pmid)
            v = {"verdict": "borderline", "confidence": "low",
                 "reason": "No agent verdict for this article — review it manually."}
        rows.append({"art": art, "verdict": v,
                     "monitored": art.get("journal_abbr") in monitored,
                     "mesh": rec.get("mesh_terms") or []})

    for r in rows:
        r["art"]["mesh_terms"] = r["mesh"]

    acc = [card_html(r) for r in rows if r["verdict"]["verdict"] == "accept"]
    bor = [card_html(r) for r in rows if r["verdict"]["verdict"] == "borderline"]
    rej = [card_html(r) for r in rows if r["verdict"]["verdict"] == "reject"]

    built = datetime.date.today().isoformat()
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PedsEndoBrief — guideline approvals</title>
<style>{CSS}</style></head><body>
<div class="wrap">
  <h1>Guideline candidates for approval</h1>
  <div class="sub">{len(rows)} guidelines found outside the 19 monitored journals.
  A review agent judged each one against the digest's scope; its reasoning is shown below.
  Tick what belongs, then Submit — that downloads <code>approved_pmids.json</code>. Built {built}.</div>
  <form id="f">
    {section("Recommended", "agent says these are core peds endo — pre-ticked", acc)}
    {section("Needs your call", "endocrine relevance is real but peripheral", bor)}
    {section("Not relevant", "agent says another specialty — tick any you disagree with", rej, collapsed=True)}
  </form>
</div>
<div class="bar">
  <b><span id="n">0</span> selected</b>
  <button type="button" class="go" id="submit">Submit approvals</button>
  <button type="button" class="alt" id="copy">Copy PMIDs</button>
  <span class="done" id="msg"></span>
</div>
<script>
const f=document.getElementById('f'), n=document.getElementById('n'), msg=document.getElementById('msg');
const boxes=()=>[...f.querySelectorAll('input[type=checkbox]')];
const picked=()=>boxes().filter(b=>b.checked).map(b=>b.value);
function sync(){{
  n.textContent=picked().length;
  boxes().forEach(b=>b.closest('.card').classList.toggle('on',b.checked));
}}
f.addEventListener('change',sync);
// select all / none act on the section the button sits in
document.querySelectorAll('[data-all],[data-none]').forEach(btn=>{{
  btn.addEventListener('click',()=>{{
    const on=btn.hasAttribute('data-all');
    let el=btn.closest('.sec').nextElementSibling, hit=[];
    while(el && !el.classList.contains('sec')){{
      hit.push(...el.querySelectorAll('input[type=checkbox]'));
      if(el.matches('input,label')&&el.querySelector) hit.push(...el.querySelectorAll('input'));
      el=el.nextElementSibling;
    }}
    hit.forEach(b=>b.checked=on); sync();
  }});
}});
document.getElementById('submit').addEventListener('click',()=>{{
  const approved=picked();
  const rejected=boxes().filter(b=>!b.checked).map(b=>b.value);
  const blob=new Blob([JSON.stringify({{approved,rejected,
      reviewed_at:new Date().toISOString()}},null,1)],{{type:'application/json'}});
  const u=URL.createObjectURL(blob), a=document.createElement('a');
  a.href=u; a.download='approved_pmids.json'; a.click(); URL.revokeObjectURL(u);
  msg.textContent='Downloaded approved_pmids.json ('+approved.length+' approved) — tell Claude it is ready.';
}});
document.getElementById('copy').addEventListener('click',async()=>{{
  try{{ await navigator.clipboard.writeText(picked().join(' ')); msg.textContent='PMIDs copied.'; }}
  catch(e){{ msg.textContent='Could not copy — use Submit instead.'; }}
}});
sync();
</script></body></html>"""

    out = os.path.join(HERE, args.out)
    open(out, "w").write(page)
    print(f"review page: {len(rows)} candidates "
          f"({len(acc)} recommended, {len(bor)} your call, {len(rej)} not relevant)")
    if missing:
        print(f"  WARNING: no agent verdict for {len(missing)} pmids: {', '.join(missing[:8])}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()

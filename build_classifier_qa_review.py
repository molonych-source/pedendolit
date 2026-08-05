"""
Build the classifier QA review page.

Reads the sample the sweep drew plus the judge's verdicts and writes a single
self-contained HTML file: cards grouped by verdict, a topic dropdown per card
(pre-set to the judge's suggestion), and a Submit button that downloads
classifier_qa_review.json. Same shape as build_review_page.py, with one real
difference — the reviewer's decision carries a TOPIC, not just yes/no, since a
plain checkbox can't capture "the judge said Growth, I think it's Pituitary."

The page never touches classifier.py or the store; apply_classifier_qa.py does
that from the downloaded file.

Usage:
  python3 build_classifier_qa_review.py [--sample classifier_qa_sample.json]
                                        [--verdicts classifier_qa_verdicts.json]
                                        [--out classifier_qa_review.html]
"""
import json, os, argparse, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# The 17-topic taxonomy (MEMORY.md "Taxonomy state") — the fixed option list for
# the per-card topic dropdown, and the set the judge's target_topic must fall in.
TOPICS = (
    "Diabetes", "Growth", "Puberty", "Thyroid", "Adrenal", "Obesity/Metabolic",
    "General Endocrinology", "Bone/Calcium", "Pituitary", "Hyperinsulinism",
    "Genetics", "Calcium/Parathyroid", "DSD", "PCOS", "Gender Medicine",
    "Cancer Late Effects", "Lipids",
)

# Same rationale as build_review_page.py: MeSH is NLM-curated, independent of both
# the classifier and the judge, shown only as corroborating evidence.
ENDO_MESH = (
    "diabetes", "insulin", "thyroid", "adrenal", "puberty", "growth hormone",
    "pituitary", "gonad", "testosterone", "estrogen", "androgen", "hypoglycemia",
    "obesity", "body mass index", "calcium", "parathyroid", "vitamin d", "bone density",
    "hyperplasia, congenital adrenal", "sex development", "endocrine", "hormone",
    "metabolic syndrome", "lipid", "cholesterol", "glucose", "somatotropin",
    "polycystic ovary", "menarche", "amenorrhea", "gender", "hyperinsulinism",
)


def mesh_evidence(mesh):
    return [m for m in mesh if any(k in m.lower() for k in ENDO_MESH)][:4]


BADGE = {"wrong": ("Flagged wrong", "no"),
         "defensible": ("Your call", "mid"),
         "correct": ("Agrees with classifier", "ok")}

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
.grp{margin:14px 0 6px;color:var(--muted);font-size:13px;font-weight:600}
.card{background:var(--surface);border:0.5px solid var(--line);border-radius:10px;
  padding:13px 15px;margin-bottom:9px;display:flex;gap:12px;align-items:flex-start}
.card.changed{border-color:var(--accent);background:var(--accent-bg)}
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
  border-radius:20px;border:1px solid currentColor;white-space:nowrap;flex:none}
.badge.ok{color:var(--ok)} .badge.mid{color:var(--mid)} .badge.no{color:var(--no)}
.pick{margin-top:8px;display:flex;align-items:center;gap:8px}
.pick label{font-size:12px;color:var(--muted)}
.pick select{font:inherit;font-size:13px;padding:4px 8px;border-radius:6px;border:0.5px solid var(--line);
  background:var(--surface);color:var(--ink)}
details.abs{margin-top:7px}
details.abs summary{cursor:pointer;font-size:12.5px;color:var(--muted)}
details.abs p{font-size:13.5px;margin:7px 0 0;color:var(--ink)}
details.tier>summary{cursor:pointer;color:var(--muted);font-size:13px;margin-bottom:10px}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--surface);border-top:0.5px solid var(--line);
  padding:13px 20px;display:flex;align-items:center;gap:14px;justify-content:center;flex-wrap:wrap}
.bar b{font-size:15px}
button.go{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:10px 22px;
  font:inherit;font-size:15px;font-weight:600;cursor:pointer}
button.go:hover{opacity:.92}
.done{color:var(--accent);font-size:13.5px}
"""


def topic_select(pmid, current, suggested):
    opts = []
    for t in ("(keep current)",) + TOPICS:
        val = current if t == "(keep current)" else t
        sel = " selected" if (t == "(keep current)" and suggested == current) or (t == suggested and t != "(keep current)") else ""
        label = f"(keep current: {html.escape(current or '?')})" if t == "(keep current)" else t
        opts.append(f'<option value="{html.escape(val or "")}"{sel}>{html.escape(label)}</option>')
    return (f'<select class="topic-pick" data-pmid="{html.escape(pmid)}" data-current="{html.escape(current or "")}">'
            + "".join(opts) + "</select>")


def card_html(item, verdict, mesh):
    a = item
    v = verdict
    label, cls = BADGE.get(v["verdict"], ("?", "mid"))
    pmid = str(a["pmid"])
    endo = mesh_evidence(mesh)
    ev = []
    if endo:
        ev.append("endocrine MeSH: " + " ".join(f"<code>{html.escape(m)}</code>" for m in endo))
    suggested = v.get("target_topic") or a.get("current_topic")
    bits = [
        f'<div class="title"><a href="{html.escape(a.get("url") or "")}" target="_blank" '
        f'rel="noopener">{html.escape(a.get("title") or "")}</a></div>',
        f'<div class="meta">{html.escape(a.get("journal_abbr") or "")} · '
        f'{html.escape(a.get("pub_date") or "")} · PMID {html.escape(pmid)} · '
        f'current topic: {html.escape(a.get("current_topic") or "")}</div>',
        f'<div class="reason"><span class="who">Review agent · {html.escape(v.get("confidence","") )} confidence</span>'
        f'{html.escape(v.get("reason") or "")}</div>',
    ]
    if ev:
        bits.append(f'<div class="ev">{" &nbsp;·&nbsp; ".join(ev)}</div>')
    if a.get("abstract"):
        bits.append('<details class="abs"><summary>Abstract</summary><p>'
                    + html.escape(a["abstract"][:1600]) + '</p></details>')
    bits.append(f'<div class="pick"><label>Topic:</label>{topic_select(pmid, a.get("current_topic"), suggested)}</div>')
    return (f'<div class="card" data-pmid="{html.escape(pmid)}">'
            f'<div class="body">{"".join(bits)}</div>'
            f'<span class="badge {cls}">{label}</span></div>')


def section(title, blurb, cards, collapsed=False):
    if not cards:
        return ""
    head = (f'<div class="sec"><h2>{html.escape(title)}</h2>'
            f'<span class="count">{len(cards)} · {html.escape(blurb)}</span></div>')
    body = "".join(cards)
    if collapsed:
        return (f'{head}<details class="tier"><summary>show {len(cards)} '
                f'(you can still change any of these)</summary>{body}</details>')
    return head + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="classifier_qa_sample.json")
    ap.add_argument("--verdicts", default="classifier_qa_verdicts.json")
    ap.add_argument("--out", default="classifier_qa_review.html")
    args = ap.parse_args()

    sample = json.load(open(os.path.join(HERE, args.sample)))
    verdicts = json.load(open(os.path.join(HERE, args.verdicts))).get("verdicts", {})
    items_by_pmid = {i["pmid"]: i for i in sample["items"]}

    missing = []
    wrong, defensible, correct = [], [], []
    wrong_groups = {}
    for pmid, item in items_by_pmid.items():
        v = verdicts.get(pmid)
        if not v:
            missing.append(pmid)
            v = {"verdict": "defensible", "confidence": "low",
                 "current_topic": item.get("current_topic"),
                 "target_topic": item.get("current_topic"),
                 "reason": "No agent verdict for this article — review it manually."}
        card = card_html(item, v, item.get("mesh_terms") or [])
        if v["verdict"] == "wrong":
            wrong.append((v.get("confidence", "low"), card))
            key = (v.get("current_topic") or item.get("current_topic"), v.get("target_topic"))
            wrong_groups.setdefault(key, 0)
            wrong_groups[key] += 1
        elif v["verdict"] == "defensible":
            defensible.append(card)
        else:
            correct.append(card)

    conf_rank = {"high": 0, "medium": 1, "low": 2}
    wrong.sort(key=lambda t: conf_rank.get(t[0], 3))
    wrong_cards = [c for _, c in wrong]

    group_blurb = "; ".join(f"{cur} → {tgt} ({n})" for (cur, tgt), n in
                             sorted(wrong_groups.items(), key=lambda kv: -kv[1])) or "no groups"

    built = datetime.date.today().isoformat()
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PedsEndoBrief — classifier QA review</title>
<style>{CSS}</style></head><body>
<div class="wrap">
  <h1>Classifier QA review</h1>
  <div class="sub">{len(items_by_pmid)} articles re-checked against the 17-topic taxonomy.
  A review agent judged whether each article's assigned topic is correct; its reasoning is
  shown below. Change the topic dropdown on any card as needed, then Submit — that downloads
  <code>classifier_qa_review.json</code>. Built {built}.</div>
  {f'<div class="sub"><b>Flagged-wrong groups:</b> {html.escape(group_blurb)}</div>' if wrong_groups else ""}
  <form id="f">
    {section("Flagged wrong", "agent disagrees with the classifier — sorted by confidence", wrong_cards)}
    {section("Defensible", "a genuine taxonomy-boundary call between two reasonable topics", defensible)}
    {section("Agrees with classifier", "spot-check only", correct, collapsed=True)}
  </form>
</div>
<div class="bar">
  <b><span id="n">0</span> changed from current</b>
  <button type="button" class="go" id="submit">Submit review</button>
  <span class="done" id="msg"></span>
</div>
<script>
const f=document.getElementById('f'), n=document.getElementById('n'), msg=document.getElementById('msg');
function selects(){{ return [...f.querySelectorAll('select.topic-pick')]; }}
function sync(){{
  let changed=0;
  selects().forEach(s=>{{
    const isChanged = s.value !== s.dataset.current;
    s.closest('.card').classList.toggle('changed', isChanged);
    if(isChanged) changed++;
  }});
  n.textContent=changed;
}}
f.addEventListener('change', sync);
document.getElementById('submit').addEventListener('click',()=>{{
  const decisions={{}};
  selects().forEach(s=>{{
    const pmid=s.dataset.pmid, current=s.dataset.current, target=s.value;
    decisions[pmid] = {{verdict: target===current ? 'correct' : 'wrong', target_topic: target}};
  }});
  const blob=new Blob([JSON.stringify({{decisions, reviewed_at:new Date().toISOString()}},null,1)],
      {{type:'application/json'}});
  const u=URL.createObjectURL(blob), a=document.createElement('a');
  a.href=u; a.download='classifier_qa_review.json'; a.click(); URL.revokeObjectURL(u);
  msg.textContent='Downloaded classifier_qa_review.json — tell Claude it is ready.';
}});
sync();
</script></body></html>"""

    out = os.path.join(HERE, args.out)
    open(out, "w").write(page)
    print(f"classifier QA review page: {len(items_by_pmid)} articles "
          f"({len(wrong_cards)} wrong, {len(defensible)} defensible, {len(correct)} correct)")
    if missing:
        print(f"  WARNING: no agent verdict for {len(missing)} pmids: {', '.join(missing[:8])}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()

# Bottom-Line Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every article carries a real one-or-two-sentence clinical takeaway, so the redesign can promote that field to headline position without exposing abstract fragments.

**Architecture:** Mirrors the two patterns this repo already uses for corrected data. Generation is done by Sonnet subagents in batches (the pattern from the classifier QA judges); the result is stored in a side file and re-applied on every build by a small function in `build_dataset.py` (the pattern from `pub_dates.json` / `apply_pub_dates()`), so a `--rebuild` cannot silently restore the weak text. `classifier.clinical_bottom_line()` is left untouched — it produces good output on structured abstracts and remains the default.

**Tech Stack:** Python 3 (stdlib only), Sonnet subagents via the Agent tool, plain HTML review page. No new dependencies.

## Global Constraints

- **This repo has no test framework.** No `tests/` directory, no `pytest` installed, no lint or build command. Verification here means: run the script, assert on real counts with a throwaway `python3 -c` check, and inspect the artifact. Do not introduce pytest — it would be the only test in the repo and nothing else would run it.
- **Plans and specs live at the repo root**, alongside `REDESIGN_SPEC.md` and `CLASSIFIER_QA_RUNBOOK.md`. The repo is also the published website, so avoid creating deep doc trees.
- **Never edit generated files.** `index.html` and `PedEndoLit-Dashboard.html` are overwritten on every build.
- **Do not run `build_dataset.py --rebuild` without `--raw comprehensive_raw.json`.** It reads the raw file, not the store; without that flag the store shrinks to one week.
- **Run `check_classifier_regressions.py` after any rebuild and BEFORE committing.** It diffs against `git HEAD`; committing destroys the comparison.
- **Nothing goes live without Christian's review of a sample.** These become the most prominent clinical text on the page.
- Commit messages end with: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `audit_bottom_lines.py` | Detect weak bottom lines mechanically; write `bottom_line_audit.md` and `bottom_line_targets.json` | Create |
| `bottom_lines.json` | The corrected text, keyed by PMID. The durable record. | Create (by task 4) |
| `build_bottom_line_review.py` | Self-contained HTML page for Christian to approve/reject/edit | Create |
| `apply_bottom_lines.py` | Read the reviewed decisions, write `bottom_lines.json` | Create |
| `build_dataset.py` | Add `apply_bottom_lines()`, called on every build | Modify (~line 49, beside `apply_pub_dates`) |
| `classifier.py` | **Unchanged.** `clinical_bottom_line()` stays the default path. | Untouched |

---

### Task 1: Audit — measure the real extent

The 182 figure came from one pattern (bottom line ≈ abstract opening). The spec requires knowing the true number before fixing, because fixing 182 while the problem is larger ships a page that still looks broken in places.

**Files:**
- Create: `audit_bottom_lines.py`
- Reads: `pedendolit-data.json`
- Writes: `bottom_line_audit.md`, `bottom_line_targets.json`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `bottom_line_targets.json` — a JSON list of PMID strings needing regeneration. Task 2 batches exactly this list.
- Produces: `classify_weakness(article) -> (bool, str)` — returns `(is_weak, reason_code)` where `reason_code` is one of `"no_abstract"`, `"placeholder"`, `"too_short"`, `"extractive"`, `"truncated_midsentence"`, or `"ok"`.

- [ ] **Step 1: Write the check script that will fail**

Create `check_audit.py` (throwaway, deleted in step 6):

```python
import json, subprocess, sys
subprocess.run([sys.executable, "audit_bottom_lines.py"], check=True)
targets = json.load(open("bottom_line_targets.json"))
store = json.load(open("pedendolit-data.json"))
by = {str(a["pmid"]): a for a in store["articles"]}

assert isinstance(targets, list), "targets must be a JSON list"
assert all(isinstance(p, str) for p in targets), "PMIDs must be strings"
assert all(p in by for p in targets), "every target must exist in the store"
assert len(targets) >= 182, f"expected at least the 182 known-extractive, got {len(targets)}"
assert len(targets) <= 700, f"{len(targets)} targets is implausibly high — check the rules"

# The 59 articles with no abstract at all must be in the target set:
no_abs = [str(a["pmid"]) for a in store["articles"]
          if not (a.get("abstract") or "").strip() and not a.get("excluded")]
missing = set(no_abs) - set(targets)
assert not missing, f"{len(missing)} abstract-less articles missing from targets"
print(f"PASS — {len(targets)} targets, {len(no_abs)} of them abstract-less")
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
python3 check_audit.py
```

Expected: fails immediately — `audit_bottom_lines.py` does not exist.

- [ ] **Step 3: Write the audit script**

Create `audit_bottom_lines.py`:

```python
"""
Find articles whose clinical_bottom_line is not a real takeaway.

classifier.clinical_bottom_line() is extractive: it looks for a CONCLUSIONS-style
section marker and takes the following sentences, else falls back to the last two
sentences of the abstract. On a structured abstract that works well. On an
unstructured one the fallback can land on the opening sentences, which is how 182
articles ended up with the abstract's first words as their "bottom line".

Read-only. Writes a report and the target list; changes nothing.

Usage: python3 audit_bottom_lines.py [--store pedendolit-data.json]
"""
import json, os, re, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def classify_weakness(a):
    """(is_weak, reason_code). See the module docstring for why each rule exists."""
    bl = _norm(a.get("clinical_bottom_line"))
    ab = _norm(a.get("abstract"))

    if not ab:
        return True, "no_abstract"
    if not bl or bl.startswith("[Abstract not available]"):
        return True, "placeholder"
    if len(bl) < 60:
        return True, "too_short"
    # Extractive: the bottom line is how the abstract begins, so it is background
    # rather than a finding.
    head = bl.split("...")[0][:50]
    if head and ab.startswith(head):
        return True, "extractive"
    # Ends mid-sentence with no terminal punctuation — a truncation, not a sentence.
    if not re.search(r"[.!?]['\")\]]?$", bl):
        return True, "truncated_midsentence"
    return False, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="pedendolit-data.json")
    ap.add_argument("--report", default="bottom_line_audit.md")
    ap.add_argument("--targets", default="bottom_line_targets.json")
    args = ap.parse_args()

    store = json.load(open(os.path.join(HERE, args.store)))
    arts = [a for a in store.get("articles", []) if not a.get("excluded")]

    reasons = collections.Counter()
    targets, examples = [], collections.defaultdict(list)
    for a in arts:
        weak, why = classify_weakness(a)
        reasons[why] += 1
        if weak:
            targets.append(str(a["pmid"]))
            if len(examples[why]) < 5:
                examples[why].append((str(a["pmid"]),
                                      _norm(a.get("title"))[:70],
                                      _norm(a.get("clinical_bottom_line"))[:110]))

    weak_n = len(targets)
    L = ["# Bottom-line audit", "",
         f"{len(arts)} articles checked. **{weak_n} need regeneration "
         f"({100*weak_n/len(arts):.1f}%)**; {reasons['ok']} are fine.", "",
         "These are mechanical rules. They catch bottom lines that are structurally",
         "wrong (missing, truncated, or the abstract's opening). They cannot catch one",
         "that is a well-formed sentence but a poor takeaway — task 2's judge sees a",
         "random sample of the `ok` group to estimate that residual.", "",
         "| Reason | Articles | What it means |", "|---|---|---|"]
    meanings = {
        "no_abstract": "No abstract indexed in PubMed — nothing to extract from",
        "placeholder": "Literally `[Abstract not available]` or empty",
        "too_short": "Under 60 characters — a fragment, not a takeaway",
        "extractive": "Repeats how the abstract opens, i.e. background not findings",
        "truncated_midsentence": "Ends without terminal punctuation — cut off",
        "ok": "Passes every mechanical check",
    }
    for why, n in reasons.most_common():
        L.append(f"| {why} | {n} | {meanings[why]} |")

    for why in [w for w in reasons if w != "ok"]:
        L += ["", f"## {why} — examples", ""]
        for pmid, title, bl in examples[why]:
            L += [f"- **{pmid}** — {title}", f"  > {bl}"]

    open(os.path.join(HERE, args.report), "w").write("\n".join(L) + "\n")
    json.dump(sorted(targets), open(os.path.join(HERE, args.targets), "w"), indent=1)
    print(f"{weak_n} of {len(arts)} need regeneration")
    for why, n in reasons.most_common():
        print(f"  {n:5d}  {why}")
    print(f"wrote {args.report} and {args.targets}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the check and confirm it passes**

```bash
python3 check_audit.py
```

Expected: `PASS — <N> targets, 59 of them abstract-less`, with N ≥ 182.

**Expected result, from a dry run of these exact rules against the live store on
2026-08-06:** **261 targets** of 1,406 — `placeholder` 119, `extractive` 63, `no_abstract`
59, `truncated_midsentence` 19, `too_short` 1; 1,145 pass. Note this is higher than the 182
quoted in `REDESIGN_SPEC.md`, which came from the extractive pattern alone — 261 is the
better number and the spec's figure is the floor, not the total. If your run differs by more
than a few articles, the store changed underneath you: find out why before generating.

- [ ] **Step 5: Read the report before continuing**

```bash
cat bottom_line_audit.md
```

Look at the examples under each reason. If `too_short` or `truncated_midsentence` is flagging text that reads fine, loosen that rule in `classify_weakness` and re-run — a false positive here costs generation spend on an article that did not need it.

- [ ] **Step 6: Clean up and commit**

```bash
rm check_audit.py
git add audit_bottom_lines.py bottom_line_audit.md bottom_line_targets.json
git commit -m "Audit bottom lines: find every article needing a real takeaway

The 182 known-extractive figure came from one pattern. This checks five:
missing abstract, placeholder text, too short, repeats the abstract's
opening, and truncated mid-sentence.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Estimate the residual in the "ok" group

Mechanical rules cannot catch a well-formed sentence that is a poor takeaway. Before spending generation on the flagged set, find out how much of the *unflagged* set is also weak — that number decides whether the scope is "fix the flagged" or "regenerate everything".

**Files:**
- Create: `/tmp/bl_sample.json` (throwaway sample for the judge)
- Reads: `pedendolit-data.json`, `bottom_line_targets.json`
- Writes: `bottom_line_residual.md`

**Interfaces:**
- Consumes: `bottom_line_targets.json` from Task 1.
- Produces: a number — the estimated weak rate among unflagged articles — recorded in `bottom_line_residual.md`. Task 3 reads that number to decide its input set.

- [ ] **Step 1: Draw a random sample of 100 unflagged articles**

```bash
python3 -c "
import json, random
store = json.load(open('pedendolit-data.json'))
targets = set(json.load(open('bottom_line_targets.json')))
ok = [a for a in store['articles']
      if not a.get('excluded') and str(a['pmid']) not in targets]
random.Random(2026).shuffle(ok)
sample = [{'pmid': str(a['pmid']), 'title': a.get('title'),
           'abstract': (a.get('abstract') or '')[:1500],
           'bottom_line': a.get('clinical_bottom_line')} for a in ok[:100]]
json.dump({'items': sample}, open('/tmp/bl_sample.json','w'), indent=1)
print(f'{len(ok)} unflagged articles; sampled 100')
"
```

- [ ] **Step 2: Dispatch one Sonnet subagent to judge the sample**

Use the Agent tool, `subagent_type: general-purpose`, `model: sonnet`. Prompt:

```
You are a pediatric endocrinologist assessing whether each article's stored
"bottom line" is a usable clinical takeaway.

Read /tmp/bl_sample.json. For each of the 100 items, compare `bottom_line`
against `abstract` and judge:

  "good"        — states what was found or what to do. A clinician could read
                  only this and know why the paper matters.
  "weak"        — grammatical but uninformative: background, methods, a restated
                  aim, or a vague gesture ("further research is needed").
  "wrong"       — contradicts or misrepresents the abstract.

Write /tmp/bl_residual.json:
{"verdicts": {"<pmid>": {"verdict": "good|weak|wrong",
                         "reason": "one short sentence"}}}

Then write a Python script that asserts: the file parses; there are exactly 100
verdicts; the PMID set matches the sample exactly; every verdict is one of the
three allowed strings. Run it. Report the counts and confirm all four assertions
passed.
```

- [ ] **Step 3: Record the estimate**

```bash
python3 -c "
import json, collections
v = json.load(open('/tmp/bl_residual.json'))['verdicts']
c = collections.Counter(x['verdict'] for x in v.values())
targets = len(json.load(open('bottom_line_targets.json')))
store = json.load(open('pedendolit-data.json'))
total = len([a for a in store['articles'] if not a.get('excluded')])
unflagged = total - targets
rate = (c['weak'] + c['wrong']) / len(v)
est = round(unflagged * rate)
lines = ['# Bottom-line residual estimate', '',
    f'Judged a random 100 of the {unflagged} articles the mechanical audit did NOT flag.', '',
    f'| Verdict | Count |', '|---|---|',
    f'| good | {c[\"good\"]} |', f'| weak | {c[\"weak\"]} |', f'| wrong | {c[\"wrong\"]} |', '',
    f'**Estimated weak-or-wrong among unflagged: {100*rate:.0f}% ≈ {est} articles.**', '',
    f'Mechanically flagged: {targets}. Estimated true total: ~{targets + est} of {total}.', '',
    'Decision rule: if the estimate is under 10%, regenerate only the flagged set.',
    'At 10% or more, regenerate everything — a page where one card in ten reads as',
    'filler is not meaningfully better than one where one in seven does.']
open('bottom_line_residual.md','w').write('\n'.join(lines) + '\n')
print('\n'.join(lines[-6:]))
"
```

- [ ] **Step 4: Commit the estimate**

```bash
git add bottom_line_residual.md
git commit -m "Estimate weak bottom lines among the articles the audit did not flag

Mechanical rules cannot catch a well-formed sentence that says nothing.
Judged a random 100 unflagged articles to size that residual before
committing to a generation scope.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: STOP. Report the number to Christian and get the scope decision.**

Show him the flagged count, the estimated residual, and the implied total. He decides: flagged-only, or everything. Do not proceed to Task 3 without that answer — it changes the input set, the cost, and how long his review takes.

---

### Task 3: Generate the bottom lines

**Files:**
- Create: `/tmp/bl_batches/batch_NN.json` (inputs), `/tmp/bl_batches/generated_NN.json` (outputs)
- Reads: `pedendolit-data.json`, `bottom_line_targets.json`

**Interfaces:**
- Consumes: `bottom_line_targets.json` (Task 1), plus the scope decision from Task 2 step 5.
- Produces: `/tmp/bl_batches/generated_*.json`, each `{"batch": N, "bottom_lines": {"<pmid>": "<text>"}}`. Task 4 merges these.

- [ ] **Step 1: Build the batches**

```bash
mkdir -p /tmp/bl_batches && python3 -c "
import json, os
store = json.load(open('pedendolit-data.json'))
by = {str(a['pmid']): a for a in store['articles']}
targets = json.load(open('bottom_line_targets.json'))   # or all PMIDs, per the scope decision
items = [{'pmid': p, 'title': by[p].get('title'),
          'abstract': (by[p].get('abstract') or '')[:2000],
          'journal': by[p].get('journal_abbr'),
          'study_type': by[p].get('study_type')} for p in targets]
N = max(1, (len(items) + 59) // 60)      # ~60 per batch
for i in range(N):
    b = items[i::N]
    json.dump({'batch': i+1, 'items': b}, open(f'/tmp/bl_batches/batch_{i+1:02d}.json','w'), indent=1)
print(f'{len(items)} articles across {N} batches')
"
```

- [ ] **Step 2: Dispatch one Sonnet subagent per batch, in parallel**

Use the Agent tool, `subagent_type: general-purpose`, `model: sonnet`, one call per batch in a single message so they run concurrently. Prompt, with `NN` substituted:

```
You are a pediatric endocrinologist writing the one-line takeaway that will be
the MOST PROMINENT TEXT on a literature dashboard card — larger than the paper's
title. A clinician reading only your sentence should know why the paper matters.

Read /tmp/bl_batches/batch_NN.json. For every item write a bottom line.

Rules:
- One or two sentences. Under 300 characters.
- Lead with the FINDING or the RECOMMENDATION, not the aim and not the methods.
  "Weekly somatrogon was non-inferior to daily somatropin over 9 years" — good.
  "This study examined the long-term efficacy of weekly somatrogon" — useless.
- Include the effect size or the number when the abstract gives one.
- Plain clinical prose. No "This study...", no "The authors...", no hedging
  filler like "further research is warranted".
- Guidelines: say what the guideline actually tells you to do differently.
- **If the item has no abstract, write a bottom line from the title alone and
  make its limits visible** — e.g. "Position statement on X; no abstract
  indexed." NEVER invent a finding that is not in the source. A fabricated
  clinical claim in the largest text on the page is the worst possible failure
  of this task.

Write /tmp/bl_batches/generated_NN.json:
{"batch": NN, "bottom_lines": {"<pmid>": "<text>"}}

Then write a Python script that asserts: the file parses; the PMID set exactly
matches the batch file; every value is a non-empty string under 300 characters;
no value starts with "This study" or "This article". Run it, fix any failures,
and report the counts plus confirmation that all four assertions passed.
```

- [ ] **Step 3: Verify the merged output covers every target**

```bash
python3 -c "
import json, glob
targets = set(json.load(open('bottom_line_targets.json')))
merged = {}
for f in sorted(glob.glob('/tmp/bl_batches/generated_*.json')):
    merged.update(json.load(open(f))['bottom_lines'])
missing = targets - set(merged)
extra = set(merged) - targets
assert not missing, f'{len(missing)} targets have no generated line: {sorted(missing)[:5]}'
assert not extra, f'{len(extra)} unexpected PMIDs'
bad = [p for p, t in merged.items() if not t.strip() or len(t) > 300]
assert not bad, f'{len(bad)} empty or over-long: {bad[:5]}'
print(f'PASS — {len(merged)} bottom lines, all targets covered')
"
```

Expected: `PASS — <N> bottom lines, all targets covered`. If any batch is missing, re-dispatch only that batch.

---

### Task 4: Review page, and Christian's approval

**Files:**
- Create: `build_bottom_line_review.py`, `apply_bottom_lines.py`
- Writes: `bottom_line_review.html` (gitignored), `bottom_lines.json`

**Interfaces:**
- Consumes: `/tmp/bl_batches/generated_*.json` (Task 3).
- Produces: `bottom_lines.json` — `{"comment": "...", "lines": {"<pmid>": {"text": "...", "source": "generated", "decided_on": "YYYY-MM-DD"}}}`. Task 5's `apply_bottom_lines()` reads exactly this shape.

- [ ] **Step 1: Write the review-page builder**

Create `build_bottom_line_review.py`. Model it on `build_classifier_qa_review.py`, which already solves this exact problem — read that file first and follow its structure: same CSS variables, same self-contained single file, same Submit-downloads-JSON pattern. Per card show the title, the old bottom line, the new one in an editable `<textarea>`, and a collapsed `<details>` with the abstract. Submit downloads `bottom_line_review.json` as `{"decisions": {"<pmid>": {"text": "<possibly edited>", "approved": true|false}}}`.

Sort cards so the **no-abstract ones come first** — those carry the fabrication risk and deserve the freshest attention.

- [ ] **Step 2: Build the page and check it renders**

```bash
python3 build_bottom_line_review.py
python3 -c "
h = open('bottom_line_review.html', encoding='utf-8').read()
import json, glob
n = sum(len(json.load(open(f))['bottom_lines']) for f in glob.glob('/tmp/bl_batches/generated_*.json'))
assert h.count('class=\"card') == n, f'{h.count(chr(34)+\"card\")} cards for {n} articles'
assert 'Submit' in h and '<textarea' in h
print(f'PASS — {n} cards, editable, Submit present')
"
```

- [ ] **Step 3: Add the review page to .gitignore**

```bash
python3 - <<'PY'
p = '.gitignore'; s = open(p).read()
add = "\n# Regenerated from bottom_lines.json; only the decisions are versioned.\nbottom_line_review.html\n"
if 'bottom_line_review.html' not in s:
    open(p, 'w').write(s.rstrip() + "\n" + add)
    print('.gitignore updated')
PY
```

- [ ] **Step 4: Christian reviews**

Tell him to open `bottom_line_review.html`, read the no-abstract cards carefully, edit anything that reads wrong, untick anything he rejects, and Submit. **Do not proceed until he has.** A rejected card keeps its existing bottom line.

- [ ] **Step 5: Write the apply script**

Create `apply_bottom_lines.py`: read `~/Downloads/bottom_line_review.json`, keep only entries with `approved: true`, and write `bottom_lines.json` in the shape given under Interfaces above. Merge onto any existing `bottom_lines.json` rather than replacing it, so a later round never silently drops an earlier decision — `apply_classifier_qa.py` does this and its comment explains why.

- [ ] **Step 6: Apply and verify**

```bash
python3 apply_bottom_lines.py
python3 -c "
import json
d = json.load(open('bottom_lines.json'))['lines']
assert all(v['text'].strip() for v in d.values()), 'empty text present'
assert all(len(v['text']) <= 300 for v in d.values()), 'over-long text present'
print(f'PASS — {len(d)} approved bottom lines recorded')
"
```

- [ ] **Step 7: Commit**

```bash
git add build_bottom_line_review.py apply_bottom_lines.py bottom_lines.json .gitignore
git commit -m "Generate and review real clinical bottom lines

Reviewed and approved by Christian before landing. No-abstract articles were
sorted first in the review page, since those carry the fabrication risk.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Make it survive a rebuild

Without this, `build_dataset.py --rebuild` regenerates every bottom line from `classifier.clinical_bottom_line()` and silently discards the approved text. Identical in shape to the `pub_dates.json` trap already fixed.

**Files:**
- Modify: `build_dataset.py` — add `apply_bottom_lines()` beside `apply_pub_dates()` (~line 49) and call it beside the existing `dates_applied = apply_pub_dates(store)` line

**Interfaces:**
- Consumes: `bottom_lines.json` (Task 4).
- Produces: `apply_bottom_lines(store) -> int`, the count applied. Called on every build, merge or `--rebuild`.

- [ ] **Step 1: Write the failing check**

```bash
python3 -c "
import json, subprocess, sys
sample = list(json.load(open('bottom_lines.json'))['lines'].items())[:3]
subprocess.run([sys.executable,'build_dataset.py','--run-date','2026-08-06',
                '--raw','comprehensive_raw.json','--rebuild'], check=True,
               capture_output=True)
store = json.load(open('pedendolit-data.json'))
by = {str(a['pmid']): a for a in store['articles']}
bad = [p for p, rec in sample if by[p].get('clinical_bottom_line') != rec['text']]
assert not bad, f'rebuild discarded approved bottom lines for {bad}'
print('PASS — approved bottom lines survive a full rebuild')
"
```

Expected: **FAIL** — the rebuild overwrites them, because nothing re-applies the file yet.

- [ ] **Step 2: Add the function to `build_dataset.py`**

Insert immediately above `def apply_pub_dates(store):`:

```python
def apply_bottom_lines(store):
    """Re-apply reviewed clinical bottom lines from bottom_lines.json.

    classifier.clinical_bottom_line() is extractive and produces background text
    rather than a finding on unstructured abstracts. The reviewed replacements
    live in bottom_lines.json; this re-applies them on every build so a --rebuild
    cannot silently restore the weak text. Same pattern as apply_pub_dates().
    """
    path = os.path.join(HERE, "bottom_lines.json")
    if not os.path.exists(path):
        return 0
    try:
        lines = (json.load(open(path)) or {}).get("lines", {})
    except (ValueError, OSError):
        return 0
    applied = 0
    for a in store["articles"]:
        rec = lines.get(str(a.get("pmid")))
        if not rec or not rec.get("text"):
            continue
        a["clinical_bottom_line"] = rec["text"]
        a["bottom_line_source"] = rec.get("source", "reviewed")
        applied += 1
    return applied
```

- [ ] **Step 3: Call it**

Find `dates_applied = apply_pub_dates(store)` and add below it:

```python
    bottom_lines_applied = apply_bottom_lines(store)
```

Then find the `if dates_applied:` print block and add after it:

```python
        if bottom_lines_applied:
            print(f"bottom_lines applied: {bottom_lines_applied} (see bottom_lines.json)")
```

- [ ] **Step 4: Re-run the check from step 1**

Expected: `PASS — approved bottom lines survive a full rebuild`.

- [ ] **Step 5: Run the regression check before committing**

```bash
python3 check_classifier_regressions.py
```

Expected: `PASS`. Bottom lines do not affect topics, so any topic movement here means something else changed and must be understood before committing.

- [ ] **Step 6: Commit**

```bash
git add build_dataset.py
git commit -m "Re-apply reviewed bottom lines on every build

--rebuild regenerates them from the extractive classifier function, which
would silently discard the reviewed text. Same trap as pub_dates.json, same
fix.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Rebuild, verify, publish

**Files:**
- Modify: `pedendolit-data.json`, `index.html` (both generated)

- [ ] **Step 1: Full rebuild**

```bash
python3 merge_raw_sources.py
python3 build_dataset.py --run-date "$(date +%F)" --raw comprehensive_raw.json --rebuild
python3 build_dashboard.py
```

- [ ] **Step 2: Verify the audit now comes back nearly clean**

```bash
python3 audit_bottom_lines.py
```

Expected: the weak count drops to near zero. Anything left should be articles Christian rejected in review, which keep their original text by design. If the number is still large, the apply step did not take — do not publish.

- [ ] **Step 3: Confirm the store and the page agree**

```bash
python3 -c "
import json
store = json.load(open('pedendolit-data.json'))
h = open('index.html', encoding='utf-8').read()
lines = json.load(open('bottom_lines.json'))['lines']
pmid, rec = next(iter(lines.items()))
assert rec['text'][:60] in h, 'approved text is not in the published page'
n = len([a for a in store['articles'] if not a.get('excluded')])
assert n == 1406, f'article count changed to {n} — investigate before publishing'
print(f'PASS — {n} articles, approved text present in index.html')
"
```

- [ ] **Step 4: Regression check, then commit and push**

```bash
python3 check_classifier_regressions.py   # must PASS before committing
git add -A
git commit -m "Rebuild with reviewed clinical bottom lines

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
```

- [ ] **Step 5: Confirm the deploy actually landed**

```bash
gh api repos/molonych-source/pedendolit/pages/builds --jq '.[0] | .status + " " + .commit[0:7]'
```

Wait for `built` with the new commit hash, then fetch the live page and confirm the approved text is present. The Pages build has taken up to ten minutes; do not report success from the build status alone.

---

## Self-Review

**Spec coverage.** `REDESIGN_SPEC.md` → "Blocking dependency: real bottom lines" requires (a) generate rather than fall back to the title — Task 3; (b) audit the other 1,165 before assuming they are fine — Tasks 1 and 2; (c) Christian spot-checks before it goes live — Task 4 step 4, with a hard stop. Covered.

**Placeholders.** None. Every step has its command or its code. Task 4 step 1 and step 5 point at an existing file to model rather than restating ~200 lines of near-identical HTML-builder code; the interface those scripts must produce is specified exactly under Interfaces, which is the contract that matters.

**Type consistency.** `bottom_line_targets.json` is a JSON list of PMID strings in Tasks 1, 2, 3. `bottom_lines.json` is `{"lines": {pmid: {"text", "source", "decided_on"}}}` in Tasks 4, 5, 6. `classify_weakness` returns `(bool, str)` and is used only inside Task 1. `apply_bottom_lines(store) -> int` matches `apply_pub_dates`.

**Scope.** This plan covers the bottom-line data work only. The UI rebuild is a separate plan, written after this one lands, because it cannot be verified until real bottom lines exist to render.

## Not in this plan

The redesign itself — topic grid, topic queue, header destinations, the async data boundary. That is a second plan against the same spec, and it starts once Task 6 is published.

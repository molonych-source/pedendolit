# Bottom-line residual estimate

Judged a random 100 of the 1145 articles the mechanical audit did NOT flag.

| Verdict | Count |
|---|---|
| good | 77 |
| weak | 23 |
| wrong | 0 |

**Estimated weak-or-wrong among unflagged: 23% (95% CI 14.8%–31.2%) ≈ 169–358 articles
(point estimate 263).**

The interval is a normal-approximation binomial CI: `se = sqrt(p*(1-p)/n)` with
p=0.23, n=100 gives se≈0.0421, margin = 1.96*se ≈ ±8.2 points.

Mechanically flagged: 261. Estimated true total needing a rewritten bottom line:
~430–619 of 1406 (point estimate ~524).

Decision rule: if the estimate is under 10%, regenerate only the flagged set.
At 10% or more, regenerate everything — a page where one card in ten reads as
filler is not meaningfully better than one where one in seven does.

**Is the conclusion robust to the uncertainty?** Yes. Even the interval's *lower*
bound, 14.8%, clears the 10% threshold — so "regenerate everything" is the correct
call across the entire plausible range, not just at the point estimate. This isn't a
borderline case where sampling noise could flip the decision.

**Caveat:** the sample was drawn at random but not stratified by journal, topic, or
publication year, so bottom-line quality could covary with one of those in ways 100
articles won't reveal — the true rate for a specific subgroup (e.g. guidelines, which
were disproportionately represented among the weak examples) could sit outside this
interval even though the overall estimate is solid.

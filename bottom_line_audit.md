# Bottom-line audit

1406 articles checked. **261 need regeneration (18.6%)**; 1145 are fine.

These are mechanical rules. They catch bottom lines that are structurally
wrong (missing, truncated, or the abstract's opening). They cannot catch one
that is a well-formed sentence but a poor takeaway — task 2's judge sees a
random sample of the `ok` group to estimate that residual.

| Reason | Articles | What it means |
|---|---|---|
| ok | 1145 | Passes every mechanical check |
| placeholder | 119 | Literally `[Abstract not available]` or empty |
| extractive | 63 | Repeats how the abstract opens, i.e. background not findings |
| no_abstract | 59 | No abstract indexed in PubMed — nothing to extract from |
| truncated_midsentence | 19 | Ends without terminal punctuation — cut off |
| too_short | 1 | Under 60 characters — a fragment, not a takeaway |

## extractive — examples

- **28216084** — Vitamin D supplementation guidelines.
  > Research carried out during the past two-decades extended the understanding of actions of vitamin D... age-, b
- **37705267** — American Academy of Pediatrics, 2023: Guideline for the Evaluation and
  > American Academy of Pediatrics (AAP) have released their first comprehensive clinical practice guideline that 
- **39377175** — Explainable Machine-Learning Models to Predict Weekly Risk of Hypergly
  > The aim of this study was to develop and validate explainable prediction models based on continuous glucose mo
- **39657603** — International Society for Pediatric and Adolescent Diabetes Clinical P
  > The International Society for Pediatric and Adolescent Diabetes (ISPAD) guidelines represent a rich repository
- **39884260** — International Society for Pediatric and Adolescent Diabetes Clinical P
  > The International Society for Pediatric and Adolescent Diabetes (ISPAD) guidelines represent a rich repository

## placeholder — examples

- **28627221** — Retraction.
  > [Abstract not available]
- **29869358** — ISPAD Clinical Practice Consensus Guidelines 2018: Assessment and mana
  > [Abstract not available]
- **29900641** — ISPAD Clinical Practice Consensus Guidelines 2018: Diabetic ketoacidos
  > [Abstract not available]
- **29900653** — ISPAD Clinical Practice Consensus Guidelines 2018: Diabetes in adolesc
  > [Abstract not available]
- **29999222** — ISPAD Clinical Practice Consensus Guidelines 2018: Insulin treatment i
  > [Abstract not available]

## no_abstract — examples

- **39362204** — ISPAD Position Statement on Type 1 Diabetes in Schools.
  > 
- **40695258** — Novel Insights into the Pathophysiology and Management of Obesity in C
  > 
- **40910900** — Considerations for Calculating and Reporting Continuous Glucose Monito
  > 
- **41150838** — The EndoCompass Research Roadmap: Directions for the Future of Endocri
  > 
- **41167645** — Letter: Beyond the Metrics: Translating Time in Range Gains into Globa
  > 

## truncated_midsentence — examples

- **39810336** — Effectiveness of Mobile Health Applications for Cardiometabolic Risk R
  > mHealth interventions can reduce diabetes risk, improve cardiometabolic health, and improve lifestyle behavior
- **40711834** — Preventing Diabetic Ketoacidosis with Continuous Ketone Monitoring: In
  > We describe a case where continuous ketone monitor (CKM) use facilitated prompt identification and interventio
- **40719607** — A Pilot Study Evaluating Meal Timing, Macronutrient Composition, and F
  > For adults with type 1 diabetes who are susceptible to morning hyperglycemia, FiAsp delivered by AHCL and high
- **41705726** — Impact of eating behaviour on craniopharyngioma-associated obesity.
  > PRISMA-ScR and JBI methodology was followed. Five databases and two
- **41766933** — Effect of vosoritide on genu varum in children with achondroplasia aft
  > Vosoritide, a targeted treatment for achondroplasia, improves growth in children and has an established safety

## too_short — examples

- **42409045** — Human versus analogue insulin for children and young adults with type 
  > and Harry B. Helmsley Charitable Trust.

"""
PedEndoLit Article Classifier — faithful port of reclassify_v2.py (spec v2.4.2).
Pure functions; no I/O. Input = article dict with keys:
  title, abstract, journal, journal_abbr, pub_types (list), authors (list), doi, pmid
Output = classification dict merged onto the article.

Implements, in documented execution order:
  exclusion -> topic+subtopic (25-branch waterfall) -> study type -> impact tier
  -> negative-outcome cap -> diabetes subtype -> age range -> society
  -> board relevance -> bottom line -> tags -> open access -> rationale
"""
import re

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wb(term):
    """word-boundary regex search helper (case-insensitive)."""
    return re.compile(r'\b' + re.escape(term) + r'\b', re.I)

def has(text, *phrases):
    """True if any phrase (substring, lowercased) is in text."""
    return any(p in text for p in phrases)

def has_re(text, *patterns):
    return any(re.search(p, text, re.I) for p in patterns)


# ---------------------------------------------------------------------------
# 1. EXCLUSION RULES  (archive if matched)
# ---------------------------------------------------------------------------

HARD_EXCLUDE = [
    # Reproductive medicine
    "recurrent implantation failure", "platelet-rich plasma", "in vitro fertilization",
    "ivf", "endometrial receptivity", "frozen embryo transfer", "vaginal progesterone",
    "adenomyosis", "artificial cycle frozen embryo", "crinone", "embryo transfer cycle",
    # Geriatric / cognitive
    "dementia risk", "alzheimer", "cognitive decline in older", "geriatric frailty",
    "elderly patients",
    # Adult-specific
    "erectile dysfunction", "menopausal hormone therapy", "postmenopausal women",
    "hemodialysis patients", "dialysis", "renal transplant recipient",
    # Oncology (non-endocrine)
    "prostate cancer", "breast cancer hormone",
    # Non-relevant conditions
    "gouty arthritis", "knee osteoarthritis", "colorectal cancer", "colorectal carcinoma",
    # Non-human models
    "zebrafish", "social/dominance/stress in fish", "in zebrafish",
    # Non-pediatric physiology
    "university exam", "academic stress in university",
]

BASIC_SCIENCE = ["in vitro", "mouse model", "rat model", "murine", "cell line",
                 "drosophila", "xenograft", "knockout mice", "transgenic mice"]
CLINICAL_TERMS = ["patient", "clinical trial", "cohort", "children", "adolescent",
                  "pediatric", "paediatric", "guideline", "review", "meta-analysis",
                  "real-world", "registry"]

ADULT_MARKERS = [r"adult patients", r"adult population", r"adults with type 2",
                 r"postmenopausal", r"geriatric", r"elderly patients",
                 r"mean age[^0-9]{0,8}(4[0-9]|[5-9][0-9])", r"older adults",
                 r"age\s*[≥>=]+\s*50", r"age\s*[≥>=]+\s*60"]
PED_MARKERS = ["child", "adolescent", "pediatric", "paediatric", "youth", "juvenile",
               "puberty", "pubertal", "neonatal", "infant", "young adult",
               "transition", "school-age"]


def is_excluded_v2(art):
    title = (art.get("title") or "").strip()
    tl = title.lower()
    abl = (art.get("abstract") or "").lower()
    text = tl + " " + abl
    pts = [p.lower() for p in (art.get("pub_types") or [])]

    # Erratum / retraction
    if tl.startswith("erratum") or tl.startswith("correction:") or tl.startswith("retraction:"):
        return "erratum/retraction"
    if any(x in pts for x in ("erratum", "published erratum", "retraction of publication")):
        return "erratum/retraction"

    # Hard-exclusion topics  (word-boundary for short/ambiguous tokens)
    for phrase in HARD_EXCLUDE:
        if phrase == "ivf":
            if _wb("ivf").search(text):
                return f"hard-exclude:{phrase}"
        elif phrase == "dialysis":
            # avoid matching 'peritoneal dialysis'? spec lists bare 'dialysis' -> keep but wb
            if _wb("dialysis").search(text):
                return f"hard-exclude:{phrase}"
        elif phrase in text:
            return f"hard-exclude:{phrase}"

    # Single case reports (case report pub_type without meta-analysis)
    if "case report" in pts and "meta-analysis" not in pts:
        return "single case report"

    # Pure basic science: >=2 basic-science terms AND no clinical terms
    bs = sum(1 for t in BASIC_SCIENCE if t in text)
    if bs >= 2 and not any(c in text for c in CLINICAL_TERMS):
        return "pure basic science"

    # Adult-only: adult markers present with no pediatric markers
    if any(re.search(p, text, re.I) for p in ADULT_MARKERS) and not any(m in text for m in PED_MARKERS):
        return "adult-only"

    return None


# ---------------------------------------------------------------------------
# 2. TOPIC CLASSIFICATION  (25-branch waterfall, first match wins)
# ---------------------------------------------------------------------------

CLE_PHRASES = [
    "childhood cancer survivor", "pediatric cancer survivor", "off-therapy cancer",
    "late effects of cancer", "endocrine late effect", "oncology late effect", "endocrine sequela",
    "radiation-induced hypothyroidism", "radiation-induced thyroid", "radiation-induced gh",
    "radiation-induced gonadal", "cranial radiation growth",
    "total body irradiation endocrine", "total body irradiation thyroid",
    "total body irradiation growth", "total body irradiation gonadal",
    "gonadotoxic chemotherapy", "gonadotoxic treatment", "gonadotoxic therapy", "gonadotoxic radiation",
    "alkylating agent gonadal", "cisplatin endocrine", "busulfan endocrine",
    "oncofertility", "fertility preservation in cancer", "ovarian tissue cryopreservation cancer",
    "hematopoietic stem cell transplant endocrine", "hsct endocrine", "hsct thyroid", "hsct growth",
    "childhood leukemia endocrine", "childhood leukemia thyroid", "childhood leukemia growth",
    "medulloblastoma survivor endocrine", "brain tumor survivor endocrine",
    "tbi endocrine",
]

def classify_topic(art):
    """Returns (topic, subtopic). subtopic only set for Diabetes."""
    title = (art.get("title") or "")
    tl = title.lower()
    abl = (art.get("abstract") or "").lower()
    text = tl + " " + abl

    # 1. Lipids pre-check (FH that contains 'insulin')
    if has(text, "familial hypercholesterolemia", "heterozygous fh", "homozygous fh"):
        return "Lipids", None

    # 2. Cancer Late Effects pre-check
    if any(p in text for p in CLE_PHRASES):
        return "Cancer Late Effects", None

    # 2b. Gender Medicine pre-check (before Puberty/DSD/Growth).
    # ABP Domain 16. Routes gender-identity care articles, which share vocabulary
    # (puberty suppression, sex steroids) with Puberty and DSD. Fire ONLY on
    # gender-identity-specific terms; and NOT when the article is really about a
    # disorder of sex development (DSD papers discuss gender identity/incongruence
    # but are about intersex conditions, not gender-affirming care).
    _dsd_context = has(text, "46,xy", "46,xx", "gonadal dysgenesis", "ovotesticular",
                       "ambiguous genitalia", "disorder of sex development",
                       "differences of sex development", "differences in sex development",
                       "androgen insensitivity", "hydroxysteroid dehydrogenase",
                       "5-alpha reductase", "virilized 46")
    if has(text, "gender-affirming", "gender affirming", "transgender", "gender dysphoria",
           "gender-diverse", "gender diverse", "gender-diverse youth", "affirming hormone",
           "gender minority") and not _dsd_context:
        return "Gender Medicine", None

    # 3. IGF-primary -> Growth (prevents 'insulin-like growth factor' -> Diabetes)
    # Spec intent: IGF is the SUBJECT of the article, not an incidental mention.
    # Require IGF in the title OR >=2 abstract mentions; and never pre-empt a clear
    # hyperinsulinism/insulinoma article (those share 'insulin*' vocabulary).
    _igf_terms = ("insulin-like growth factor", "igf-1", "igf-i", "igf1", "igf-2", "igf-ii")
    _igf_in_title = any(t in tl for t in _igf_terms)
    _igf_count = sum(text.count(t) for t in _igf_terms)
    _hi_context = has(text, "congenital hyperinsulinism", "hyperinsulinemic hypoglycemia",
                      "hyperinsulinism of infancy", "insulinoma", "nesidioblastosis",
                      "focal hyperinsulinism", "diffuse hyperinsulinism")
    if (_igf_in_title or _igf_count >= 2) and not _hi_context \
            and not has(text, "type 1 diabetes", "type 2 diabetes", "diabetic ketoacidosis", "hba1c"):
        return "Growth", None

    # 4. Adrenal pre-check (high-specificity)
    if has(text, "pseudohypoaldosteronism", "adrenocortical carcinoma", "adrenocortical tumor",
           "pheochromocytoma", "primary aldosteronism", "adrenal crisis") \
       or "congenital adrenal hyperplasia" in tl:
        return "Adrenal", None

    # 5a. Calcium/Parathyroid pre-check (PTH-axis disorders) — before Bone.
    if has(text, "pseudohypoparathyroidism", "albright hereditary osteodystrophy"):
        return "Calcium/Parathyroid", None

    # 5b. Bone pre-check (skeletal mineralization / phosphate-wasting)
    if has(text, "burosumab", "fgf23", "fgf-23", "x-linked hypophosphatemia", "xlh",
           "phosphate wasting", "hypophosphatemic rickets"):
        return "Bone/Calcium", None

    # 5c. PCOS/PMOS pre-check — must fire before Diabetes (insulin resistance), Obesity, and Puberty
    # (all share vocabulary with PCOS/PMOS). Guard against CAH, which also causes hyperandrogenism.
    # PMOS = Polyendocrine Metabolic Ovarian Syndrome (official rename of PCOS, 2024+).
    # Both old and new terminology captured here.
    _cah_context = has(text, "congenital adrenal hyperplasia", "21-hydroxylase") or _wb("cah").search(text)
    if not _cah_context and (
        has(text, "polycystic ovary", "polycystic ovarian", "polycystic ovarian morphology",
            "polycystic morphology", "polyendocrine metabolic ovarian")
        or _wb("pcos").search(text)
        or _wb("pmos").search(text)
        or _wb("pcom").search(text)
    ):
        return "PCOS", None

    # 6. General Endocrinology pre-check (broad transition + multi-endocrine / APS)
    # Spec intent: the article is ABOUT a multi-endocrine/APS syndrome. Guard against
    # incidental abstract mentions (e.g. MEN1 listed only as family history) by
    # requiring the syndrome term in the title OR repeated in the abstract.
    _genendo_terms = ("apeced", "aps-1", "autoimmune polyendocrin", "multiple endocrine neoplasia")
    _genendo_in_title = any(t in tl for t in _genendo_terms)
    _genendo_count = sum(text.count(t) for t in _genendo_terms)
    if (has(text, "transition to adult care") and has(text, "multiple endocrine")) \
       or _genendo_in_title or _genendo_count >= 2:
        return "General Endocrinology", None

    # 7. Pituitary (before Growth/Adrenal); specific pathology only
    if has(text, "craniopharyngioma", "pituitary adenoma", "pituitary tumor", "prolactinoma",
           "hypophysitis", "hypopituitarism", "acromegaly", "diabetes insipidus", "avp-d",
           "siadh", "central hypothyroidism", "central adrenal insufficiency", "copeptin",
           "septo-optic dysplasia"):
        return "Pituitary", None

    # 8. Hyperinsulinism pre-check (before Diabetes)
    if has(text, "congenital hyperinsulinism", "hyperinsulinism hyperammonemia",
           "hyperinsulinemic hypoglycemia", "focal hyperinsulinism", "diffuse hyperinsulinism",
           "nesidioblastosis", "hyperinsulinism of infancy", "insulinoma"):
        return "Hyperinsulinism", None

    # 9. Diabetes — Technology
    if has(text, "cgm", "continuous glucose monitoring", "glucose monitoring", "insulin pump",
           "closed loop", "closed-loop", "artificial pancreas", "hybrid closed",
           "automated insulin delivery", "flash glucose", "libre", "dexcom", "tandem",
           "omnipod", "medtronic 780", "aid system", "diabetes technology", "time in range"):
        return "Diabetes", "Technology"

    # 10. Diabetes — General
    if has(text, "diabetes", "insulin", "hyperglycemia", "hypoglycemia", "dka",
           "diabetic ketoacidosis", "hba1c", "glycemic", "type 1", "type 2",
           "neonatal diabetes", "islet", "beta cell", "autoimmune diabetes",
           "monogenic diabetes", "glucokinase") or _wb("mody").search(text):
        return "Diabetes", "General"

    # 11. Hyperinsulinism / Hypoglycemia (post-Diabetes)
    if has(text, "hyperinsulinism", "persistent hypoglycemia", "diazoxide",
           "octreotide hypoglycemia", "katp channel", "kcnj11", "abcc8"):
        return "Hyperinsulinism", None

    # 12. Puberty pre-check (CPP treatment terms, before Growth)
    if has(text, "precocious puberty", "central precocious", "gnrh agonist", "gnrh analog",
           "leuprolide", "triptorelin", "histrelin", "nafarelin", "puberty suppression",
           "pubertal suppression", "thelarche variant"):
        return "Puberty", None

    # 13. Growth
    if has(text, "growth hormone", "growth disorder", "short stature", "idiopathic short",
           "igf-1", "igf-i", "igf1", "growth velocity", "growth failure", "somatotropin",
           "ghd", "sga", "prader-willi", "turner syndrome", "skeletal dysplasia",
           "achondroplasia", "growth chart", "somavaratan", "lonapegsomatropin", "somatrogon"):
        return "Growth", None

    # 14. DSD
    if has(text, "disorder of sex development", "differences of sex development", "dsd",
           "46,xy", "46,xx", "ambiguous genitalia", "cah gender",
           "virilizing ovarian", "virilizing adrenal"):
        return "DSD", None

    # 15. Puberty (main)
    if has(text, "hypogonadotropic", "puberty", "pubertal", "delayed puberty", "gonadotropin",
           "gnrh", "lh-rh", "menarche", "thelarche", "adrenarche", "pubarche",
           "tanner stage", "kallmann"):
        return "Puberty", None

    # 16. PCOS/PMOS (catches articles that slipped past the pre-check and adds broader terms)
    # PMOS = Polyendocrine Metabolic Ovarian Syndrome (official rename of PCOS, 2024+)
    if has(text, "polycystic ovary", "polycystic ovarian", "polycystic ovarian morphology",
           "polycystic morphology", "polyendocrine metabolic ovarian",
           "hyperandrogenism adolescent",
           "oligomenorrhea adolescent", "hyperandrogenic", "anovulation in adolescent",
           "androgen excess", "oligo-amenorrhea", "ovarian hyperandrogenism",
           "hyperandrogenic anovulation") \
       or _wb("pcos").search(text) or _wb("pmos").search(text) or _wb("pcom").search(text):
        return "PCOS", None

    # 17. Obesity/Metabolic — EDC pre-check (before Thyroid)
    if (has(text, "endocrine-disrupting", "endocrine disrupting", "edc", "bisphenol",
            "phthalate", "pfas") and
        has(text, "obesity", "adipogen", "obesogen", "metabolic")):
        return "Obesity/Metabolic", None

    # 18. Thyroid  (word-boundary 'thyroid' excludes parathyroid)
    if has(text, "hypothyroid", "hyperthyroid", "graves", "hashimoto", "thyrotoxicosis",
           "goiter", "tsh", "thyroxine", "congenital hypothyroid", "thyroid cancer",
           "thyroid nodule", "antithyroid") or \
       (_wb("thyroid").search(text) and not re.search(r'\bparathyroid\b', text, re.I)
        and "thyroid" in re.sub(r'\bparathyroid\b', '', text, flags=re.I)):
        return "Thyroid", None

    # 19. Adrenal (main)
    if has(text, "adrenal", "cortisol", "cushing", "congenital adrenal hyperplasia", "cah",
           "aldosterone", "pheochromocytoma", "adrenal insufficiency", "glucocorticoid",
           "mineralocorticoid", "addison"):
        return "Adrenal", None

    # 20. Lipids (main)
    if has(text, "familial hypercholesterolemia", "lipid-lowering therapy in children",
           "statin in children", "statin in adolescents", "pediatric dyslipidemia",
           "lipoprotein(a)", "lp(a)") or (has(text, "hypercholesterolemia") and has(text, "lipid")):
        return "Lipids", None

    # 21. Water/Electrolytes
    if has(text, "hyponatremia", "hypernatremia", "desmopressin", "water balance",
           "anti-diuretic hormone", "salt-wasting"):
        return "Water/Electrolytes", None

    # 22a. Calcium/Parathyroid (main) — mineral homeostasis / PTH axis.
    # Checked before Bone so calcium/PTH/vitamin-D/rickets articles route here;
    # skeletal-density articles fall through to Bone below.
    if has(text, "parathyroid", "hypoparathyroidism", "hyperparathyroidism",
           "hypocalcemia", "hypercalcemia", "calcium homeostasis", "serum calcium",
           "vitamin d deficiency", "vitamin d", "nutritional rickets", "rickets",
           "calcitriol", "pth ", "parathyroid hormone"):
        return "Calcium/Parathyroid", None

    # 22b. Bone (main) — skeletal density / fragility / antiresorptives.
    if has(text, "bone density", "osteoporosis", "osteopenia", "bone mineral",
           "fracture risk", "fracture", "burosumab", "hypophosphatemia", "fgf23",
           "denosumab", "bisphosphonate", "zoledronic acid", "pamidronate", "dxa",
           "bone health", "bone mass", "osteogenesis imperfecta") or _wb("xlh").search(text):
        return "Bone/Calcium", None

    # 23. Obesity/Metabolic (main)
    if has(text, "obesity", "overweight", "metabolic syndrome", "nafld", "nash",
           "insulin resistance", "glp-1", "semaglutide", "tirzepatide", "liraglutide",
           "weight management", "bariatric", "bmi", "dyslipidemia", "lipid disorder"):
        return "Obesity/Metabolic", None

    # 24. Genetics
    if has(text, "genetic", "exome", "whole exome", "variant", "pathogenic variant",
           "mutation", "gnomad", "monogenic", "rare disease", "chromosome", "del(",
           "duplication", "imprinting", "uniparental disomy"):
        return "Genetics", None

    # 25. General Endocrinology (catch-all)
    return "General Endocrinology", None


# ---------------------------------------------------------------------------
# 3. DIABETES SUBTYPE  (only when topic == Diabetes; Hyperinsulinism checked first)
# ---------------------------------------------------------------------------

def diabetes_subtype(text):
    """v2.5.0 priority order (per Diabetes Classification Framework):
    Hyperinsulinism -> CFRD -> MODY/Monogenic -> Steroid-induced
    -> T1D (with optional Stage sub-label) -> T2D -> GDM -> General.
    Order matters: CFRD before MODY (CF articles mention insulin),
    Steroid-induced before T1D/T2D (avoid generic type assignment)."""
    # 1. Hyperinsulinism — must remain first
    if has(text, "congenital hyperinsulinism", "hyperinsulinism of infancy",
           "nesidioblastosis", "focal hyperinsulinism"):
        return "Hyperinsulinism"
    # 2. CFRD — before MODY (CF articles mention insulin resistance)
    if has(text, "cfrd", "cystic fibrosis-related diabetes",
           "cystic fibrosis related diabetes", "cf-related diabetes",
           "diabetes in cystic fibrosis", "diabetes mellitus in cf"):
        return "CFRD"
    # 3. MODY / Monogenic
    if _wb("mody").search(text) or has(text, "maturity-onset diabetes of the young",
            "maturity onset", "monogenic diabetes", "hnf1", "hnf4", "gck mutation",
            "glucokinase", "neonatal diabetes", "transient neonatal",
            "permanent neonatal", "kcnj11", "abcc8"):
        return "MODY/Monogenic"
    # 4. Steroid-induced — before T1D/T2D
    if has(text, "steroid-induced diabetes", "steroid induced diabetes",
           "glucocorticoid-induced hyperglycemia", "glucocorticoid-induced diabetes",
           "glucocorticoid induced hyperglycemia", "glucocorticoid induced diabetes",
           "corticosteroid-induced diabetes", "posttransplant diabetes",
           "post-transplant diabetes", "new-onset diabetes after transplant", "nodat"):
        return "Steroid-induced"
    # 5. T1D — with optional Stage sub-label
    if has(text, "type 1 diabetes", "t1d", "t1dm", "autoimmune diabetes",
           "islet autoantibody", "latent autoimmune"):
        if has(text, "stage 1 type 1", "stage 2 type 1", "stage 3 type 1",
               "stage 1 t1d", "stage 2 t1d", "preclinical type 1",
               "presymptomatic type 1", "islet autoantibody positive",
               "multiple autoantibody", "t1d staging", "teplizumab", "tzield",
               "anti-cd3"):
            return "T1D·Stage"
        return "T1D"
    # 6. T2D
    if has(text, "type 2 diabetes", "t2d", "t2dm"):
        return "T2D"
    # 7. GDM
    if has(text, "gestational diabetes", "gdm"):
        return "GDM"
    return "General"


# ---------------------------------------------------------------------------
# 4. STUDY TYPE  (first match wins; ev_level secondary)
# ---------------------------------------------------------------------------

def classify_study_type(art):
    pts = [p.lower() for p in (art.get("pub_types") or [])]
    title = (art.get("title") or "")
    tl = title.lower()
    head = (tl + " " + (art.get("abstract") or "").lower())[:120]
    text = tl + " " + (art.get("abstract") or "").lower()

    if "meta-analysis" in pts or "meta-analysis" in text:
        return "Meta-analysis", 1
    if "systematic review" in pts or "systematic review" in text:
        return "Systematic Review", 1
    if any(p in pts for p in ("guideline", "practice guideline")) or \
       has(head, "guidelines for", "clinical practice guideline", "consensus statement",
           "position statement", "expert consensus", "expert panel", "clinical recommendations"):
        return "Guideline/Consensus", 1
    if "randomized controlled trial" in pts or "randomized" in pts or \
       ("randomized" in text and ("trial" in text or "rct" in text)):
        return "RCT", 2
    if "clinical trial" in pts:
        return "Clinical Trial", 2
    if "review" in pts or tl.startswith("review") or has(head, "mini review", "narrative review") \
       or tl.endswith("review") or ": a review" in text:
        return "Review", 2
    if "scoping review" in text:
        return "Scoping Review", 2
    if "cohort" in text or "retrospective" in text or "prospective cohort" in text:
        return "Observational/Cohort", 3
    if "registry" in text or ("database" in text and "analysis" in text):
        return "Registry/Database", 3
    if "prospective" in text:
        return "Prospective Study", 3
    if "real-world" in text or "real world" in text:
        return "Real-World Study", 3
    if "case-control" in text or "case control" in text:
        return "Case-Control", 3
    if "cross-sectional" in text or "cross-sectional" in pts:
        return "Cross-Sectional", 4
    if "pilot" in text and ("study" in text or "trial" in text):
        return "Pilot Study", 4
    if "survey" in text or "questionnaire" in text:
        return "Survey/Questionnaire", 4
    if "economic" in text and ("cost" in text or "burden" in text):
        return "Health Economics", 4
    if "case series" in text or ("cases" in text and "series" in text):
        return "Case Series", 5
    if any(p in pts for p in ("letter", "letter to the editor")):
        return "Letter/Correspondence", 6
    if any(p in pts for p in ("editorial", "comment")) or has(head, "commentary", "editorial"):
        return "Editorial/Commentary", 6
    return "Other", 5


# ---------------------------------------------------------------------------
# 5. IMPACT TIER
# ---------------------------------------------------------------------------

PRESTIGE = ["nature reviews endocrinology", "lancet", "new england journal", "jama",
            "bmj", "british medical journal", "diabetologia", "diabetes care",
            "journal of clinical endocrinology", "endocrine reviews", "nat rev endocrinol"]

PA_SIGNALS = ["guideline", "consensus statement", "position statement",
              "clinical practice guideline", "clinical practice recommendation",
              "fda approved", "fda approval", "ema approved", "ema approval",
              "regulatory approval", "newly approved",
              "first-line treatment", "first-line therapy", "first-line recommendation",
              "changes clinical practice", "practice-changing"]

NEG_OUTCOME = ["did not meet the prespecified criteria", "did not meet its primary endpoint",
               "failed to demonstrate", "noninferiority was not achieved",
               "did not demonstrate noninferiority", "did not alter",
               "did not significantly differ", "was not superior",
               "no significant difference in the primary", "did not significantly reduce",
               "did not significantly improve", "failed to meet",
               "primary endpoint was not met", "primary outcome was not met"]

SAMPLE_PATTERNS = [
    r'n\s*=\s*([0-9][0-9,]*)',
    r'([0-9][0-9,]*)\s+(?:patients|children|adolescents|participants|subjects|individuals|infants|neonates)',
    r'enrolled\s+([0-9][0-9,]*)',
    r'included\s+([0-9][0-9,]*)\s+(?:patients|children|adolescents|participants)',
    r'total of\s+([0-9][0-9,]*)',
]

def extract_n(text):
    for pat in SAMPLE_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None

def is_prestige(journal):
    j = (journal or "").lower()
    return any(p in j for p in PRESTIGE)

def classify_impact(art, study_type, journal):
    text = ((art.get("title") or "") + " " + (art.get("abstract") or "")).lower()
    prestige = is_prestige(journal)
    pa_score = sum(1 for s in PA_SIGNALS if s in text)
    n = extract_n(text)
    large_n = n is not None and n >= 100
    small_n = n is not None and n < 30
    multicenter = "multicenter" in text or "multicentre" in text or "multi-center" in text

    # Always LOW for case reports, editorials, letters
    if study_type in ("Case Series", "Editorial/Commentary", "Letter/Correspondence"):
        return "LOW"

    pa_qualifies = pa_score >= 2 or (pa_score >= 1 and prestige)

    # PRACTICE-ALTERING
    if study_type == "Guideline/Consensus":
        impact = "PRACTICE-ALTERING"
    elif study_type == "RCT" and prestige and (large_n or multicenter) and pa_score >= 1:
        impact = "PRACTICE-ALTERING"
    elif study_type == "Meta-analysis" and (pa_score >= 2 or (prestige and pa_score >= 1)):
        impact = "PRACTICE-ALTERING"
    elif study_type == "Systematic Review" and pa_score >= 2:
        impact = "PRACTICE-ALTERING"
    # HIGH
    elif study_type == "Meta-analysis":
        impact = "HIGH"
    elif study_type == "Systematic Review":
        impact = "HIGH"
    elif study_type == "RCT" and (not small_n or prestige):
        impact = "HIGH"
    elif study_type == "Clinical Trial" and (prestige or large_n or pa_score >= 1):
        impact = "HIGH"
    elif study_type == "Review" and prestige:
        impact = "HIGH"
    # MODERATE
    elif study_type == "RCT" and small_n and not prestige:
        impact = "MODERATE"
    elif study_type == "Clinical Trial":
        impact = "MODERATE"
    elif study_type in ("Observational/Cohort", "Registry/Database", "Prospective Study",
                        "Real-World Study") and (large_n or multicenter or prestige):
        impact = "MODERATE"
    elif study_type == "Review":
        impact = "MODERATE"
    elif study_type in ("Cross-Sectional", "Survey/Questionnaire") and prestige and large_n:
        impact = "MODERATE"
    else:
        impact = "LOW"

    # Negative-outcome cap (RCT/Clinical Trial only): PA -> HIGH if null primary
    if study_type in ("RCT", "Clinical Trial") and impact == "PRACTICE-ALTERING":
        if any(s in text for s in NEG_OUTCOME):
            impact = "HIGH"

    return impact


# ---------------------------------------------------------------------------
# 6. SOCIETY ATTRIBUTION
# ---------------------------------------------------------------------------

def detect_societies(text):
    out = []
    def add(name):
        if name not in out:
            out.append(name)
    if has(text, "ispad", "international society for pediatric and adolescent diabetes"):
        add("ISPAD")
    if has(text, "american diabetes association", "ada standards of care", "ada 2026", "ada guidelines"):
        add("ADA")
    if has(text, "european society for paediatric endocrinology") or _wb("espe").search(text):
        add("ESPE")
    if has(text, "pediatric endocrine society", "pes guidelines"):
        add("PES")
    if has(text, "endocrine society clinical", "endocrine society guideline", "endocrine society position"):
        add("ES")
    if has(text, "european association for the study of diabetes", "easd"):
        add("EASD")
    if has(text, "american thyroid association", "ata guideline"):
        add("ATA")
    if has(text, "american academy of pediatrics", "aap policy", "aap clinical practice"):
        add("AAP")
    if has(text, "american association of clinical endocrinology", "aace"):
        add("AACE")
    if has(text, "world health organization", "who guideline", "who recommendation"):
        add("WHO")
    if re.search(r"ispad.*ada|ada.*ispad", text, re.I):
        add("ISPAD/ADA")
    return out


# ---------------------------------------------------------------------------
# 7. AGE RANGE
# ---------------------------------------------------------------------------

def detect_age_ranges(text):
    labels = []
    def add(l):
        if l not in labels:
            labels.append(l)
    if has(text, "neonatal", "newborn", "neonate", "neonates", "at birth", "nicu",
           "premature infant", "preterm neonate", "gestational age"):
        add("Neonatal")
    if has(text, "infant", "infancy", "toddler", "under 2 years", "age < 2", "aged 0-2", "young child"):
        add("Infant")
    if has(text, "children", "school-age", "school age", "aged 2-12", "prepubertal",
           "prepubescent", "preadolescent", "pediatric", "mct8", "allan-herndon-dudley", "slc16a2"):
        add("Child")
    if has(text, "adolescent", "teenager", "teen", "youth", "aged 12-18", "aged 13-18",
           "pubertal", "high school", "middle school", "paediatric", "pediatric adolescent"):
        add("Adolescent")
    if has(text, "young adult", "transfer of care", "emerging adult", "aged 18-25", "aged 16-25",
           "transition age", "transitional age", "transition to adult care", "transition clinic",
           "transition program", "transition readiness", "youth to adult", "pediatric to adult",
           "transfer to adult care"):
        add("Transition")
    if not labels:
        if any(t in text for t in ("pediatric", "paediatric", "child", "youth")):
            add("Child"); add("Adolescent")
        else:
            add("Adult")
    return labels


# ---------------------------------------------------------------------------
# 8. BOARD RELEVANCE  (ABP exam domains)
# ---------------------------------------------------------------------------

BOARD_TOPICS = [
    # Domain 3 Diabetes
    "t1d", "dka", "insulin regimen", "hybrid closed loop", "automated insulin delivery",
    "cgm", "type 2 diabetes", "metformin", "neonatal diabetes", "mody", "cfrd",
    "steroid-induced hyperglycemia", "diabetes screening",
    "cystic fibrosis-related diabetes", "cystic fibrosis related diabetes",
    "steroid-induced diabetes", "glucocorticoid-induced hyperglycemia",
    "teplizumab", "tzield", "t1d staging", "presymptomatic type 1",
    "islet autoantibody positive", "multiple autoantibody positive",
    # Domain 4 Growth
    "ghd", "gh therapy", "igf-1 deficiency", "short stature", "gh stimulation test",
    "turner", "noonan", "silver-russell", "sga", "skeletal dysplasia", "achondroplasia",
    "prader-willi", "beckwith-wiedemann", "tall stature", "sotos",
    # Domain 5 Thyroid
    "congenital hypothyroidism", "newborn screening", "hashimoto", "graves",
    "antithyroid drug", "methimazole", "thyroid nodule", "thyroid cancer",
    "differentiated thyroid cancer", "radioiodine", "central hypothyroidism",
    # Domain 6 Puberty
    "precocious puberty", "cpp", "gnrh agonist", "leuprolide", "histrelin",
    "delayed puberty", "constitutional delay", "hypogonadotropic", "hypergonadotropic",
    "testosterone therapy", "estrogen therapy", "pcos", "gynecomastia", "klinefelter",
    # Domain 7 Adrenal
    "cah", "21-hydroxylase", "adrenal crisis", "adrenal insufficiency", "addison",
    "cushing", "pheochromocytoma", "paraganglioma", "adrenal tumor", "stress dose steroid",
    "mineralocorticoid replacement", "salt-wasting",
    # Domain 8 HP axis
    "craniopharyngioma", "hypopituitarism", "combined pituitary hormone deficiency",
    "prolactinoma", "acromegaly", "cushing disease", "septo-optic dysplasia", "pituitary adenoma",
    # Domain 9 Hypoglycemia
    "neonatal hypoglycemia", "persistent hyperinsulinism", "congenital hyperinsulinism",
    "diazoxide", "octreotide", "focal hyperinsulinism", "ketotic hypoglycemia",
    # Domain 10 DSD
    "dsd", "differences of sex development", "ambiguous genitalia", "46,xy", "46,xx",
    "androgen insensitivity", "gonadal dysgenesis",
    # Domain 11 Posterior pituitary
    "diabetes insipidus", "central di", "vasopressin deficiency", "desmopressin", "siadh",
    "cerebral salt wasting", "hyponatremia", "hypernatremia",
    # Domain 12 Weight
    "pediatric obesity", "glp-1", "semaglutide", "liraglutide", "bariatric surgery",
    "monogenic obesity", "leptin", "mc4r", "hypothalamic obesity", "syndromic obesity",
    # Domain 13 Bone
    "vitamin d deficiency rickets", "nutritional rickets", "hypoparathyroidism",
    "hypocalcemia", "hypercalcemia", "osteoporosis", "x-linked hypophosphatemia",
    "fgf23", "hypophosphatemic rickets", "hyperparathyroidism",
    # Domain 14 NET/combined
    "autoimmune polyglandular", "multiple endocrine neoplasia", "men1", "men2",
    "neuroendocrine tumor", "insulinoma",
    # Domain 15 Lipids
    "familial hypercholesterolemia", "statin in children", "pediatric dyslipidemia",
    "ldl lowering", "heterozygous fh",
    # Domain 16 Gender
    "gender-affirming", "transgender youth", "gender-diverse", "gender dysphoria",
    "pubertal suppression", "gender incongruence",
    # Domain 17 Pop health
    "newborn screening endocrine", "neonatal screening hypothyroidism",
    "transition of care endocrine", "transition care diabetes",
]

BOARD_QUALIFYING_TYPES = {"Guideline/Consensus", "Meta-analysis", "RCT", "Systematic Review",
                          "Clinical Trial", "Review", "Review Article", "Position Statement"}

def board_relevant(impact, study_type, text):
    if impact == "PRACTICE-ALTERING":
        return 1
    if study_type in BOARD_QUALIFYING_TYPES and any(k in text for k in BOARD_TOPICS):
        return 1
    return 0


# ---------------------------------------------------------------------------
# 9. TAGS
# ---------------------------------------------------------------------------

PRIMARY_TAG = {
    "Diabetes": "#Diabetes", "Growth": "#Growth", "Puberty": "#Puberty",
    "Pituitary": "#Pituitary", "Thyroid": "#Thyroid", "Adrenal": "#Adrenal",
    "Bone/Calcium": "#BoneCalcium", "Calcium/Parathyroid": "#CalciumParathyroid",
    "Gender Medicine": "#GenderMedicine", "Obesity/Metabolic": "#Obesity", "PCOS": "#PCOS",
    "DSD": "#DSD", "Water/Electrolytes": "#WaterElectrolytes",
    "Hyperinsulinism": "#Hyperinsulinism", "Genetics": "#Genetics",
    "Lipids": "#Lipids", "General Endocrinology": "#GeneralEndo",
    "Cancer Late Effects": "#CancerLateEffects",
}

TRANSITION_PHRASES = ["transition to adult", "transition of care", "transition from pediatric",
                      "transfer to adult", "transition program", "transition clinic",
                      "transition readiness", "transition intervention", "transitioning to adult",
                      "adult transition", "pediatric to adult", "paediatric to adult",
                      "transition in care", "youth transition", "adolescent transition to"]

# secondary cross-topic tags: (tag, any-scope phrases, title-only phrases)
SECONDARY = [
    ("#Thyroid", ["autoimmune thyroid", "hashimoto", "graves disease", "thyroid autoimmunity",
                  "thyroid disease", "thyroid dysfunction", "thyroiditis", "anti-tpo",
                  "thyroid antibod", "thyroid disorder"], []),
    ("#Diabetes", ["type 1 diabetes", "type 2 diabetes", "t1d ", "diabetes mellitus",
                   "autoimmune diabetes", "monogenic diabetes", "neonatal diabetes", "mody ",
                   "insulin-dependent diabetes"], []),
    ("#Growth", ["growth hormone deficiency", "growth failure", "growth retardation",
                 "growth impairment"], ["short stature", "height sds", "growth velocity"]),
    ("#Puberty", ["precocious puberty", "delayed puberty", "early puberty", "pubertal delay",
                  "pubertal advancement", "premature thelarche", "premature adrenarche"], []),
    ("#Adrenal", ["adrenal insufficiency", "cah", "adrenocortical insufficiency",
                  "cortisol deficiency", "glucocorticoid deficiency", "adrenal androgen excess"], []),
    ("#PCOS", ["polycystic ovary", "polycystic ovarian", "polycystic ovarian morphology",
               "polycystic morphology", "polyendocrine metabolic ovarian",
               "pcos", "pmos", "pcom"], []),
    ("#Obesity", ["cardiometabolic risk", "nonalcoholic fatty liver", "anti-obesity medication",
                  "childhood obesity", "pediatric obesity"],
                 ["obesity", "overweight", "insulin resistance", "metabolic syndrome"]),
    ("#BoneCalcium", ["bone mineral density", "bone mass", "osteoporosis", "osteopenia",
                      "bone loss", "fracture risk", "low bone mass", "bone density",
                      "vertebral fracture"], []),
    ("#CalciumParathyroid", ["hypoparathyroidism", "hyperparathyroidism", "hypocalcemia",
                      "hypercalcemia", "parathyroid hormone", "vitamin d deficiency",
                      "nutritional rickets"], []),
    ("#GenderMedicine", ["gender-affirming", "transgender", "gender dysphoria",
                      "gender incongruence", "gender-diverse"], []),
    ("#DSD", ["turner syndrome", "klinefelter syndrome", "disorder of sex development",
              "difference of sex development", "gonadal dysgenesis", "45,x", "47,xxy",
              "sex chromosome disorder"], []),
    ("#Pituitary", ["craniopharyngioma", "hypopituitarism", "pituitary adenoma",
                    "pituitary tumor", "central diabetes insipidus", "pituitary insufficiency"], []),
    ("#Lipids", ["familial hypercholesterolemia", "dyslipidemia", "statin therapy",
                 "lipid-lowering therapy", "lipid-lowering treatment"],
                ["hypercholesterolemia", "elevated ldl"]),
    ("#Hyperinsulinism", ["congenital hyperinsulinism", "hyperinsulinism"], []),
    ("#Genetics", ["pathogenic variant", "likely pathogenic", "de novo variant",
                   "copy number variant", "chromosomal microarray", "whole exome sequencing",
                   "next-generation sequencing", "multigene panel", "genetic testing"], []),
]

def generate_tags(art, topic, subtopic, study_type, impact, board, text, title_l):
    tags = []
    # primary
    pt = PRIMARY_TAG.get(topic)
    if pt:
        tags.append(pt)
    # contextual
    if any(p in text for p in TRANSITION_PHRASES):
        tags.append("#Transition")
    if "equity" in text or "disparit" in text:
        tags.append("#HealthEquity")
    if re.search(r"\bnct\d+", text, re.I) or "clinicaltrials" in text:
        tags.append("#RegisteredTrial")
    if board == 1:
        tags.append("#BoardRelevant")
    if has(text, "artificial intelligence", "machine learning", "deep learning",
           "natural language processing", "ai model"):
        tags.append("#AIinMedicine")
    if has(text, "telemedicine", "telehealth", "remote monitoring", "digital health",
           "mobile health", "mhealth"):
        tags.append("#DigitalHealth")
    if subtopic == "Technology":
        tags.append("#Technology")
    stmap = {"Guideline/Consensus": "#Guidelines", "RCT": "#RCT", "Meta-analysis": "#MetaAnalysis",
             "Systematic Review": "#SystematicReview", "Review": "#Review",
             "Scoping Review": "#ScopingReview"}
    if study_type in stmap:
        tags.append(stmap[study_type])
    if study_type in ("Registry/Database", "Real-World Study"):
        tags.append("#RealWorldData")
    # secondary cross-topic (never re-add own primary)
    for tag, any_scope, title_scope in SECONDARY:
        if tag == pt:
            continue
        if tag in tags:
            continue
        if any(p in text for p in any_scope) or any(p in title_l for p in title_scope):
            tags.append(tag)
    # dedupe preserve order
    seen = set(); out = []
    for t in tags:
        if t not in seen:
            seen.add(t); out.append(t)
    return out


# ---------------------------------------------------------------------------
# 10. OPEN ACCESS
# ---------------------------------------------------------------------------

OA_MARKERS = ["frontiers", "j clin res pediatr endocrinol",
              "journal of clinical research in pediatric endocrinology",
              "journal of the endocrine society"]

def open_access(journal, journal_abbr):
    j = ((journal or "") + " " + (journal_abbr or "")).lower()
    return "Open" if any(m in j for m in OA_MARKERS) else "Subscription"


# ---------------------------------------------------------------------------
# 11. CLINICAL BOTTOM LINE
# ---------------------------------------------------------------------------

BOILERPLATE_TAIL = [
    r'prospero.*$', r'crd\d+.*$', r'nct\d+.*$', r'isrctn.*$', r'chictr.*$',
    r'actrn.*$', r'eudract.*$', r'trial registr.*$', r'this (?:study|trial) was registered.*$',
    r'clinicaltrials\.gov.*$', r'funding:.*$', r'data availability.*$',
    r'this article is protected by copyright.*$', r'registered at.*$', r'is registered with.*$',
]
SECTION_MARKERS = ["CONCLUSIONS:", "CONCLUSION:", "INTERPRETATION:", "FINDINGS:",
                   "CLINICAL SIGNIFICANCE:", "CLINICAL RELEVANCE:", "WHAT THIS STUDY ADDS:",
                   "IMPLICATIONS:", "SUMMARY:", "KEY FINDINGS:", "KEY MESSAGES:",
                   "TAKE-HOME MESSAGE:", "RELEVANCE:", "SIGNIFICANCE:"]

def _sentences(s):
    return [x.strip() for x in re.split(r'(?<=[.!?])\s+', s.strip()) if x.strip()]

def clinical_bottom_line(abstract):
    if not abstract:
        return ""
    ab = abstract.strip()
    stripped = ab
    for pat in BOILERPLATE_TAIL:
        stripped = re.sub(pat, '', stripped, flags=re.I).strip()
    if len(stripped) < 40:
        stripped = ab
    up = stripped.upper()
    for marker in SECTION_MARKERS:
        idx = up.find(marker)
        if idx != -1:
            after = stripped[idx + len(marker):].strip()
            # cut at next ALLCAPS section header if present
            after = re.split(r'\b[A-Z][A-Z ]{3,}:', after)[0].strip()
            sents = _sentences(after)
            if sents:
                return " ".join(sents[:2])
    sents = _sentences(stripped)
    return " ".join(sents[-2:]) if sents else ""


# ---------------------------------------------------------------------------
# 12. IMPACT RATIONALE
# ---------------------------------------------------------------------------

def impact_rationale(impact, study_type, journal, topic, n, societies):
    soc = f" from {societies[0]}" if societies else ""
    nstr = f"n = {n}" if n else "n not reported"
    jr = journal or "a peer-reviewed journal"
    if impact == "PRACTICE-ALTERING":
        if study_type == "Guideline/Consensus":
            return f"Official guideline or consensus statement{soc}. Directly informs clinical protocols and management standards."
        if study_type in ("RCT", "Clinical Trial"):
            return f"Landmark {study_type} ({nstr}) in {jr}. High-prestige trial with direct implications for clinical management."
        if study_type == "Meta-analysis":
            return f"Meta-analysis with strong practice-relevant signal in {jr}. Level I evidence with direct clinical guideline implications."
        if study_type == "Systematic Review":
            return "Systematic review with multiple convergent guideline-level signals. Level I evidence warranting practice change."
    if impact == "HIGH":
        if study_type == "RCT":
            return f"Randomized controlled trial ({nstr}). Level II evidence with direct applicability to clinical decision-making."
        if study_type == "Meta-analysis":
            return f"Meta-analysis synthesizing multiple studies on {topic}. Published in {jr}. Level I evidence summary."
        if study_type == "Systematic Review":
            return f"Systematic review of {topic} evidence. Level I synthesis; strongest available summary short of a guideline."
        if study_type == "Review":
            return f"Authoritative review in {jr}. High-impact journal curation adds clinical credibility."
    if impact == "MODERATE":
        if study_type == "RCT":
            return f"Small or early-phase randomized trial. Small sample ({nstr}). Interesting signal but underpowered for definitive conclusions."
        if study_type in ("Observational/Cohort", "Registry/Database", "Prospective Study"):
            return f"Observational study on {topic}. Cohort size {nstr}. Clinically informative but limited by non-randomized design."
        if study_type == "Real-World Study":
            return f"Real-world evidence study ({nstr}) on {topic}. Reflects clinical practice conditions; no randomization."
    if impact == "LOW":
        if study_type in ("Editorial/Commentary", "Letter/Correspondence"):
            return f"Expert letter or commentary. No new primary data; provides perspective on {topic} but does not independently change practice."
        if study_type == "Case Series":
            return f"Small case series. Hypothesis-generating but lacks the power to guide practice changes in {topic}."
    return f"{study_type} on {topic}. Background reading for clinical awareness."


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def classify(art):
    """Full pipeline. Returns dict of classification fields (or {'excluded': reason})."""
    excl = is_excluded_v2(art)
    if excl:
        return {"excluded": True, "exclude_reason": excl}

    title = art.get("title") or ""
    title_l = title.lower()
    text = (title_l + " " + (art.get("abstract") or "").lower())
    journal = art.get("journal") or ""
    journal_abbr = art.get("journal_abbr") or ""

    topic, subtopic = classify_topic(art)
    study_type, ev_level = classify_study_type(art)
    impact = classify_impact(art, study_type, journal)
    dm_sub = diabetes_subtype(text) if topic == "Diabetes" else None
    ages = detect_age_ranges(text)
    societies = detect_societies(text)
    board = board_relevant(impact, study_type, text)
    n = extract_n(text)
    tags = generate_tags(art, topic, subtopic, study_type, impact, board, text, title_l)
    access = open_access(journal, journal_abbr)
    bottom = clinical_bottom_line(art.get("abstract") or "")
    rationale = impact_rationale(impact, study_type, journal, topic, n, societies)

    return {
        "excluded": False,
        "topic": topic,
        "subtopic": subtopic,
        "diabetes_subtype": dm_sub,
        "study_type": study_type,
        "ev_level": ev_level,
        "impact": impact,
        "age_range": ages,
        "society": societies,
        "board_relevant": board,
        "sample_n": n,
        "tags": tags,
        "access": access,
        "clinical_bottom_line": bottom,
        "impact_rationale": rationale,
    }

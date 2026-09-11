import re

from job_radar.models import RawJob

# Weights. A keyword is counted ONCE, at the strongest place it appears -
# so "robotics" in both the title and the description scores 20, not 26.
#
# Why description hits are worth less than title hits: a title is a
# deliberate summary of the role, while a description is long, noisy, and
# often carries company boilerplate ("Bosch is a global leader in robotics
# and automation...") that says nothing about the actual job.
HIGH_TITLE = 20
HIGH_DESC = 8
MEDIUM_TITLE = 8
MEDIUM_DESC = 2
EXCLUDE_TITLE = -40
EXCLUDE_DESC = -12

# A single high-value word found ONLY in the description is worth this much
# instead of HIGH_DESC - see RULE 2 in score_job().
LONE_DESC_HIGH = 3

# Returned when an exclude term appears in the title - see RULE 1.
HARD_REJECT = -999

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """Most ATSs return descriptions as HTML. Strip tags before matching.

    Without this, tag and attribute content can produce phantom matches
    (a CSS class or tracking URL containing "embedded"), and words split
    across tags won't match at all.
    """
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


def score_job(job: RawJob, keywords: dict) -> tuple[int, list[str]]:
    """Weighted keyword match over title+department, and the description.

    Returns (score, matched) where matched annotates WHERE each hit landed:
      "ros2"        -> matched in the title/department
      "ros2~"       -> matched only in the description (weaker signal)
      "-senior"     -> exclude term, in the title
      "-10+ years~" -> exclude term, in the description
    That annotation is the whole point of staying rule-based: when an alert
    looks wrong you can see exactly which words caused it and fix
    config/keywords.yaml in two minutes.
    """
    title_text = f"{job.title} {job.department or ''}".lower()
    desc_text = strip_html(job.description or "").lower()

    score = 0
    matched: list[str] = []

    # RULE 1 - an exclude term in the TITLE is a hard reject.
    # Previously this was just -40, which a keyword-rich description could
    # out-score: "Senior Robotics Engineer" scored +46 and alerted, even
    # though the seniority alone rules it out. Title excludes are
    # categorical, so short-circuit instead of arithmetic.
    title_excludes = [kw for kw in keywords.get("exclude", []) if kw.lower() in title_text]
    if title_excludes:
        return HARD_REJECT, [f"-{kw}" for kw in title_excludes]

    def apply(kw_list, title_weight, desc_weight, prefix=""):
        nonlocal score
        title_hits, desc_hits = [], []
        for kw in kw_list:
            k = kw.lower()
            if k in title_text:
                score += title_weight
                matched.append(f"{prefix}{kw}")
                title_hits.append(kw)
            elif desc_text and k in desc_text:
                score += desc_weight
                matched.append(f"{prefix}{kw}~")
                desc_hits.append(kw)
        return title_hits, desc_hits

    high_title, high_desc = apply(keywords.get("high_value", []), HIGH_TITLE, HIGH_DESC)
    apply(keywords.get("medium_value", []), MEDIUM_TITLE, MEDIUM_DESC)
    apply(keywords.get("exclude", []), EXCLUDE_TITLE, EXCLUDE_DESC, prefix="-")

    # RULE 2 - discount a LONE high-value mention that appears only in the
    # description. Big employers open every posting with boilerplate like
    # "Bosch is a global leader in robotics and automation", which would
    # otherwise push unrelated CI/backend roles over the threshold. One
    # passing mention is probably marketing; two or more distinct robotics
    # concepts is a real robotics job.
    if not high_title and len(high_desc) == 1:
        score -= HIGH_DESC - LONE_DESC_HIGH
        matched = [m.replace(f"{high_desc[0]}~", f"{high_desc[0]}~(lone)") for m in matched]

    return score, matched
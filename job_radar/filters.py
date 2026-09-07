from job_radar.models import RawJob

HIGH_VALUE_WEIGHT = 20
MEDIUM_VALUE_WEIGHT = 8
EXCLUDE_WEIGHT = -40


def score_job(job: RawJob, keywords: dict) -> tuple[int, list[str]]:
    """Weighted keyword match against the job title + department.

    This is intentionally plain keyword matching, not ML — it's fast, has
    zero external dependencies, and (most importantly) you can look at the
    matched list and immediately understand *why* a job scored the way it
    did, which makes it trivial to tune config/keywords.yaml.
    """
    text = f"{job.title} {job.department or ''}".lower()
    score = 0
    matched: list[str] = []

    for kw in keywords.get("high_value", []):
        if kw.lower() in text:
            score += HIGH_VALUE_WEIGHT
            matched.append(kw)

    for kw in keywords.get("medium_value", []):
        if kw.lower() in text:
            score += MEDIUM_VALUE_WEIGHT
            matched.append(kw)

    for kw in keywords.get("exclude", []):
        if kw.lower() in text:
            score += EXCLUDE_WEIGHT
            matched.append(f"-{kw}")

    return score, matched

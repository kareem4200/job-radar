from job_radar.filters import score_job
from job_radar.models import RawJob


def make_job(title, department=None):
    return RawJob(
        source="test",
        company="TestCo",
        external_id="1",
        title=title,
        location="Munich",
        url="https://example.com",
        department=department,
    )


def test_high_value_keyword_scores_positively():
    keywords = {"high_value": ["ROS2"], "medium_value": [], "exclude": []}
    job = make_job("Robotics Software Engineer (ROS2)")
    score, matched = score_job(job, keywords)
    assert score == 20
    assert "ROS2" in matched


def test_excluded_keyword_pulls_score_down():
    keywords = {"high_value": ["robotics"], "medium_value": [], "exclude": ["director"]}
    job = make_job("Director of Robotics")
    score, matched = score_job(job, keywords)
    assert score == 20 - 40
    assert "-director" in matched


def test_no_match_scores_zero():
    keywords = {"high_value": ["robotics"], "medium_value": [], "exclude": []}
    job = make_job("Accounts Payable Clerk")
    score, matched = score_job(job, keywords)
    assert score == 0
    assert matched == []


def test_department_is_also_searched():
    keywords = {"high_value": [], "medium_value": ["mechatronics"], "exclude": []}
    job = make_job("Working Student", department="Mechatronics")
    score, matched = score_job(job, keywords)
    assert score == 8
    assert "mechatronics" in matched

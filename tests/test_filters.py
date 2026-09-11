from job_radar.filters import HARD_REJECT, score_job, strip_html
from job_radar.models import RawJob


def make_job(title, department=None, description=None):
    return RawJob(source="test", company="TestCo", external_id="1", title=title,
                  location="Munich", url="https://example.com",
                  department=department, description=description)


KW = {"high_value": ["robotic", "ros2", "slam", "motion planning"],
      "medium_value": ["c++", "python", "embedded"],
      "exclude": ["senior", "werkstudent"]}


def test_high_value_in_title_scores_full():
    score, matched = score_job(make_job("Robotic Software Engineer (ROS2)"), KW)
    assert score == 40  # robotic + ros2, both in title
    assert "robotic" in matched and "ros2" in matched


def test_description_only_match_still_scores():
    """The whole point of scanning descriptions: titles rarely say ROS2."""
    job = make_job("Software Engineer, Advanced Engineering",
                   description="<p>Work with <b>ROS2</b>, SLAM and motion planning.</p>")
    score, matched = score_job(job, KW)
    assert score > 0
    assert all(m.endswith("~") for m in matched)  # all came from description


def test_lone_description_mention_is_discounted_as_boilerplate():
    """'X is a global leader in robotics' must not trigger an alert."""
    job = make_job("Data Engineer",
                   description="<p>Acme is a global leader in robotic automation. "
                               "Build ETL pipelines.</p>")
    score, _ = score_job(job, KW)
    assert score < 10


def test_two_distinct_description_concepts_are_not_discounted():
    job = make_job("Data Engineer", description="We use ROS2 and SLAM heavily.")
    score, _ = score_job(job, KW)
    assert score >= 16


def test_exclude_in_title_is_a_hard_reject():
    """A rich description must not out-score a disqualifying title."""
    job = make_job("Senior Robotic Engineer",
                   description="ROS2 SLAM motion planning c++ python embedded")
    score, matched = score_job(job, KW)
    assert score == HARD_REJECT
    assert matched == ["-senior"]


def test_title_match_beats_description_match_no_double_count():
    job = make_job("Robotic Engineer", description="robotic robotic robotic")
    score, matched = score_job(job, KW)
    assert score == 20
    assert matched == ["robotic"]


def test_strip_html_removes_tags():
    assert "<p>" not in strip_html("<p>ROS2</p>")
    assert "ROS2" in strip_html("<p>ROS2</p>")


def test_no_match_scores_zero():
    score, matched = score_job(make_job("Accounts Payable Clerk"), KW)
    assert score == 0 and matched == []
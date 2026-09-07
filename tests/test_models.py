from job_radar.models import RawJob


def test_fingerprint_is_stable_for_same_job():
    job1 = RawJob(source="greenhouse", company="KUKA", external_id="42", title="A", location="Munich", url="u")
    job2 = RawJob(source="greenhouse", company="KUKA", external_id="42", title="A (typo fix)", location="Munich", url="u")
    assert job1.fingerprint == job2.fingerprint


def test_fingerprint_differs_across_companies():
    job1 = RawJob(source="greenhouse", company="KUKA", external_id="42", title="A", location="Munich", url="u")
    job2 = RawJob(source="greenhouse", company="Bosch", external_id="42", title="A", location="Munich", url="u")
    assert job1.fingerprint != job2.fingerprint

import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class AshbyAdapter(JobAdapter):
    """Ashby's public Job Posting API. No authentication required.

    Popular with VC-backed startups (OpenAI, Cohere, Ramp, Linear, and
    several German robotics companies incl. Sereact and RobCo use it).

    Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true
    """

    ats_name = "ashby"
    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{name}"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        url = self.BASE_URL.format(name=company.identifier)
        resp = requests.get(
            url,
            params={"includeCompensation": "true"},
            timeout=20,
            headers={"User-Agent": "job-radar/0.1"},
        )
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for j in data.get("jobs", []):
            if j.get("isListed") is False:
                continue  # unlisted roles shouldn't appear on a public board
            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=str(j.get("id")),
                    title=j.get("title", ""),
                    location=j.get("location", ""),
                    url=j.get("jobUrl") or j.get("applyUrl", ""),
                    updated_at=j.get("publishedAt"),
                    department=j.get("department") or j.get("team"),
                    description=j.get("descriptionPlain") or j.get("descriptionHtml"),
                )
            )
        return jobs
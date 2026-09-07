import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class GreenhouseAdapter(JobAdapter):
    """Greenhouse's public Job Board API. No authentication required for reads.

    Docs: https://developers.greenhouse.io/job-board.html
    Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
    """

    ats_name = "greenhouse"
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        url = self.BASE_URL.format(token=company.identifier)
        resp = requests.get(url, timeout=20, headers={"User-Agent": "job-radar/0.1"})
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for j in data.get("jobs", []):
            departments = j.get("departments") or []
            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=str(j["id"]),
                    title=j.get("title", ""),
                    location=(j.get("location") or {}).get("name", ""),
                    url=j.get("absolute_url", ""),
                    updated_at=j.get("updated_at"),
                    department=", ".join(d.get("name", "") for d in departments) or None,
                )
            )
        return jobs

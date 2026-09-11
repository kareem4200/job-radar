import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class GreenhouseAdapter(JobAdapter):
    """Greenhouse's public Job Board API. No authentication required for reads.

    Docs: https://developers.greenhouse.io/job-board.html
    Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs

    NOTE ON EU BOARDS: some European companies' careers pages live on
    job-boards.eu.greenhouse.io / boards.eu.greenhouse.io. That is only the
    front-end; there is NO boards-api.eu.greenhouse.io. Greenhouse documents
    a single API host, and the board token works there regardless of which
    front-end domain the company uses. `region` is ignored for Greenhouse.
    """

    ats_name = "greenhouse"
    BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        url = self.BASE_URL.format(token=company.identifier)
        # content=true makes Greenhouse include the full job description in
        # the LIST response, so we don't need a second request per job.
        resp = requests.get(
            url,
            params={"content": "true"},
            timeout=30,
            headers={"User-Agent": "job-radar/0.1"},
        )
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
                    description=j.get("content"),
                )
            )
        return jobs
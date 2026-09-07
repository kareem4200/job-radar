import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class LeverAdapter(JobAdapter):
    """Lever's public Postings API. No authentication required.

    Docs: https://github.com/lever/postings-api
    Endpoint: GET https://api.lever.co/v0/postings/{site_slug}?mode=json
    EU-hosted accounts: https://api.eu.lever.co/v0/postings/{site_slug}?mode=json
    """

    ats_name = "lever"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        host = "api.eu.lever.co" if company.region == "eu" else "api.lever.co"
        url = f"https://{host}/v0/postings/{company.identifier}?mode=json"
        resp = requests.get(url, timeout=20, headers={"User-Agent": "job-radar/0.1"})
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for p in data:
            categories = p.get("categories") or {}
            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=str(p.get("id")),
                    title=p.get("text", ""),
                    location=categories.get("location", ""),
                    url=p.get("hostedUrl") or p.get("applyUrl", ""),
                    department=categories.get("team") or categories.get("department"),
                )
            )
        return jobs

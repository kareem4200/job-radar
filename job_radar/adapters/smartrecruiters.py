import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class SmartRecruitersAdapter(JobAdapter):
    """SmartRecruiters' public Posting API. No authentication required for reads.

    Docs: https://developers.smartrecruiters.com/reference/postings
    Endpoint: GET https://api.smartrecruiters.com/v1/companies/{id}/postings

    identifier = the company id, i.e. the path segment in
    careers.smartrecruiters.com/{id}  (e.g. "BoschGroup", "Continental").
    Case-sensitive.

    Unlike the other adapters this one PAGINATES (limit/offset, max 100 per
    page), so we loop until a short page comes back. Large employers like
    Bosch Group have thousands of postings worldwide, so we cap the number
    of pages to avoid hammering them - see MAX_PAGES.
    """

    ats_name = "smartrecruiters"
    BASE_URL = "https://api.smartrecruiters.com/v1/companies/{cid}/postings"
    PAGE_SIZE = 100
    MAX_PAGES = 20  # 2000 postings; plenty for a personal radar

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        url = self.BASE_URL.format(cid=company.identifier)
        jobs: list[RawJob] = []
        offset = 0

        for _ in range(self.MAX_PAGES):
            resp = requests.get(
                url,
                params={"limit": self.PAGE_SIZE, "offset": offset},
                timeout=30,
                headers={"User-Agent": "job-radar/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("content", [])

            for j in content:
                loc = j.get("location") or {}
                location = ", ".join(
                    x for x in (loc.get("city"), loc.get("country")) if x
                )
                dept = (j.get("department") or {}).get("label")
                jobs.append(
                    RawJob(
                        source=self.ats_name,
                        company=company.name,
                        external_id=str(j.get("id")),
                        title=j.get("name", ""),
                        location=location,
                        # applyUrl is the canonical public posting URL
                        url=j.get("applyUrl")
                        or f"https://careers.smartrecruiters.com/{company.identifier}/{j.get('id')}",
                        updated_at=j.get("releasedDate") or j.get("createdOn"),
                        department=dept or (j.get("function") or {}).get("label"),
                    )
                )

            if len(content) < self.PAGE_SIZE:
                break
            offset += self.PAGE_SIZE

        return jobs
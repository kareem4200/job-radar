import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class WorkdayAdapter(JobAdapter):
    """Workday careers, via the CXS endpoint the careers page itself calls.

    >>> READ THIS BEFORE RELYING ON IT <<<
    Unlike every other adapter here, this endpoint is UNDOCUMENTED. Workday
    publishes no public jobs API; this is the internal JSON endpoint their
    own careers SPA hits. It works and is widely used, but SAP/Workday owe
    us nothing here - it can change shape without notice. Treat breakage as
    expected maintenance, not a bug.

        POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
        body: {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}

    identifier = "{tenant}/{wd}/{site}", three values separated by slashes,
                 all read off the careers URL. For
                     https://trumpf.wd3.myworkdayjobs.com/TRUMPF_Graduates_and_Professionals
                 that is:
                     trumpf/wd3/TRUMPF_Graduates_and_Professionals
                 and for https://ag.wd3.myworkdayjobs.com/Airbus it is:
                     ag/wd3/Airbus

    Note the tenant is NOT always the brand name - Airbus's tenant is "ag".
    """

    ats_name = "workday"
    PAGE_SIZE = 20  # Workday rejects larger values on most tenants
    MAX_PAGES = 25  # 500 postings

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        try:
            tenant, wd, site = company.identifier.split("/")
        except ValueError:
            raise ValueError(
                f"workday identifier must be 'tenant/wd/site', got {company.identifier!r}"
            )

        base = f"https://{tenant}.{wd}.myworkdayjobs.com"
        url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

        jobs: list[RawJob] = []
        offset = 0

        for _ in range(self.MAX_PAGES):
            resp = requests.post(
                url,
                json={
                    "appliedFacets": {},
                    "limit": self.PAGE_SIZE,
                    "offset": offset,
                    "searchText": "",
                },
                timeout=30,
                headers={
                    "User-Agent": "job-radar/0.1",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            postings = data.get("jobPostings", [])

            for p in postings:
                path = p.get("externalPath", "")
                jobs.append(
                    RawJob(
                        source=self.ats_name,
                        company=company.name,
                        # bulletFields usually carries the human-facing req id;
                        # externalPath is the stable fallback.
                        external_id=(p.get("bulletFields") or [None])[0] or path,
                        title=p.get("title", ""),
                        location=p.get("locationsText", ""),
                        url=f"{base}/{site}{path}" if path else base,
                        updated_at=p.get("postedOn"),
                        department=None,
                    )
                )

            if len(postings) < self.PAGE_SIZE:
                break
            offset += self.PAGE_SIZE

        return jobs

    def fetch_description(self, company: CompanyConfig, job: RawJob) -> str | None:
        """One extra GET per NEW job only. Same undocumented-API caveat."""
        try:
            tenant, wd, site = company.identifier.split("/")
        except ValueError:
            return None

        # job.url is "{base}/{site}{externalPath}"; the CXS detail endpoint
        # is "{base}/wday/cxs/{tenant}/{site}{externalPath}".
        base = f"https://{tenant}.{wd}.myworkdayjobs.com"
        prefix = f"{base}/{site}"
        if not job.url.startswith(prefix):
            return None
        external_path = job.url[len(prefix):]

        try:
            resp = requests.get(
                f"{base}/wday/cxs/{tenant}/{site}{external_path}",
                timeout=20,
                headers={"User-Agent": "job-radar/0.1", "Accept": "application/json"},
            )
            resp.raise_for_status()
            return (resp.json().get("jobPostingInfo") or {}).get("jobDescription")
        except Exception:
            return None
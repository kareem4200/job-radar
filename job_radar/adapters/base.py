from abc import ABC, abstractmethod

from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class JobAdapter(ABC):
    """Every ATS adapter fetches raw jobs for one company and normalizes them."""

    ats_name: str

    @abstractmethod
    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        ...

    def fetch_description(self, company: CompanyConfig, job: RawJob) -> str | None:
        """Fetch one job's description, for ATSs whose list endpoint omits it.

        Default: nothing extra to fetch (the adapter already filled in
        job.description, or the ATS simply doesn't expose one).

        main.py calls this ONLY for jobs that are new, never for the whole
        board - otherwise a 2,000-posting employer like Bosch would mean
        2,000 extra HTTP requests every single run.
        """
        return None
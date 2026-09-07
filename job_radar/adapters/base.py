from abc import ABC, abstractmethod

from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class JobAdapter(ABC):
    """Every ATS adapter fetches raw jobs for one company and normalizes them."""

    ats_name: str

    @abstractmethod
    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        ...

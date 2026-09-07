from dataclasses import dataclass
from typing import Optional


@dataclass
class RawJob:
    """A job posting normalized to a common shape, regardless of which ATS it came from."""

    source: str  # "greenhouse" | "personio" | "lever"
    company: str  # display name, from companies.yaml
    external_id: str  # id as given by the ATS itself
    title: str
    location: str
    url: str
    updated_at: Optional[str] = None  # ISO-ish string if the ATS provided one
    department: Optional[str] = None

    @property
    def fingerprint(self) -> str:
        """Stable unique key used for de-duplication and storage.

        Deliberately scoped to (source, company, external_id) rather than a
        content hash, so an edited job (e.g. a typo fix) does not re-trigger
        an alert as if it were a brand-new posting.
        """
        return f"{self.source}:{self.company}:{self.external_id}"

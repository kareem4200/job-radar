import xml.etree.ElementTree as ET

import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class TeamtailorAdapter(JobAdapter):
    """Teamtailor's public per-company RSS jobs feed. No authentication required.

    Teamtailor's own docs say: take the careers site's main jobs page and
    append ".rss". Their token-gated REST API (api.teamtailor.com) is for
    customers managing their own data - we don't need it for read-only
    listings.

    Docs: https://support.teamtailor.com/en/articles/11171756-rss-feed-how-to-guide
    Endpoint: GET {careers_base}/jobs.rss?per_page=200

    identifier here is the FULL careers-site base URL without a trailing
    slash, because Teamtailor customers use wildly different hosts:
        careers.korial.com          (custom domain)
        jobs.acme.com               (custom domain)
        acme.teamtailor.com         (default teamtailor host)
    so a bare slug isn't enough to construct the URL.

    Example:
        identifier: https://careers.korial.com
    """

    ats_name = "teamtailor"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        base = company.identifier.rstrip("/")
        if not base.startswith("http"):
            # tolerate a bare host being pasted in
            base = f"https://{base}"

        url = f"{base}/jobs.rss"
        resp = requests.get(
            url,
            params={"per_page": "200"},
            timeout=20,
            headers={"User-Agent": "job-radar/0.1"},
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.content)

        jobs = []
        for item in root.iter("item"):
            link = (item.findtext("link") or "").strip()
            title = (item.findtext("title") or "").strip()

            # RSS has no dedicated id; the job URL ends in /jobs/<id>-<slug>,
            # so derive a stable id from the last path segment. Falls back to
            # the whole link if the shape is unexpected.
            external_id = link.rstrip("/").split("/")[-1] or link

            # Teamtailor's public feed does not expose department, and
            # location handling varies by tenant - pull it if present.
            location = (item.findtext("location") or "").strip()

            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=external_id,
                    title=title,
                    location=location,
                    url=link,
                    updated_at=(item.findtext("pubDate") or "").strip() or None,
                    department=None,
                )
            )
        return jobs
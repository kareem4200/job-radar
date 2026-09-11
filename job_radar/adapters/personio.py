import xml.etree.ElementTree as ET

import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class PersonioAdapter(JobAdapter):
    """Personio's public XML job feed. No authentication required.

    Personio is the dominant ATS for the German "Mittelstand" and many
    startups/scale-ups — often better coverage for German robotics/industrial
    companies than Greenhouse or Lever.

    Endpoint: GET https://{subdomain}.jobs.personio.de/xml?language=en
    (some tenants use .com instead of .de — set region: "com" if so)

    Docs: https://developer.personio.de/v2.0/docs/retrieving-open-job-positions
    """

    ats_name = "personio"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        domain = "com" if company.region == "com" else "de"
        url = f"https://{company.identifier}.jobs.personio.{domain}/xml?language=en"
        resp = requests.get(url, timeout=20, headers={"User-Agent": "job-radar/0.1"})
        resp.raise_for_status()

        root = ET.fromstring(resp.content)

        jobs = []
        for pos in root.findall("position"):
            pos_id = (pos.findtext("id") or "").strip()
            name = (pos.findtext("name") or "").strip()
            office = (pos.findtext("office") or "").strip()
            department = (pos.findtext("department") or "").strip()

            # Personio nests the description as repeated
            # <jobDescriptions><jobDescription><name/><value/> blocks
            # (e.g. "Your tasks", "Your profile"). Concatenate all values.
            parts = []
            for jd in pos.iter("jobDescription"):
                for tag in ("name", "value"):
                    v = jd.findtext(tag)
                    if v and v.strip():
                        parts.append(v.strip())
            description = "\n".join(parts) or None

            # Personio's XML feed doesn't always include a direct per-job URL,
            # so we build the standard job-detail URL pattern. Spot-check one
            # link per company after your first run to make sure it resolves.
            job_url = f"https://{company.identifier}.jobs.personio.{domain}/job/{pos_id}?language=en"

            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=pos_id,
                    title=name,
                    location=office,
                    url=job_url,
                    department=department or None,
                    description=description,
                )
            )
        return jobs
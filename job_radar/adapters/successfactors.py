import xml.etree.ElementTree as ET

import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


class SuccessFactorsAdapter(JobAdapter):
    """SAP SuccessFactors public XML jobs feed.

    SAP KB 2428902 documents a standard feed URL that returns all jobs posted
    to a customer's default career site, with no authentication:

        https://career{N}.successfactors.{com|eu}/career
            ?company={COMPANY_ID}&career_ns=job_listing_summary&resultType=XML

    Do NOT confuse this with the SuccessFactors OData API - that one is
    OAuth-gated and issued only to the employer, and will never return
    another company's public postings.

    identifier = the company id, i.e. the ?company= value on the employer's
                 apply URL (e.g. "dlrdeutsch", "fraunhofer").
    region     = the full career host. SuccessFactors shards its customers
                 across numbered hosts AND two different domains:
                     career5.successfactors.eu    (many EU customers)
                     career2.successfactors.eu
                     career4.successfactors.com
                     career55.sapsf.eu            (SAP's newer domain)
                 Always read it off the employer's own Apply link rather
                 than assuming. Defaults to career4.successfactors.com.

    Tip on company ids: many production tenants carry a suffix - e.g.
    "sickagP", "festoagcokP" (trailing P) or "VitescoProd". Copy the value
    verbatim from the Apply URL; don't tidy it up.

    CAVEAT: the fields SuccessFactors exposes in this feed are configurable
    per customer (Admin Center > Internal and External Career Search
    Settings), so some tenants return fewer fields than others. The parser
    below is deliberately tolerant and falls back rather than raising.
    """

    ats_name = "successfactors"
    DEFAULT_HOST = "career4.successfactors.com"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        host = company.region or self.DEFAULT_HOST
        url = f"https://{host}/career"
        resp = requests.get(
            url,
            params={
                "company": company.identifier,
                "career_ns": "job_listing_summary",
                "resultType": "XML",
            },
            timeout=30,
            headers={"User-Agent": "job-radar/0.1"},
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.content)

        def text(node, *names):
            """First non-empty child matching any of the given tag names."""
            for n in names:
                v = node.findtext(n)
                if v and v.strip():
                    return v.strip()
            return ""

        jobs = []
        # Tenants differ in wrapper naming; accept any <job>/<jobs> element.
        for j in list(root.iter("job")) + list(root.iter("jobs")):
            jid = text(j, "jobReqId", "id", "jobId", "requisitionId")
            title = text(j, "jobTitle", "title", "jobReqTitle")
            if not jid and not title:
                continue
            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=jid or title,
                    title=title,
                    location=text(j, "location", "city", "jobLocation"),
                    url=text(j, "jobUrl", "url", "applyUrl"),
                    updated_at=text(j, "postedDate", "lastModified") or None,
                    department=text(j, "department", "businessUnit") or None,
                )
            )
        return jobs
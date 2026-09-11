import xml.etree.ElementTree as ET

import requests

from job_radar.adapters.base import JobAdapter
from job_radar.config import CompanyConfig
from job_radar.models import RawJob


def _local(tag: str) -> str:
    """Tag name without its XML namespace ('{http://...}item' -> 'item')."""
    return tag.rsplit("}", 1)[-1]


class SuccessFactorsAdapter(JobAdapter):
    """SAP SuccessFactors jobs, via the public career-site feed.

    TWO MODES, chosen by the shape of `identifier`:

    1. RSS MODE (recommended) - identifier is the career-site base URL:
           identifier: https://jobs.dlr.de
       Fetches {base}/sitemal.xml. That is not a typo on our end: every
       SuccessFactors Recruiting Marketing instance serves an RSS 1.0
       document at the misspelt "sitemal.xml" path listing every posted job.
       It is undocumented by SAP but consistent across instances.

    2. LEGACY MODE - identifier is a bare company id, region is the career
       host:
           identifier: dlrdeutsch
           region: career5.successfactors.eu
       Uses the SAP-documented feed (KB 2428902):
           /career?company=X&career_ns=job_listing_summary&resultType=XML
       In practice this returned an HTML error page for most tenants we
       tried (KUKA, SICK, Fraunhofer, Schaeffler) and an empty document for
       the rest (DLR, Festo), so it is kept only as a fallback.

    Prefer mode 1. Verify by opening {base}/sitemal.xml in a browser first:
    if you get XML, the adapter will work; if you get a 404 or HTML, that
    tenant doesn't serve it and the company can't be polled.
    """

    ats_name = "successfactors"
    DEFAULT_HOST = "career4.successfactors.com"

    def fetch_jobs(self, company: CompanyConfig) -> list[RawJob]:
        if company.identifier.startswith("http"):
            return self._fetch_rss(company)
        return self._fetch_legacy(company)

    # ---------- mode 1: career-site RSS ----------
    def _fetch_rss(self, company: CompanyConfig) -> list[RawJob]:
        base = company.identifier.rstrip("/")
        resp = requests.get(
            f"{base}/sitemal.xml",
            timeout=30,
            headers={"User-Agent": "job-radar/0.1"},
        )
        resp.raise_for_status()
        self._assert_xml(resp, f"{base}/sitemal.xml")

        root = ET.fromstring(resp.content)
        jobs = []
        for item in root.iter():
            if _local(item.tag) != "item":
                continue
            fields = {_local(c.tag): (c.text or "").strip() for c in item}
            link = fields.get("link", "")
            title = fields.get("title", "")
            if not link and not title:
                continue
            # Job URLs look like /job/<City>-<Title>/<id>/ - the numeric
            # segment is the stable id.
            segs = [s for s in link.rstrip("/").split("/") if s]
            external_id = next(
                (s for s in reversed(segs) if s.isdigit()), link or title
            )
            jobs.append(
                RawJob(
                    source=self.ats_name,
                    company=company.name,
                    external_id=external_id,
                    title=title,
                    location="",  # not carried in this feed
                    url=link,
                    updated_at=fields.get("date") or fields.get("pubDate") or None,
                    department=None,
                    description=fields.get("description") or None,
                )
            )
        return jobs

    # ---------- mode 2: legacy documented feed ----------
    def _fetch_legacy(self, company: CompanyConfig) -> list[RawJob]:
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
        self._assert_xml(resp, url)

        root = ET.fromstring(resp.content)

        def text(node, *names):
            for n in names:
                v = node.findtext(n)
                if v and v.strip():
                    return v.strip()
            return ""

        jobs = []
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
                    description=text(j, "jobDescription", "description") or None,
                )
            )
        return jobs

    @staticmethod
    def _assert_xml(resp, url: str) -> None:
        """Fail with a readable message instead of a cryptic parse error.

        SuccessFactors answers 200-with-HTML when a feed isn't enabled, which
        surfaced as 'not well-formed (invalid token): line 26, column 1' -
        useless for diagnosis.
        """
        head = resp.content[:200].lstrip().lower()
        if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
            raise ValueError(
                f"returned HTML, not XML - feed not enabled for this tenant ({url})"
            )
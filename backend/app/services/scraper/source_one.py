from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.scraper.base import BaseScraper, ScrapingError


class YCombinatorScraper(BaseScraper):
    BASE_URL = "https://www.ycombinator.com"
    LISTING_URL = f"{BASE_URL}/jobs/role/all"

    def __init__(self, max_jobs: int | None = 20):
        if max_jobs is not None and max_jobs <= 0:
            raise ValueError("max_jobs must be positive or None")

        super().__init__(
            source_name="ycombinator",
            delay_seconds=1.5,
        )

        self.max_jobs = max_jobs

    def _discover_job_urls(self) -> list[str]:
        response = self.get(self.LISTING_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        job_urls = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()

            if "/companies/" not in href or "/jobs/" not in href:
                continue

            job_url = urljoin(
                self.BASE_URL,
                href,
            ).split("#", 1)[0]

            parsed_url = urlparse(job_url)

            if parsed_url.netloc != "www.ycombinator.com":
                continue

            if job_url in seen_urls:
                continue

            seen_urls.add(job_url)
            job_urls.append(job_url)

        if not job_urls:
            raise ScrapingError(
                "No YC job links were found. "
                "The listing page structure may have changed."
            )

        if self.max_jobs is not None:
            return job_urls[: self.max_jobs]

        return job_urls

    @staticmethod
    def _get_external_id(job_url: str) -> str:
        path = urlparse(job_url).path.rstrip("/")
        slug = path.split("/")[-1]

        if not slug:
            raise ScrapingError(
                f"Could not extract a job ID from {job_url}"
            )

        external_id = slug.split("-", 1)[0]

        if not external_id:
            raise ScrapingError(
                f"Could not extract a job ID from {job_url}"
            )

        return external_id

    @staticmethod
    def _extract_raw_text(
        soup: BeautifulSoup,
    ) -> str:
        for element in soup.find_all(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "nav",
                "header",
                "footer",
            ]
        ):
            element.decompose()

        content = soup.find("main") or soup.body

        if content is None:
            return ""

        return " ".join(
            content.get_text(
                " ",
                strip=True,
            ).split()
        )

    def _scrape_job(
        self,
        job_url: str,
    ) -> dict:
        response = self.get(job_url)

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title_element = soup.find("h1")

        if title_element is None:
            raise ScrapingError(
                f"Could not find the job title at {job_url}"
            )

        title = " ".join(
            title_element.get_text(
                " ",
                strip=True,
            ).split()
        )

        if not title:
            raise ScrapingError(
                f"Job title was empty at {job_url}"
            )

        raw_text = self._extract_raw_text(soup)

        if not raw_text:
            raise ScrapingError(
                f"No job content was found at {job_url}"
            )

        return {
            "source": self.source_name,
            "external_id": self._get_external_id(
                job_url
            ),
            "source_url": job_url,
            "title": title,
            "raw_text": raw_text,
            "scraped_at": datetime.now(
                timezone.utc
            ),
        }

    def scrape(self) -> list[dict]:
        job_urls = self._discover_job_urls()

        jobs = []

        for job_url in job_urls:
            try:
                job = self._scrape_job(
                    job_url
                )
                jobs.append(job)

            except ScrapingError as exc:
                print(
                    f"Skipping YC job "
                    f"{job_url}: {exc}"
                )

        if not jobs:
            raise ScrapingError(
                "YC job links were found, "
                "but none of the job pages "
                "could be scraped successfully."
            )

        return jobs
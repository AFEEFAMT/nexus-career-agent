import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.services.scraper.base import BaseScraper, ScrapingError


class WellfoundScraper(BaseScraper):
    BASE_URL = "https://wellfound.com"
    LISTING_URL = f"{BASE_URL}/location/india"

    JOB_PATH_PATTERN = re.compile(
        r"^/jobs/(\d+)-"
    )

    PAGE_PATTERN = re.compile(
        r"Page\s+(\d+)\s+of\s+(\d+)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        max_pages: int | None = 2,
        max_jobs: int | None = 20,
    ):
        if max_pages is not None and max_pages <= 0:
            raise ValueError(
                "max_pages must be positive or None"
            )

        if max_jobs is not None and max_jobs <= 0:
            raise ValueError(
                "max_jobs must be positive or None"
            )

        super().__init__(
            source_name="wellfound",
            delay_seconds=2.0,
        )

        self.max_pages = max_pages
        self.max_jobs = max_jobs

    def _get_listing_url(
        self,
        page: int,
    ) -> str:
        if page == 1:
            return self.LISTING_URL

        return f"{self.LISTING_URL}?page={page}"

    def _extract_page_info(
        self,
        soup: BeautifulSoup,
    ) -> tuple[int | None, int | None]:
        page_text = " ".join(
            soup.stripped_strings
        )

        match = self.PAGE_PATTERN.search(
            page_text
        )

        if match is None:
            return None, None

        current_page = int(
            match.group(1)
        )

        total_pages = int(
            match.group(2)
        )

        return current_page, total_pages

    def _discover_page(
        self,
        page: int,
    ) -> tuple[list[str], int | None]:
        listing_url = self._get_listing_url(
            page
        )

        response = self.get(
            listing_url
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        _, total_pages = (
            self._extract_page_info(soup)
        )

        job_urls = []
        seen_urls = set()

        for link in soup.find_all(
            "a",
            href=True,
        ):
            href = link.get(
                "href",
                "",
            ).strip()

            full_url = urljoin(
                self.BASE_URL,
                href,
            )

            parsed_url = urlparse(
                full_url
            )

            if (
                parsed_url.netloc
                != "wellfound.com"
            ):
                continue

            match = (
                self.JOB_PATH_PATTERN.match(
                    parsed_url.path
                )
            )

            if match is None:
                continue

            job_url = (
                f"{self.BASE_URL}"
                f"{parsed_url.path.rstrip('/')}"
            )

            if job_url in seen_urls:
                continue

            seen_urls.add(job_url)
            job_urls.append(job_url)

        return job_urls, total_pages

    def _discover_job_urls(
        self,
    ) -> list[str]:
        all_job_urls = []
        seen_urls = set()

        page = 1
        total_pages = None

        while True:
            if (
                self.max_pages is not None
                and page > self.max_pages
            ):
                break

            page_urls, detected_total = (
                self._discover_page(page)
            )

            if (
                detected_total is not None
                and total_pages is None
            ):
                total_pages = detected_total

            new_urls = 0

            for job_url in page_urls:
                if job_url in seen_urls:
                    continue

                seen_urls.add(job_url)
                all_job_urls.append(
                    job_url
                )

                new_urls += 1

                if (
                    self.max_jobs is not None
                    and len(all_job_urls)
                    >= self.max_jobs
                ):
                    return all_job_urls

            if (
                total_pages is not None
                and page >= total_pages
            ):
                break

            if not page_urls or new_urls == 0:
                break

            page += 1

        if not all_job_urls:
            raise ScrapingError(
                "No Wellfound job links were found. "
                "The listing page structure may have changed."
            )

        return all_job_urls

    @classmethod
    def _get_external_id(
        cls,
        job_url: str,
    ) -> str:
        path = urlparse(
            job_url
        ).path

        match = (
            cls.JOB_PATH_PATTERN.match(
                path
            )
        )

        if match is None:
            raise ScrapingError(
                f"Could not extract a job ID from {job_url}"
            )

        return match.group(1)

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

        content = (
            soup.find("main")
            or soup.body
        )

        if content is None:
            return ""

        raw_text = " ".join(
            content.get_text(
                " ",
                strip=True,
            ).split()
        )

        # Similar job recommendations are unrelated
        # to the listing being extracted.
        if "Similar Jobs" in raw_text:
            raw_text = raw_text.split(
                "Similar Jobs",
                1,
            )[0].strip()

        return raw_text

    def _scrape_job(
        self,
        job_url: str,
    ) -> dict:
        response = self.get(
            job_url
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title_element = soup.find(
            "h1"
        )

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

        raw_text = (
            self._extract_raw_text(
                soup
            )
        )

        if not raw_text:
            raise ScrapingError(
                f"No job content was found at {job_url}"
            )

        return {
            "source": self.source_name,
            "external_id": (
                self._get_external_id(
                    job_url
                )
            ),
            "source_url": job_url,
            "title": title,
            "raw_text": raw_text,
            "scraped_at": datetime.now(
                timezone.utc
            ),
        }

    def scrape(
        self,
    ) -> list[dict]:
        job_urls = (
            self._discover_job_urls()
        )

        jobs = []

        for job_url in job_urls:
            try:
                jobs.append(
                    self._scrape_job(
                        job_url
                    )
                )

            except ScrapingError as exc:
                print(
                    f"Skipping Wellfound job "
                    f"{job_url}: {exc}"
                )

        if not jobs:
            raise ScrapingError(
                "Wellfound job links were found, "
                "but none of the job pages "
                "could be scraped successfully."
            )

        return jobs
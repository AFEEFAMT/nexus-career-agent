import time
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ScrapingError(Exception):
    pass


class BaseScraper(ABC):
    def __init__(
        self,
        source_name: str,
        user_agent: str = (
            "NexusCareerAgent/1.0 "
            "(+https://github.com/AFEEFAMT/nexus-career-agent)"
        ),
        delay_seconds: float = 1.5,
        timeout: int = 15,
    ):
        self.source_name = source_name
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        retry_strategy = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._last_request_time = 0.0
        self._robots_cache: dict[str, RobotFileParser] = {}

    def _get_robot_parser(self, url: str) -> RobotFileParser:
        parsed_url = urlparse(url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

        if origin in self._robots_cache:
            return self._robots_cache[origin]

        robots_url = f"{origin}/robots.txt"

        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            response = self.session.get(
                robots_url,
                timeout=self.timeout,
            )

            self._last_request_time = time.monotonic()

            if response.ok:
                parser.parse(response.text.splitlines())

            elif 400 <= response.status_code < 500:
                # A missing robots.txt means no published restrictions.
                parser.parse([])

            else:
                # Be conservative if the server itself is unavailable.
                parser.parse(
                    [
                        "User-agent: *",
                        "Disallow: /",
                    ]
                )

        except requests.RequestException:
            parser.parse(
                [
                    "User-agent: *",
                    "Disallow: /",
                ]
            )

        self._robots_cache[origin] = parser
        return parser

    def can_fetch(self, url: str) -> bool:
        parser = self._get_robot_parser(url)
        return parser.can_fetch(self.user_agent, url)

    def _wait_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        remaining = self.delay_seconds - elapsed

        if remaining > 0:
            time.sleep(remaining)

    def get(
        self,
        url: str,
        params: dict | None = None,
    ) -> requests.Response:
        if not self.can_fetch(url):
            raise ScrapingError(
                f"robots.txt does not allow scraping this URL: {url}"
            )

        self._wait_if_needed()

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )

            self._last_request_time = time.monotonic()

            response.raise_for_status()
            return response

        except requests.RequestException as exc:
            raise ScrapingError(
                f"Failed to fetch {url}: {exc}"
            ) from exc

    @abstractmethod
    def scrape(self) -> list[dict]:
        pass
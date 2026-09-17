import argparse
import json

from app.db.database import SessionLocal
from app.services.job_pipeline import run_job_pipeline
from app.services.scraper.source_one import YCombinatorScraper
from app.services.scraper.source_two import WellfoundScraper


def build_scrapers(
    source: str,
    max_jobs: int,
    max_pages: int,
):
    scrapers = []

    if source in {"all", "yc"}:
        scrapers.append(
            YCombinatorScraper(
                max_jobs=max_jobs,
            )
        )

    if source in {"all", "wellfound"}:
        scrapers.append(
            WellfoundScraper(
                max_pages=max_pages,
                max_jobs=max_jobs,
            )
        )

    return scrapers


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Scrape job listings and run the NEXUS "
            "ingestion, embedding, and extraction pipeline."
        )
    )

    parser.add_argument(
        "--source",
        choices=[
            "all",
            "yc",
            "wellfound",
        ],
        default="all",
        help="Source to scrape. Default: all.",
    )

    parser.add_argument(
        "--max-jobs",
        type=int,
        default=10,
        help=(
            "Maximum jobs to scrape per source. "
            "Default: 10."
        ),
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,
        help=(
            "Maximum Wellfound listing pages to scan. "
            "Default: 2."
        ),
    )

    args = parser.parse_args()

    if args.max_jobs <= 0:
        parser.error(
            "--max-jobs must be greater than 0"
        )

    if args.max_pages <= 0:
        parser.error(
            "--max-pages must be greater than 0"
        )

    scrapers = build_scrapers(
        source=args.source,
        max_jobs=args.max_jobs,
        max_pages=args.max_pages,
    )

    results = {}

    with SessionLocal() as db:
        for scraper in scrapers:
            print(
                f"\nRunning source: "
                f"{scraper.source_name}"
            )

            try:
                result = run_job_pipeline(
                    db=db,
                    scraper=scraper,
                )

                results[
                    scraper.source_name
                ] = result

                print(
                    json.dumps(
                        result,
                        indent=2,
                        default=str,
                    )
                )

            except Exception as exc:
                db.rollback()

                results[
                    scraper.source_name
                ] = {
                    "error": str(exc)
                }

                print(
                    f"{scraper.source_name} "
                    f"failed: {exc}"
                )

    print(
        "\nFinal pipeline summary:"
    )

    print(
        json.dumps(
            results,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()

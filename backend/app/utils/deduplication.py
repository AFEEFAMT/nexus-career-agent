import hashlib
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())

    scheme = parts.scheme.lower()
    hostname = parts.hostname.lower() if parts.hostname else ""

    if parts.port:
        hostname = f"{hostname}:{parts.port}"

    path = parts.path.rstrip("/") or "/"

    query_items = [
        (key, value)
        for key, value in parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
        if key.lower() not in TRACKING_PARAMS
    ]

    query_items.sort()

    return urlunsplit(
        (
            scheme,
            hostname,
            path,
            urlencode(query_items),
            "",
        )
    )


def make_dedup_key(
    source: str,
    source_url: str,
    external_id: str | None = None,
) -> str:
    source = source.strip().lower()

    if external_id:
        identity = (
            f"{source}:{external_id.strip()}"
        )
    else:
        identity = (
            f"{source}:{normalize_url(source_url)}"
        )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def make_content_hash(raw_text: str) -> str:
    normalized_text = " ".join(
        raw_text.split()
    )

    return hashlib.sha256(
        normalized_text.encode("utf-8")
    ).hexdigest()
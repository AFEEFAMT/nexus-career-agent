import asyncio
from pathlib import Path
from time import sleep
from uuid import UUID

import edge_tts
import requests
from google import genai
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import (
    Briefing,
    Job,
    Match,
    Resume,
)


TAVUS_BASE_URL = "https://tavusapi.com/v2"

GENERATED_DIR = (
    Path(__file__).resolve().parents[2]
    / "generated"
)

GENERATED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


class BriefingError(Exception):
    pass


def _is_temporary_gemini_error(
    exc: Exception,
) -> bool:
    message = str(exc).lower()

    code = getattr(
        exc,
        "code",
        None,
    )

    status_code = getattr(
        exc,
        "status_code",
        None,
    )

    return (
        code in {429, 503}
        or status_code in {429, 503}
        or "quota exceeded" in message
        or "rate limit" in message
        or "high demand" in message
        or "503 unavailable" in message
    )


def _get_top_matches(
    db: Session,
    user_id: UUID,
) -> list[tuple[Match, Job]]:
    resume = db.scalar(
        select(Resume)
        .where(
            Resume.user_id
            == user_id
        )
        .order_by(
            Resume.created_at.desc()
        )
        .limit(1)
    )

    if resume is None:
        raise BriefingError(
            "Upload a resume first."
        )

    rows = db.execute(
        select(
            Match,
            Job,
        )
        .join(
            Job,
            Match.job_id == Job.id,
        )
        .where(
            Match.user_id == user_id,
            Match.resume_id == resume.id,
        )
        .order_by(
            Match.score.desc()
        )
        .limit(3)
    ).all()

    if not rows:
        raise BriefingError(
            "Generate job matches first."
        )

    return rows


def _fallback_script(
    rows: list[tuple[Match, Job]],
) -> str:
    parts = [
        (
            "Here is your Nexus career briefing. "
            "These are your three strongest "
            "current semantic job matches."
        )
    ]

    for index, (
        match,
        job,
    ) in enumerate(
        rows,
        start=1,
    ):
        reason = (
            match.justification
            or (
                "This role has meaningful "
                "semantic overlap with your "
                "resume and experience."
            )
        )

        parts.append(
            f"Number {index}: "
            f"{job.title}. "
            f"Your semantic match score is "
            f"{float(match.score):.1f} percent. "
            f"{reason}"
        )

    parts.append(
        "Review each role carefully and "
        "shortlist the opportunities that "
        "best fit your interests and goals."
    )

    return " ".join(parts)


def _generate_script(
    rows: list[tuple[Match, Job]],
) -> str:
    sections = []

    for index, (
        match,
        job,
    ) in enumerate(
        rows,
        start=1,
    ):
        sections.append(
            f"""
MATCH {index}
Title: {job.title}
Company: {job.company or "Not available"}
Match score: {float(match.score):.2f}
Reason: {match.justification or "Not available"}
Job description:
{job.raw_text[:2500]}
""".strip()
        )

    matches_block = "\n\n".join(
        sections
    )

    prompt = f"""
Create a spoken weekly career briefing
using the three job matches below.

Requirements:
- Around 140 to 180 words.
- Natural spoken English.
- Designed for roughly 60 to 90 seconds.
- Mention all three jobs.
- Mention each semantic match score.
- Briefly explain why each job is relevant.
- Use only information provided below.
- Do not invent facts.
- Do not claim the candidate will get hired.
- Do not use markdown or bullet points.
- Return only the narration script.

MATCHES:

{matches_block}
""".strip()

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    for attempt in range(3):
        try:
            response = (
                client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                )
            )

            script = (
                response.text
                or ""
            ).strip()

            if script:
                return script

        except Exception as exc:
            if not _is_temporary_gemini_error(
                exc
            ):
                break

            if attempt < 2:
                sleep(
                    2 ** attempt
                )

    return _fallback_script(
        rows
    )


def _tavus_configured() -> bool:
    return bool(
        settings.TAVUS_API_KEY
        and settings.TAVUS_REPLICA_ID
    )


def _tavus_headers() -> dict:
    return {
        "x-api-key": (
            settings.TAVUS_API_KEY
            or ""
        ),
        "Content-Type": (
            "application/json"
        ),
    }


def _submit_tavus_video(
    script: str,
) -> str:
    if not _tavus_configured():
        raise BriefingError(
            "Tavus is not configured."
        )

    response = requests.post(
        f"{TAVUS_BASE_URL}/videos",
        headers=_tavus_headers(),
        json={
            "replica_id": (
                settings.TAVUS_REPLICA_ID
            ),
            "script": script,
            "video_name": (
                "Nexus Career Briefing"
            ),
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    video_id = (
        payload.get("video_id")
        or (
            payload.get("data", {})
            .get("video_id")
            if isinstance(
                payload.get("data"),
                dict,
            )
            else None
        )
    )

    if not video_id:
        raise BriefingError(
            "Tavus did not return "
            "a video ID."
        )

    return video_id


async def _save_edge_audio(
    script: str,
    output_path: Path,
) -> None:
    communicator = (
        edge_tts.Communicate(
            text=script,
            voice=(
                settings.EDGE_TTS_VOICE
            ),
        )
    )

    await communicator.save(
        str(output_path)
    )


def _generate_audio(
    briefing_id: UUID,
    script: str,
) -> str:
    filename = (
        f"{briefing_id}.mp3"
    )

    output_path = (
        GENERATED_DIR
        / filename
    )

    asyncio.run(
        _save_edge_audio(
            script=script,
            output_path=output_path,
        )
    )

    if not output_path.exists():
        raise BriefingError(
            "Audio file was not generated."
        )

    return (
        f"/media/{filename}"
    )


def _use_audio_fallback(
    db: Session,
    briefing: Briefing,
    script: str,
    reason: str | None = None,
) -> None:
    media_url = _generate_audio(
        briefing_id=briefing.id,
        script=script,
    )

    briefing.briefing_type = "audio"
    briefing.provider = "edge-tts"
    briefing.provider_job_id = None
    briefing.media_url = media_url
    briefing.status = "done"

    briefing.error_message = (
        (
            "Video unavailable; "
            "audio fallback used."
        )
        if reason
        else None
    )

    db.commit()


def process_briefing(
    briefing_id: UUID,
) -> None:
    with SessionLocal() as db:
        briefing = db.get(
            Briefing,
            briefing_id,
        )

        if briefing is None:
            return

        try:
            briefing.status = (
                "processing"
            )

            db.commit()

            rows = _get_top_matches(
                db=db,
                user_id=(
                    briefing.user_id
                ),
            )

            script = _generate_script(
                rows
            )

            briefing.script = script

            db.commit()

            if _tavus_configured():
                try:
                    video_id = (
                        _submit_tavus_video(
                            script
                        )
                    )

                    briefing.briefing_type = (
                        "video"
                    )

                    briefing.provider = (
                        "tavus"
                    )

                    briefing.provider_job_id = (
                        video_id
                    )

                    briefing.media_url = None
                    briefing.error_message = None

                    briefing.status = (
                        "queued"
                    )

                    db.commit()

                    return

                except Exception as exc:
                    _use_audio_fallback(
                        db=db,
                        briefing=briefing,
                        script=script,
                        reason=str(exc),
                    )

                    return

            _use_audio_fallback(
                db=db,
                briefing=briefing,
                script=script,
            )

        except Exception as exc:
            db.rollback()

            failed = db.get(
                Briefing,
                briefing_id,
            )

            if failed is not None:
                failed.status = (
                    "failed"
                )

                failed.error_message = (
                    str(exc)
                )

                db.commit()


def _extract_tavus_video_data(
    payload: dict,
) -> dict:
    # Tavus video-status responses currently
    # expose status and URLs at the top level.
    if (
        "status" in payload
        or "video_status" in payload
        or "download_url" in payload
        or "hosted_url" in payload
    ):
        return payload

    nested = payload.get(
        "data"
    )

    # Also tolerate an API wrapper such as
    # {"data": {"status": "...", ...}}.
    if (
        isinstance(nested, dict)
        and (
            "status" in nested
            or "video_status" in nested
            or "download_url"
            in nested
            or "hosted_url"
            in nested
        )
    ):
        return nested

    return payload


def refresh_tavus_status(
    db: Session,
    briefing: Briefing,
) -> None:
    if (
        briefing.provider != "tavus"
        or not briefing.provider_job_id
        or briefing.status
        not in {
            "queued",
            "processing",
        }
    ):
        return

    if not settings.TAVUS_API_KEY:
        raise BriefingError(
            "Tavus API key is not configured."
        )

    response = requests.get(
        (
            f"{TAVUS_BASE_URL}/videos/"
            f"{briefing.provider_job_id}"
        ),
        headers=_tavus_headers(),
        timeout=20,
    )

    response.raise_for_status()

    payload = response.json()

    data = _extract_tavus_video_data(
        payload
    )

    provider_status = str(
        data.get("status")
        or data.get(
            "video_status"
        )
        or ""
    ).lower()

    # Prefer the direct MP4 URL because
    # the React <video> player can play it.
    media_url = (
        data.get(
            "download_url"
        )
        or data.get(
            "video_url"
        )
        or data.get(
            "hosted_url"
        )
    )

    if provider_status in {
        "ready",
        "completed",
        "complete",
        "success",
    }:
        if not media_url:
            raise BriefingError(
                "Tavus marked the video ready "
                "but did not return a media URL."
            )

        briefing.status = "done"
        briefing.media_url = media_url
        briefing.error_message = None

        db.commit()

        return

    if provider_status in {
        "failed",
        "error",
    }:
        reason = (
            data.get(
                "status_details"
            )
            or data.get(
                "error_message"
            )
            or (
                "Tavus video "
                "generation failed."
            )
        )

        if briefing.script:
            _use_audio_fallback(
                db=db,
                briefing=briefing,
                script=briefing.script,
                reason=reason,
            )

            return

        briefing.status = "failed"
        briefing.error_message = (
            reason
        )

        db.commit()

        return

    if provider_status in {
        "queued",
        "pending",
    }:
        briefing.status = "queued"

    else:
        briefing.status = (
            "processing"
        )

    db.commit()
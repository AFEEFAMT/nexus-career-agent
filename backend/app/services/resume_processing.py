from dataclasses import dataclass

from app.services.embedding import create_embedding
from app.services.pdf_service import extract_pdf_text


@dataclass
class ProcessedResume:
    raw_text: str
    embedding: list[float]


def process_resume(
    pdf_bytes: bytes,
) -> ProcessedResume:
    raw_text = extract_pdf_text(
        pdf_bytes
    )

    embedding = create_embedding(
        raw_text
    )

    return ProcessedResume(
        raw_text=raw_text,
        embedding=embedding,
    )
import pymupdf


MAX_PDF_SIZE = 5 * 1024 * 1024


class PDFExtractionError(Exception):
    pass


def extract_pdf_text(
    pdf_bytes: bytes,
) -> str:
    if not pdf_bytes:
        raise PDFExtractionError(
            "PDF is empty."
        )

    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise PDFExtractionError(
            "PDF must be smaller than 5 MB."
        )

    if not pdf_bytes.startswith(b"%PDF"):
        raise PDFExtractionError(
            "Uploaded file is not a valid PDF."
        )

    try:
        document = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

    except Exception as exc:
        raise PDFExtractionError(
            "Could not open the PDF."
        ) from exc

    try:
        if document.page_count == 0:
            raise PDFExtractionError(
                "PDF has no pages."
            )

        pages = []

        for page in document:
            text = page.get_text(
                "text"
            ).strip()

            if text:
                pages.append(text)

        raw_text = "\n".join(
            pages
        )

    finally:
        document.close()

    raw_text = "\n".join(
        line.strip()
        for line in raw_text.splitlines()
        if line.strip()
    )

    if len(raw_text) < 50:
        raise PDFExtractionError(
            "The PDF contains too little readable text."
        )

    return raw_text
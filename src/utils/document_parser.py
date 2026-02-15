from __future__ import annotations

from io import BytesIO


def extract_text_from_pdf_bytes(data: bytes) -> tuple[str, int]:
    """Return extracted text and page count from PDF bytes."""
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "pypdf is not installed. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

    reader = PdfReader(BytesIO(data))
    pages_text: list[str] = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")

    content = "\n\n".join(chunk.strip() for chunk in pages_text if chunk.strip()).strip()
    return content, len(reader.pages)


def extract_text_from_txt_bytes(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()

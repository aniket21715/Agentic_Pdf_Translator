from __future__ import annotations

from datetime import datetime


_UNICODE_REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2026": "...",
    "\u00a0": " ",
}


def _safe_text(value: str) -> str:
    # Normalize unicode punctuation to avoid Latin-1 encoding failures in default PDF font.
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    for source, target in _UNICODE_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text.encode("latin-1", errors="replace").decode("latin-1")




def build_translated_document_pdf(result: dict) -> bytes:
    """
    Build a PDF containing only the translated document content.
    """
    try:
        from fpdf import FPDF
    except Exception as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "PDF export requires fpdf2. Install with `pip install fpdf2`."
        ) from exc

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.multi_cell(0, 8, _safe_text("Translated Document"))
    pdf.set_font("Helvetica", size=11)
    pdf.ln(1)
    pdf.multi_cell(0, 6, _safe_text(result.get("translated_text", "")))
    return _pdf_output_to_bytes(pdf)


def _pdf_output_to_bytes(pdf) -> bytes:
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    if isinstance(raw, str):
        return raw.encode("latin-1", errors="ignore")
    return bytes(raw)

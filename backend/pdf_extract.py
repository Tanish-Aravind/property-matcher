"""Extract raw text from a property brochure PDF."""
import io
from pypdf import PdfReader


def _sanitize_text(text: str) -> str:
    """Strip null bytes and other control chars that Postgres's UTF8 encoding rejects."""
    return text.replace("\x00", "").replace("\ufeff", "")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract and concatenate text from all pages of a PDF."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(_sanitize_text(text.strip()))
    full_text = "\n\n".join(t for t in pages_text if t)
    if not full_text.strip():
        raise ValueError("No extractable text found in PDF (may be scanned/image-only)")
    return full_text

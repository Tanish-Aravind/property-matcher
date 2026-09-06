"""Basic test for pdf_extract.py — generates a throwaway PDF in-memory, no fixture file needed."""
import io
import pytest
from pypdf import PdfWriter

from pdf_extract import _sanitize_text, extract_text_from_pdf


def _make_test_pdf_bytes(text: str) -> bytes:
    """Build a minimal single-page PDF containing given text, for test purposes."""
    from pypdf import PdfReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    buf.seek(0)
    return buf.read()


def test_extract_text_from_pdf():
    pdf_bytes = _make_test_pdf_bytes("3 bedroom apartment in Koramangala")
    result = extract_text_from_pdf(pdf_bytes)
    assert "Koramangala" in result
    assert "bedroom" in result


def test_extract_text_raises_on_empty_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    with pytest.raises(ValueError):
        extract_text_from_pdf(buf.read())


def test_sanitize_text_removes_postgres_unsafe_characters():
    assert _sanitize_text("\ufeff3\x00 bedroom apartment") == "3 bedroom apartment"

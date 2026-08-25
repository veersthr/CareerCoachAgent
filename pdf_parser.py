"""JD PDF ingestion. Extracts text via PyMuPDF's text layer; any page that
yields too little text is assumed to be a scanned image and is OCR'd via
Tesseract instead. Used by api.py's POST /roadmap/pdf endpoint.
"""

from typing import Union

from config import settings


class PDFParseError(Exception):
    """Raised when a PDF cannot be parsed into usable text."""


MIN_CHARS_PER_PAGE = 20  # below this, a page is assumed to be scanned/image-only


def _configure_tesseract() -> None:
    if settings.tesseract_cmd:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def _ocr_page(page) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise PDFParseError(
            "OCR fallback requires pytesseract and Pillow. Run: pip install pytesseract Pillow"
        ) from exc

    _configure_tesseract()
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    try:
        return pytesseract.image_to_string(img)
    except Exception as exc:
        raise PDFParseError(
            f"Tesseract OCR failed (is the Tesseract binary installed and on PATH, "
            f"or TESSERACT_CMD set?): {exc}"
        ) from exc


def extract_text_from_pdf(source: Union[str, bytes]) -> str:
    """Extracts JD text from a PDF file path or raw bytes.

    Text-layer extraction (PyMuPDF) is tried first for each page; any page
    with fewer than MIN_CHARS_PER_PAGE characters is assumed to be a scanned
    image and is OCR'd via Tesseract instead. Returns the concatenated text
    of all pages, page breaks separated by a blank line.
    """
    try:
        import pymupdf
    except ImportError as exc:
        raise PDFParseError("PyMuPDF is not installed. Run: pip install pymupdf") from exc

    try:
        if isinstance(source, (bytes, bytearray)):
            doc = pymupdf.open(stream=bytes(source), filetype="pdf")
        else:
            doc = pymupdf.open(source)
    except Exception as exc:
        raise PDFParseError(f"Could not open PDF: {exc}") from exc

    pages_text: list[str] = []
    try:
        for page in doc:
            text = page.get_text().strip()
            if len(text) < MIN_CHARS_PER_PAGE:
                text = _ocr_page(page).strip()
            pages_text.append(text)
    finally:
        doc.close()

    full_text = "\n\n".join(pages_text).strip()
    if not full_text:
        raise PDFParseError("No extractable text found in PDF (text layer and OCR both empty).")
    return full_text

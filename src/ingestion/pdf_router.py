"""
DocuLens — PDF Ingestion & Routing Layer
----------------------------------------
Detects whether a PDF has extractable text or is scanned/image-based,
then routes to the appropriate extraction method.

Supports:
  - Text-based PDFs  → PyMuPDF (fast, accurate)
  - Scanned PDFs     → pdf2image + Tesseract OCR (CPU-safe)
  - Mixed PDFs       → per-page routing (some pages text, some scanned)

Classifies document type: invoice | contract | report | unknown
"""

import fitz  # PyMuPDF
import logging
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ── Document type enum ────────────────────────────────────────────────────────

class DocType(str, Enum):
    INVOICE  = "invoice"
    CONTRACT = "contract"
    REPORT   = "report"
    UNKNOWN  = "unknown"


class ExtractionMethod(str, Enum):
    TEXT = "text"   # native PDF text layer
    OCR  = "ocr"    # Tesseract OCR on rendered images
    MIXED = "mixed" # some pages text, some OCR


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class PageResult:
    page_num: int          # 1-indexed
    text: str
    method: ExtractionMethod
    char_count: int = 0
    confidence: Optional[float] = None  # OCR confidence 0-100, None for text

    def __post_init__(self):
        self.char_count = len(self.text.strip())


@dataclass
class IngestionResult:
    file_path: str
    doc_type: DocType
    extraction_method: ExtractionMethod
    pages: list[PageResult] = field(default_factory=list)
    full_text: str = ""
    page_count: int = 0
    language_hint: str = "de"  # German by default
    errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.full_text = "\n\n".join(
            p.text for p in self.pages if p.text.strip()
        )
        self.page_count = len(self.pages)

    @property
    def success(self) -> bool:
        return len(self.pages) > 0 and bool(self.full_text.strip())

    @property
    def avg_ocr_confidence(self) -> Optional[float]:
        ocr_pages = [p for p in self.pages if p.confidence is not None]
        if not ocr_pages:
            return None
        return round(sum(p.confidence for p in ocr_pages) / len(ocr_pages), 1)


# ── Core router ───────────────────────────────────────────────────────────────

class PDFRouter:
    """
    Main entry point. Call process(path) to get an IngestionResult.

    Parameters
    ----------
    text_threshold : float
        Minimum ratio of text characters to page area to consider a page
        "text-based". Pages below this are routed to OCR. Default: 0.01
    ocr_dpi : int
        Resolution for rendering pages before OCR. 200 is fast, 300 is
        more accurate for small fonts. Default: 200
    ocr_lang : str
        Tesseract language string. "deu" = German, "deu+eng" = both.
        Default: "deu+eng"
    """

    def __init__(
        self,
        text_threshold: float = 0.01,
        ocr_dpi: int = 200,
        ocr_lang: str = "deu+eng",
    ):
        self.text_threshold = text_threshold
        self.ocr_dpi = ocr_dpi
        self.ocr_lang = ocr_lang
        self._ocr_available = self._check_ocr()

    def _check_ocr(self) -> bool:
        """Check if pdf2image + pytesseract are installed."""
        try:
            import pytesseract
            import pdf2image  # noqa: F401
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR available.")
            return True
        except Exception as e:
            logger.warning(f"OCR not available: {e}. Scanned pages will be skipped.")
            return False

    def process(self, pdf_path: str | Path) -> IngestionResult:
        """
        Main method. Ingests a PDF and returns structured IngestionResult.

        Usage
        -----
        router = PDFRouter()
        result = router.process("path/to/document.pdf")
        print(result.doc_type)
        print(result.full_text[:500])
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {pdf_path.suffix}")

        logger.info(f"Processing: {pdf_path.name}")

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise RuntimeError(f"Could not open PDF: {e}") from e

        pages: list[PageResult] = []
        methods_used: set[ExtractionMethod] = set()

        for i, page in enumerate(doc):
            page_num = i + 1
            page_result = self._process_page(page, page_num)
            pages.append(page_result)
            methods_used.add(page_result.method)
            logger.debug(
                f"  Page {page_num}: {page_result.method.value}, "
                f"{page_result.char_count} chars"
                + (f", OCR conf={page_result.confidence:.0f}%" if page_result.confidence else "")
            )

        doc.close()

        # Determine overall extraction method
        if methods_used == {ExtractionMethod.TEXT}:
            overall_method = ExtractionMethod.TEXT
        elif methods_used == {ExtractionMethod.OCR}:
            overall_method = ExtractionMethod.OCR
        else:
            overall_method = ExtractionMethod.MIXED

        result = IngestionResult(
            file_path=str(pdf_path),
            doc_type=DocType.UNKNOWN,  # classifier sets this next
            extraction_method=overall_method,
            pages=pages,
        )

        # Classify document type from extracted text
        result.doc_type = classify_doc_type(result.full_text)
        logger.info(
            f"Done: {pdf_path.name} | type={result.doc_type.value} | "
            f"method={overall_method.value} | pages={result.page_count} | "
            f"chars={len(result.full_text)}"
        )
        return result

    def _process_page(self, page: fitz.Page, page_num: int) -> PageResult:
        """Route a single page to text extraction or OCR."""
        # Try native text first — it's fast and free
        text = self._extract_text(page)

        if self._is_text_sufficient(page, text):
            return PageResult(
                page_num=page_num,
                text=_clean_text(text),
                method=ExtractionMethod.TEXT,
            )

        # Text is sparse or missing — try OCR
        if self._ocr_available:
            ocr_text, confidence = self._ocr_page(page)
            return PageResult(
                page_num=page_num,
                text=_clean_text(ocr_text),
                method=ExtractionMethod.OCR,
                confidence=confidence,
            )

        # OCR not available, return whatever text we got (may be empty)
        logger.warning(f"  Page {page_num}: sparse text, OCR unavailable.")
        return PageResult(
            page_num=page_num,
            text=_clean_text(text),
            method=ExtractionMethod.TEXT,
        )

    def _extract_text(self, page: fitz.Page) -> str:
        """Extract native text from a PDF page using PyMuPDF."""
        # "text" mode preserves reading order better than raw extraction
        return page.get_text("text")

    def _is_text_sufficient(self, page: fitz.Page, text: str) -> bool:
        """
        Decide if the extracted text is usable.
        Compares text character count against page area.
        A mostly-image page returns very few characters.
        """
        rect = page.rect
        page_area = rect.width * rect.height
        if page_area == 0:
            return False
        char_density = len(text.strip()) / page_area
        return char_density >= self.text_threshold

    def _ocr_page(self, page: fitz.Page) -> tuple[str, float]:
        """
        Render page to image and run Tesseract OCR.
        Returns (text, confidence_score).
        """
        import pytesseract
        from PIL import Image
        import io

        # Render page to PNG bytes using PyMuPDF (no poppler needed!)
        mat = fitz.Matrix(self.ocr_dpi / 72, self.ocr_dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img_bytes = pix.tobytes("png")

        img = Image.open(io.BytesIO(img_bytes))

        # Get text + confidence data
        data = pytesseract.image_to_data(
            img,
            lang=self.ocr_lang,
            output_type=pytesseract.Output.DICT,
            config="--psm 3",  # fully automatic page segmentation
        )

        # Filter confident words and compute average confidence
        words, confidences = [], []
        for word, conf in zip(data["text"], data["conf"]):
            if int(conf) > 0 and word.strip():
                words.append(word)
                confidences.append(int(conf))

        text = " ".join(words)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        return text, round(avg_conf, 1)


# ── Document type classifier ──────────────────────────────────────────────────

# German keyword sets per document type
_KEYWORDS: dict[DocType, list[str]] = {
    DocType.INVOICE: [
        "rechnung", "invoice", "rechnungsnummer", "rechnungsdatum",
        "zahlbar", "fälligkeit", "netto", "brutto", "mwst", "mehrwertsteuer",
        "iban", "bankverbindung", "betrag", "gesamtbetrag", "lieferschein",
        "steuernummer", "ust-id", "eur", "€",
    ],
    DocType.CONTRACT: [
        "vertrag", "vereinbarung", "vertragspartei", "auftraggeber",
        "auftragnehmer", "leistung", "laufzeit", "kündigung", "kündigungsfrist",
        "sla", "dienstleistungsvertrag", "rahmenvertrag", "vertragsgegenstand",
        "haftung", "gewährleistung", "datenschutz", "unterschrift", "partei",
    ],
    DocType.REPORT: [
        "bericht", "report", "analyse", "zusammenfassung", "ergebnis",
        "fazit", "kennzahl", "kpi", "quartal", "geschäftsjahr", "umsatz",
        "jahresbericht", "lagebericht", "prüfungsbericht", "management",
    ],
}


def classify_doc_type(text: str) -> DocType:
    """
    Score text against keyword lists and return the best-matching DocType.
    Simple but effective for the three main German document types.
    """
    if not text.strip():
        return DocType.UNKNOWN

    text_lower = text.lower()
    scores: dict[DocType, int] = {dt: 0 for dt in _KEYWORDS}

    for doc_type, keywords in _KEYWORDS.items():
        for kw in keywords:
            scores[doc_type] += text_lower.count(kw)

    best_type = max(scores, key=lambda dt: scores[dt])
    best_score = scores[best_type]

    logger.debug(f"Classification scores: {scores}")
    return best_type if best_score > 0 else DocType.UNKNOWN


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """
    Normalize extracted text:
    - Collapse excessive whitespace
    - Fix common PDF extraction artifacts (ligatures, broken hyphens)
    - Preserve paragraph breaks (double newlines)
    """
    import re

    # Fix common PDF ligature issues
    replacements = {
        "\ufb01": "fi",  # ﬁ ligature
        "\ufb02": "fl",  # ﬂ ligature
        "\ufb00": "ff",  # ﬀ ligature
        "\ufb03": "ffi", # ﬃ ligature
        "\ufb04": "ffl", # ﬄ ligature
        "\u00ad": "",    # soft hyphen
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Collapse multiple spaces (but keep newlines)
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse more than 2 consecutive newlines into exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove lines that are just whitespace
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()

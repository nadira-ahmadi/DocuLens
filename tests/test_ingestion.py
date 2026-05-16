"""
DocuLens — Tests for the PDF ingestion layer
---------------------------------------------
Run with:  pytest tests/ -v

Tests cover:
  - PDF router routing logic
  - Text extraction from generated PDFs
  - Document type classification (German keywords)
  - Text cleaning utilities
  - IngestionResult properties
"""

import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pdf_router import (
    PDFRouter,
    DocType,
    ExtractionMethod,
    IngestionResult,
    PageResult,
    classify_doc_type,
    _clean_text,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_invoice(tmp_path_factory):
    """Generate a real synthetic invoice PDF for testing."""
    from src.utils.generate_samples import generate_invoice
    path = tmp_path_factory.mktemp("pdfs") / "test_invoice.pdf"
    generate_invoice(path, seed=42)
    return path


@pytest.fixture(scope="session")
def router():
    return PDFRouter()


# ── Text cleaning tests ───────────────────────────────────────────────────────

class TestCleanText:
    def test_removes_ligatures(self):
        result = _clean_text("pro\ufb01t und e\ufb00ektiv")
        assert "ﬁ" not in result
        assert "ﬀ" not in result
        assert "profit" in result
        assert "effektiv" in result

    def test_collapses_spaces(self):
        result = _clean_text("Muster    GmbH   AG")
        assert "  " not in result
        assert "Muster GmbH AG" in result

    def test_collapses_excess_newlines(self):
        result = _clean_text("Zeile 1\n\n\n\n\nZeile 2")
        assert "\n\n\n" not in result
        assert "Zeile 1" in result
        assert "Zeile 2" in result

    def test_empty_string(self):
        assert _clean_text("") == ""

    def test_strips_whitespace(self):
        result = _clean_text("  Hallo Welt  \n")
        assert result == "Hallo Welt"


# ── Classification tests ──────────────────────────────────────────────────────

class TestClassifyDocType:
    def test_invoice_keywords(self):
        text = "Rechnung Nr. 1234 | Gesamtbetrag: 1.500,00 € | MwSt. 19% | IBAN: DE89..."
        assert classify_doc_type(text) == DocType.INVOICE

    def test_contract_keywords(self):
        text = "Dienstleistungsvertrag zwischen Auftraggeber und Auftragnehmer. Laufzeit 12 Monate. Kündigung mit 3 Monaten Frist."
        assert classify_doc_type(text) == DocType.CONTRACT

    def test_report_keywords(self):
        text = "Quartalsbericht Q3 2025 – Zusammenfassung der Kennzahlen und KPIs. Jahresbericht Ergebnis."
        assert classify_doc_type(text) == DocType.REPORT

    def test_empty_text(self):
        assert classify_doc_type("") == DocType.UNKNOWN

    def test_random_text(self):
        assert classify_doc_type("Lorem ipsum dolor sit amet") == DocType.UNKNOWN

    def test_case_insensitive(self):
        text = "RECHNUNG GESAMTBETRAG MWST IBAN"
        assert classify_doc_type(text) == DocType.INVOICE

    def test_german_english_mixed(self):
        # Should still detect invoice with mixed language
        text = "Invoice / Rechnung | Total amount | Gesamtbetrag | IBAN"
        assert classify_doc_type(text) == DocType.INVOICE


# ── PageResult tests ──────────────────────────────────────────────────────────

class TestPageResult:
    def test_char_count_set_on_init(self):
        page = PageResult(page_num=1, text="Hallo Welt", method=ExtractionMethod.TEXT)
        assert page.char_count == 10

    def test_empty_text(self):
        page = PageResult(page_num=1, text="", method=ExtractionMethod.TEXT)
        assert page.char_count == 0

    def test_confidence_none_for_text(self):
        page = PageResult(page_num=1, text="Text", method=ExtractionMethod.TEXT)
        assert page.confidence is None


# ── IngestionResult tests ─────────────────────────────────────────────────────

class TestIngestionResult:
    def _make_result(self, texts: list[str], method=ExtractionMethod.TEXT):
        pages = [
            PageResult(page_num=i+1, text=t, method=method)
            for i, t in enumerate(texts)
        ]
        return IngestionResult(
            file_path="test.pdf",
            doc_type=DocType.INVOICE,
            extraction_method=method,
            pages=pages,
        )

    def test_full_text_concatenates_pages(self):
        result = self._make_result(["Seite eins", "Seite zwei"])
        assert "Seite eins" in result.full_text
        assert "Seite zwei" in result.full_text

    def test_page_count(self):
        result = self._make_result(["A", "B", "C"])
        assert result.page_count == 3

    def test_success_true_when_text_present(self):
        result = self._make_result(["Genug Text hier"])
        assert result.success is True

    def test_success_false_when_empty(self):
        result = self._make_result(["", "  ", "\n"])
        assert result.success is False

    def test_avg_ocr_confidence_none_for_text(self):
        result = self._make_result(["Text"])
        assert result.avg_ocr_confidence is None

    def test_avg_ocr_confidence_computed(self):
        pages = [
            PageResult(page_num=1, text="A", method=ExtractionMethod.OCR, confidence=80.0),
            PageResult(page_num=2, text="B", method=ExtractionMethod.OCR, confidence=90.0),
        ]
        result = IngestionResult(
            file_path="test.pdf",
            doc_type=DocType.INVOICE,
            extraction_method=ExtractionMethod.OCR,
            pages=pages,
        )
        assert result.avg_ocr_confidence == 85.0


# ── Integration tests (need actual PDF) ──────────────────────────────────────

class TestPDFRouterIntegration:
    def test_process_generated_invoice(self, router, sample_invoice):
        result = router.process(sample_invoice)
        assert result.success
        assert result.page_count >= 1
        assert result.doc_type == DocType.INVOICE
        # ReportLab PDFs embed text as vector graphics — router may use OCR
        assert result.extraction_method in (ExtractionMethod.TEXT, ExtractionMethod.OCR, ExtractionMethod.MIXED)
        assert len(result.full_text) > 100

    def test_invoice_contains_expected_fields(self, router, sample_invoice):
        result = router.process(sample_invoice)
        text_lower = result.full_text.lower()
        # All generated invoices have these German terms
        assert "rechnung" in text_lower
        assert "€" in result.full_text or "eur" in text_lower

    def test_file_not_found_raises(self, router):
        with pytest.raises(FileNotFoundError):
            router.process("does_not_exist.pdf")

    def test_non_pdf_raises(self, router, tmp_path):
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError):
            router.process(txt)

    def test_result_has_file_path(self, router, sample_invoice):
        result = router.process(sample_invoice)
        assert result.file_path == str(sample_invoice)

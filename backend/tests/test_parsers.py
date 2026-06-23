"""Tests for document parsers — validate_upload + parse functions."""

import pytest

from app.services.ingestion.parsers import (
    ParsedSegment,
    _ext,
    _render_rows,
    parse_csv,
    parse_document,
    parse_pdf,
    validate_upload,
)


# ── _ext ──


class TestExt:
    def test_pdf(self):
        assert _ext("report.PDF") == ".pdf"

    def test_dotless(self):
        assert _ext("README") == ""

    def test_nested_dots(self):
        assert _ext("archive.tar.gz") == ".gz"

    def test_docx(self):
        assert _ext("My File.DOCX") == ".docx"


# ── validate_upload ──


class TestValidateUpload:
    def test_valid_pdf(self):
        assert validate_upload("doc.pdf", b"%PDF-1.7 content") is None

    def test_valid_csv(self):
        assert validate_upload("data.csv", b"a,b,c\n1,2,3") is None

    def test_valid_docx(self):
        assert validate_upload("doc.docx", b"PK\x03\x04 rest") is None

    def test_valid_xlsx(self):
        assert validate_upload("data.xlsx", b"PK\x03\x04 rest") is None

    def test_unsupported_extension(self):
        err = validate_upload("image.png", b"PNG data")
        assert err is not None
        assert "Obsługiwane formaty" in err

    def test_legacy_doc(self):
        err = validate_upload("old.doc", b"\xd0\xcf\x11\xe0")
        assert err is not None
        assert ".docx" in err

    def test_legacy_xls(self):
        err = validate_upload("old.xls", b"\xd0\xcf\x11\xe0")
        assert err is not None
        assert ".xlsx" in err

    def test_pdf_bad_magic(self):
        err = validate_upload("fake.pdf", b"NOT A PDF")
        assert err is not None
        assert "PDF" in err

    def test_docx_bad_magic(self):
        err = validate_upload("fake.docx", b"NOT A ZIP")
        assert err is not None
        assert "uszkodzony" in err

    def test_empty_filename(self):
        err = validate_upload("", b"data")
        assert err is not None


# ── _render_rows ──


class TestRenderRows:
    def test_basic(self):
        result = _render_rows(["Name", "Age"], [["Alice", "30"], ["Bob", "25"]])
        assert "Name: Alice" in result
        assert "Age: 30" in result
        assert "Name: Bob" in result

    def test_empty_values_skipped(self):
        result = _render_rows(["A", "B"], [["val", "  "]])
        assert "A: val" in result
        assert "B:" not in result

    def test_empty_rows(self):
        result = _render_rows(["A"], [])
        assert result == ""


# ── parse_csv ──


class TestParseCsv:
    def test_simple(self):
        data = "Imie,Wiek\nAlice,30\nBob,25".encode()
        segments = parse_csv(data)
        assert len(segments) >= 1
        assert segments[0].page == 1
        assert "wiersze" in segments[0].location
        assert "Imie: Alice" in segments[0].text

    def test_semicolon_delimiter(self):
        data = "A;B\n1;2\n3;4".encode()
        segments = parse_csv(data)
        assert len(segments) >= 1
        assert "A: 1" in segments[0].text

    def test_empty_csv(self):
        segments = parse_csv(b"")
        assert segments == []

    def test_header_only(self):
        segments = parse_csv(b"A,B,C\n")
        assert segments == []


# ── parse_pdf ──


class TestParsePdf:
    def test_real_minimal_pdf(self):
        pdf_bytes = _make_minimal_pdf("Hello World")
        segments = parse_pdf(pdf_bytes)
        assert len(segments) == 1
        assert "Hello" in segments[0].text
        assert segments[0].page == 1
        assert segments[0].location == "s. 1"


# ── parse_document dispatch ──


class TestParseDocument:
    def test_csv_dispatch(self):
        data = "X,Y\n1,2".encode()
        segments = parse_document("file.csv", data)
        assert len(segments) >= 1

    def test_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            parse_document("file.xyz", b"data")


def _make_minimal_pdf(text: str) -> bytes:
    """Create a minimal valid single-page PDF with the given text."""
    content = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
    content_length = len(content)
    return (
        f"%PDF-1.0\n"
        f"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        f"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        f"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        f"/Contents 4 0 R/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
        f"4 0 obj<</Length {content_length}>>\nstream\n{content}\nendstream\nendobj\n"
        f"xref\n0 5\n"
        f"0000000000 65535 f \n"
        f"0000000009 00000 n \n"
        f"0000000058 00000 n \n"
        f"0000000115 00000 n \n"
        f"0000000316 00000 n \n"
        f"trailer<</Size 5/Root 1 0 R>>\n"
        f"startxref\n416\n%%EOF"
    ).encode()

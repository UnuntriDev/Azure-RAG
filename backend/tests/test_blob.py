"""Tests for blob storage helpers (pure functions only)."""

import uuid

from app.services.storage.blob import blob_name_for


class TestBlobNameFor:
    def test_pdf(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        assert blob_name_for(uid, "report.pdf") == "12345678-1234-1234-1234-123456789abc.pdf"

    def test_docx(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        assert blob_name_for(uid, "doc.DOCX") == "12345678-1234-1234-1234-123456789abc.docx"

    def test_xlsx(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        assert blob_name_for(uid, "data.xlsx") == "12345678-1234-1234-1234-123456789abc.xlsx"

    def test_csv(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        assert blob_name_for(uid, "data.csv") == "12345678-1234-1234-1234-123456789abc.csv"

    def test_no_filename_fallback(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        result = blob_name_for(uid)
        assert result == "12345678-1234-1234-1234-123456789abc.bin"

    def test_empty_filename_fallback(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        result = blob_name_for(uid, "")
        assert result.endswith(".bin")

    def test_no_extension_fallback(self):
        uid = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        result = blob_name_for(uid, "README")
        assert result.endswith(".bin")

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import sqlite

from app.scheduler import booking_document_cleanup
from app.services import cdn_service


def test_cleanup_deletes_documents_returned_at_least_ten_days_ago(monkeypatch):
    document = SimpleNamespace(id="document-id", file_url="private/admin-documents/file.pdf")
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [document]
    monkeypatch.setattr(
        booking_document_cleanup,
        "delete_private_document_file",
        lambda file_url: file_url == document.file_url,
    )

    summary = booking_document_cleanup.cleanup_expired_booking_documents(
        db,
        today=date(2026, 11, 5),
    )

    statement = db.execute.call_args.args[0]
    compiled_statement = statement.compile(dialect=sqlite.dialect())
    assert "return_date <= ?" in str(compiled_statement)
    assert date(2026, 10, 26) in compiled_statement.params.values()
    db.delete.assert_called_once_with(document)
    db.commit.assert_called_once()
    assert summary == {"documents_deleted": 1, "files_deleted": 1}


def test_cleanup_retains_document_if_private_file_cannot_be_deleted(monkeypatch):
    document = SimpleNamespace(id="document-id", file_url="invalid/path")
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = [document]

    def reject_file(_file_url):
        raise HTTPException(status_code=404, detail="Document not found")

    monkeypatch.setattr(
        booking_document_cleanup,
        "delete_private_document_file",
        reject_file,
    )

    summary = booking_document_cleanup.cleanup_expired_booking_documents(
        db,
        today=date(2026, 11, 5),
    )

    db.delete.assert_not_called()
    db.commit.assert_called_once()
    assert summary == {"documents_deleted": 0, "files_deleted": 0}


def test_delete_private_document_file_removes_only_valid_files(tmp_path, monkeypatch):
    private_folder = tmp_path / "private" / "admin-documents"
    private_folder.mkdir(parents=True)
    file_path = private_folder / "0123456789abcdef0123456789abcdef.pdf"
    file_path.write_bytes(b"booking document")
    monkeypatch.setattr(cdn_service, "CDN_ROOT", tmp_path)

    assert cdn_service.delete_private_document_file(
        "private/admin-documents/0123456789abcdef0123456789abcdef.pdf"
    )
    assert not file_path.exists()
    assert not cdn_service.delete_private_document_file(
        "private/admin-documents/0123456789abcdef0123456789abcdef.pdf"
    )

    with pytest.raises(HTTPException):
        cdn_service.delete_private_document_file("../outside/file.pdf")

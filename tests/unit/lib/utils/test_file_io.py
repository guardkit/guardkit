"""
Unit tests for file_io utility module.

Tests safe_read_file and safe_write_file functions with various error conditions.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from lib.utils.file_io import safe_read_file, safe_write_file


class TestSafeReadFile:
    """Tests for safe_read_file function."""

    def test_read_existing_file_success(self, tmp_path):
        """Test reading an existing file successfully."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!\nLine 2"
        test_file.write_text(test_content)

        success, content = safe_read_file(test_file)

        assert success is True
        assert content == test_content

    def test_read_file_not_found(self, tmp_path):
        """Test file not found error."""
        missing_file = tmp_path / "missing.txt"

        success, msg = safe_read_file(missing_file)

        assert success is False
        assert "File not found" in msg
        assert str(missing_file) in msg

    def test_read_permission_denied(self, tmp_path, monkeypatch):
        """Test permission denied error."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        def mock_read_text(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        success, msg = safe_read_file(test_file)

        assert success is False
        assert "Permission denied" in msg
        assert str(test_file) in msg

    def test_read_unicode_decode_error(self, tmp_path):
        """Test unicode decode error."""
        test_file = tmp_path / "binary.bin"
        # Write binary content that will fail UTF-8 decoding
        test_file.write_bytes(b'\x80\x81\x82\x83')

        success, msg = safe_read_file(test_file)

        assert success is False
        assert "Encoding error" in msg
        assert str(test_file) in msg

    def test_read_custom_encoding(self, tmp_path):
        """Test reading with custom encoding."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content, encoding='latin-1')

        success, content = safe_read_file(test_file, encoding='latin-1')

        assert success is True
        assert content == test_content

    def test_read_os_error(self, tmp_path, monkeypatch):
        """Test OSError handling."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        def mock_read_text(*args, **kwargs):
            raise OSError(5, "Input/output error")

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        success, msg = safe_read_file(test_file)

        assert success is False
        assert "I/O error" in msg
        assert str(test_file) in msg

    def test_read_unexpected_error(self, tmp_path, monkeypatch):
        """Test unexpected error handling."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        def mock_read_text(*args, **kwargs):
            raise ValueError("Unexpected error")

        monkeypatch.setattr(Path, "read_text", mock_read_text)

        success, msg = safe_read_file(test_file)

        assert success is False
        assert "Unexpected error" in msg
        assert str(test_file) in msg


class TestSafeWriteFile:
    """Tests for safe_write_file function."""

    def test_write_file_success(self, tmp_path):
        """Test writing file successfully."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!\nLine 2"

        success, error_msg = safe_write_file(test_file, test_content)

        assert success is True
        assert error_msg is None
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_write_permission_denied(self, tmp_path, monkeypatch):
        """Test permission denied error."""
        test_file = tmp_path / "test.txt"

        def mock_write_text(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        success, msg = safe_write_file(test_file, "content")

        assert success is False
        assert msg is not None
        assert "Permission denied" in msg
        assert str(test_file) in msg

    def test_write_unicode_encode_error(self, tmp_path, monkeypatch):
        """Test unicode encode error."""
        test_file = tmp_path / "test.txt"

        def mock_write_text(*args, **kwargs):
            raise UnicodeEncodeError('ascii', 'test', 0, 1, 'ordinal not in range')

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        success, msg = safe_write_file(test_file, "content")

        assert success is False
        assert msg is not None
        assert "Encoding error" in msg
        assert str(test_file) in msg

    def test_write_disk_full(self, tmp_path, monkeypatch):
        """Test disk full error (ENOSPC)."""
        test_file = tmp_path / "test.txt"

        def mock_write_text(*args, **kwargs):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        success, msg = safe_write_file(test_file, "content")

        assert success is False
        assert msg is not None
        assert "I/O error" in msg
        assert str(test_file) in msg

    def test_write_path_too_long(self, tmp_path, monkeypatch):
        """Test path too long error (ENAMETOOLONG)."""
        test_file = tmp_path / "test.txt"

        def mock_write_text(*args, **kwargs):
            raise OSError(36, "File name too long")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        success, msg = safe_write_file(test_file, "content")

        assert success is False
        assert msg is not None
        assert "I/O error" in msg
        assert str(test_file) in msg

    def test_write_custom_encoding(self, tmp_path):
        """Test writing with custom encoding."""
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"

        success, error_msg = safe_write_file(test_file, test_content, encoding='latin-1')

        assert success is True
        assert error_msg is None
        assert test_file.exists()
        # Read with same encoding to verify
        assert test_file.read_text(encoding='latin-1') == test_content

    def test_write_unexpected_error(self, tmp_path, monkeypatch):
        """Test unexpected error handling."""
        test_file = tmp_path / "test.txt"

        def mock_write_text(*args, **kwargs):
            raise ValueError("Unexpected error")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        success, msg = safe_write_file(test_file, "content")

        assert success is False
        assert msg is not None
        assert "Unexpected error" in msg
        assert str(test_file) in msg

    def test_write_overwrite_existing(self, tmp_path):
        """Test overwriting existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content")

        new_content = "new content"
        success, error_msg = safe_write_file(test_file, new_content)

        assert success is True
        assert error_msg is None
        assert test_file.read_text() == new_content


class TestFileIOLogging:
    """Tests for logging behavior."""

    def test_read_error_logged(self, tmp_path, caplog):
        """Test that read errors are logged."""
        import logging
        caplog.set_level(logging.ERROR)

        missing_file = tmp_path / "missing.txt"
        safe_read_file(missing_file)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "File not found" in caplog.records[0].message

    def test_write_error_logged(self, tmp_path, monkeypatch, caplog):
        """Test that write errors are logged."""
        import logging
        caplog.set_level(logging.ERROR)

        test_file = tmp_path / "test.txt"

        def mock_write_text(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        safe_write_file(test_file, "content")

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "Permission denied" in caplog.records[0].message

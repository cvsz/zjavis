"""Unit tests for SSRF prevention and path traversal prevention."""

from __future__ import annotations

import os
import tempfile

import pytest

from jarvis.core.exceptions import ValidationError
from jarvis.core.security import (
    is_private_ip,
    validate_safe_path,
    validate_ssrf_safe_url,
)


class TestIsPrivateIP:
    """Tests for private IP address detection."""

    def test_private_10_range(self) -> None:
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True

    def test_private_172_range(self) -> None:
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True
        assert is_private_ip("172.15.255.255") is False
        assert is_private_ip("172.32.0.0") is False

    def test_private_192_168_range(self) -> None:
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True

    def test_loopback(self) -> None:
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.255.255.255") is True

    def test_link_local(self) -> None:
        assert is_private_ip("169.254.0.1") is True

    def test_public_ip(self) -> None:
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
        assert is_private_ip("203.0.113.5") is False

    def test_multicast(self) -> None:
        assert is_private_ip("224.0.0.1") is True

    def test_invalid_ip(self) -> None:
        assert is_private_ip("not.an.ip") is False
        assert is_private_ip("") is False
        assert is_private_ip("999.999.999.999") is False


class TestValidateSSRFSafeURL:
    """Tests for SSRF-safe URL validation."""

    def test_https_public_url(self) -> None:
        validate_ssrf_safe_url("https://example.com/api")

    def test_http_public_url(self) -> None:
        validate_ssrf_safe_url("http://example.com/api")

    def test_private_ip_blocked(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_ssrf_safe_url("http://10.0.0.1/api")
        assert exc.value.code == "ssrf_private_address"

    def test_loopback_blocked(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_ssrf_safe_url("http://127.0.0.1/api")
        assert exc.value.code == "ssrf_private_address"

    def test_link_local_blocked(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_ssrf_safe_url("http://169.254.169.254/metadata")
        assert exc.value.code == "ssrf_private_address"

    def test_unsafe_scheme_blocked(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_ssrf_safe_url("ftp://example.com/file")
        assert exc.value.code == "unsafe_url_scheme"

    def test_file_scheme_blocked(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_ssrf_safe_url("file:///etc/passwd")
        assert exc.value.code == "unsafe_url_scheme"

    def test_missing_hostname(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_ssrf_safe_url("http:///path")
        assert exc.value.code == "missing_hostname"

    def test_invalid_url(self) -> None:
        with pytest.raises(ValidationError):
            validate_ssrf_safe_url("not-a-url")


class TestValidateSafePath:
    """Tests for path traversal prevention."""

    def test_safe_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_safe_path(tmp, "subdir/file.txt")
            assert result.startswith(tmp)
            assert "subdir" in result

    def test_traversal_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(ValidationError) as exc:
                validate_safe_path(tmp, "../../../etc/passwd")
            assert exc.value.code == "path_traversal"

    def test_traversal_with_dotdot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, pytest.raises(ValidationError):
            validate_safe_path(tmp, "..//..//etc/passwd")

    def test_null_byte_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(ValidationError) as exc:
                validate_safe_path(tmp, "file\x00.txt")
            assert exc.value.code == "path_null_byte"

    def test_absolute_path_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(ValidationError) as exc:
                validate_safe_path(tmp, "/etc/passwd")
            assert exc.value.code == "absolute_path_not_allowed"

    def test_absolute_path_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "allowed.txt")
            result = validate_safe_path(tmp, target, allow_absolute=True)
            assert result == os.path.realpath(target)

    def test_nonexistent_base_dir(self) -> None:
        with pytest.raises(ValidationError) as exc:
            validate_safe_path("/nonexistent/dir", "file.txt")
        assert exc.value.code == "invalid_base_directory"

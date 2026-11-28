"""Unit tests for the JARVIS Voice service audio validation (Phase 4).

Covers audio payload validation without external credentials. Real STT/TTS
integration requires audio hardware and live API credentials and remains
BLOCKED in this environment.
"""

from __future__ import annotations

import pytest

from jarvis.ai.voice import MAX_AUDIO_BYTES, validate_audio


class TestValidateAudio:
    """Tests for audio payload validation."""

    def test_valid_audio(self) -> None:
        # Should not raise.
        validate_audio(b"\x00\x01\x02\x03")

    def test_empty_audio_raises(self) -> None:
        with pytest.raises(ValueError, match="Audio data is empty"):
            validate_audio(b"")

    def test_too_large_raises(self) -> None:
        oversized = b"\x00" * (MAX_AUDIO_BYTES + 1)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            validate_audio(oversized)

    def test_at_limit_is_allowed(self) -> None:
        at_limit = b"\x00" * MAX_AUDIO_BYTES
        # Should not raise.
        validate_audio(at_limit)

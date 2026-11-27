"""Unit tests for the JARVIS voice and vision API endpoints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jarvis.api.vision import AnalyzeImageRequest, DescribeImageRequest
from jarvis.api.voice import SpeechToTextRequest, TextToSpeechRequest


class TestSpeechToTextRequest:
    """Tests for SpeechToTextRequest model."""

    def test_valid(self) -> None:
        import base64

        audio = base64.b64encode(b"fake audio").decode("ascii")
        req = SpeechToTextRequest(audio_b64=audio, language="en-US")
        assert req.language == "en-US"

    def test_defaults(self) -> None:
        import base64

        audio = base64.b64encode(b"fake audio").decode("ascii")
        req = SpeechToTextRequest(audio_b64=audio)
        assert req.language is None

    def test_language_too_long(self) -> None:
        import base64

        audio = base64.b64encode(b"fake audio").decode("ascii")
        with pytest.raises(ValidationError):
            SpeechToTextRequest(audio_b64=audio, language="x" * 11)


class TestTextToSpeechRequest:
    """Tests for TextToSpeechRequest model."""

    def test_valid(self) -> None:
        req = TextToSpeechRequest(text="Hello world", voice="alloy", language="en")
        assert req.text == "Hello world"
        assert req.voice == "alloy"
        assert req.language == "en"

    def test_text_empty(self) -> None:
        with pytest.raises(ValidationError):
            TextToSpeechRequest(text="")

    def test_text_too_long(self) -> None:
        with pytest.raises(ValidationError):
            TextToSpeechRequest(text="x" * 4001)

    def test_voice_too_long(self) -> None:
        with pytest.raises(ValidationError):
            TextToSpeechRequest(text="hi", voice="x" * 51)

    def test_language_too_long(self) -> None:
        with pytest.raises(ValidationError):
            TextToSpeechRequest(text="hi", language="x" * 11)


class TestDescribeImageRequest:
    """Tests for DescribeImageRequest model."""

    def test_valid(self) -> None:
        import base64

        img = base64.b64encode(b"fake image").decode("ascii")
        req = DescribeImageRequest(image_b64=img, prompt="What is this?")
        assert req.prompt == "What is this?"

    def test_prompt_too_long(self) -> None:
        import base64

        img = base64.b64encode(b"fake image").decode("ascii")
        with pytest.raises(ValidationError):
            DescribeImageRequest(image_b64=img, prompt="x" * 1001)


class TestAnalyzeImageRequest:
    """Tests for AnalyzeImageRequest model."""

    def test_valid(self) -> None:
        import base64

        img = base64.b64encode(b"fake image").decode("ascii")
        req = AnalyzeImageRequest(image_b64=img, questions=["What color?", "What shape?"])
        assert len(req.questions) == 2

    def test_questions_empty(self) -> None:
        import base64

        img = base64.b64encode(b"fake image").decode("ascii")
        with pytest.raises(ValidationError):
            AnalyzeImageRequest(image_b64=img, questions=[])

    def test_questions_too_many(self) -> None:
        import base64

        img = base64.b64encode(b"fake image").decode("ascii")
        with pytest.raises(ValidationError):
            AnalyzeImageRequest(
                image_b64=img, questions=["q"] * 11
            )
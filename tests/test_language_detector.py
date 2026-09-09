import pytest

from src.tts.language_detector import detect_language, segment_by_language


class TestDetectLanguage:
    def test_russian_text(self) -> None:
        assert detect_language("Привет мир") == "ru"

    def test_english_text(self) -> None:
        assert detect_language("Hello world") == "en"

    def test_mixed_more_russian(self) -> None:
        assert detect_language("Привет world это test") == "ru"

    def test_mixed_more_english(self) -> None:
        assert detect_language("Hello мир world это test") == "en"

    def test_only_digits(self) -> None:
        assert detect_language("123 456") == "ru"

    def test_empty_string(self) -> None:
        assert detect_language("") == "ru"

    def test_only_punctuation(self) -> None:
        assert detect_language("... !!!") == "ru"


class TestSegmentByLanguage:
    def test_pure_russian(self) -> None:
        result = segment_by_language("Привет мир")
        assert result == [("ru", "Привет мир")]

    def test_pure_english(self) -> None:
        result = segment_by_language("Hello world")
        assert result == [("en", "Hello world")]

    def test_russian_then_english(self) -> None:
        result = segment_by_language("Привет Hello")
        assert len(result) == 2
        assert result[0][0] == "ru"
        assert result[1][0] == "en"

    def test_english_then_russian(self) -> None:
        result = segment_by_language("Hello Привет")
        assert len(result) == 2
        assert result[0][0] == "en"
        assert result[1][0] == "ru"

    def test_three_segments(self) -> None:
        result = segment_by_language("Привет Hello Мир")
        assert len(result) == 3
        assert result[0][0] == "ru"
        assert result[1][0] == "en"
        assert result[2][0] == "ru"

    def test_empty_string(self) -> None:
        result = segment_by_language("")
        assert result == []

    def test_whitespace_only(self) -> None:
        result = segment_by_language("   ")
        assert result == []

    def test_digits_attached_to_language(self) -> None:
        result = segment_by_language("Привет 123")
        assert len(result) == 1
        assert result[0][0] == "ru"

    def test_mixed_with_punctuation(self) -> None:
        result = segment_by_language("Привет! Hello! Мир.")
        assert len(result) == 3
        assert result[0][0] == "ru"
        assert result[1][0] == "en"
        assert result[2][0] == "ru"

import re

from loguru import logger

_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF\u0500-\u052F]")
_LATIN_RE = re.compile(r"[a-zA-Z]")
_NEUTRAL_RE = re.compile(r"[0-9\s\.,!?;:\-\"'()\[\]{}@#$%^&*+=/\\<>~`]")


def _char_language(char: str) -> str | None:
    if _CYRILLIC_RE.match(char):
        return "ru"
    if _LATIN_RE.match(char):
        return "en"
    return None


def detect_language(text: str) -> str:
    cyrillic_count = len(_CYRILLIC_RE.findall(text))
    latin_count = len(_LATIN_RE.findall(text))
    if cyrillic_count == 0 and latin_count == 0:
        return "ru"
    return "ru" if cyrillic_count >= latin_count else "en"


def segment_by_language(text: str) -> list[tuple[str, str]]:
    if not text.strip():
        return []

    segments: list[tuple[str, str]] = []
    current_lang: str | None = None
    current_chars: list[str] = []

    for char in text:
        char_lang = _char_language(char)

        if char_lang is not None:
            if current_lang is None:
                current_lang = char_lang
                current_chars.append(char)
            elif char_lang == current_lang:
                current_chars.append(char)
            else:
                segment_text = "".join(current_chars).strip()
                if segment_text:
                    segments.append((current_lang, segment_text))
                current_lang = char_lang
                current_chars = [char]
        else:
            current_chars.append(char)

    if current_lang is not None:
        segment_text = "".join(current_chars).strip()
        if segment_text:
            segments.append((current_lang, segment_text))
    else:
        segment_text = "".join(current_chars).strip()
        if segment_text:
            segments.append(("ru", segment_text))

    merged: list[tuple[str, str]] = []
    for lang, seg_text in segments:
        if merged and merged[-1][0] == lang:
            merged[-1] = (lang, merged[-1][1] + " " + seg_text)
        else:
            merged.append((lang, seg_text))

    logger.debug(
        "Segmented text into {} parts: {}",
        len(merged), [(lang, t[:20]) for lang, t in merged],
    )
    return merged

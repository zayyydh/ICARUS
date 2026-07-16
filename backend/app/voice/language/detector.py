"""
ICARUS Language Detector
=========================
Detects the primary language of user input.
Handles Hindi, Marathi, Urdu, Hinglish, English.

Fixes common langdetect misclassifications for Indian text
by checking for Devanagari script and known Hindi/Urdu patterns.

Usage:
    from app.voice.language.detector import detect_language
    lang = detect_language("yaar kya scene hai")
    # returns "hinglish"
"""

import re
import logging

logger = logging.getLogger(__name__)

# Devanagari Unicode range
DEVANAGARI_PATTERN = re.compile(r'[\u0900-\u097F]')

# Urdu (Nastaliq) Unicode range
URDU_PATTERN = re.compile(r'[\u0600-\u06FF]')

# Common Hinglish markers — English words mixed with Hindi
HINGLISH_MARKERS = {
    "yaar", "bhai", "arre", "arrey", "accha", "acha",
    "theek", "nahi", "hai", "kya", "bas", "abhi",
    "matlab", "pakka", "mast", "sahi", "bol", "kar",
    "bata", "dekh", "sun", "ho", "gaya", "hua",
}

# langdetect codes that usually mean Hinglish
HINGLISH_MISCLASSIFICATIONS = {"tl", "so", "cy", "af", "sw", "id", "ms"}


def detect_language(text: str) -> str:
    """
    Detect the primary language of input text.

    Returns one of: "hi", "mr", "ur", "en", "hinglish"
    Defaults to "hinglish" when uncertain — safe for Indian context.
    """
    if not text or not text.strip():
        return "hinglish"

    text_lower = text.lower().strip()

    # Check for Devanagari script first (definitive)
    if DEVANAGARI_PATTERN.search(text):
        # Could be Hindi or Marathi — both use Devanagari
        # Without more context, default to Hindi
        return "hi"

    # Check for Urdu script
    if URDU_PATTERN.search(text):
        return "ur"

    # Check for Hinglish markers in Roman text
    words = set(text_lower.split())
    if words & HINGLISH_MARKERS:
        # Has Hindi/Urdu words in Roman script — Hinglish
        return "hinglish"

    # Try langdetect for pure English or other languages
    try:
        from langdetect import detect
        detected = detect(text)

        if detected == "en":
            return "en"
        elif detected == "hi":
            return "hi"
        elif detected == "mr":
            return "mr"
        elif detected == "ur":
            return "ur"
        elif detected in HINGLISH_MISCLASSIFICATIONS:
            return "hinglish"
        else:
            # Unknown — default to hinglish for Indian context
            return "hinglish"

    except Exception:
        return "hinglish"


def get_response_instruction(language: str) -> str:
    """
    Returns instruction for LLM on what language to reply in.
    Injected into system prompt.
    """
    instructions = {
        "hi":       "Reply in Hindi (Devanagari or Roman, match user's style).",
        "mr":       "Reply in Marathi, natural and conversational.",
        "ur":       "Reply in Urdu, warm and respectful tone.",
        "en":       "Reply in English.",
        "hinglish": (
            "Reply in Hinglish — natural mix of Hindi and English "
            "the way Indians speak daily. "
            "Example: 'Haan bhai, main search kar leta hoon' "
            "not pure Hindi or pure English."
        ),
    }
    return instructions.get(language, instructions["hinglish"])
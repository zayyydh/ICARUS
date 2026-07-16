"""
ICARUS Text-to-Speech
======================
Speaks ICARUS responses in your cloned ElevenLabs voice.
Uses eleven_multilingual_v2 — speaks Hindi, Marathi, Urdu,
Hinglish and English all in the same voice naturally.

Voice settings tuned for a friendly, warm, Jarvis-like feel.
Two modes: default (Carter-style warm) and precise (Adam-style).

Usage:
    from app.voice.tts import tts
    await tts.speak("Haan bhai, gana laga raha hoon.")
    await tts.speak("Repository created.", mode="precise")
"""

import asyncio
import logging
import tempfile
import os
import time

from app.config.settings import settings

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    ElevenLabs-powered TTS with your cloned voice.
    Gracefully degrades to print() if ElevenLabs unavailable.
    """

    # Voice settings tuned for daily use —
    # warm enough for casual chat, clear enough for commands
    VOICE_SETTINGS_DEFAULT = {
        "stability":         0.55,   # More expressive
        "similarity_boost":  0.80,   # Matches your voice closely
        "style":             0.35,   # Natural personality
        "use_speaker_boost": True,
    }

    # Slightly more stable for serious/technical responses
    VOICE_SETTINGS_PRECISE = {
        "stability":         0.72,
        "similarity_boost":  0.85,
        "style":             0.18,
        "use_speaker_boost": True,
    }

    def __init__(self):
        self._pygame_ready = False
        self._el_ready     = False
        logger.info("TTS initialized (lazy load)")

    def _ensure_pygame(self) -> bool:
        """Initialize pygame mixer for audio playback."""
        if self._pygame_ready:
            return True
        try:
            import pygame
            pygame.mixer.init()
            self._pygame_ready = True
            return True
        except ImportError:
            logger.warning("pygame not installed — audio playback unavailable")
            return False
        except Exception as e:
            logger.warning("pygame init failed", extra={"error": str(e)})
            return False

    async def speak(
        self,
        text:     str,
        mode:     str = "default",
        language: str = "hinglish",
    ) -> bool:
        """
        Speak text in ICARUS's cloned voice.

        Args:
            text:     Text to speak
            mode:     "default" (warm) or "precise" (stable)
            language: Detected language — for thinking sound selection

        Returns True if audio played, False if fallback to print.
        """
        if not text or not text.strip():
            return False

        # Check API key
        if not settings.ELEVENLABS_API_KEY or settings.ELEVENLABS_API_KEY == "test-elevenlabs-key":
            logger.debug("ElevenLabs not configured — printing instead")
            print(f"\n🔊 ICARUS: {text}\n")
            return False

        try:
            audio_data = await self._generate_audio(text, mode)
            if audio_data:
                await self._play_audio(audio_data)
                return True
            else:
                print(f"\n🔊 ICARUS: {text}\n")
                return False
        except Exception as e:
            logger.error("TTS failed", extra={"error": str(e)})
            print(f"\n🔊 ICARUS: {text}\n")
            return False

    async def _generate_audio(self, text: str, mode: str) -> bytes | None:
        """Call ElevenLabs API to generate audio bytes."""
        import httpx

        settings_map = {
            "default": self.VOICE_SETTINGS_DEFAULT,
            "precise": self.VOICE_SETTINGS_PRECISE,
        }
        voice_settings = settings_map.get(mode, self.VOICE_SETTINGS_DEFAULT)

        payload = {
            "text":           text,
            "model_id":       settings.ELEVENLABS_MODEL,
            "voice_settings": voice_settings,
        }

        headers = {
            "Accept":       "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key":   settings.ELEVENLABS_API_KEY,
        }

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(
                "ElevenLabs API error",
                extra={"status": response.status_code, "body": response.text[:200]}
            )
            return None

        return response.content

    async def _play_audio(self, audio_data: bytes) -> None:
        """Save audio to temp file and play via pygame."""
        if not self._ensure_pygame():
            return

        import pygame

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name

        try:
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._wait_for_playback
            )
        finally:
            pygame.mixer.music.unload()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _wait_for_playback(self) -> None:
        """Block until pygame finishes playing."""
        import pygame
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)

    async def speak_thinking(self, language: str = "hinglish") -> None:
        """
        Play a short thinking sound immediately while ICARUS processes.
        Makes conversations feel natural — no dead silence.
        """
        import random
        from app.config.constants import THINKING_SOUNDS, LANGUAGE
        try:
            lang_enum = LANGUAGE(language)
        except ValueError:
            lang_enum = LANGUAGE.HINGLISH
        sounds = THINKING_SOUNDS.get(lang_enum, ["..."])
        sound  = random.choice(sounds)
        await self.speak(sound, mode="default")

    async def boot_greeting(self, personality: str = "bro") -> None:
        """
        Speaks the boot greeting on ICARUS startup.
        Personality-aware.
        """
        from app.personality.manager import personality_manager
        greeting = personality_manager.get_greeting(personality)
        await self.speak(greeting, mode="default")
        logger.info("Boot greeting spoken", extra={"personality": personality})


# ── Singleton ──────────────────────────────────────────────────────
tts = TextToSpeech()
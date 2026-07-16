"""
ICARUS Voice Loop
==================
The main voice interaction loop.
Ties together wake word → STT → Orchestrator → TTS.

This is what makes ICARUS feel like Jarvis.

Flow:
  [always listening]
       │
  Wake word detected ("Jarvis")
       │
  STT listens until silence
       │
  Language detected
       │
  Orchestrator handles request
       │
  TTS speaks response in your voice
       │
  [back to listening]

Usage:
    from app.voice.voice_loop import voice_loop
    await voice_loop.start()
"""

import asyncio
import logging
import uuid

from app.voice.stt import stt
from app.voice.tts import tts
from app.voice.wake_word import WakeWordDetector
from app.voice.language.detector import detect_language
from app.brain.orchestrator import orchestrator
from app.config.settings import settings

logger = logging.getLogger(__name__)


class VoiceLoop:
    """
    The main ICARUS voice interaction loop.
    Manages state between wake word, listening, and responding.
    """

    def __init__(self):
        self._session_id   = uuid.uuid4().hex[:12]
        self._personality  = settings.DEFAULT_PERSONALITY
        self._active       = False
        self._detector     = None
        logger.info(
            "Voice loop initialized",
            extra={"session_id": self._session_id}
        )

    async def start(self) -> None:
        """
        Start ICARUS in voice mode.
        Plays boot greeting, then waits for wake word.
        """
        self._active = True

        # Boot greeting
        await tts.boot_greeting(self._personality)

        # Start wake word detector
        self._detector = WakeWordDetector(on_wake=self._on_wake)
        await self._detector.run()

    async def stop(self) -> None:
        """Stop the voice loop."""
        self._active = False
        if self._detector:
            await self._detector.stop()
        logger.info("Voice loop stopped")

    async def _on_wake(self) -> None:
        """
        Called when wake word is detected.
        Plays acknowledgement → listens → processes → responds.
        """
        if not self._active:
            return

        logger.info("Wake word triggered — listening for command")

        # 1. Play immediate acknowledgement
        await tts.speak("Yes?", mode="default")

        # 2. Listen for command
        result = await stt.listen()

        if not result or not result.text.strip():
            await tts.speak("I didn't catch that.", mode="default")
            return

        text     = result.text.strip()
        language = self._normalise_language(result.language)

        logger.info(
            "Command received",
            extra={"text": text[:60], "language": language}
        )

        # 3. Play thinking sound immediately (no dead silence)
        think_task = asyncio.create_task(
            tts.speak_thinking(language)
        )

        # 4. Process through orchestrator
        try:
            response = await orchestrator.handle(
                text=text,
                language=language,
                personality=self._personality,
                session_id=self._session_id,
            )

            # Update personality if it was switched
            if response.intent == "personality_switch":
                self._personality = response.personality
                logger.info(
                    "Personality switched",
                    extra={"to": self._personality}
                )

        except Exception as e:
            logger.error("Orchestrator error", extra={"error": str(e)})
            await think_task
            await tts.speak(
                "Kuch gadbad ho gayi. Dobara try karo.",
                mode="default",
                language=language,
            )
            return

        # 5. Wait for thinking sound to finish
        await think_task

        # 6. Speak the response
        voice_mode = "precise" if response.used_tool else "default"
        await tts.speak(
            response.text,
            mode=voice_mode,
            language=language,
        )

        logger.info(
            "Response delivered",
            extra={
                "intent":    response.intent,
                "used_llm":  response.used_llm,
                "used_tool": response.used_tool,
                "tokens":    response.tokens_used,
            }
        )

    def _normalise_language(self, whisper_lang: str) -> str:
        """
        Map Whisper's language codes to ICARUS language codes.
        Whisper returns ISO 639-1 codes; we use our own set.
        """
        mapping = {
            "hi": "hi",
            "mr": "mr",
            "ur": "ur",
            "en": "en",
            # Whisper sometimes returns these for Hinglish
            "tl": "hinglish",
            "so": "hinglish",
            "cy": "hinglish",
            "af": "hinglish",
        }
        return mapping.get(whisper_lang, "hinglish")


# ── Run script ─────────────────────────────────────────────────────
# python -m app.voice.voice_loop
# or: from app.voice.voice_loop import voice_loop; asyncio.run(voice_loop.start())

voice_loop = VoiceLoop()


if __name__ == "__main__":
    import sys
    print("\n" + "="*50)
    print("  ICARUS Voice Mode")
    print("="*50)
    print("  Starting voice loop...")
    print("  Press Ctrl+C to quit\n")

    try:
        asyncio.run(voice_loop.start())
    except KeyboardInterrupt:
        print("\n\nICARUS voice mode stopped.")
        sys.exit(0)
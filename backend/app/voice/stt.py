"""
ICARUS Speech-to-Text
======================
Listens to your microphone, detects silence, transcribes
using Whisper large-v3 with full Indian language support.

Supports: Hindi, Marathi, Urdu, Hinglish, English
Uses the Indian slang initial_prompt to prime Whisper
for better accuracy on desi words and code-switching.

Usage:
    from app.voice.stt import stt
    result = await stt.listen()
    print(result.text, result.language)
"""

import asyncio
import logging
import tempfile
import os
import wave
from dataclasses import dataclass

import numpy as np

from app.config.settings import settings
from app.config.constants import WHISPER_SAMPLE_RATE, AUDIO_CHUNK_SIZE

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# TRANSCRIPTION RESULT
# ══════════════════════════════════════════════════════════════════

@dataclass
class TranscriptionResult:
    text:       str
    language:   str    # detected language code
    confidence: float  # 0.0 - 1.0


# ══════════════════════════════════════════════════════════════════
# INDIAN LANGUAGE WHISPER PRIMER
# Primes Whisper with common Indian words so it doesn't
# mishear Hinglish as Tagalog or Somali (langdetect quirk)
# ══════════════════════════════════════════════════════════════════

INDIAN_PROMPT = (
    "The following is a conversation in Indian languages "
    "including Hindi, Marathi, Urdu, and Hinglish "
    "(Hindi-English code-switching). "
    "Common words: yaar, bhai, kya, hai, nahi, acha, theek, kal, "
    "abhi, matlab, arrey, bol, kar, de, le, ho, bas, sahi, "
    "pakka, mast, bindaas, jugaad, lafda, gana, baja, laga, "
    "search kar, dekh, sun, ek second, ho gaya, nahi hua."
)


# ══════════════════════════════════════════════════════════════════
# SPEECH TO TEXT
# ══════════════════════════════════════════════════════════════════

class SpeechToText:
    """
    Whisper-powered multilingual speech recognition.
    Handles Indian language code-switching natively.
    Gracefully degrades if pyaudio/whisper not installed.
    """

    SILENCE_THRESHOLD = settings.SILENCE_THRESHOLD
    SILENCE_SECONDS   = settings.SILENCE_SECONDS

    def __init__(self):
        self._model   = None
        self._ready   = False
        self._loading = False
        logger.info(
            "STT initialized (lazy model load)",
            extra={"model": settings.WHISPER_MODEL}
        )

    async def _ensure_model(self) -> bool:
        """Load Whisper model on first use."""
        if self._ready:
            return True
        if self._loading:
            # Wait for another coroutine that's already loading
            while self._loading:
                await asyncio.sleep(0.1)
            return self._ready

        self._loading = True
        try:
            import whisper
            loop = asyncio.get_event_loop()
            logger.info(
                "Loading Whisper model...",
                extra={"model": settings.WHISPER_MODEL}
            )
            self._model = await loop.run_in_executor(
                None,
                lambda: whisper.load_model(
                    settings.WHISPER_MODEL,
                    device=settings.WHISPER_DEVICE,
                )
            )
            self._ready   = True
            self._loading = False
            logger.info("Whisper model loaded")
            return True
        except ImportError:
            logger.warning("openai-whisper not installed — STT unavailable")
            self._loading = False
            return False
        except Exception as e:
            logger.error("Failed to load Whisper", extra={"error": str(e)})
            self._loading = False
            return False

    def _is_silent(self, data: bytes) -> bool:
        """Check if audio chunk is below silence threshold."""
        audio = np.frombuffer(data, dtype=np.int16)
        return float(np.abs(audio).mean()) < self.SILENCE_THRESHOLD

    async def listen(self) -> TranscriptionResult | None:
        """
        Record from microphone until silence detected.
        Returns transcription result or None if unavailable.
        """
        if not await self._ensure_model():
            return None

        try:
            import pyaudio
        except ImportError:
            logger.warning("pyaudio not installed — microphone unavailable")
            return None

        audio  = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=WHISPER_SAMPLE_RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK_SIZE,
        )

        logger.info("Listening...")
        frames            = []
        silence_chunks    = 0
        silence_limit     = int(
            WHISPER_SAMPLE_RATE / AUDIO_CHUNK_SIZE * self.SILENCE_SECONDS
        )
        recording_started = False

        try:
            while True:
                data = stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)

                if not self._is_silent(data):
                    recording_started = True
                    silence_chunks    = 0
                    frames.append(data)
                elif recording_started:
                    frames.append(data)
                    silence_chunks += 1
                    if silence_chunks >= silence_limit:
                        break
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

        if not frames:
            return None

        return await self._transcribe(frames, audio)

    async def _transcribe(
        self,
        frames: list[bytes],
        audio,
    ) -> TranscriptionResult:
        """Save audio to temp file and transcribe with Whisper."""
        import pyaudio

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            wf = wave.open(f.name, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(WHISPER_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
            wf.close()

        try:
            loop   = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._model.transcribe(
                    tmp_path,
                    fp16=False,
                    task="transcribe",
                    language=None,           # Auto-detect
                    initial_prompt=INDIAN_PROMPT,
                )
            )

            text     = result["text"].strip()
            lang     = result.get("language", "hi")
            segments = result.get("segments", [])

            # Average confidence from segments
            if segments:
                avg_conf = sum(
                    abs(s.get("avg_logprob", -1.0))
                    for s in segments
                ) / len(segments)
                confidence = max(0.0, min(1.0, 1.0 - avg_conf / 5.0))
            else:
                confidence = 0.8

            logger.info(
                "Transcribed",
                extra={"text": text[:60], "lang": lang}
            )
            return TranscriptionResult(
                text=text,
                language=lang,
                confidence=confidence,
            )

        finally:
            os.unlink(tmp_path)

    async def transcribe_file(self, file_path: str) -> TranscriptionResult | None:
        """
        Transcribe an audio file directly.
        Used for testing without a microphone.
        """
        if not await self._ensure_model():
            return None

        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(
                file_path,
                fp16=False,
                task="transcribe",
                language=None,
                initial_prompt=INDIAN_PROMPT,
            )
        )
        return TranscriptionResult(
            text=result["text"].strip(),
            language=result.get("language", "hi"),
            confidence=0.9,
        )


# ── Singleton ──────────────────────────────────────────────────────
stt = SpeechToText()
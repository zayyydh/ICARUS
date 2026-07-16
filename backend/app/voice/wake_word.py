"""
ICARUS Wake Word Detection
===========================
Always-on listener that wakes ICARUS when triggered.
Uses Porcupine for on-device detection — near-zero CPU.

Free built-in keywords: "jarvis", "computer", "hey google"
Custom "hey icarus": needs Porcupine paid tier keyword file.

Gracefully degrades to keyboard trigger if Porcupine unavailable.

Usage:
    from app.voice.wake_word import WakeWordDetector
    detector = WakeWordDetector(on_wake=my_callback)
    await detector.run()
"""

import asyncio
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """
    Porcupine-powered always-on wake word detection.
    Calls on_wake() whenever the wake word is heard.
    Falls back to keyboard input if hardware unavailable.
    """

    def __init__(self, on_wake):
        self.on_wake    = on_wake
        self._running   = False
        self._porcupine = None

    async def run(self) -> None:
        """
        Start listening for wake word.
        Runs until stop() is called.
        """
        self._running = True

        if await self._try_porcupine():
            logger.info(
                "Wake word active",
                extra={"keyword": settings.WAKE_WORD}
            )
            await self._porcupine_loop()
        else:
            logger.info("Wake word: keyboard fallback active (press Enter)")
            await self._keyboard_loop()

    async def stop(self) -> None:
        """Stop the wake word detector."""
        self._running = False
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

    async def _try_porcupine(self) -> bool:
        """Try to initialise Porcupine. Returns False if unavailable."""
        if not settings.PICOVOICE_KEY:
            logger.debug("No Picovoice key — skipping Porcupine")
            return False

        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(
                access_key=settings.PICOVOICE_KEY,
                keywords=[settings.WAKE_WORD],
            )
            return True
        except ImportError:
            logger.warning("pvporcupine not installed")
            return False
        except Exception as e:
            logger.warning(
                "Porcupine init failed",
                extra={"error": str(e)}
            )
            return False

    async def _porcupine_loop(self) -> None:
        """Main Porcupine listening loop."""
        import struct
        import pyaudio

        pa     = pyaudio.PyAudio()
        stream = pa.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
        )

        print(f'\n🎙️  Say "{settings.WAKE_WORD}" to wake ICARUS...\n')

        try:
            while self._running:
                pcm = stream.read(
                    self._porcupine.frame_length,
                    exception_on_overflow=False,
                )
                pcm = struct.unpack_from(
                    "h" * self._porcupine.frame_length, pcm
                )

                keyword_index = self._porcupine.process(pcm)
                if keyword_index >= 0:
                    logger.info("Wake word detected!")
                    await self.on_wake()

                # Yield control to event loop
                await asyncio.sleep(0)

        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            if self._porcupine:
                self._porcupine.delete()

    async def _keyboard_loop(self) -> None:
        """
        Keyboard fallback — press Enter to activate ICARUS.
        Used when Porcupine isn't available.
        Perfect for development on machines without a mic setup.
        """
        print('\n⌨️   Press Enter to speak to ICARUS (Ctrl+C to quit)\n')

        loop = asyncio.get_event_loop()
        while self._running:
            try:
                # Non-blocking input read
                await loop.run_in_executor(None, input)
                await self.on_wake()
            except (EOFError, KeyboardInterrupt):
                self._running = False
                break
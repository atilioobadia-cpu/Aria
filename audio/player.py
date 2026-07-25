import asyncio
import edge_tts
import sounddevice as sd
import numpy as np
from utils.logger import setup_logger

log = setup_logger("aria.tts")


class TextToSpeech:
    def __init__(self, config):
        self.voice = config.get("voice", "en-US-AriaNeural")
        self.rate = config.get("rate", "+0%")
        self.pitch = config.get("pitch", "+0Hz")
        self.volume = config.get("volume", "+0%")

    async def _generate_audio(self, text):
        communicate = edge_tts.Communicate(
            text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
            volume=self.volume,
        )
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        return audio_data

    def speak(self, text):
        if not text or not text.strip():
            return
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_bytes = loop.run_until_complete(self._generate_audio(text))
            if audio_bytes:
                sd.stop()
                sd.play(bytes_to_float32(audio_bytes), 24000)
                sd.wait()
        except Exception as e:
            log.warning("TTS failed: %s", e)
        finally:
            if loop:
                loop.close()


def bytes_to_float32(audio_bytes):
    raw = np.frombuffer(audio_bytes, dtype=np.int16)
    return raw.astype(np.float32) / 32768.0



def play_tone(duration=0.15, frequency=880, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone = 0.3 * np.sin(2 * np.pi * frequency * t)
    sd.play(tone, sample_rate)
    sd.wait()

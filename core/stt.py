import numpy as np
from faster_whisper import WhisperModel
from utils.logger import setup_logger

log = setup_logger("aria.stt")


class SpeechToText:
    def __init__(self, config):
        model_name = config.get("model", "tiny.en")
        device = config.get("device", "cpu")
        compute_type = config.get("compute_type", "int8")
        self.language = config.get("language", "en")
        log.info("Loading whisper model: %s (device=%s, compute=%s)", model_name, device, compute_type)
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, quiet: bool = False) -> str:
        if audio is None or len(audio) == 0:
            return ""
        audio_float = audio.astype(np.float32)
        if audio_float.ndim > 1:
            audio_float = audio_float.mean(axis=1)
        duration = len(audio_float) / sample_rate
        peak = float(np.abs(audio_float).max()) if len(audio_float) > 0 else 0
        if not quiet:
            log.info("Audio: %.1fs, peak=%.4f", duration, peak)
        if peak < 0.001:
            return ""
        segments, info = self.model.transcribe(
            audio_float, beam_size=5, language=self.language,
            no_speech_threshold=0.1, condition_on_previous_text=False,
        )
        text = " ".join(seg.text for seg in segments)
        result = text.strip()
        if not quiet:
            if result:
                log.info("Transcribed: %s", result)
            else:
                log.info("No speech detected in audio")
        return result

    def contains_wake_word(self, text: str, wake_word: str = "aria") -> bool:
        if not text:
            return False
        return wake_word.lower() in text.lower()

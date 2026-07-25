import time
import numpy as np
import sounddevice as sd
from utils.logger import setup_logger

log = setup_logger("aria.audio")


def rms_mono(block: np.ndarray) -> float:
    if block.ndim > 1:
        block = np.mean(block.astype(np.float64), axis=1)
    else:
        block = block.astype(np.float64)
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(block**2)))


class AudioListener:
    def __init__(self, config):
        self.sample_rate = config.get("sample_rate", 16000)
        self.channels = config.get("channels", 1)
        self.silence_timeout = config.get("silence_timeout_s", 1.5)
        self.max_record = config.get("max_record_s", 10.0)
        self.min_audio_ms = config.get("min_audio_ms", 300)
        self.silence_threshold = config.get("silence_threshold", 0.008)
        self.blocksize = int(self.sample_rate * 0.1)
        self._device = None

    def _choose_device(self):
        default = sd.default.device[0]
        if default is not None and default >= 0:
            return default
        inputs = [(i, dev) for i, dev in enumerate(sd.query_devices()) if dev["max_input_channels"] >= 1]
        if not inputs:
            raise RuntimeError("No input devices found")
        return inputs[0][0]

    def record_until_silence(self, timeout=None):
        if self._device is None:
            self._device = self._choose_device()
        if timeout is None:
            timeout = self.max_record
        audio_buffers = []
        silence_frames = 0
        silence_blocks_needed = int(self.silence_timeout / 0.1)
        total_blocks = 0
        max_blocks = int(timeout / 0.1)
        started_speech = False
        idle_blocks_max = int(3.0 / 0.1)
        idle_blocks = 0

        stream = sd.InputStream(
            device=self._device,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
        )
        with stream:
            while total_blocks < max_blocks:
                data, _ = stream.read(self.blocksize)
                audio_buffers.append(data.copy())
                level = rms_mono(data)
                total_blocks += 1
                if level >= self.silence_threshold:
                    started_speech = True
                    silence_frames = 0
                    idle_blocks = 0
                elif started_speech:
                    silence_frames += 1
                    if silence_frames >= silence_blocks_needed:
                        break
                else:
                    silence_frames += 1
                    idle_blocks += 1
                    if idle_blocks >= idle_blocks_max:
                        return None
                    if silence_frames >= silence_blocks_needed:
                        audio_buffers.clear()
                        silence_frames = 0
                        total_blocks = 0

        if not audio_buffers:
            return None

        audio = np.concatenate(audio_buffers)
        duration_ms = len(audio) / self.sample_rate * 1000
        if duration_ms < self.min_audio_ms:
            return None
        return audio

    def get_stream_for_wake(self, blocksize):
        if self._device is None:
            self._device = self._choose_device()
        return sd.InputStream(
            device=self._device,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=blocksize,
        )

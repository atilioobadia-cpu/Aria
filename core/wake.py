import time
import numpy as np
import sounddevice as sd
from utils.logger import setup_logger

log = setup_logger("aria.wake")

CLAP = "clap"
VOICE = "voice"


def rms_mono(block):
    if block.ndim > 1:
        block = np.mean(block.astype(np.float64), axis=1)
    else:
        block = block.astype(np.float64)
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(block**2)))


class WakeDetector:
    def __init__(self, config, stt=None):
        self.config = config
        self.stt = stt
        self.clap_enabled = config.get("clap_enabled", True)
        self.voice_wake_enabled = bool(stt)
        self.wake_word = config.get("voice_wake_word", "aria")

        clap_cfg = config.get("clap", {})
        self.clap_rate = clap_cfg.get("sample_rate", 44100)
        self.block_ms = clap_cfg.get("block_ms", 40)
        self.channels = clap_cfg.get("channels", 1)
        self.spike_ratio = clap_cfg.get("spike_ratio", 7.0)
        self.min_rms = clap_cfg.get("min_rms", 0.012)
        self.cooldown_s = clap_cfg.get("cooldown_s", 0.45)
        self.min_double_gap = clap_cfg.get("min_double_gap_s", 0.05)
        self.max_double_gap = clap_cfg.get("max_double_gap_s", 0.35)
        self.retrigger_ratio = clap_cfg.get("retrigger_ratio", 0.55)
        self.noise_floor_alpha = clap_cfg.get("noise_floor_alpha", 0.992)
        self.quiet_gate_mult = clap_cfg.get("quiet_gate_mult", 2.2)
        self.blocksize = max(1, int(self.clap_rate * self.block_ms / 1000))

        self.voice_rate = 16000
        self.voice_blocksize = int(self.voice_rate * 0.5)
        self._voice_buffer = []
        self._voice_counter = 0
        self._voice_check_interval = 10

        self._device = None

    def _choose_device(self):
        default = sd.default.device[0]
        if default is not None and default >= 0:
            return default
        inputs = [(i, dev) for i, dev in enumerate(sd.query_devices()) if dev["max_input_channels"] >= 1]
        if not inputs:
            raise RuntimeError("No input devices found")
        return inputs[0][0]

    def _downsample(self, data, original_rate, target_rate):
        if original_rate == target_rate:
            return data
        ratio = original_rate / target_rate
        n = int(len(data) / ratio)
        if n == 0:
            return data
        indices = np.linspace(0, len(data) - 1, n, dtype=int)
        indices = np.clip(indices, 0, len(data) - 1)
        return data[indices]

    def wait_for_wake(self):
        if self._device is None:
            self._device = self._choose_device()

        noise_floor = 1e-4
        last_logged_double = 0.0
        first_clap_time = None
        spike_armed = True
        block_count = 0

        log.info("Listening for clap or '%s'...", self.wake_word)
        self._voice_buffer = []

        rate = self.clap_rate if self.clap_enabled else self.voice_rate
        bs = self.blocksize if self.clap_enabled else self.voice_blocksize

        with sd.InputStream(
            device=self._device,
            samplerate=rate,
            channels=self.channels,
            dtype="float32",
            blocksize=bs,
        ) as stream:
            while True:
                data, _ = stream.read(bs)
                block_count += 1

                if self.clap_enabled:
                    level = rms_mono(data)
                    quiet_gate = noise_floor * self.quiet_gate_mult
                    if level < quiet_gate:
                        noise_floor = self.noise_floor_alpha * noise_floor + (
                            1.0 - self.noise_floor_alpha
                        ) * level
                        noise_floor = max(noise_floor, 1e-7)

                    threshold = max(noise_floor * self.spike_ratio, self.min_rms)
                    now = time.monotonic()
                    retrigger_level = threshold * self.retrigger_ratio

                    if level < retrigger_level:
                        spike_armed = True

                    if (
                        spike_armed
                        and level >= threshold
                        and (now - last_logged_double) >= self.cooldown_s
                    ):
                        spike_armed = False
                        if first_clap_time is None:
                            first_clap_time = now
                        else:
                            gap = now - first_clap_time
                            if self.min_double_gap <= gap <= self.max_double_gap:
                                log.info("Double clap detected (gap=%.3fs)", gap)
                                return CLAP
                            elif gap > self.max_double_gap:
                                first_clap_time = now

                if self.voice_wake_enabled:
                    downsampled = self._downsample(data, rate, self.voice_rate)
                    self._voice_buffer.append(downsampled)
                    self._voice_counter += 1

                    if self._voice_counter >= self._voice_check_interval:
                        combined = np.concatenate(self._voice_buffer) if self._voice_buffer else np.array([], dtype=np.float32)
                        self._voice_buffer = []
                        self._voice_counter = 0
                        if len(combined) > self.voice_rate * 0.3:
                            text = self.stt.transcribe(combined, self.voice_rate, quiet=True)
                            if text and self.stt.contains_wake_word(text, self.wake_word):
                                log.info("Wake word '%s' detected in: %s", self.wake_word, text)
                                return VOICE

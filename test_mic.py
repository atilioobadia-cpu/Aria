import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import sounddevice as sd
import numpy as np
from utils.logger import setup_logger
from utils.config import load_config

log = setup_logger("test")

def rms(block):
    if block.ndim > 1:
        block = np.mean(block.astype(np.float64), axis=1)
    else:
        block = block.astype(np.float64)
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(block**2)))

print("=" * 50)
print("MICROPHONE TEST")
print("=" * 50)

print("\nAvailable input devices:")
for i, dev in enumerate(sd.query_devices()):
    if dev["max_input_channels"] > 0:
        print(f"  [{i}] {dev['name']} (channels={dev['max_input_channels']}, rate={dev['default_samplerate']})")

default = sd.default.device[0]
print(f"\nDefault input device: [{default}] {sd.query_devices(default)['name']}")

print("\nRecording 3 seconds of audio... Speak now!")
print("(waiting for audio level to show...)")

input("\nPress Enter to start 3s test recording...")

SAMPLE_RATE = 16000
DURATION = 3
recording = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
sd.wait()

peak = float(np.abs(recording).max()) if len(recording) > 0 else 0
rms_val = rms(recording)
duration = len(recording) / SAMPLE_RATE

print(f"\nRecording stats:")
print(f"  Duration: {duration:.1f}s")
print(f"  Peak level: {peak:.5f}")
print(f"  RMS level: {rms_val:.5f}")

if peak < 0.001:
    print("\n⚠️  Audio is VERY quiet. Check your microphone:")
    print("   1. Is your mic connected and enabled?")
    print("   2. Windows Settings → System → Sound → Input")
    print("   3. Try speaking louder or closer to the mic")
elif peak < 0.01:
    print("\n⚠️  Audio is quite low. You may need to speak louder or adjust mic gain.")
else:
    print("\n✅ Microphone working! Audio level looks good.")

print("\nNow testing transcription...")
from core.stt import SpeechToText
config = load_config()
stt = SpeechToText(config.get("stt", {}))

print("Transcribing recorded audio...")
text = stt.transcribe(recording.flatten(), 16000)
if text:
    print(f"\n✅ Transcribed: \"{text}\"")
else:
    print("\n❌ No speech recognized. Try speaking more clearly or closer to the mic.")

print("\n" + "=" * 50)
print("Test complete. If transcription failed, check the suggestions above.")
print("=" * 50)

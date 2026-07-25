import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.config import load_config
from utils.logger import setup_logger
from audio.listener import AudioListener
from audio.player import TextToSpeech, play_tone
from core.stt import SpeechToText
from core.brain import Brain
from core.conversation import Conversation
from core.wake import WakeDetector, CLAP, VOICE
from tools.registry import ToolRegistry
from tools import browser
from tools import spotify
from tools import cursor
from tools import web_search

log = setup_logger("aria")


def build_tools(registry):
    registry.register("browser", browser.open_chrome, "Open Chrome with optional URL and monitor")
    registry.register("open_url", browser.open_url, "Open a URL in default browser")
    registry.register("spotify", spotify.play_song, "Play a Spotify track or playlist")
    registry.register("cursor", cursor.focus_cursor, "Focus or open Cursor editor")
    registry.register("web_search", web_search.web_search, "Search the web for information")


def main():
    log.info("Aria Voice Assistant starting...")
    config = load_config()

    tts = TextToSpeech(config.get("tts", {}))
    stt = SpeechToText(config.get("stt", {}))
    brain = Brain(config.get("brain", {}))
    conv = Conversation(
        system_prompt=config["brain"]["system_prompt"],
        max_history=config["brain"].get("max_history", 20),
    )
    listener = AudioListener(config.get("stt", {}))
    registry = ToolRegistry()
    build_tools(registry)

    wake = WakeDetector(config.get("wake", {}), stt=stt)

    log.info("Aria is ready. Clap twice or say 'Aria' to wake me.")
    log.info("Press Ctrl+C to exit.")

    session_active = False

    while True:
        try:
            if not session_active:
                log.info("Waiting for wake... (clap or say 'Aria')")
                wake_type = wake.wait_for_wake()
                session_active = True
                log.info("Woken by %s", "clap" if wake_type == CLAP else "voice")
                play_tone(duration=0.12, frequency=660)
                time.sleep(0.1)
                play_tone(duration=0.12, frequency=880)
                tts.speak("Yes sir, I'm listening.")

            log.info("Listening... (speak now)")
            full_text = ""
            silent_chunks = 0
            max_silent = 3
            chunk_s = config["stt"].get("chunk_s", 2.0)
            chunks_max = int(chunk_s / 0.5) + 2
            for chunk_idx in range(chunks_max):
                import numpy as np
                chunk = listener.record_until_silence(timeout=0.6)
                if chunk is None or len(chunk) < 1600:
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break
                    continue
                peak = float(np.abs(chunk).max())
                if peak < 0.002:
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break
                    continue
                silent_chunks = 0
                log.info("Transcribing chunk %d...", chunk_idx + 1)
                chunk_text = stt.transcribe(chunk, sample_rate=16000)
                if chunk_text:
                    full_text += (" " + chunk_text) if full_text else chunk_text
                    log.info("Partial: %s", full_text)
                if chunk_idx >= chunks_max - 2:
                    break

            text = full_text.strip()
            if not text:
                log.info("No speech recognized, going back to sleep")
                session_active = False
                continue

            log.info("You: %s", text)
            conv.add_user_message(text)

            log.info("Thinking...")
            result = brain.process(conv.get_messages())

            if result["tool_call"]:
                tc = result["tool_call"]
                tool_name = tc["tool"]
                tool_args = tc.get("args", {})
                log.info("Executing tool: %s %s", tool_name, tool_args)
                tool_result = registry.execute(tool_name, tool_args)
                conv.add_tool_result(tool_name, tool_result)
                log.info("Tool result: %s", tool_result)

                result2 = brain.process(conv.get_messages())
                response_text = result2.get("text", "")
                if result2.get("tool_call"):
                    response_text = brain.strip_tool_from_response(response_text)
            else:
                response_text = result.get("text", "")

            if not response_text:
                response_text = "I'm not sure how to respond to that."

            conv.add_assistant_message(response_text)
            log.info("Aria: %s", response_text)
            tts.speak(response_text)

            session_active = False

        except KeyboardInterrupt:
            log.info("Goodbye!")
            break
        except Exception as e:
            log.error("Unexpected error: %s", e)
            session_active = False
            time.sleep(1)


if __name__ == "__main__":
    main()

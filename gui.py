import sys
import os
import threading
import queue
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont

from utils.config import load_config
from utils.logger import setup_logger
from audio.listener import AudioListener
from audio.player import TextToSpeech, play_tone
from core.stt import SpeechToText
from core.brain import Brain
from core.conversation import Conversation
from core.wake import WakeDetector, CLAP, VOICE
from tools.registry import ToolRegistry
from tools import browser, spotify, cursor, web_search

log = setup_logger("aria.gui")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ChatBubble(ctk.CTkFrame):
    def __init__(self, master, text, is_user=False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1 if is_user else 0, weight=1)
        padx = 60
        color = "#2b5a8c" if is_user else "#2a2d32"
        align = "e" if is_user else "w"
        self.label = ctk.CTkLabel(
            self,
            text=text,
            wraplength=400,
            justify="left",
            fg_color=color,
            text_color="#ffffff",
            corner_radius=12,
            padx=14,
            pady=10,
        )
        self.label.grid(row=0, column=0 if is_user else 1, sticky=align, padx=(padx if is_user else 10, 10 if is_user else padx), pady=3)


class AriaGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aria")
        self.geometry("520x640")
        self.minsize(400, 500)
        self.configure(fg_color="#121212")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.msg_queue = queue.Queue()
        self.running = True
        self.aria_thread = None
        self.is_listening = False

        self._build_ui()
        self._start_aria_engine()

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="#1a1a1a", height=56, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        title = ctk.CTkLabel(header, text="Aria", font=ctk.CTkFont(size=20, weight="bold"), text_color="#7eb8ff")
        title.pack(side="left", padx=20, pady=12)

        self.status_dot = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=14), text_color="#555555")
        self.status_dot.pack(side="right", padx=(0, 6), pady=12)

        self.status_text = ctk.CTkLabel(header, text="Idle", font=ctk.CTkFont(size=12), text_color="#888888")
        self.status_text.pack(side="right", padx=(0, 20), pady=12)

        chat_frame = ctk.CTkFrame(self, fg_color="transparent")
        chat_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_canvas = ctk.CTkScrollableFrame(chat_frame, fg_color="transparent", corner_radius=0)
        self.chat_canvas.grid(row=0, column=0, sticky="nsew")

        self.chat_content = ctk.CTkFrame(self.chat_canvas, fg_color="transparent")
        self.chat_content.pack(fill="both", expand=True, padx=10, pady=10)

        bottom = ctk.CTkFrame(self, fg_color="#1a1a1a", height=48, corner_radius=0)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.grid_propagate(False)

        self.toggle_btn = ctk.CTkButton(
            bottom,
            text="● Start Listening",
            font=ctk.CTkFont(size=13),
            fg_color="#2b5a8c",
            hover_color="#1e4a7a",
            corner_radius=20,
            height=32,
            command=self.toggle_listening,
        )
        self.toggle_btn.pack(side="left", padx=16, pady=8)

        self.add_message("Aria", "Clap twice or say my name to wake me. I'm always listening.", is_assistant=True)

    def set_status(self, text, color="#888888"):
        self.status_text.configure(text=text)
        self.status_dot.configure(text_color=color)
        self.update_idletasks()

    def add_message(self, speaker, text, is_assistant=False):
        is_user = not is_assistant
        bubble = ChatBubble(self.chat_content, text, is_user=is_user)
        bubble.pack(fill="x", pady=(0, 6))

    def toggle_listening(self):
        if self.is_listening:
            self.is_listening = False
            self.toggle_btn.configure(text="● Start Listening", fg_color="#2b5a8c")
            self.set_status("Paused", "#555555")
        else:
            self.is_listening = True
            self.toggle_btn.configure(text="■ Stop Listening", fg_color="#8c2b2b")
            self.set_status("Listening", "#4caf50")

    def _start_aria_engine(self):
        self.aria_thread = threading.Thread(target=self._aria_loop, daemon=True)
        self.aria_thread.start()
        self.after(200, self._process_queue)

    def _process_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get_nowait()
            msg_type = msg.get("type")
            if msg_type == "status":
                self.set_status(msg["text"], msg.get("color", "#888888"))
            elif msg_type == "message":
                self.add_message(msg["speaker"], msg["text"], is_assistant=msg.get("is_assistant", False))
            elif msg_type == "append":
                self.add_message(msg["speaker"], msg["text"], is_assistant=msg.get("is_assistant", False))
        if self.running:
            self.after(200, self._process_queue)

    def _aria_loop(self):
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
        registry.register("browser", browser.open_chrome, "Open Chrome")
        registry.register("open_url", browser.open_url, "Open URL")
        registry.register("spotify", spotify.play_song, "Play song")
        registry.register("cursor", cursor.focus_cursor, "Open Cursor")
        registry.register("web_search", web_search.web_search, "Search web")

        wake = WakeDetector(config.get("wake", {}), stt=stt)
        self.msg_queue.put({"type": "status", "text": "Idle", "color": "#4caf50"})

        while self.running:
            try:
                self.msg_queue.put({"type": "status", "text": "Listening for wake...", "color": "#4caf50"})
                wake_type = wake.wait_for_wake()
                self.msg_queue.put({"type": "status", "text": "Wake!", "color": "#ff9800"})
                play_tone(duration=0.12, frequency=660)
                time.sleep(0.1)
                play_tone(duration=0.12, frequency=880)

                self.msg_queue.put({"type": "message", "speaker": "Aria", "text": "Yes sir, I'm listening.", "is_assistant": True})
                tts.speak("Yes sir, I'm listening.")

                self.msg_queue.put({"type": "status", "text": "Listening...", "color": "#ff9800"})
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
                    chunk_text = stt.transcribe(chunk, sample_rate=16000, quiet=True)
                    if chunk_text:
                        full_text += (" " + chunk_text) if full_text else chunk_text
                    if chunk_idx >= chunks_max - 2:
                        break

                text = full_text.strip()
                if not text:
                    self.msg_queue.put({"type": "status", "text": "Idle", "color": "#4caf50"})
                    continue

                self.msg_queue.put({"type": "message", "speaker": "You", "text": text, "is_assistant": False})
                conv.add_user_message(text)

                self.msg_queue.put({"type": "status", "text": "Thinking...", "color": "#2196f3"})
                result = brain.process(conv.get_messages())

                if result["tool_call"]:
                    tc = result["tool_call"]
                    tool_name = tc["tool"]
                    tool_args = tc.get("args", {})
                    tool_result = registry.execute(tool_name, tool_args)
                    conv.add_tool_result(tool_name, tool_result)
                    result2 = brain.process(conv.get_messages())
                    response_text = result2.get("text", "")
                    if result2.get("tool_call"):
                        response_text = brain.strip_tool_from_response(response_text)
                else:
                    response_text = result.get("text", "")

                if not response_text:
                    response_text = "I'm not sure how to respond to that."

                conv.add_assistant_message(response_text)
                self.msg_queue.put({"type": "message", "speaker": "Aria", "text": response_text, "is_assistant": True})

                self.msg_queue.put({"type": "status", "text": "Speaking...", "color": "#ff9800"})
                tts.speak(response_text)
                self.msg_queue.put({"type": "status", "text": "Idle", "color": "#4caf50"})

            except Exception as e:
                log.error("Engine error: %s", e)
                self.msg_queue.put({"type": "status", "text": "Error", "color": "#f44336"})
                time.sleep(2)

    def on_close(self):
        self.running = False
        self.destroy()


if __name__ == "__main__":
    app = AriaGUI()
    app.mainloop()

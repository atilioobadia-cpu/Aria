# Aria — Voice AI Assistants

Aria is a free, local voice AI assistant for Windows. Wake her with a **double clap** or by saying **"Aria"**, then speak naturally — she responds with a warm female voice, can search the web, open apps, and control your desktop.

## Features

- **Voice wake** — clap twice or say "Aria" to activate
- **Natural conversation** — powered by a local LLM (Ollama)
- **Desktop control** — open Chrome, Spotify, Cursor, and more
- **Web search** — fetches live information via DuckDuckGo
- **100% free & private** — everything runs locally, no API keys needed
- **Female voice** — uses Microsoft Edge TTS (en-US-AriaNeural)

## Quick Start

```powershell
pip install -r requirements.txt
ollama pull llama3.1:8b
python main.py
```

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) (for the AI brain)
- A working microphone
- Windows 10/11

## Repository Structure

```
aria/
├── main.py              # Entry point
├── config.yaml          # Settings
├── core/                # Audio, STT, TTS, LLM integration
├── tools/               # Desktop automation tools
└── audio/               # Microphone and playback
```

## Acknowledgments

Built on open-source tools: faster-whisper, edge-tts, Ollama, sounddevice, and duckduckgo-search.

---

*Your personal AI companion — always listening, always ready.*

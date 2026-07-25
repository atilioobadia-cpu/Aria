import json
import requests
from utils.logger import setup_logger

log = setup_logger("aria.brain")


class Brain:
    def __init__(self, config):
        self.endpoint = config.get("endpoint", "http://localhost:11434")
        self.model = config.get("model", "llama3.1:8b")
        self.temperature = config.get("temperature", 0.7)

    def process(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
        }
        try:
            resp = requests.post(f"{self.endpoint}/api/chat", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "").strip()
            return {"text": content, "tool_call": self._parse_tool_call(content)}
        except requests.exceptions.ConnectionError:
            log.error("Cannot connect to Ollama at %s. Is Ollama running?", self.endpoint)
            return {"text": "I'm having trouble connecting to my brain. Please make sure Ollama is running.", "tool_call": None}
        except Exception as e:
            log.error("Brain error: %s", e)
            return {"text": "Sorry, I encountered an error processing that.", "tool_call": None}

    def _parse_tool_call(self, content):
        if "{" not in content:
            return None
        start = content.index("{")
        end = content.rindex("}")
        if start >= end:
            return None
        try:
            obj = json.loads(content[start:end+1])
            if "tool" in obj and "args" in obj:
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    def strip_tool_from_response(self, content):
        if "{" not in content:
            return content
        start = content.index("{")
        end = content.rindex("}")
        if start >= end:
            return content
        before = content[:start].strip()
        after = content[end+1:].strip()
        return (before + " " + after).strip()

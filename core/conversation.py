from utils.logger import setup_logger

log = setup_logger("aria.conversation")


class Conversation:
    def __init__(self, system_prompt: str, max_history: int = 20):
        self.max_history = max_history
        self.messages = [{"role": "system", "content": system_prompt}]

    def add_user_message(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant_message(self, text: str):
        self.messages.append({"role": "assistant", "content": text})
        self._trim()

    def add_tool_result(self, tool_name: str, result: str):
        self.messages.append({"role": "user", "content": f"[Tool {tool_name} returned]: {result}"})
        self._trim()

    def get_messages(self):
        return self.messages

    def _trim(self):
        if len(self.messages) > self.max_history + 1:
            system = self.messages[:1]
            history = self.messages[1:]
            self.messages = system + history[-(self.max_history):]

    def reset(self):
        system = self.messages[0] if self.messages else None
        self.messages.clear()
        if system:
            self.messages.append(system)

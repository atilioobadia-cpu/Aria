from utils.logger import setup_logger

log = setup_logger("aria.tools")


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, name, func, description=""):
        self._tools[name] = {"func": func, "description": description}
        log.info("Registered tool: %s", name)

    def execute(self, name, args=None):
        if name not in self._tools:
            return f"Tool '{name}' not found"
        if args is None:
            args = {}
        try:
            result = self._tools[name]["func"](**args)
            return str(result) if result is not None else "Done"
        except Exception as e:
            log.error("Tool '%s' failed: %s", name, e)
            return f"Error: {e}"

    def list_tools(self):
        return {name: info["description"] for name, info in self._tools.items()}

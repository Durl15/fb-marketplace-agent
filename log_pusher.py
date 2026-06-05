import os
import requests

COMMAND_CENTER_URL = os.getenv("COMMAND_CENTER_URL", "https://djai-command-center.onrender.com")

def push_log(agent: str, log_path: str, max_lines: int = 500):
    if not os.path.exists(log_path):
        return
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        content = "".join(lines[-max_lines:])
        requests.post(
            f"{COMMAND_CENTER_URL}/logs/{agent}",
            json={"content": content},
            timeout=10,
        )
        print(f"  [*] Log pushed to command center ({len(lines)} lines)")
    except Exception as e:
        print(f"  [!] Log push failed: {e}")

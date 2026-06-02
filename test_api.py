from dotenv import load_dotenv
import os
load_dotenv(override=True)
from anthropic import Anthropic
key = os.getenv("ANTHROPIC_API_KEY", "")
print(f"Key loaded: {key[:30]}...{key[-10:]}")
client = Anthropic(api_key=key)
resp = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=10,
    messages=[{"role": "user", "content": "Say OK"}]
)
print("API response:", resp.content[0].text)

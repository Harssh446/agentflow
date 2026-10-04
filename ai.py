import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

SYSTEM = ("You are an AI agent inside a multi-agent workflow. Follow your role, goal and "
          "instructions. Reply with only your result, with no preamble.")


def _mock(prompt, reason):
    role = re.search(r"^Role:\s*(.*)$", prompt, re.M)
    goal = re.search(r"^Goal:\s*(.*)$", prompt, re.M)
    body = prompt.split("INPUT:\n", 1)[-1].strip()
    body = re.sub(r"^\[MOCK RESPONSE[^\n]*\n", "", body)
    snippet = " ".join(body.split())[:160] or "(no input)"
    return (f"[MOCK RESPONSE - {reason}]\n"
            f"As {role.group(1) if role else 'Agent'}, working toward "
            f"\"{goal.group(1) if goal else 'the goal'}\", here is a sample result.\n"
            f"- Input considered: {snippet}\n"
            f"- Sample finding: the topic has several key aspects worth reviewing.\n"
            f"- Next step: hand these findings to the next agent.")


def ask_ai(prompt, model=None):
    """Send a prompt to Grok (xAI). Falls back to a labeled mock response on any problem."""
    if not model or model == "default":
        model = os.getenv("GROK_MODEL", "grok-3-mini")
    key = os.getenv("XAI_API_KEY", "").strip()
    if not key or key.startswith("your-"):
        return _mock(prompt, "no XAI_API_KEY set in .env")
    url = os.getenv("GROK_URL", "https://api.x.ai/v1/chat/completions")
    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role": "system", "content": SYSTEM},
                               {"role": "user", "content": prompt}],
                  "temperature": 0.4},
            timeout=60)
        r.raise_for_status()
        text = (r.json()["choices"][0]["message"]["content"] or "").strip()
        return text or _mock(prompt, "Grok returned an empty reply")
    except Exception as e:  # network error, bad key, bad model name, etc.
        return _mock(prompt, f"Grok unreachable: {str(e)[:120]}")

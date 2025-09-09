# chat_backend.py
import requests
import json
import os

# Global storage for all chats
chats = {}

# JSON file path
CHAT_FILE = "chats.json"

# ------------------------
# Persistence functions
# ------------------------
def load_chats():
    """Load saved chats from JSON into memory."""
    global chats
    print("Reading from file...")
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            chats = json.load(f)
            print(chats)
    else:
        print("No chats...")
        chats = {}

def save_chats():
    """Save current chats to JSON."""
    global chats
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, indent=2, ensure_ascii=False)

# ------------------------
# Existing functions
# ------------------------
def add_chat(name, system_prompt=""):
    chats[name] = {"system_prompt": system_prompt, "history": []}
    save_chats()  # Save immediately when adding a new chat

def format_history_for_gradio(history_):
    """Convert [(user, bot), ...] to [{'role':'user','content':...}, ...]"""
    messages = []
    for u, b in history_:
        messages.append({"role": "user", "content": u})
        messages.append({"role": "assistant", "content": b})
    return messages


def make_chat_fn(system_prompt, history):
    def chat_with_ollama(message, history_):
        url = "http://localhost:11434/api/chat"
        payload = {"model": "gemma3:4b", "messages": []}

        # Add system message
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})

        # Add history
        for msg in history_:
            payload["messages"].append(msg)

        # Add new user message
        payload["messages"].append({"role": "user", "content": message})

        response = requests.post(url, json=payload, stream=True)

        bot_reply = ""
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if '"message":' in data:
                    import json
                    try:
                        obj = json.loads(data)
                        bot_reply += obj["message"]["content"]
                    except:
                        pass

        # Append new messages in Gradio format
        history_.append({"role": "user", "content": message})
        history_.append({"role": "assistant", "content": bot_reply})
        
        save_chats()  # Save after each new message
        return history_
    return chat_with_ollama

import requests
import json
import os
import re
from datetime import datetime

# Paths
CHAT_FOLDER = "chat_data"
INDEX_FILE = os.path.join(CHAT_FOLDER, "chats_index.json")
LAST_CHAT_FILE = "last_chat.json"

# Ensure folder exists
os.makedirs(CHAT_FOLDER, exist_ok=True)

# ------------------------
# Utilities
# ------------------------

def italics_to_bold(text: str) -> str:
    """
    Converts Markdown italics (*text* or _text_) to bold (**text**).
    """
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'**\1**', text)  # *text*
    text = re.sub(r'_(.*?)_', r'**\1**', text)  # _text_
    return text

# ------------------------
# Index management
# ------------------------

def load_index():
    if not os.path.exists(INDEX_FILE):
        return {}
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(index):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def list_chats():
    index = load_index()
    return list(index.keys())

# ------------------------
# Last chat tracking
# ------------------------

def save_last_chat(chat_name: str):
    with open(LAST_CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_chat": chat_name}, f)

def load_last_chat():
    if os.path.exists(LAST_CHAT_FILE):
        with open(LAST_CHAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_chat", "")
    return ""

# ------------------------
# Chat persistence
# ------------------------

def load_chats():
    """Load all chats from the old single-file or folder-based storage into the global `chats` dict."""
    global chats
    # Load from folder-based structure
    index = load_index()
    chats = {}
    for name in index:
        chat_data = load_chat(name)
        if chat_data:
            chats[name] = chat_data

def load_chat(name: str):
    index = load_index()
    if name not in index:
        return {"system_prompt": "", "history": []}
    
    file_path = os.path.join(CHAT_FOLDER, index[name]["file"])
    if not os.path.exists(file_path):
        return {"system_prompt": "", "history": []}
    
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_chat(name: str, chat_data: dict):
    index = load_index()
    file_name = f"{name}.json"
    file_path = os.path.join(CHAT_FOLDER, file_name)

    # Save chat file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, indent=2, ensure_ascii=False)

    # Update index
    index[name] = {
        "file": file_name,
        "system_prompt": chat_data.get("system_prompt", ""),
        "last_updated": datetime.now().isoformat()
    }
    save_index(index)

def add_chat(name: str, system_prompt: str = ""):
    """Create a new chat and save it."""
    chat_data = {"system_prompt": system_prompt, "history": []}
    save_chat(name, chat_data)

# ------------------------
# History helpers
# ------------------------

def normalize_history_for_ui(history):
    """
    Normalize history into list[dict] for Gradio Chatbot(type="messages").
    Handles both tuple-style [(user, bot)] and dict-style [{"role":..., "content":...}]
    """
    messages = []
    for item in history:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            messages.append({"role": "user", "content": italics_to_bold(item[0])})
            messages.append({"role": "assistant", "content": italics_to_bold(item[1])})
        elif isinstance(item, dict):
            if "role" in item and "content" in item:
                messages.append(item)
    return messages

# ------------------------
# Ollama backend
# ------------------------

def make_chat_fn(system_prompt, history):
    def chat_with_ollama(message, history_input):
        url = "http://localhost:11434/api/chat"
        payload = {"model": "hf.co/ArliAI/Mistral-Nemo-12B-ArliAI-RPMax-v1.1-GGUF:Q4_K_M", "messages": []}

        # Add system prompt
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})

        # Add history
        for item in history_input:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                payload["messages"].append({"role": "user", "content": italics_to_bold(item[0])})
                payload["messages"].append({"role": "assistant", "content": italics_to_bold(item[1])})
            elif isinstance(item, dict):
                if "role" in item and "content" in item:
                    payload["messages"].append(item)

        # Add latest user message
        payload["messages"].append({"role": "user", "content": message})

        response = requests.post(url, json=payload, stream=True)

        bot_reply = ""
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if '"message":' in data:
                    try:
                        obj = json.loads(data)
                        bot_reply += obj["message"]["content"]

                        # Yield partial update
                        temp_history = history + [(message, bot_reply)]
                        yield normalize_history_for_ui(temp_history)
                    except:
                        pass

        # Save final result
        history_input.append({"role": "user", "content": message})
        history_input.append({"role": "assistant", "content": bot_reply})

        # Persist to file
        chat_data = {"system_prompt": system_prompt, "history": history_input}
        # Need the active chat name from UI to save properly
        # UI should pass the active chat name when calling save_chat()
        yield normalize_history_for_ui(history)

    return chat_with_ollama

import json
import os
import re
import shutil
from datetime import datetime
import ollama
from ollama import chat_with_ollama

# Paths
CHAT_FOLDER = "chat_data"
INDEX_FILE = os.path.join(CHAT_FOLDER, "chats_index.json")
LAST_CHAT_FILE = "last_chat.json"
BACKUP_FOLDER = "backup"
BACKUP_CHAT_FOLDER = "backup/chat_data"


# Ensure folder exists
os.makedirs(CHAT_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)
os.makedirs(BACKUP_CHAT_FOLDER, exist_ok=True)

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
    print("Retrieving all characters info...")
    if not os.path.exists(INDEX_FILE):
        return {}
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_index(name, character_info, index=None):
    print("Saving info of character: ", name)
    if index is None:
        index = load_index()
    index[name] = character_info
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def remove_from_index(name, index):
    print("Removing character from index: ", name)
    del index[name]
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    return index

# ------------------------
# Last chat tracking
# ------------------------

def save_last_chat(name: str):
    print("Saving last chat of: ", name)
    with open(LAST_CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_chat": name}, f)

def reset_last_chat(default_chat="Default Chat"):
    save_last_chat(default_chat)
    return default_chat

def load_last_chat():
    if os.path.exists(LAST_CHAT_FILE):
        with open(LAST_CHAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            print("Last chat was: ", data.get("last_chat", ""))
        return data.get("last_chat", "")
    return ""

# ------------------------
# Chat persistence
# ------------------------

def load_chat(name: str, character=None):
    if character is None:
        index = load_index()
        character = index[name]

    file_path = os.path.join(CHAT_FOLDER, character["file"])
    
    # Ensure chat_data always exists
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            chat_data = json.load(f)
            print("Chat data for ", name, " has been loaded")
    else:
        chat_data = {"system_prompt": "", "history": []}
    return chat_data

def save_chat(name: str, chat_data: dict):
    print("Saving character chat: ", name)
    file_path = os.path.join(CHAT_FOLDER, f"{name}.json")
    chat_data["timestamp"] = datetime.now().isoformat()

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print("FAIL", ex)
    print("Saved succesfully")

def remove_chat(name, index):
    # Save as backup chat file
    chat_file = index[name].get("file")
    system_prompt = index[name].get("system_prompt", "")

    chat_data = load_chat(name, index[name])
    chat_data["system_prompt"] = system_prompt

    if os.path.exists(os.path.join("chat_data", chat_file)):
        shutil.move(os.path.join(CHAT_FOLDER, chat_file), os.path.join(BACKUP_CHAT_FOLDER, chat_file))
    else:
        print("File does not exist to delete!")

# ------------------------
# Ollama backend
# ------------------------

def make_chat_fn(system_prompt, history):
    print("Making chat")
    def generator(history_input):
        return ollama.chat_with_ollama(system_prompt, history, history_input)
    return generator

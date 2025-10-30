import json
import os
import re
import shutil
import logging
from datetime import datetime
import ollama
from ollama import chat_with_ollama

logging.basicConfig(level=logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL

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

def get_character_list():
    logging.debug("get_character_list")
    return [
        name for name in os.listdir("chat_data")
        if os.path.isdir(os.path.join("chat_data", name))
    ]

# ------------------------
# Index management
# ------------------------

def load_characters_list():
    logging.debug("Retrieving all characters list")
    if not os.path.exists(CHAT_FOLDER):
        logging.critical("Chat data does not exist!")
        return {}
    try:
        characters = [name for name in os.listdir(CHAT_FOLDER)
           if os.path.isdir(os.path.join(CHAT_FOLDER, name))]
        return characters
    except Exception as ex:
        logging.critical("Failed trying to load characters folders! " + ex)

def load_index():
    logging.debug("Retrieving all characters info...")
    if not os.path.exists(INDEX_FILE):
        logging.critical("Index file does not exist!")
        return {}
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            logging.debug("Index file exists!")
            return json.load(f)
    except Exception as ex:
        logging.critical("Failed trying to load the index file! " + ex)

def save_index(name, character_info, index=None):
    logging.debug("Saving info of character: ", name)
    if index is None:
        index = load_index()
    index[name] = character_info
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def remove_from_index(name, index):
    logging.debug("Removing character from index: ", name)
    del index[name]
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    return index

# ------------------------
# Last chat tracking
# ------------------------

def save_last_chat_name(name: str):
    logging.debug("Saving last chat of: ", name)
    try:
        with open(LAST_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_chat": name}, f)
    except Exception as ex:
        logging.critical("Failed to save last chat!")

def reset_last_chat_name(default_chat="Default Chat"):
    save_last_chat_name(default_chat)
    return default_chat

def load_last_chat_name():
    logging.debug("load_last_chat_name")
    if os.path.exists(LAST_CHAT_FILE):
        logging.debug("Last chat file exists!")
        try:
            with open(LAST_CHAT_FILE, "r", encoding="utf-8") as f:
                last_chat_file = json.load(f)
                logging.debug(last_chat_file)
                return last_chat_file.get("last_chat", "")
        except Exception as ex:
            logging.critical("Cannot open last chat: " + ex)
            return last_chat_file.get("last_chat", "")
    return ""

# ------------------------
# Character file paths
# ------------------------

def get_chat_file_path(name: str):
    """Return the path to the chat file for this character."""
    character_folder = os.path.join(CHAT_FOLDER, name)
    logging.debug("Getting the chat folder...")
    return os.path.join(character_folder, "chat.json")

def get_metadata_file_path(name: str):
    """Return the path to the metadata file for this character."""
    character_folder = os.path.join(CHAT_FOLDER, name)
    logging.debug("Getting metadata path for: "+ name)
    return os.path.join(character_folder, "metadata.json")

def get_avatar_file_path(name: str):
    """Return the path to the avatar file for this character."""
    character_folder = os.path.join(CHAT_FOLDER, name)
    avatar_folder = os.path.join(character_folder, "assets")
    logging.debug("Getting metadata path for: "+ name)
    return os.path.join(avatar_folder, "avatar.png")

# ------------------------
# Character metadata
# ------------------------

def new_metadata(name, system_prompt):
    return {
            "name": f"{name}",
            "system_prompt": system_prompt,
            "avatar": "assets/Avatar.png",
            "last_updated": datetime.now().isoformat()
        }
    
def get_metadata(name: str):
    logging.debug("Getting metadata for: "+ name)
    metadata_path = get_metadata_file_path(name)
    logging.debug("Metadata path: " + metadata_path)
    metadata = None

    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            logging.debug("Getting metadata from character: " + name)
            metadata = json.load(f)
            logging.debug(metadata)
    else:
        logging.critical("Metadata not found for character: " + name)
        
    return metadata

def save_metadata(character_info):
    logging.debug("Saving metadata for: " + character_info["name"])
    metadata_path = get_metadata_file_path(character_info["name"])
    logging.debug("Metadata path: " + metadata_path)

    if os.path.exists(metadata_path):
        with open(metadata_path, "w", encoding="utf-8") as f:
            logging.debug("Saving metadata for character: " + character_info["name"])
            json.dump(character_info, f, indent=2)
            logging.debug("Saved metadata for: " + character_info["name"])
    else:
        logging.warning("Metadata path not found for character: " + character_info["name"] + " Creating new one.")
        with open(metadata_path, "w", encoding="utf-8") as f:
            logging.debug("Saving metadata for character: " + character_info["name"])
            json.dump(character_info, f, indent=2)
        
    return character_info




# ------------------------
# Chat CRUD
# ------------------------

def load_chat(name: str):
    # 1: Gets path of chat of character
    chat_file = get_chat_file_path(name)
    logging.debug("Chat file: " + chat_file)

    # 2: Gets chat from character
    if os.path.exists(chat_file):
        with open(chat_file, "r", encoding="utf-8") as f:
            logging.debug("Getting chat from character: " + chat_file)
            chat_data = json.load(f)
            logging.debug(chat_data)
    else:
        logging.info("Creating empty chat for: " + chat_file)
        chat_data = {"system_prompt": "", "history": []}

    # Load metadata if exists
    metadata_file = get_metadata_file_path(name)
    metadata = {}
    if os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            logging.debug("Loading metadata for: " + name)
            metadata = json.load(f)
            logging.debug(metadata)
    else:
        logging.critical("No metadata found for character: " + name)

    return chat_data, metadata

def save_chat(name: str, chat_data: dict, metadata: dict = None):
    """Save chat data and metadata for a given character."""
    chat_file = get_chat_file_path(name)
    metadata_file = get_metadata_file_path(name)

    chat_data["timestamp"] = datetime.now().isoformat()

    # Save chat file
    with open(chat_file, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, indent=2, ensure_ascii=False)

    # Save metadata
    if metadata:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    logging.debug(f"Saved chat and metadata for {name}")

def remove_chat(name):
    """Backup and remove a character chat folder."""
    src_folder = os.path.join(CHAT_FOLDER, name)
    if not os.path.exists(src_folder):
        logging.warning(f"Chat folder for {name} not found.")
        return

    dst_folder = os.path.join(BACKUP_CHAT_FOLDER, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.move(src_folder, dst_folder)
    logging.debug(f"Chat {name} backed up to {dst_folder}")

# ------------------------
# Ollama backend
# ------------------------

def make_chat_fn(system_prompt, history):
    logging.debug("Making chat")
    def generator(history_input):
        return ollama.chat_with_ollama(system_prompt, history, history_input)
    return generator

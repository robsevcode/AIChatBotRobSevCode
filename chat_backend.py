import json
import os
import re
import shutil
import logging
from datetime import datetime
from pydantic import BaseModel
import ollama
from ollama import chat_with_ollama

logging.basicConfig(level=logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Paths
CHAT_FOLDER = "chat_data"
LAST_CHAT_FILE = "last_chat.json"
BACKUP_FOLDER = "backup"
BACKUP_CHAT_FOLDER = "backup/chat_data"

# Ensure folder exists
os.makedirs(CHAT_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)
os.makedirs(BACKUP_CHAT_FOLDER, exist_ok=True)

# ------------------------
# Classes
# ------------------------

class Metadata(BaseModel):
    character_name: str
    system_prompt: str
    avatar_path: str
    last_updated: str

class LastChat(BaseModel):
    character_name: str


# ------------------------
# Character list
# ------------------------

def load_characters_list():
    logging.debug("Retrieving all characters list")
    try:
        character_list = [character_name for character_name in os.listdir(CHAT_FOLDER)
           if os.path.isdir(os.path.join(CHAT_FOLDER, character_name))]
        return character_list
    except Exception as ex:
        logging.critical("Failed trying to load characters folders! " + ex)

# ------------------------
# Last chat tracking
# ------------------------

def save_last_chat_name(character_name: str):
    logging.debug("Saving last chat of: ", character_name)
    try:
        with open(LAST_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(LastChat(last_chat=character_name).model_dump_json(), f)
    except Exception as ex:
        logging.critical("Failed to save last chat!")

def reset_last_chat_name(default_chat="Default Chat"):
    save_last_chat_name(default_chat)
    return default_chat

def load_last_chat_name():
    logging.debug("load_last_chat_name")
    last_chat = ""
    if os.path.exists(LAST_CHAT_FILE):
        logging.debug("Last chat file exists!")
        try:
            with open(LAST_CHAT_FILE, "r", encoding="utf-8") as f:
                last_chat_file = json.load(f)
                last_chat = LastChat.model_validate(last_chat_file)
                logging.debug(last_chat)
                return last_chat.character_name
        except Exception as ex:
            logging.critical("Cannot open last chat: ")
            return last_chat.character_name
    return ""

# ------------------------
# Character file paths
# ------------------------

def get_chat_file_path(character_name: str):
    character_folder = os.path.join(CHAT_FOLDER, character_name)
    logging.debug("Getting the chat folder...")
    return os.path.join(character_folder, "chat.json")

def get_metadata_file_path(character_name: str):
    character_folder = os.path.join(CHAT_FOLDER, character_name)
    logging.debug("Getting metadata path for: "+ character_name)
    return os.path.join(character_folder, "metadata.json")

def get_avatar_file_path(character_name: str):
    character_folder = os.path.join(CHAT_FOLDER, character_name)
    assets_folder = os.path.join(character_folder, "assets")
    logging.debug("Getting avatar path for: "+ character_name)
    return os.path.join(assets_folder, "avatar.png")

# ------------------------
# Character metadata
# ------------------------

def new_metadata(character_name: str, system_prompt: str):
    return Metadata(character_name=character_name, system_prompt= system_prompt, avatar="assets/Avatar.png", last_updated=datetime.now().isoformat())
    
def get_metadata(character_name: str):
    logging.debug("Getting metadata for: "+ character_name)
    metadata_path = get_metadata_file_path(character_name)
    logging.debug("Metadata path: " + metadata_path)
    metadata = None

    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            logging.debug("Getting metadata from character: " + character_name)
            metadata = json.load(f)
            logging.debug(metadata)
    else:
        logging.critical("Metadata not found for character: " + character_name)
        
    return metadata

def save_metadata(metadata: Metadata):
    logging.debug("Saving metadata for: " + metadata.character_name)
    metadata_path = get_metadata_file_path(metadata.character_name)
    logging.debug("Metadata path: " + metadata_path)

    if os.path.exists(metadata_path):
        with open(metadata_path, "w", encoding="utf-8") as f:
            logging.debug("Saving metadata for character: " + metadata.character_name)
            json.dump(metadata.model_dump_json(), f, indent=2)
            logging.debug("Saved metadata for: " + metadata.character_name)
    else:
        logging.warning("Metadata path not found for character: " + metadata.character_name + " Creating new one.")
        with open(metadata_path, "w", encoding="utf-8") as f:
            logging.debug("Saving metadata for character: " + metadata.character_name)
            json.dump(metadata.model_dump_json(), f, indent=2)
        
    return metadata

# ------------------------
# Chat CRUD
# ------------------------

def load_chat(character_name: str):
    chat_file = get_chat_file_path(character_name)
    logging.debug("Chat file: " + chat_file)

    if os.path.exists(chat_file):
        with open(chat_file, "r", encoding="utf-8") as f:
            logging.debug("Getting chat from character: " + chat_file)
            chat_data = json.load(f)
            logging.debug(chat_data)
    else:
        logging.info("Creating empty chat for: " + chat_file)
        chat_data = {"system_prompt": "", "history": []}

    # Load metadata if exists
    metadata_file = get_metadata_file_path(character_name)
    metadata = {}
    if os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            logging.debug("Loading metadata for: " + character_name)
            metadata = json.load(f)
            logging.debug(metadata)
    else:
        logging.critical("No metadata found for character: " + character_name)

    return chat_data, metadata

def save_chat(character_name: str, chat_data: dict, metadata: dict = None):
    """Save chat data and metadata for a given character."""
    chat_file = get_chat_file_path(character_name)
    metadata_file = get_metadata_file_path(character_name)

    chat_data["timestamp"] = datetime.now().isoformat()

    # Save chat file
    with open(chat_file, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, indent=2, ensure_ascii=False)

    # Save metadata
    if metadata:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    logging.debug(f"Saved chat and metadata for {character_name}")

def remove_chat(character_name):
    """Backup and remove a character chat folder."""
    src_folder = os.path.join(CHAT_FOLDER, character_name)
    if not os.path.exists(src_folder):
        logging.warning(f"Chat folder for {character_name} not found.")
        return

    dst_folder = os.path.join(BACKUP_CHAT_FOLDER, f"{character_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.move(src_folder, dst_folder)
    logging.debug(f"Chat {character_name} backed up to {dst_folder}")

# ------------------------
# Ollama backend
# ------------------------

def make_chat_fn(system_prompt, history):
    logging.debug("Making chat")
    def generator(history_input):
        return ollama.chat_with_ollama(system_prompt, history, history_input)
    return generator

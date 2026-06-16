import gradio as gr
import chat_backend
import stable_diffusion
import ollama
import os
import logging
import time
from PIL import Image

logging.basicConfig(level=logging.DEBUG)


def normalize_path(path):
    if not path:
        return path
    return path.replace('\\', '/')


def build_sidebar_ui():
    """Build the sidebar UI for chat selection and character management."""
    last_chat_name = chat_backend.load_last_chat_name()
    characters_list = chat_backend.get_character_list()

    if last_chat_name and (last_chat_name in characters_list):
        chat_data, metadata = chat_backend.load_chat(last_chat_name)
        character_avatar = normalize_path(chat_backend.get_avatar_file_path(last_chat_name))
        system_prompt = metadata.get("system_prompt", "")
    else:
        logging.warning("No last chat available... Setting default one...")
        chat_data = {"system_prompt": "", "history": []}
        system_prompt = "You are a helpful assistant."
        last_chat_name = "Default Chat"
        character_avatar = "assets/default.png"

    current_chat = gr.State(last_chat_name)

    with gr.Column(scale=1, min_width=280):
        gr.Markdown("### 📚 Chats")
        
        # Dropdown to select chat
        chat_list = gr.Dropdown(
            choices=characters_list,
            allow_custom_value=False,
            label="Select Chat",
            value=last_chat_name,
            interactive=True
        )
        
        remove_button = gr.Button("🗑️ Remove Chat", variant="stop", scale=1)

        # Accordion for creating a new character
        with gr.Accordion("➕ Create New Character", open=False):
            char_name_input = gr.Textbox(label="Character Name", placeholder="Enter character name")
            system_prompt_input = gr.Textbox(
                label="System Prompt / Identity",
                placeholder="Describe the character...",
                lines=3
            )
            create_char_btn = gr.Button("Create", variant="primary")

    # --- Callbacks ---

    def create_character(name, system_prompt):
        if not name:
            logging.warning("No name was added!")
            gr.Warning("No name was added!")
            return
        if not system_prompt:
            logging.warning("No personality was added!")
            gr.Warning("No personality was added!")
            return
        
        prompt = ollama.generate_image_prompt(system_prompt)
        path = normalize_path(stable_diffusion.generate_avatar_a1111(name, prompt))

        metadata = chat_backend.new_metadata(name, system_prompt)
        metadata["avatar"] = path
        chat_backend.save_metadata(metadata)

        new_character_chat = {"history": []}
        chat_backend.save_chat(name, new_character_chat)

        chat_backend.save_last_chat_name(name)
        gr.Info(message=f"ℹ️ Character '{name}' created!")
        character_list = chat_backend.load_characters_list()

        return (
            gr.update(choices=list(character_list), value=name),
            gr.update(value=name),
            gr.update(value=""),
            gr.update(value=""),
        )
    
    def remove_character(name):
        logging.info("Deleting character: " + str(name))
        character_list = chat_backend.load_characters_list()
        if name == "Default Chat":
            logging.warning("ℹ️ Default Character cannot be removed!")
            gr.Error("ℹ️ Default Character cannot be removed!")
            return gr.update(choices=list(character_list))

        if name not in character_list:
            return gr.update(choices=list(character_list))

        chat_backend.reset_last_chat_name()
        chat_backend.remove_chat(name)

        logging.info("Character " + name + " removed!")
        gr.Info(message=f"ℹ️ Character '{name}' removed!")

        return gr.update(choices=list(chat_backend.load_characters_list()))

    def switch_chat(name):
        if not name:
            logging.critical("No name found when switching characters!")
            return ""
        logging.debug("Switch character to: " + name)
        chat_backend.save_last_chat_name(name)
        return gr.update(value=name)

    # Wire up callbacks
    create_char_btn.click(
        create_character,
        [char_name_input, system_prompt_input],
        [chat_list, current_chat, char_name_input, system_prompt_input]
    )

    chat_list.change(
        switch_chat,
        [chat_list],
        [current_chat],
        show_progress="hidden"
    )

    remove_button.click(remove_character, inputs=[chat_list], outputs=[chat_list])

    return (
        chat_list, current_chat,
        char_name_input, system_prompt_input, create_char_btn
    )
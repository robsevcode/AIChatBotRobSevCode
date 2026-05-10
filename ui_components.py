import gradio as gr
import chat_backend
import stable_diffusion
import re
import os
import time
import threading
from queue import Queue, Empty
import ollama
import logging
import settings
from ollama import generate_image_prompt
from datetime import datetime

logging.basicConfig(level=logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL


def italics_to_bold(text):
    """
    Converts action-style markup to bold-italic text.

    Supported action formatting:
    - *text* or _text_
    - (text)
    - [text]
    """
    if not isinstance(text, str):
        return text

    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'***\1***', text)
    text = re.sub(r'_(.*?)_', r'***\1***', text)
    text = re.sub(r'\(([^)]+)\)', r'***\1***', text)
    text = re.sub(r'\[([^\]]+)\]', r'***\1***', text)
    return text

def build_chat_ui(demo=None):
    last_chat_name = chat_backend.load_last_chat_name()
    characters_list = chat_backend.get_character_list()

    if last_chat_name and (last_chat_name in characters_list):
        chat_data, metadata = chat_backend.load_chat(last_chat_name)

        character_avatar = chat_backend.get_avatar_file_path(last_chat_name)
        system_prompt = metadata["system_prompt"]
    else:
        logging.warning("No last chat available... Setting default one...")
        chat_data = {"system_prompt": "", "history": []}
        system_prompt = "You are a helpful assistant."
        last_chat_name = "Default Chat"
        character_avatar = "assets/default.png"

    # --- Helpers for Gradio 3.x Chatbot format ---
    def format_chat_message(content):
        if isinstance(content, tuple) and len(content) == 1 and isinstance(content[0], str):
            return content[0]
        if isinstance(content, dict):
            if content.get("type") == "image":
                return content.get("path", "")
            return str(content)
        return content

    def history_dicts_to_chatbot(history):
        if history is None:
            return []

        chatbot_value = []

        for msg in history:
            if isinstance(msg, (list, tuple)):
                # Support legacy Gradio 3.x pair format
                user_text = msg[0] if len(msg) > 0 else ""
                assistant_text = msg[1] if len(msg) > 1 else ""
                if user_text:
                    chatbot_value.append({"role": "user", "content": user_text})
                if assistant_text:
                    chatbot_value.append({"role": "assistant", "content": assistant_text})
                continue

            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content", "")
            if isinstance(content, tuple) and len(content) == 1 and isinstance(content[0], str):
                content = content[0]
            if isinstance(content, dict) and content.get("type") == "image":
                content = content.get("path", "")

            if role in ("user", "assistant"):
                if isinstance(content, str):
                    content = italics_to_bold(content)
                chatbot_value.append({"role": role, "content": content})

        return chatbot_value

    # --- Saving current chat ---
    current_chat = gr.State(last_chat_name)
    logging.debug("Setting current chat as: "+ last_chat_name)

    with gr.Row():
        with gr.Column(scale=1, min_width=200) as Sidebar:
            # Image of Character (Always visible)
            character_image = gr.Image(
                value=character_avatar,
                show_label=False
                )
            
            # Accordion for settings
            # Dropdown to select chat
            chat_list = gr.Dropdown(
                choices=characters_list,
                allow_custom_value=False,
                label="Chats",
                value= last_chat_name,
                interactive=True
            )
            remove_button = gr.Button("Remove", variant="stop")

            # Accordion for editing character personality
            with gr.Accordion("System Prompt / Identity", open=False):
                system_prompt_display = gr.Textbox(
                    value=system_prompt,
                    show_label=False,
                    interactive=True,   # editable
                    lines=3
                )
                update_prompt_btn = gr.Button("Update System Prompt")

            # Accordion for creating a new character
            with gr.Accordion("Create new character", open=False):
                with gr.Column(scale=1):
                    char_name_input = gr.Textbox(label="Character Name")
                    system_prompt_input = gr.Textbox(label="System Prompt / Identity")
                    create_char_btn = gr.Button("Create Character")
    
            # Accordion for settings
            with gr.Accordion("Settings", open=False):
                image_style = gr.Dropdown(choices=["Realistic", "Anime"], label="Image Style", value="Realistic")
                response_type = gr.Dropdown(choices=["Slow", "Average", "Fast"], label="Response Type", value="Average")
                apply_button = gr.Button("Apply")
    
        with gr.Column(scale=5) as Textbox:
            # Textbox of chatbot
            chatbot = gr.Chatbot(
                show_label=False,
                height=700,
                elem_id="chatbot",
                value=history_dicts_to_chatbot(chat_data.get("history", [])),
                avatar_images=("assets/user.png", character_avatar),  # (user, bot)
                buttons=[]
            )
            msg_box = gr.Textbox(label="Message")

    # ------------------------
    #        Callback
    # ------------------------

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
        path = stable_diffusion.generate_avatar_a1111(name, prompt)

        metadata = chat_backend.new_metadata(name, system_prompt)
        chat_backend.save_metadata(metadata)

        new_character_chat = {"history": []}
        chat_backend.save_chat(name, new_character_chat)

        chat_backend.save_last_chat_name(name)
        gr.Info(message=f"ℹ️ Character {name} was created!")
        character_list = chat_backend.load_characters_list()

        return gr.update(choices=list(character_list), value=name), gr.update(value=path)
    
    def remove_character(name):
        logging.info("Deleting character: ", name)
        character_list = chat_backend.load_characters_list()
        if name == "Default Chat":
            logging.warning("ℹ️ Default Character cannot be removed!")
            gr.Error("ℹ️ Default Character cannot be removed!")
            return gr.update(choices=list(character_list))

        if name not in character_list:
            return gr.update(choices=list(character_list)), "Character not found."

        chat_backend.reset_last_chat_name()
        chat_backend.remove_chat(name)

        logging.info("Character " + name + " removed!")
        gr.Info(message=f"ℹ️ Character {name} was removed!")

        return gr.update(choices=list(chat_backend.load_characters_list()))

    # When using the Dropdown
    def switch_chat(name):
        if not name:
            logging.critical("No name found when switching characters!")
            return gr.update(value=[]), "", gr.update(value="")
        logging.debug("Switch character to:", name)

        chat_backend.save_last_chat_name(name)
        chat_data, metadata = chat_backend.load_chat(name)
        logging.debug("Chat data loaded for: "+name)
        history = chat_data["history"]
        system_prompt = metadata["system_prompt"]
        character_avatar = chat_backend.get_avatar_file_path(name)
        return (
            gr.update(
                value=history_dicts_to_chatbot(history),
                avatar_images=("assets/user.png", character_avatar)
            ),
            name,
            gr.update(value=system_prompt),
            gr.update(value=character_avatar),
        )

    def update_system_prompt(new_prompt, name):
        if not name:
            return gr.update(value="⚠️ No active chat selected")
        
        logging.info("Updating personality of: " + name)
        metadata = chat_backend.get_metadata(name)
        metadata["system_prompt"] = new_prompt
        chat_backend.save_metadata(metadata)
        return gr.update(value=new_prompt)
    
    def clean_chat_history(history):
        cleaned = []
        logging.debug("Cleaning history from chat")

        if history is None:
            return cleaned

        if isinstance(history, list) and all(isinstance(item, (list, tuple)) for item in history):
            for row in history:
                if not row:
                    continue
                user_text = row[0] if len(row) > 0 else ""
                assistant_text = row[1] if len(row) > 1 else ""
                if user_text:
                    cleaned.append({"role": "user", "content": user_text})
                if assistant_text:
                    cleaned.append({"role": "assistant", "content": assistant_text})
            return cleaned

        for msg in history:
            if "role" not in msg or "content" not in msg:
                continue

            content = msg["content"]
            if isinstance(content, tuple) and len(content) == 1 and isinstance(content[0], str):
                content = {"type": "image", "path": content[0]}
            elif isinstance(content, str) and os.path.splitext(content)[1].lower() in (".png", ".jpg", ".jpeg"):
                content = {"type": "image", "path": content}
            elif isinstance(content, str):
                content = italics_to_bold(content)
            elif isinstance(content, dict) and content.get("type") == "image":
                pass

            cleaned.append({"role": msg["role"], "content": content})

        return cleaned

    def send_message(message, chatbot_history, current_chat_name):
        logging.debug("SENDING MESSAGE")
        chatbot_history = clean_chat_history(chatbot_history)

        if chatbot_history is None:
            chatbot_history = []

        if not current_chat_name:
            logging.warning("No chat selected")
            yield history_dicts_to_chatbot(chatbot_history), "⚠️ Select a chat first"
            return

        if not message:
            yield history_dicts_to_chatbot(chatbot_history), ""
            return

        chatbot_history.append({"role": "user", "content": message})

        metadata = chat_backend.get_metadata(current_chat_name)
        system_prompt = metadata.get("system_prompt", "")

        chat_data = {
            "history": chatbot_history,
            "system_prompt": system_prompt
        }

        display_history = chatbot_history + [{"role": "assistant", "content": "Writing."}]
        yield history_dicts_to_chatbot(display_history), ""

        if message:
            for placeholder in ["Writing", "Writing.", "Writing..", "Writing..."]:
                display_history[-1]["content"] = placeholder
                yield history_dicts_to_chatbot(display_history), ""
                time.sleep(0.12)

        if "show me" in str(message).lower():
            img_path = "assets\\Paty_20250916_010533.png"
            final_history = chatbot_history + [{"role": "assistant", "content": {"type": "image", "path": img_path}}]
            chat_data["history"] = final_history
            chat_backend.save_chat(current_chat_name, chat_data)
            yield history_dicts_to_chatbot(final_history), ""
            return

        backend_gen_fn = chat_backend.make_chat_fn(
            system_prompt,
            chatbot_history
        )

        output_queue = Queue()
        stop_token = object()

        def backend_worker():
            try:
                gen = backend_gen_fn(chatbot_history)
                for partial_history in gen:
                    output_queue.put(partial_history)
            except Exception as ex:
                output_queue.put(("error", ex))
            finally:
                output_queue.put(stop_token)

        threading.Thread(target=backend_worker, daemon=True).start()

        placeholders = ["Writing", "Writing.", "Writing..", "Writing..."]
        placeholder_index = 0
        final_history = chatbot_history
        last_word_count = 0
        running = True

        while running:
            try:
                item = output_queue.get(timeout=0.2)
            except Empty:
                display_history[-1]["content"] = placeholders[placeholder_index]
                placeholder_index = (placeholder_index + 1) % len(placeholders)
                yield history_dicts_to_chatbot(display_history), ""
                continue

            if item is stop_token:
                running = False
                continue

            if isinstance(item, tuple) and item[0] == "error":
                raise item[1]

            final_history = item
            assistant_text = ""
            if final_history and final_history[-1].get("role") == "assistant":
                assistant_text = final_history[-1].get("content", "")

            words = assistant_text.split()
            if words:
                for next_word_count in range(last_word_count + 1, len(words) + 1):
                    typing_text = " ".join(words[:next_word_count])
                    display_history[-1]["content"] = typing_text
                    yield history_dicts_to_chatbot(display_history), ""
                    time.sleep(0.03)
                last_word_count = len(words)
            else:
                display_history[-1]["content"] = assistant_text
                yield history_dicts_to_chatbot(display_history), ""

        chat_data["history"] = final_history
        chat_backend.save_chat(current_chat_name, chat_data)
        yield history_dicts_to_chatbot(final_history), ""

    # --- Wiring ---
    create_char_btn.click(create_character, [char_name_input, system_prompt_input], [chat_list, character_image])
    chat_list.change(
        switch_chat,
        [chat_list],
        [chatbot, current_chat, system_prompt_display, character_image],
        scroll_to_output=True,
        show_progress="hidden"
    )
    update_prompt_btn.click(update_system_prompt, [system_prompt_display, current_chat], [system_prompt_display])
    msg_box.submit(
        send_message,
        inputs=[msg_box, chatbot, current_chat],
        outputs=[chatbot, msg_box],
        scroll_to_output=True,
        show_progress="hidden"
    )
    remove_button.click(remove_character, inputs=[chat_list], outputs=[chat_list])

    apply_button.click(settings.apply_settings, inputs=[image_style, response_type])

    if demo is not None:
        def initial_load():
            return history_dicts_to_chatbot(chat_data.get("history", []))
        demo.load(initial_load, outputs=[chatbot], scroll_to_output=True, show_progress="hidden")

    return (
        chat_list, chatbot, msg_box, current_chat,
        char_name_input, system_prompt_input, create_char_btn, system_prompt_display
    )

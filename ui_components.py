import gradio as gr
import chat_backend
import stable_diffusion
import re
import os
import time
import threading
from queue import Queue, Empty
import shutil
from PIL import Image
import tempfile
import numpy as np
import ollama
import logging
import settings
from ollama import generate_image_prompt
from datetime import datetime

logging.basicConfig(level=logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL


def normalize_path(path):
    if not path:
        return path
    return path.replace('\\', '/')


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

        character_avatar = normalize_path(chat_backend.get_avatar_file_path(last_chat_name))
        system_prompt = metadata.get("system_prompt", "")
    else:
        logging.warning("No last chat available... Setting default one...")
        chat_data = {"system_prompt": "", "history": []}
        system_prompt = "You are a helpful assistant."
        last_chat_name = "Default Chat"
        character_avatar = "assets/default.png"

    # --- Helpers for Gradio 3.x Chatbot format ---
    def normalize_chat_content(content):
        if isinstance(content, list):
            if len(content) == 1 and isinstance(content[0], dict):
                item = content[0]
                if item.get("type") == "text":
                    return item.get("text", "")
                if item.get("type") == "image":
                    return {"type": "image", "path": item.get("path", "")}
            parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif item.get("type") == "image":
                        return {"type": "image", "path": item.get("path", "")}
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "".join(parts)
            return content
        if isinstance(content, dict) and content.get("type") == "text":
            return content.get("text", "")
        return content

    def format_chat_message(content):
        content = normalize_chat_content(content)
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
                    chatbot_value.append({"role": "user", "content": italics_to_bold(user_text)})
                if assistant_text:
                    chatbot_value.append({"role": "assistant", "content": italics_to_bold(assistant_text)})
                continue

            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = normalize_chat_content(msg.get("content", ""))

            if role in ("user", "assistant"):
                if isinstance(content, str):
                    content = italics_to_bold(content)
                chatbot_value.append({"role": role, "content": content})

        return chatbot_value

    # --- Saving current chat ---
    current_chat = gr.State(last_chat_name)
    logging.debug("Setting current chat as: "+ last_chat_name)

    character_avatar_image = None
    if character_avatar and os.path.exists(character_avatar):
        try:
            character_avatar_image = Image.open(character_avatar).convert('RGBA')
        except Exception:
            character_avatar_image = None

    with gr.Row():
        with gr.Column(scale=1) as Sidebar:
            # Image of Character (Always visible)
            character_image = gr.Image(
                value=character_avatar_image or character_avatar,
                show_label=False,
                every=60000,
                buttons=["fullscreen"]
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
    
            with gr.Accordion("Generate new character image", open=False):
                new_image_prompt = gr.Textbox(
                    label="Image prompt",
                    placeholder="Use the avatar as a base and describe clothes, background, scenario...",
                    lines=2
                )
                create_image_btn = gr.Button("Create new image")
                image_status = gr.Markdown("", visible=True)
                generated_image = gr.Image(label="Generated image preview", visible=False)
                download_image = gr.File(label="Download generated image", visible=False)

            # Settings button at bottom
            settings_button = gr.Button("⚙️ Settings", scale=1)
            
            # Settings modal (hidden by default)
            with gr.Group(visible=False) as settings_modal:
                settings_close_btn = gr.Button("✕ Close", scale=1)
                image_style = gr.Dropdown(choices=["Realistic", "Anime"], label="Image Style", value="Realistic")
                response_type = gr.Dropdown(choices=["Slow", "Average", "Fast"], label="Response Type", value="Average")
                apply_button = gr.Button("Apply")
                gr.Markdown("### Change Avatar")
                edit_button = gr.Button("Edit")
                with gr.Column(visible=False) as avatar_edit_panel:
                    avatar_upload = gr.File(file_types=[".png", ".jpg", ".jpeg"], label="Upload Avatar", type="filepath", visible=False)

        with gr.Column(scale=5) as Textbox:
            status_banner = gr.Markdown("", visible=True)
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
        path = normalize_path(stable_diffusion.generate_avatar_a1111(name, prompt))

        metadata = chat_backend.new_metadata(name, system_prompt)
        metadata["avatar"] = path
        chat_backend.save_metadata(metadata)

        new_character_chat = {"history": []}
        chat_backend.save_chat(name, new_character_chat)

        chat_backend.save_last_chat_name(name)
        gr.Info(message=f"ℹ️ Character {name} was created!")
        character_list = chat_backend.load_characters_list()

        return (
            gr.update(choices=list(character_list), value=name),
            gr.update(value=name),
            gr.update(value=history_dicts_to_chatbot([]), avatar_images=("assets/user.png", path)),
            gr.update(value=path),
            gr.update(value=system_prompt),
            gr.update(value="✅ New character created and avatar loaded."),
        )
    
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
        character_avatar = normalize_path(chat_backend.get_avatar_file_path(name))

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

        def normalize_history_content(content):
            if isinstance(content, tuple) and len(content) == 1 and isinstance(content[0], str):
                return content[0]
            if isinstance(content, list):
                if len(content) == 1 and isinstance(content[0], dict):
                    item = content[0]
                    if item.get("type") == "text":
                        return item.get("text", "")
                    if item.get("type") == "image":
                        return {"type": "image", "path": item.get("path", "")}
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            parts.append(item.get("text", ""))
                        elif item.get("type") == "image":
                            return {"type": "image", "path": item.get("path", "")}
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "".join(parts)
                return content
            if isinstance(content, dict):
                if content.get("type") == "text":
                    return content.get("text", "")
                if content.get("type") == "image":
                    return {"type": "image", "path": content.get("path", "")}
            return content

        if isinstance(history, list) and all(isinstance(item, (list, tuple)) for item in history):
            for row in history:
                if not row:
                    continue
                user_text = row[0] if len(row) > 0 else ""
                assistant_text = row[1] if len(row) > 1 else ""
                if user_text:
                    cleaned.append({"role": "user", "content": normalize_history_content(user_text)})
                if assistant_text:
                    cleaned.append({"role": "assistant", "content": normalize_history_content(assistant_text)})
            return cleaned

        for msg in history:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                continue

            content = normalize_history_content(msg["content"])
            if isinstance(content, str):
                content = italics_to_bold(content)

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
                time.sleep(0.20)

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

            if assistant_text:
                if display_history[-1].get("content") != assistant_text:
                    display_history[-1]["content"] = assistant_text
                    yield history_dicts_to_chatbot(display_history), ""
            else:
                display_history[-1]["content"] = assistant_text
                yield history_dicts_to_chatbot(display_history), ""

        chat_data["history"] = final_history
        chat_backend.save_chat(current_chat_name, chat_data)
        yield history_dicts_to_chatbot(final_history), ""

    # --- Wiring ---
    create_char_btn.click(
        create_character,
        [char_name_input, system_prompt_input],
        [chat_list, current_chat, chatbot, character_image, system_prompt_display, status_banner]
    )
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
    
    # Settings modal toggle
    def open_settings():
        return gr.update(visible=True)
    
    def close_settings():
        return gr.update(visible=False)
    
    settings_button.click(open_settings, outputs=[settings_modal])
    settings_close_btn.click(close_settings, outputs=[settings_modal])
    
    # Show edit controls when Edit is clicked
    def show_edit_panel(name):
        return gr.update(visible=True), gr.update(visible=True)

    edit_button.click(show_edit_panel, inputs=[current_chat], outputs=[avatar_edit_panel, avatar_upload])

    def resolve_uploaded_path(uploaded):
        if not uploaded:
            return None
        if isinstance(uploaded, str) and os.path.exists(uploaded):
            return uploaded
        if hasattr(uploaded, 'name') and os.path.exists(uploaded.name):
            return uploaded.name
        if isinstance(uploaded, dict) and 'name' in uploaded and os.path.exists(uploaded['name']):
            return uploaded['name']
        return str(uploaded)

    def update_avatar_from_file(src, name):
        """Common logic for updating avatar from file path."""
        try:
            img = Image.open(src).convert('RGBA')
            final = img.resize((512, 512), Image.LANCZOS)
            avatar_folder = os.path.dirname(chat_backend.get_avatar_file_path(name))
            os.makedirs(avatar_folder, exist_ok=True)
            current_avatar = chat_backend.get_avatar_file_path(name)
            timestamped_avatar = os.path.join(avatar_folder, f"Avatar_{int(time.time())}.png")

            if os.path.exists(current_avatar):
                os.replace(current_avatar, timestamped_avatar)

            dest = current_avatar
            final.save(dest)

            metadata = chat_backend.get_metadata(name) or chat_backend.new_metadata(name, "")
            if not isinstance(metadata, dict):
                metadata = chat_backend.new_metadata(name, "")
            metadata.setdefault('name', name)
            metadata['avatar'] = dest
            chat_backend.save_metadata(metadata)

            updated_path = normalize_path(dest)
            return (
                gr.update(value=updated_path),
                gr.update(avatar_images=("assets/user.png", updated_path)),
                gr.update(value=f"✅ Avatar updated successfully.")
            )
        except Exception as ex:
            logging.exception("Failed updating avatar")
            fallback_path = chat_backend.get_avatar_file_path(name) if name else None
            return (
                gr.update(value=normalize_path(fallback_path) if fallback_path else None),
                gr.update(avatar_images=("assets/user.png", normalize_path(fallback_path) if fallback_path else None)),
                gr.update(value=f"⚠️ Failed to update avatar: {ex}")
            )

    def save_uploaded_avatar(uploaded, name):
        src = resolve_uploaded_path(uploaded)
        if not src or not os.path.exists(src):
            logging.warning("Uploaded avatar path invalid")
            fallback = normalize_path(chat_backend.get_avatar_file_path(name)) if name else None
            return (
                gr.update(value=fallback),
                gr.update(avatar_images=("assets/user.png", fallback if fallback else None)),
                gr.update(value="⚠️ Failed to upload avatar. Please try again.")
            )
        if not name:
            logging.warning("No active chat selected for avatar change")
            return gr.update(value=None), gr.update(), gr.update(value="⚠️ No active chat selected.")

        return update_avatar_from_file(src, name)

    def create_character_image(name, prompt):
        if not name:
            yield (
                gr.update(value=None, visible=False),
                gr.update(value=None, visible=False),
                "⚠️ Select a character before generating an image."
            )
            return
        if not prompt:
            yield (
                gr.update(value=None, visible=False),
                gr.update(value=None, visible=False),
                "⚠️ Add an image prompt to describe clothes, background, or scenario."
            )
            return

        yield (
            gr.update(value=None, visible=False),
            gr.update(value=None, visible=False),
            "⏳ Generating image... this may take a moment."
        )

        metadata = chat_backend.get_metadata(name) or chat_backend.new_metadata(name, "")
        character_info = metadata.get("system_prompt", f"Character name: {name}.")

        try:
            request_prompt = ollama.generate_image_request_prompt(prompt, character_info)
            img_path = stable_diffusion.generate_requested_image(name, request_prompt)
            file_path = os.path.abspath(img_path)
            metadata.setdefault("assets", [])
            asset_path = normalize_path(os.path.relpath(img_path).replace('\\', '/'))
            if asset_path not in metadata["assets"]:
                metadata["assets"].append(asset_path)
            chat_backend.save_metadata(metadata)

            yield (
                gr.update(value=file_path, visible=True),
                gr.update(value=file_path, visible=True),
                f"✅ Generated image saved as {asset_path}."
            )
        except Exception as ex:
            logging.exception("Failed to generate requested image")
            yield (
                gr.update(value=None, visible=False),
                gr.update(value=None, visible=False),
                f"⚠️ Failed to generate image: {ex}"
            )

    avatar_upload.change(save_uploaded_avatar, inputs=[avatar_upload, current_chat], outputs=[character_image, chatbot, status_banner], show_progress='hidden')

    create_image_btn.click(
        create_character_image,
        inputs=[current_chat, new_image_prompt],
        outputs=[generated_image, download_image, image_status],
        show_progress='minimal'
    )

    if demo is not None:
        def initial_load():
            return history_dicts_to_chatbot(chat_data.get("history", []))
        demo.load(initial_load, outputs=[chatbot], scroll_to_output=True, show_progress="hidden")

    return (
        chat_list, chatbot, msg_box, current_chat,
        char_name_input, system_prompt_input, create_char_btn, system_prompt_display
    )
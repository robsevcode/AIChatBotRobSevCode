import gradio as gr
import chat_backend
import stable_diffusion
import re
import os
import time
import threading
from queue import Queue, Empty
from PIL import Image
import ollama
import logging
import settings
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)


def normalize_path(path):
    if not path:
        return path
    return path.replace('\\', '/')


def italics_to_bold(text):
    """Converts action-style markup to bold-italic text."""
    if not isinstance(text, str):
        return text

    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'***\1***', text)
    text = re.sub(r'_(.*?)_', r'***\1***', text)
    text = re.sub(r'\(([^)]+)\)', r'***\1***', text)
    text = re.sub(r'\[([^\]]+)\]', r'***\1***', text)
    return text


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


def history_dicts_to_chatbot(history):
    if history is None:
        return []

    chatbot_value = []

    for msg in history:
        if isinstance(msg, (list, tuple)):
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


def build_chat_page(demo=None, current_chat_state=None):
    """Build the chat page with messaging interface and settings."""
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

    # Use provided state or create new one
    if current_chat_state is None:
        current_chat = gr.State(last_chat_name)
    else:
        current_chat = current_chat_state
    character_avatar_image = None
    if character_avatar and os.path.exists(character_avatar):
        try:
            character_avatar_image = Image.open(character_avatar).convert('RGBA')
        except Exception:
            character_avatar_image = None

    with gr.Row():
        # Small avatar on the left
        with gr.Column(scale=1, min_width=80):
            character_image = gr.Image(
                value=character_avatar_image or character_avatar,
                show_label=False,
                every=60000,
                buttons=[],
                height=100
            )

        # Chat area on the right
        with gr.Column(scale=5):
            with gr.Row():
                gr.Markdown("### Chat", scale=4)
                settings_btn = gr.Button("⚙️", scale=1, size="sm")

            chatbot = gr.Chatbot(
                show_label=False,
                height=650,
                elem_id="chatbot",
                value=history_dicts_to_chatbot(chat_data.get("history", [])),
                avatar_images=("assets/user.png", character_avatar),
                buttons=[]
            )
            
            with gr.Row():
                msg_box = gr.Textbox(label="Message", scale=5)
                gen_image_btn = gr.Button("🎨", scale=1, size="sm")

    # Settings modal
    with gr.Group(visible=False) as settings_modal:
        gr.Markdown("### Settings")
        with gr.Row():
            system_prompt_display = gr.Textbox(
                label="Personality / System Prompt",
                value=system_prompt,
                interactive=True,
                lines=4
            )
        with gr.Row():
            image_style = gr.Dropdown(choices=["Realistic", "Anime"], label="Image Style", value="Realistic", scale=1)
            response_type = gr.Dropdown(choices=["Slow", "Average", "Fast"], label="Response Type", value="Average", scale=1)
        with gr.Row():
            update_prompt_btn = gr.Button("Update Personality", scale=1)
            apply_settings_btn = gr.Button("Apply Settings", scale=1)
            close_settings_btn = gr.Button("Close", scale=1)

    # Image generation modal
    with gr.Group(visible=False) as image_gen_modal:
        gr.Markdown("### Generate Character Image")
        new_image_prompt = gr.Textbox(
            label="Image Prompt",
            placeholder="Describe clothes, background, scenario...",
            lines=3
        )
        with gr.Row():
            create_image_btn = gr.Button("Generate")
            cancel_image_btn = gr.Button("Cancel")
        image_status = gr.Markdown("", visible=True)
        generated_image = gr.Image(label="Preview", visible=False)
        download_image = gr.File(label="Download", visible=False)

    # --- Helper functions ---
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

    def update_system_prompt(new_prompt, name):
        if not name:
            return gr.update(value="⚠️ No active chat selected")
        
        logging.info("Updating personality of: " + name)
        metadata = chat_backend.get_metadata(name)
        metadata["system_prompt"] = new_prompt
        chat_backend.save_metadata(metadata)
        return gr.update(value=new_prompt)

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

    # --- Callbacks ---
    def toggle_settings():
        return gr.update(visible=True)

    def close_settings():
        return gr.update(visible=False)

    def toggle_image_gen():
        return gr.update(visible=True)

    def close_image_gen():
        return gr.update(visible=False)

    settings_btn.click(toggle_settings, outputs=[settings_modal])
    close_settings_btn.click(close_settings, outputs=[settings_modal])

    gen_image_btn.click(toggle_image_gen, outputs=[image_gen_modal])
    cancel_image_btn.click(close_image_gen, outputs=[image_gen_modal])

    update_prompt_btn.click(update_system_prompt, [system_prompt_display, current_chat], [system_prompt_display])
    apply_settings_btn.click(settings.apply_settings, inputs=[image_style, response_type])

    msg_box.submit(
        send_message,
        inputs=[msg_box, chatbot, current_chat],
        outputs=[chatbot, msg_box],
        scroll_to_output=True,
        show_progress="hidden"
    )

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
        chatbot, msg_box, current_chat, character_image,
        system_prompt_display
    )

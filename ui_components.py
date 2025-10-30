import gradio as gr
import chat_backend
import stable_diffusion
import os
import ollama
import logging
from pydantic import BaseModel
from ollama import generate_image_prompt
from datetime import datetime

logging.basicConfig(level=logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL

def build_chat_ui():
    last_chat_name = chat_backend.load_last_chat_name()
    characters_list = chat_backend.load_characters_list()

    if last_chat_name and (last_chat_name in characters_list):
        chat_data, metadata = chat_backend.load_chat(last_chat_name)
        character_avatar_path = chat_backend.get_avatar_file_path(last_chat_name)
        system_prompt = metadata["system_prompt"]
    else:
        logging.warning("No last chat available... Setting default one...")
        chat_data = {"system_prompt": "", "history": []}
        system_prompt = "You are a helpful assistant."
        last_chat_name = "Default Chat"
        character_avatar_path = "assets/default.png"

    # --- Saving current chat ---
    current_chat = gr.State(last_chat_name)
    logging.debug("Setting current chat as: "+ last_chat_name)

    with gr.Row():
        with gr.Column(scale=1, min_width=200) as Sidebar:
            # Image of Character (Always visible)
            character_image = gr.Image(
                value=character_avatar_path,
                show_label=False,
                show_download_button=False
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
    
        with gr.Column(scale=5) as Textbox:
            # Textbox of chatbot
            chatbot = gr.Chatbot(
                type="messages",
                show_label=False,
                height=700,
                value=chat_data.get("history", []),
                avatar_images=("assets/user.png", character_avatar_path)  # (user, bot)
            )
            msg_box = gr.Textbox(label="Message", submit_btn = True)

    # ------------------------
    #        Callback
    # ------------------------

    def create_character(character_name, system_prompt):
        if not character_name:
            logging.warning("No name was added!")
            gr.Warning("No name was added!")
            return
        if not system_prompt:
            logging.warning("No personality was added!")
            gr.Warning("No personality was added!")
            return
        
        prompt = ollama.generate_image_prompt(system_prompt)
        avatar_path = stable_diffusion.generate_avatar_a1111(character_name, prompt)

        metadata = chat_backend.new_metadata(character_name, system_prompt)
        chat_backend.save_metadata(metadata)

        new_character_chat = {"history": []}
        chat_backend.save_chat(character_name, new_character_chat)

        chat_backend.save_last_chat_name(character_name)
        gr.Info(message=f"ℹ️ Character {character_name} was created!")
        character_list = chat_backend.load_characters_list()

        return gr.update(choices=list(character_list), value=character_name), gr.update(value=avatar_path)
    
    def remove_character(character_name):
        logging.info("Deleting character: ", character_name)
        character_list = chat_backend.load_characters_list()
        if character_name == "Default Chat":
            logging.warning("ℹ️ Default Character cannot be removed!")
            gr.Error("ℹ️ Default Character cannot be removed!")
            return gr.update(choices=list(character_list))

        if character_name not in character_list:
            return gr.update(choices=list(character_list)), "Character not found."

        chat_backend.reset_last_chat_name()
        chat_backend.remove_chat(character_name)

        logging.info("Character " + character_name + " removed!")
        gr.Info(message=f"ℹ️ Character {character_name} was removed!")

        return gr.update(choices=list(chat_backend.load_characters_list()))

    # When using the Dropdown
    def switch_chat(character_name):
        if not character_name:
            logging.critical("No name found when switching characters!")
            return gr.update(value=[]), "", gr.update(value="")
        logging.debug("Switch character to:", character_name)

        chat_backend.save_last_chat_name(character_name)
        chat_data, metadata = chat_backend.load_chat(character_name)
        logging.debug("Chat data loaded for: "+character_name)
        history = chat_data["history"]
        system_prompt = metadata["system_prompt"]
        character_avatar = chat_backend.get_avatar_file_path(character_name)
        return gr.update(value=history), character_name, gr.update(value=system_prompt), gr.update(value=character_avatar), gr.update(avatar_images=("assets/user.png", character_avatar))

    def update_system_prompt(new_prompt, character_name):
        if not character_name:
            return gr.update(value="⚠️ No active chat selected")
        
        logging.info("Updating personality of: " + character_name)
        metadata = chat_backend.get_metadata(character_name)
        metadata["system_prompt"] = new_prompt
        chat_backend.save_metadata(metadata)
        return gr.update(value=new_prompt)
    

    def clean_chat_history(history):
        cleaned = []
        logging.debug("Cleaning history from chat")
        for msg in history:
            if "role" not in msg or "content" not in msg:
                continue

            content = msg["content"]
            # Case 1: single-element tuple (from Gradio)
            if isinstance(content, tuple) and len(content) == 1 and isinstance(content[0], str):
                content = {"type": "image", "path": content[0]}

            # Case 2: string pointing to an image file
            elif isinstance(content, str) and os.path.splitext(content)[1].lower() in (".png", ".jpg", ".jpeg"):
                content = {"type": "image", "path": content}

            # Case 3: already dict with type image -> leave as-is
            elif isinstance(content, dict) and content.get("type") == "image":
                pass

            # Case 4: everything else -> leave as-is

            cleaned.append({"role": msg["role"], "content": content})

        return cleaned

    def display_user_message(message, chatbot_history):
        logging.debug("DISPLAY MESSAGE")
        history = clean_chat_history(chatbot_history)
        logging.debug("Sending new message...")
        history_with_user = history + [{"role": "user", "content": message}]
        yield history_with_user, ""

    def send_message(chatbot_history, current_chat_name):
        logging.debug("SENDING MESSAGE")
        # 1: Clean chat history if needed
        chatbot_history = clean_chat_history(chatbot_history)
        
        if not current_chat_name:
            logging.warning("No chat selected")
            return chatbot_history, "⚠️ Select a chat first"
        
        logging.debug("Sending message to: ", current_chat_name)

        if chatbot_history is None:
            # Consider creating a new one
            logging.warning("No chat available for that user")
            return chatbot_history, "⚠️ Chat data missing"

        chat_data = {"history": chatbot_history}
        metadata = chat_backend.get_metadata(current_chat_name)
        chat_data["system_prompt"] = metadata.get("system_prompt", "")

        logging.debug("Getting the last chat from user")
        last_message = chatbot_history[-1]["content"] if chatbot_history else ""

        if "show me" in last_message.lower():
            prompt = ollama.generate_image_request_prompt(last_message, chat_data["system_prompt"])
            img_path = stable_diffusion.generate_requested_image(current_chat_name, prompt)

            chatbot_history.append({
                "role": "assistant",
                "content": {"type": "image", "path": img_path}
            })

            #yield chatbot_history, ""

            # Save after
            chat_data["history"] = chatbot_history
            chat_backend.save_chat(current_chat_name, chat_data)
        
        backend_gen_fn = chat_backend.make_chat_fn(
            chat_data.get("system_prompt", ""),
            chat_data.get("history", [])
        )
        gen = backend_gen_fn(chat_data["history"])

        for partial_history in gen:
            yield partial_history, ""

        # Save after everything is finished, to avoid extra calls
        chat_backend.save_chat(current_chat_name, chat_data)

    # --- Wiring ---
    create_char_btn.click(create_character, [char_name_input, system_prompt_input], [chat_list, character_image])
    chat_list.change(switch_chat, [chat_list], [chatbot, current_chat, system_prompt_display, character_image, chatbot])
    update_prompt_btn.click(update_system_prompt, [system_prompt_display, current_chat], [system_prompt_display])
    msg_box.submit(display_user_message, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box]).then(send_message, [chatbot, current_chat], [chatbot, msg_box])
    remove_button.click(remove_character, inputs=[chat_list], outputs=[chat_list])

    return (
        chat_list, chatbot, msg_box, current_chat,
        char_name_input, system_prompt_input, create_char_btn, system_prompt_display
    )

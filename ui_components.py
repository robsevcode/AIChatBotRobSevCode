import gradio as gr
import chat_backend
import stable_diffusion
import re
import os
import ollama
import json
from ollama import generate_image_prompt
from datetime import datetime

def italics_to_bold(text):
    """
    Converts Markdown italics (*text* or _text_) to bold (**text**)
    """
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'**\1**', text)
    text = re.sub(r'_(.*?)_', r'**\1**', text)
    return text

def build_chat_ui():
    # --- Initial state ---
    print("***")
    print("Building the UI")
    print("***")
    last_chat_name = chat_backend.load_last_chat()
    all_characters_info = chat_backend.load_index()
    all_characters_names = list(all_characters_info.keys())
    print("All characters are:", all_characters_names)

    # --- Loading last chat ---
    if last_chat_name and last_chat_name in all_characters_names:
        chat_data = chat_backend.load_chat(last_chat_name, all_characters_info[last_chat_name])
        character_avatar = all_characters_info[last_chat_name].get("avatar", "assets/default.png")
        system_prompt = chat_data.get("system_prompt", "")
        character_chat_name = last_chat_name
    else:
        print("No last chat available...")
        chat_data = {"system_prompt": "", "history": []}
        character_avatar = "assets/default.png"
        system_prompt = ""
        character_chat_name = ""

    # --- Saving current chat ---
    current_chat = gr.State(character_chat_name)

    with gr.Row():
        with gr.Column(scale=1, min_width=200) as Sidebar:
            # Image of Character (Always visible)
            character_image = gr.Image(
                value=character_avatar,
                show_label=False,
                show_download_button=False
                )
            
            # Accordion for settings
            # Dropdown to select chat
            chat_list = gr.Dropdown(
                choices=all_characters_names,
                allow_custom_value=False,
                label="Chats",
                value= character_chat_name if character_chat_name in all_characters_names else None,
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
                avatar_images=("assets/user.png", character_avatar)  # (user, bot)
            )
            msg_box = gr.Textbox(label="Message")
            send_btn = gr.Button("Send")       

    # --- Callbacks ---
    def create_character(name, system_prompt):
        prompt = ollama.generate_image_prompt(system_prompt)
        path = stable_diffusion.generate_avatar_a1111(name, prompt)
        print(path)
        print("Creating character: ", name)
        if not name:
            gr.Warning("No name was added!", duration=5)
            return
        if not system_prompt:
            gr.Warning("No personality was added!", duration=5)
            return
            
        # Populate character info
        character_info = {
            "file": f"{name}.json",
            "system_prompt": system_prompt,
            "avatar": f"assets/{name}.png",
            "last_updated": datetime.now().isoformat()
        }
        index = chat_backend.load_index()
        chat_backend.save_index(name, character_info, index)

        new_character_chat = {"history": []}
        chat_backend.save_chat(name, new_character_chat)
        chat_backend.save_last_chat(name)
        gr.Info(f"ℹ️ Character {name} was created!", duration=5)
        return gr.update(choices=list(index.keys()), value=name), gr.update(value=path) #Refactor this to avoid calling load_index twice
    
    def remove_character(name):
        print("Deleting character: ", name)
        if name == "Default Chat":
            print("ℹ️ Default Character cannot be removed!")
            gr.Error("ℹ️ Default Character cannot be removed!", duration=5)
            return gr.update(choices=list(chat_backend.load_index().keys()))
        
        # Load index
        index = chat_backend.load_index()

        if name not in index:
            return gr.update(choices=list(index.keys())), "Character not found."

        # Remove chat
        chat_backend.reset_last_chat()
        chat_backend.remove_chat(name, index)

        # Remove from index
        index = chat_backend.remove_from_index(name, index)
        print("Character ", name, " removed!")
        gr.Info(f"ℹ️ Character {name} was removed!", duration=5)

        return gr.update(choices=list(index.keys()))

    # When using the Dropdown
    def switch_chat(name):
        print("Switch character to:", name)
        if not name:
            return gr.update(value=[]), "", gr.update(value="")

        chat_backend.save_last_chat(name)
        index = chat_backend.load_index()
        chat_data = chat_backend.load_chat(name, index[name])
        history = chat_data.get("history", [])
        system_prompt = index[name]["system_prompt"]
        character_avatar = index[name].get("avatar", "assets/default.png")
        return gr.update(value=history), name, gr.update(value=system_prompt), gr.update(value=character_avatar), gr.update(avatar_images=("assets/user.png", character_avatar))



    def update_system_prompt(new_prompt, chat_name):
        print("Updating personality of: ", chat_name)
        if not chat_name:
            return gr.update(value="⚠️ No active chat selected")

        index = chat_backend.load_index()
        if index[chat_name] is None:
            return gr.update(value="⚠️ No index for character")
        index[chat_name]["system_prompt"] = new_prompt
        chat_backend.save_index(chat_name, index[chat_name], index)
        return gr.update(value=new_prompt)
    


    def clean_chat_history(history):
        cleaned = []
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
        history = clean_chat_history(chatbot_history)
        print("Sending new message...")
        history_with_user = history + [{"role": "user", "content": message}]
        yield history_with_user, ""

    def send_message(chatbot_history, current_chat_name):
        chatbot_history = clean_chat_history(chatbot_history)
        print("Sending message to: ", current_chat_name)
        if not current_chat_name:
            return chatbot_history, "⚠️ Select a chat first"

        if chatbot_history is None:
            # Consider creating a new one
            return chatbot_history, "⚠️ Chat data missing"

        index = chat_backend.load_index()
        chat_data = {"history": chatbot_history}
        chat_data["system_prompt"] = index[current_chat_name].get("system_prompt", "")

        # Get the last user message
        last_message = chatbot_history[-1]["content"] if chatbot_history else ""
        if "show me" in last_message.lower():
            # Get prompt to generate image
            #prompt = ollama.generate_image_request_prompt(last_message, chat_data["system_prompt"])
            
            # Call your image generation method

            img_path = "assets\\Paty_20250916_010533.png"
            #img_path = stable_diffusion.generate_requested_image(current_chat_name, prompt)  # ← your method

            # Append image message instead of text
            chatbot_history.append({
                "role": "assistant",
                "content": {"type": "image", "path": img_path}
            })

            yield chatbot_history, ""

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
    send_btn.click(display_user_message, [msg_box, chatbot], [chatbot, msg_box]).then(send_message, [chatbot, current_chat], [chatbot, msg_box])
    msg_box.submit(display_user_message, [msg_box, chatbot], [chatbot, msg_box]).then(send_message, [chatbot, current_chat], [chatbot, msg_box])
    remove_button.click(remove_character, inputs=[chat_list], outputs=[chat_list])

    return (
        chat_list, chatbot, msg_box, send_btn, current_chat,
        char_name_input, system_prompt_input, create_char_btn, system_prompt_display
    )

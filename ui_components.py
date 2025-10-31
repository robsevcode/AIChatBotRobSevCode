import gradio as gr
import chat_backend
import stable_diffusion
import os
import json
import ollama
import logging
from gradio.components import Chatbot, ChatMessage
from pydantic import BaseModel
from ollama import generate_image_prompt
from datetime import datetime
from classes import *

logging.basicConfig(level=logging.INFO) # DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger('UI') 

def build_chat_ui():
    logger.info("*** build_chat_ui ***")
    last_chat_name = chat_backend.load_last_chat_name()
    characters_list = chat_backend.load_characters_list()

    if last_chat_name and (last_chat_name in characters_list):
        chat_data, metadata = chat_backend.load_chat(last_chat_name)
        character_avatar_path = chat_backend.get_avatar_file_path(last_chat_name)
        system_prompt = metadata.system_prompt
    else:
        logger.warning("No last chat available... Setting default one...")
        chat_data = Chat(system_prompt= "", history= [])
        system_prompt = "You are a helpful assistant."
        last_chat_name = "Default Chat"
        character_avatar_path = "assets/default.png"

    # --- Saving current chat ---
    current_chat = gr.State(last_chat_name)
    logger.debug("Setting current chat as: "+ last_chat_name)
    logger.debug(current_chat)

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
                value=[msg.model_dump() for msg in chat_data.history],
                avatar_images=("assets/user.png", character_avatar_path)  # (user, bot)
            )
            msg_box = gr.Textbox(label="Message", submit_btn = True)

    # ------------------------
    #        Callback
    # ------------------------

    def create_character(character_name, system_prompt):
        logger.info("*** create_character ***")
        if not character_name:
            logger.warning("No name was added!")
            gr.Warning("No name was added!")
            return
        if not system_prompt:
            logger.warning("No personality was added!")
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
        logger.info("*** remove_character ***")
        logger.info("Deleting character: ", character_name)
        character_list = chat_backend.load_characters_list()
        if character_name == "Default Chat":
            logger.warning("ℹ️ Default Character cannot be removed!")
            gr.Error("ℹ️ Default Character cannot be removed!")
            return gr.update(choices=list(character_list))

        if character_name not in character_list:
            return gr.update(choices=list(character_list)), "Character not found."

        chat_backend.reset_last_chat_name()
        chat_backend.remove_chat(character_name)

        logger.info("Character " + character_name + " removed!")
        gr.Info(message=f"ℹ️ Character {character_name} was removed!")

        return gr.update(choices=list(chat_backend.load_characters_list()))

    # When using the Dropdown
    def switch_chat(character_name):
        logger.info("*** switch_chat ***")
        if not character_name:
            logger.critical("No name found when switching characters!")
            return gr.update(value=[]), "", gr.update(value="")
        logger.debug("Switch character to:" + character_name)

        chat_backend.save_last_chat_name(character_name)
        chat_data, metadata = chat_backend.load_chat(character_name)
        logger.debug("Chat data loaded for: "+character_name)
        history = chat_data.history
        system_prompt = metadata.system_prompt
        character_avatar = chat_backend.get_avatar_file_path(character_name)
        return gr.update(value=[msg.model_dump() for msg in history]), character_name, gr.update(value=system_prompt), gr.update(value=character_avatar), gr.update(avatar_images=("assets/user.png", character_avatar))

    def update_system_prompt(new_prompt, character_name):
        logger.info("*** update_system_prompt ***")
        if not character_name:
            return gr.update(value="⚠️ No active chat selected")
        
        logger.info("Updating personality of: " + character_name)
        metadata = chat_backend.get_metadata(character_name)
        metadata.system_prompt = new_prompt
        chat_backend.save_metadata(metadata)
        return gr.update(value=new_prompt)

    def display_user_message(message, history):
        logger.info("*** display_user_message ***")
        logger.debug("Sending new message...")
        history_with_user = history + [{"role": "user", "content": message}]
        yield history_with_user, ""

    def convert_chatbot_to_chatdata(chatbot_history: str) -> list[Message]:
        logger.debug("DEF: convert_chatbot_to_chatdata")
        messages = []
        for message in chatbot_history:
            if isinstance(message, ChatMessage):
                messages.append(Message(role=message.role, content=message.content))
            elif isinstance(message, dict):
                messages.append(Message.model_validate(message))
            else:
                raise TypeError(f"Unsupported history item type: {type(message)}")
        return messages

    def send_message(chatbot_history: Chatbot, current_chat_name: str):
        logger.info("*** send_message ***")
        
        if not current_chat_name:
            logger.warning("No chat selected")
            return chatbot_history, "⚠️ Select a chat first"
        
        logger.debug("Sending message to: " + current_chat_name)

        if chatbot_history is None:
            # Consider creating a new one
            logger.warning("No chat available for that user")
            return chatbot_history, "⚠️ Chat data missing"

        chat_data_history = convert_chatbot_to_chatdata(chatbot_history)
        logger.debug("Chat converted to chatdata")
        logger.debug(chat_data_history)
        metadata = chat_backend.get_metadata(current_chat_name)

        last_message = Message(role=chat_data_history[-1].role, content=chat_data_history[-1].content) if chatbot_history else ""

        if "show me" in last_message.content.lower():
            prompt = ollama.generate_image_request_prompt(last_message, metadata.system_prompt)
            img_path = stable_diffusion.generate_requested_image(current_chat_name, prompt)

            #yield chatbot_history, ""

            # Save after
            chat_data_history.append(Message(role="assistant", content=MessageContentMedia(type="image", path=img_path)))
            chat_backend.save_chat(current_chat_name, Chat(history=chat_data_history))
        
        backend_gen_fn = chat_backend.make_chat_fn(
            metadata,
            chat_data_history
        )
        logger.debug("Message sent with history")
        logger.debug(chat_data_history)
        gen = backend_gen_fn(last_message)

        for partial_history in gen:
            yield partial_history, ""

        logger.debug("Partial")
        logger.debug(partial_history)

        # Save after everything is finished, to avoid extra calls
        logger.debug(chat_data_history)
        chat_backend.save_chat(current_chat_name, Chat(history=chat_data_history))

    # --- Wiring ---
    create_char_btn.click(create_character, [char_name_input, system_prompt_input], [chat_list, character_image])
    chat_list.change(switch_chat, [chat_list], [chatbot, current_chat, system_prompt_display, character_image, chatbot])
    update_prompt_btn.click(update_system_prompt, [system_prompt_display, current_chat], [system_prompt_display])
    msg_box.submit(display_user_message, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box]).then(send_message, [chatbot, current_chat], [chatbot, msg_box])
    remove_button.click(remove_character, inputs=[chat_list], outputs=[chat_list])

    return chat_list, chatbot, msg_box, current_chat, char_name_input, system_prompt_input, create_char_btn, system_prompt_display
    

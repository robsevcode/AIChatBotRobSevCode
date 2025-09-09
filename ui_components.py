import gradio as gr
import chat_backend
from chat_backend import chats, make_chat_fn, add_chat

def build_chat_ui():
    chats = chat_backend.chats
    current_chat = gr.State("")  # active chat

    with gr.Row():
        # --- Sidebar ---
        with gr.Column(scale=1):
            chat_list = gr.Dropdown(
                choices=list(chats.keys()),  # <- already loaded
                label="Chats",
                value=None,
                interactive=True
            )

            char_name_input = gr.Textbox(label="Character Name")
            system_prompt_input = gr.Textbox(label="System Prompt / Identity")
            create_char_btn = gr.Button("Create Character")

        # --- Chat area ---
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(type="messages")
            msg_box = gr.Textbox(label="Message")
            send_btn = gr.Button("Send")

    # Callbacks

    # Create a character
    def create_character(name, system_prompt):
        if not name:
            return gr.update(choices=list(chats.keys()))
        add_chat(name, system_prompt)
        return gr.update(choices=list(chats.keys()))

    create_char_btn.click(
        create_character,
        [char_name_input, system_prompt_input],
        [chat_list]
    )

    # Switch chat
    def switch_chat(name):
        if not name or name not in chats:
            return [], ""
        return chats[name]["history"], name

    chat_list.change(switch_chat, [chat_list], [chatbot, current_chat])

    # Send message
    def send_message(message, history, current_chat):
        if not current_chat or current_chat not in chats:
            return history, "⚠️ Select a chat first"
        chat_data = chats[current_chat]
        fn = make_chat_fn(chat_data["system_prompt"], chat_data["history"])
        reply = fn(message, history)
        chats[current_chat]["history"] = reply
        return reply, ""

    send_btn.click(send_message, [msg_box, chatbot, current_chat], [chatbot, msg_box])
    msg_box.submit(send_message, [msg_box, chatbot, current_chat], [chatbot, msg_box])

    # Return references for main.py
    return chat_list, chatbot, msg_box, send_btn, current_chat, char_name_input, system_prompt_input, create_char_btn

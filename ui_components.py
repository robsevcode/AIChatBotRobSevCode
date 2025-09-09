# ui_components.py
import gradio as gr
from chat_backend import chats, make_chat_fn

def build_chat_ui():
    current_chat = gr.State("")

    with gr.Row():
        # --- Sidebar ---
        with gr.Column(scale=1):
            chat_list = gr.Radio(choices=list(chats.keys()), label="Chats")

        # --- Chat area ---
        with gr.Column(scale=3):
            chatbot = gr.Chatbot()
            msg_box = gr.Textbox(label="Message")
            send_btn = gr.Button("Send")

    # --- Callbacks ---
    def switch_chat(name):
        if name not in chats:
            return [], ""
        return chats[name]["history"], name

    def send_message(message, history, current_chat):
        if not current_chat or current_chat not in chats:
            return history, "⚠️ Select a chat first"
        chat_data = chats[current_chat]
        fn = make_chat_fn(chat_data["system_prompt"], chat_data["history"])
        reply = fn(message, history)
        chats[current_chat]["history"] = reply
        return reply, ""

    chat_list.change(switch_chat, [chat_list], [chatbot, current_chat])
    send_btn.click(send_message, [msg_box, chatbot, current_chat], [chatbot, msg_box])
    msg_box.submit(send_message, [msg_box, chatbot, current_chat], [chatbot, msg_box])


    return chat_list, chatbot, msg_box, send_btn, current_chat

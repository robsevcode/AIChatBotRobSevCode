import gradio as gr
from chat_backend import list_chats, load_chat, save_chat, add_chat, load_last_chat, save_last_chat, load_chats
from ui_components import build_chat_ui

load_chats()  # load saved chats before UI

with gr.Blocks() as demo:
    chat_list, chatbot, msg_box, send_btn, current_chat, char_name_input, system_prompt_input, create_char_btn, system_prompt_display = build_chat_ui()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)

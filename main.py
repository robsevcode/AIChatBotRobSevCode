import gradio as gr
from chat_backend import load_chats, chats
from ui_components import build_chat_ui

print("Calling chats...")
load_chats()  # load saved chats before UI
print("The chats are... ", chats)

print("Building UI...")
with gr.Blocks() as demo:
    chat_list, chatbot, msg_box, send_btn, current_chat, char_name_input, system_prompt_input, create_char_btn = build_chat_ui()

if __name__ == "__main__":
    demo.launch()

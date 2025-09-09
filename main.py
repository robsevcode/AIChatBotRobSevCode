# main.py
import gradio as gr
from chat_backend import add_chat
from ui_components import build_chat_ui

# Preload some example chats
add_chat("Alice", "You are Alice, a helpful assistant.")
add_chat("Bob", "You are Bob, a sarcastic AI.")

with gr.Blocks() as demo:
    build_chat_ui()

if __name__ == "__main__":
    demo.launch()

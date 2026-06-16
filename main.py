import logging
import gradio as gr
from ui_components import build_sidebar_ui
from chat_frontend import build_chat_page
from gr_html_assets import inject_gr_html
import os

logging.getLogger("httpx").setLevel(logging.WARNING)

css = """
.generating,
.generating.svelte-zlszon.svelte-zlszon {
    border: none !important;
    box-shadow: none !important;
    background-color: transparent !important;
}
"""

# Get the path to scrolldown.js in the same directory as this script
js_path = os.path.join(os.path.dirname(__file__), "scrolldown.js")

with gr.Blocks(title="AI Chat bot") as demo:
    demo.queue()
    inject_gr_html(demo)
    
    with gr.Row():
        # Left sidebar
        chat_list, current_chat, char_name_input, system_prompt_input, create_char_btn = build_sidebar_ui()
        
        # Right chat area - pass the shared current_chat state
        chatbot, msg_box, chat_current, character_image, system_prompt_display = build_chat_page(demo, current_chat)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, css=css, js=js_path)

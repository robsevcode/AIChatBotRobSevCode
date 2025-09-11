import gradio as gr
import chat_backend
import re

def italics_to_bold(text):
    """
    Converts Markdown italics (*text* or _text_) to bold (**text**)
    """
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)\*(?!\*)', r'**\1**', text)
    text = re.sub(r'_(.*?)_', r'**\1**', text)
    return text

def build_chat_ui():
    # --- Initial state ---
    last_chat_name = chat_backend.load_last_chat()
    all_chats = chat_backend.list_chats()

    if last_chat_name and last_chat_name in all_chats:
        chat_data = chat_backend.load_chat(last_chat_name)
        initial_chat_history = chat_backend.normalize_history_for_ui(chat_data.get("history", []))
        initial_system_prompt = chat_data.get("system_prompt", "")
        initial_chat_name = last_chat_name
    else:
        initial_chat_history = []
        initial_system_prompt = ""
        initial_chat_name = ""

    current_chat = gr.State(initial_chat_name)

    with gr.Row():
        # --- Left Sidebar ---
        with gr.Column(scale=1):
            chat_list = gr.Dropdown(
                choices=all_chats,
                label="Chats",
                value=initial_chat_name if initial_chat_name in all_chats else None,
                interactive=True
            )
            char_name_input = gr.Textbox(label="Character Name")
            system_prompt_input = gr.Textbox(label="System Prompt / Identity")
            create_char_btn = gr.Button("Create Character")

        # --- Right Column ---
        with gr.Column(scale=3):
            system_prompt_display = gr.Textbox(
                label="System Prompt / Identity",
                value=initial_system_prompt,
                interactive=True,   # editable
                lines=3
            )
            update_prompt_btn = gr.Button("Update System Prompt")

            chatbot = gr.Chatbot(type="messages", height=700, value=initial_chat_history)
            msg_box = gr.Textbox(label="Message")
            send_btn = gr.Button("Send")

    # --- Callbacks ---
    def create_character(name, system_prompt):
        if not name:
            return gr.update(choices=chat_backend.list_chats())
        chat_backend.add_chat(name, system_prompt)
        chat_backend.save_last_chat(name)
        return gr.update(choices=chat_backend.list_chats(), value=name)

    def switch_chat(name):
        if not name:
            return gr.update(value=[]), "", gr.update(value="")

        chat_backend.save_last_chat(name)
        chat_data = chat_backend.load_chat(name)
        history = chat_backend.normalize_history_for_ui(chat_data.get("history", []))
        system_prompt = chat_data.get("system_prompt", "")
        return gr.update(value=history), name, gr.update(value=system_prompt)

    def update_system_prompt(new_prompt, active_chat):
        chat_name = active_chat if isinstance(active_chat, str) else getattr(active_chat, "value", "")
        if not chat_name:
            return gr.update(value="⚠️ No active chat selected")

        chat_data = chat_backend.load_chat(chat_name)
        chat_data["system_prompt"] = new_prompt
        chat_backend.save_chat(chat_name, chat_data)
        return gr.update(value=new_prompt)

    def send_message(message, chatbot_history, active_chat):
        current_chat_name = active_chat.value if isinstance(active_chat, gr.State) else active_chat
        if not current_chat_name:
            return chatbot_history, "⚠️ Select a chat first"

        chat_data = chat_backend.load_chat(current_chat_name)
        if chat_data is None:
            return chatbot_history, "⚠️ Chat data missing"

        backend_gen_fn = chat_backend.make_chat_fn(
            chat_data.get("system_prompt", ""),
            chat_data.get("history", [])
        )
        gen = backend_gen_fn(message, chat_data["history"])

        for partial_history in gen:
            # Save after each update to persist chat data
            chat_backend.save_chat(current_chat_name, chat_data)
            yield partial_history, ""

    # --- Wiring ---
    create_char_btn.click(create_character, [char_name_input, system_prompt_input], [chat_list])
    chat_list.change(switch_chat, [chat_list], [chatbot, current_chat, system_prompt_display])
    update_prompt_btn.click(update_system_prompt, [system_prompt_display, current_chat], [system_prompt_display])
    send_btn.click(send_message, [msg_box, chatbot, current_chat], [chatbot, msg_box])
    msg_box.submit(send_message, [msg_box, chatbot, current_chat], [chatbot, msg_box])

    return (
        chat_list, chatbot, msg_box, send_btn, current_chat,
        char_name_input, system_prompt_input, create_char_btn, system_prompt_display
    )

import requests
import gradio as gr
import json

def chat_with_ollama(message, system_prompt):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "gemma3:4b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
    }
    response = requests.post(url, json=payload, stream=True)
    bot_reply = ""
    for line in response.iter_lines():
        if line:
            data = line.decode("utf-8")
            if '"message":' in data:
                try:
                    obj = json.loads(data)
                    bot_reply += obj["message"]["content"]
                except:
                    pass
    return bot_reply

def make_chat_fn(system_prompt):
    def fn(message, history):
        if history is None:
            history = []
        bot_reply = chat_with_ollama(message, system_prompt)
        # Convert to Gradio 4.x expected format: list of dicts
        new_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": bot_reply}
        ]
        return new_history
    return fn

with gr.Blocks() as demo:
    with gr.Column() as pre_chat_ui:
        gr.Markdown("### Enter Character Info")
        name_input = gr.Textbox(label="Character Name", value="Pickle Bob")
        system_prompt_input = gr.Textbox(
            label="System Prompt",
            value="You are Pickle Bob, a funny pickle with a big mustache and bad sense of humor."
        )
        start_btn = gr.Button("Start Chat")

    with gr.Column(visible=False) as chat_container:
        chat_interface = gr.ChatInterface(
            fn=make_chat_fn(system_prompt_input.value),
            type="messages",
            autofocus=True
        )

    def start_chat(name, system_prompt):
        chat_interface.fn = make_chat_fn(system_prompt)
        return gr.update(visible=False), gr.update(visible=True)

    start_btn.click(
        start_chat,
        inputs=[name_input, system_prompt_input],
        outputs=[pre_chat_ui, chat_container]
    )

if __name__ == "__main__":
    demo.launch()

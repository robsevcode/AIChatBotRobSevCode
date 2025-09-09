import requests
import gradio as gr
import json

firstTime = True

# Load character from file
def load_character(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
# Load character
character = load_character("character.json")

def chat_with_ollama(message, history):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "gemma3:4b",   # change to your model
        "messages": [
            {"role": "system", "content": character["system_prompt"]},
            {"role": "user", "content": message}]
    }

    response = requests.post(url, json=payload, stream=True)

    bot_reply = ""
    for line in response.iter_lines():
        if line:
            data = line.decode("utf-8")
            if '"message":' in data:
                # Get assistant output piece by piece
                import json
                try:
                    obj = json.loads(data)
                    bot_reply += obj["message"]["content"]
                except:
                    pass

    return bot_reply

demo = gr.ChatInterface(chat_with_ollama, type="messages", autofocus=True)

if __name__ == "__main__":
    demo.launch()

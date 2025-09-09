# chat_backend.py
import requests

# Global storage for all chats
chats = {}

def add_chat(name, system_prompt=""):
    chats[name] = {"system_prompt": system_prompt, "history": []}

def make_chat_fn(system_prompt, history):
    def chat_with_ollama(message, history_):
        url = "http://localhost:11434/api/chat"
        payload = {"model": "gemma3:4b", "messages": []}

        # Add system message
        if system_prompt:
            payload["messages"].append({"role": "system", "content": system_prompt})

        # Add history
        for user, bot in history_:
            payload["messages"].append({"role": "user", "content": user})
            payload["messages"].append({"role": "assistant", "content": bot})

        # Add new user message
        payload["messages"].append({"role": "user", "content": message})

        response = requests.post(url, json=payload, stream=True)

        bot_reply = ""
        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if '"message":' in data:
                    import json
                    try:
                        obj = json.loads(data)
                        bot_reply += obj["message"]["content"]
                    except:
                        pass

        history_.append((message, bot_reply))
        return history_
    return chat_with_ollama

import requests
import json

def chat_with_ollama(system_prompt, history, history_input):
    print("***")
    print("Calling Ollama")
    print("***")
    url = "http://localhost:11434/api/chat"
    payload = {"model": "hf.co/ArliAI/Mistral-Nemo-12B-ArliAI-RPMax-v1.1-GGUF:Q4_K_M", "messages": []}

    # Add system prompt
    if system_prompt:
        payload["messages"].append({"role": "system", "content": system_prompt})

    # Add history
    for message_history in history_input:
        if "role" in message_history and "content" in message_history:
            payload["messages"].append(message_history)

    # Add latest user message
    print("Sending message to Ollama and waiting for response")
    try:
        response = requests.post(url, json=payload, stream=True)
    except Exception as ex:
        print("Oh no ",ex)

    bot_reply = ""
    for line in response.iter_lines():
        if line:
            data = line.decode("utf-8")
            if '"message":' in data:
                try:
                    obj = json.loads(data)
                    bot_reply += obj["message"]["content"]

                    # Yield partial update
                    temp_history = history + [{"role": "assistant", "content": bot_reply}]
                    yield temp_history
                except:
                    pass

    print("Full message has been sent")
    
    # Save final result
    history_input.append({"role": "assistant", "content": bot_reply})

    # Persist to file
    chat_data = {"system_prompt": system_prompt, "history": history_input}
    # Need the active chat name from UI to save properly
    # UI should pass the active chat name when calling save_chat()
    yield history

def generate_image_prompt(prompt):
    print("***")
    print("Generating prompt with Ollama")
    print("***")
    url = "http://localhost:11434/api/chat"
    payload = {"model": "gemma3:4b", "messages": [], "stream": False}

    system_prompt= "You are prompter, my AI assistant that helps me creates prompts for stable diffusion, removing information not needed and "
    "focusing more on the details that can create an image, representing both obvious details like hair color, body type, race and also adapting "
    "the personality into the image, like clothes, face expressions and accesories. Focus on the photography angles, styles, composition, trying to "
    "prompt a photo like use in social media, portrait mode."

    payload["messages"].append({"role": "system", "content": system_prompt})
    prompt = "Generate a prompt for a stable diffusion realistic image, that defines race/etnicity, " \
    "age, hair color and style, skin tone, body type/build, eye color and any other distinctive features. " \
    "Photo angle should be a close portrait, just like an avatar for a social media. Consider the following description:" + prompt + "DO NOT RESPOND ANYTHING, OTHER THAN THE PROMPT."
    payload["messages"].append({"role": "user", "content": prompt})

    # Add latest user message
    print("Sending message to Ollama and waiting for response")
    try:
        response = requests.post(url, json=payload, stream=False)
    except Exception as ex:
        print("Oh no ",ex)

    extra_prompts = ",masterpiece, (photorealistic:1.4), best quality, soft lighting, photograph, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9), slightly blurred, (morning light:0.5), (ambient occlusion:0.6), (realistic shadows), portrait photography, (social media style:0.8), (vertical composition), 85mm lens, f/2.8, ISO 400 <lora:DarkLighting:0.1> <lora:InstantPhotoX3:0.15> <lora:add_detail:1.1>"
    reponse_prompt = response.json()["message"]["content"] + extra_prompts
    print("Full message has been sent")
    return reponse_prompt

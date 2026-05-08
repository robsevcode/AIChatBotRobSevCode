import requests
import json
import logging

logging.basicConfig(level=logging.INFO) # DEBUG, INFO, WARNING, ERROR, CRITICAL

def chat_with_ollama(system_prompt, history, history_input):
    logging.debug("Calling Ollama")
    url = "http://localhost:11434/api/chat"
    payload = {"model": "gemma3:4b", "messages": []}

    # Add system prompt
    if system_prompt:
        payload["messages"].append({"role": "system", "content": system_prompt})

    # Add history
    for message_history in history_input:
        if "role" in message_history and "content" in message_history:
            payload["messages"].append(message_history)

    if payload["messages"] and payload["messages"][-1]["role"] == "assistant":
        logging.debug("Last message was: %s", payload["messages"][-1]["content"])
        payload["messages"].pop()
        if payload["messages"]:
            logging.debug("New last message: %s", payload["messages"][-1]["content"])

    logging.debug("Sending message to Ollama and waiting for response")
    bot_reply = ""
    response = None
    try:
        logging.debug(payload)
        response = requests.post(url, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            line = raw_line.decode("utf-8").strip() if isinstance(raw_line, bytes) else raw_line.strip()
            if line == "[DONE]":
                break
            if line.startswith("data: "):
                line = line[len("data: "):]

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                logging.debug("Skipping non-JSON line from Ollama: %s", line)
                continue

            if not isinstance(obj, dict):
                continue

            message = obj.get("message") if isinstance(obj.get("message"), dict) else None
            content_piece = ""
            if isinstance(message, dict):
                content_piece = message.get("content", "")
            elif isinstance(obj.get("content"), str):
                content_piece = obj.get("content", "")

            if content_piece:
                bot_reply += content_piece
                partial_history = history_input + [{"role": "assistant", "content": bot_reply}]
                yield partial_history

        if not bot_reply and response is not None:
            try:
                text = response.text.strip()
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line == "[DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[len("data: "):]
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        message = obj.get("message") if isinstance(obj.get("message"), dict) else None
                        if isinstance(message, dict):
                            bot_reply = message.get("content", bot_reply)
                        elif isinstance(obj.get("content"), str):
                            bot_reply = obj.get("content", bot_reply)
            except Exception:
                pass
    except requests.RequestException as ex:
        if response is not None:
            logging.critical("Ollama request failed [%s]: %s", response.status_code, response.text)
        logging.critical("Ollama API call failed", exc_info=ex)
        bot_reply = ""

    logging.debug("Full message has been sent")

    history_input.append({"role": "assistant", "content": bot_reply})
    yield history_input

def generate_image_prompt(prompt):
    logging.debug("Generating prompt for avatar with Ollama")
    url = "http://localhost:11434/api/chat"
    payload = {"model": "hf.co/mradermacher/IceLemonTeaRP-32k-7b-GGUF:Q8_0", "messages": [], "stream": False}

    system_prompt= "You are prompter, my AI assistant that helps me creates prompts for stable diffusion, removing information not needed and "
    "focusing more on the details that can create an image, representing both obvious details like hair color, body type, race and also adapting "
    "the personality into the image, like clothes, face expressions and accesories. Focus on the photography angles, styles, composition, trying to "
    "prompt a photo like use in social media, portrait mode."

    payload["messages"].append({"role": "system", "content": system_prompt})
    prompt = "Generate a prompt for a stable diffusion realistic image, that defines race/etnicity, " \
    "age, hair color and style, skin tone, body type/build, eye color and any other distinctive features. " \
    "Photo angle should be a close portrait, just like an avatar for a social media. If the name of prompt is a real person or a person from the fictional world, KEEP THE NAME. Consider the following description:" + prompt + "DO NOT RESPOND ANYTHING, OTHER THAN THE PROMPT."
    payload["messages"].append({"role": "user", "content": prompt})

    # Add latest user message
    logging.debug("Sending message to Ollama and waiting for response")
    response = None
    try:
        response = requests.post(url, json=payload, stream=False)
    except Exception as ex:
        logging.critical("Oh no ",ex)

    extra_prompts = ",masterpiece, (photorealistic:1.4), best quality, soft lighting, photograph, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9), slightly blurred, (morning light:0.5), (ambient occlusion:0.6), (realistic shadows), portrait photography, (social media style:0.8), (vertical composition), 85mm lens, f/2.8, ISO 400 <lora:DarkLighting:0.1> <lora:InstantPhotoX3:0.15> <lora:add_detail:1.1>"
    reponse_prompt = response.json()["message"]["content"] + extra_prompts
    logging.debug("Full message has been sent")
    return reponse_prompt

def generate_image_request_prompt(user_prompt, character_info):
    logging.debug("Generating prompt for requested image with Ollama")
    url = "http://localhost:11434/api/chat"
    payload = {"model": "hf.co/TheDrummer/Tiger-Gemma-9B-v2-GGUF:Q2_K", "messages": [], "stream": False}

    system_prompt= "You are prompter, my AI assistant that helps me creates prompts for stable diffusion, removing information not needed and "
    "focusing more on the details that can create an image, representing both obvious details like hair color, body type, race and also adapting "
    "the personality into the image, like clothes, face expressions and accesories. Focus on the photography angles, styles, composition, trying to "
    "prompt a photo like use in social media, portrait mode."

    payload["messages"].append({"role": "system", "content": system_prompt})
    prompt = (
        "Generate a prompt for a stable diffusion realistic image, that defines race/etnicity, " 
        "age, hair color and style, skin tone, body type/build, eye color and any other distinctive features. " 
        "Photo angle should be aadapted, depending on the user request. Consider the original character description:" 
        + character_info
        + "Then, consider the request the user is making, to generate an accurate image: " 
        + user_prompt
        + "DO NOT RESPOND ANYTHING, OTHER THAN THE PROMPT."
    )
    payload["messages"].append({"role": "user", "content": prompt})

    # Add latest user message
    logging.debug("Sending message to Ollama and waiting for response")
    try:
        response = requests.post(url, json=payload, stream=False)
    except Exception as ex:
        logging.critical("Oh no ",ex)

    extra_prompts = ",masterpiece, (photorealistic:1.4), best quality, soft lighting, photograph, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9), slightly blurred, (morning light:0.5), (ambient occlusion:0.6), (realistic shadows), 85mm lens, f/2.8, ISO 400 <lora:DarkLighting:0.1> <lora:InstantPhotoX3:0.15> <lora:add_detail:1.1>"
    reponse_prompt = response.json()["message"]["content"] + extra_prompts
    logging.debug("Full message has been sent")
    return reponse_prompt
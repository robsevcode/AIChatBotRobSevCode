import requests
import json
import logging
from pydantic import BaseModel
from classes import *

logging.basicConfig(level=logging.INFO) # DEBUG, INFO, WARNING, ERROR, CRITICAL
logger = logging.getLogger('OLLAMA') 

def chat_with_ollama(metadata: Metadata, chat_history: list[Message], user_message: Message):
    logger.debug("DEF: chat_with_ollama")
    url = "http://localhost:11434/api/chat"
    payload = Payload(model="hf.co/ArliAI/Mistral-Nemo-12B-ArliAI-RPMax-v1.1-GGUF:Q4_K_M")

    system_prompt = metadata.system_prompt
    # Add system prompt
    if system_prompt:
        payload.messages.append(Message(role="system", content=system_prompt))

    # Add history
    for message in chat_history:
        payload.messages.append(message)
        
    if payload.messages[-1].role == "assistant":
        logger.debug("Last message was: ", payload.messages[-1].content)
        payload.messages.pop()
        logger.debug("New last message: ", payload.messages[-1].content)

    # Add latest user message
    logger.debug("Sending message to Ollama and waiting for response")
    logger.debug(payload.model_dump_json())
    try:
        response = requests.post(url, json=payload.model_dump(), stream=True)
        logger.debug("Ollama response")
        logger.debug(response)
    except Exception as ex:
        logger.critical("Error when sending message to Ollama",ex)

    bot_reply = ""
    assistant_msg = Message(role="assistant", content="")  # one object for streaming
    for line in response.iter_lines():
        if line:
            data = line.decode("utf-8")
            if '"message":' in data:
                try:
                    obj = json.loads(data)
                    bot_reply += obj["message"]["content"]
                    assistant_msg.content = bot_reply  # update the content

                    # Yield partial update
                    temp_history = chat_history + [assistant_msg]
                    #logger.debug(temp_history)
                    yield [msg.model_dump() for msg in temp_history]
                except:
                    pass

    logger.debug("Full message has been sent")
    
    # Save final result
    chat_history.append(Message(role="assistant", content=bot_reply))

    # Persist to file
    # Need the active chat name from UI to save properly
    # UI should pass the active chat name when calling save_chat()
    logger.debug(chat_history)
    yield [msg.model_dump() for msg in chat_history]

def generate_image_prompt(prompt: str):
    logger.debug("Generating prompt for avatar with Ollama")
    url = "http://localhost:11434/api/chat"
    payload = Payload(model="hf.co/mradermacher/IceLemonTeaRP-32k-7b-GGUF:Q8_0", stream=False)

    system_prompt= "You are prompter, my AI assistant that helps me creates prompts for stable diffusion, removing information not needed and "
    "focusing more on the details that can create an image, representing both obvious details like hair color, body type, race and also adapting "
    "the personality into the image, like clothes, face expressions and accesories. Focus on the photography angles, styles, composition, trying to "
    "prompt a photo like use in social media, portrait mode."

    payload.messages.append(Message(role="system", content=system_prompt))
    prompt = "Generate a prompt for a stable diffusion realistic image, that defines race/etnicity, " \
    "age, hair color and style, skin tone, body type/build, eye color and any other distinctive features. " \
    "Photo angle should be a close portrait, just like an avatar for a social media. If the name of prompt is a real person or a person from the fictional world, KEEP THE NAME. Consider the following description:" + prompt + "DO NOT RESPOND ANYTHING, OTHER THAN THE PROMPT."
    payload.messages.append(Message(role="user", content=prompt))

    # Add latest user message
    logger.debug("Sending message to Ollama and waiting for response")
    response = None
    try:
        response = requests.post(url, json=payload.model_dump_json(), stream=False)
    except Exception as ex:
        logger.critical("Oh no ",ex)

    extra_prompts = ",masterpiece, (photorealistic:1.4), best quality, soft lighting, photograph, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9), slightly blurred, (morning light:0.5), (ambient occlusion:0.6), (realistic shadows), portrait photography, (social media style:0.8), (vertical composition), 85mm lens, f/2.8, ISO 400 <lora:DarkLighting:0.1> <lora:InstantPhotoX3:0.15> <lora:add_detail:1.1>"
    reponse_prompt = response.json()["message"]["content"] + extra_prompts
    logger.debug("Full message has been sent")
    return reponse_prompt

def generate_image_request_prompt(user_prompt, character_info):
    logger.debug("Generating prompt for requested image with Ollama")
    url = "http://localhost:11434/api/chat"
    payload = Payload(model="hf.co/TheDrummer/Tiger-Gemma-9B-v2-GGUF:Q2_K", stream=False)

    system_prompt= "You are prompter, my AI assistant that helps me creates prompts for stable diffusion, removing information not needed and "
    "focusing more on the details that can create an image, representing both obvious details like hair color, body type, race and also adapting "
    "the personality into the image, like clothes, face expressions and accesories. Focus on the photography angles, styles, composition, trying to "
    "prompt a photo like use in social media, portrait mode."

    payload.messages.append(Message(role="system", content=system_prompt))
    prompt = (
        "Generate a prompt for a stable diffusion realistic image, that defines race/etnicity, " 
        "age, hair color and style, skin tone, body type/build, eye color and any other distinctive features. " 
        "Photo angle should be aadapted, depending on the user request. Consider the original character description:" 
        + character_info
        + "Then, consider the request the user is making, to generate an accurate image: " 
        + user_prompt
        + "DO NOT RESPOND ANYTHING, OTHER THAN THE PROMPT."
    )
    
    payload.messages.append(Message(role="role", content=prompt))

    # Add latest user message
    logger.debug("Sending message to Ollama and waiting for response")
    try:
        response = requests.post(url, json=payload, stream=False)
    except Exception as ex:
        logger.critical("Oh no ",ex)

    extra_prompts = ",masterpiece, (photorealistic:1.4), best quality, soft lighting, photograph, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9), slightly blurred, (morning light:0.5), (ambient occlusion:0.6), (realistic shadows), 85mm lens, f/2.8, ISO 400 <lora:DarkLighting:0.1> <lora:InstantPhotoX3:0.15> <lora:add_detail:1.1>"
    reponse_prompt = response.json()["message"]["content"] + extra_prompts
    logger.debug("Full message has been sent")
    return reponse_prompt
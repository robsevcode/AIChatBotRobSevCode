import base64
import os
import json
import requests
import logging
from PIL import Image, PngImagePlugin
from io import BytesIO
from datetime import datetime

logging.basicConfig(level=logging.INFO) # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ------------------------
# Stable Diffusion backend
# ------------------------
A1111_URL = "http://127.0.0.1:7861"   # change if different host/port
ASSETS_DIR = "assets"

def generate_avatar_a1111(name, system_prompt, *,
                          width=512, height=512,
                          steps=20, cfg_scale=7.0, sampler_name="DPM++ 2M",
                          seed=-1, negative_prompt=None):
    logging.debug("Generating image for: " + name)
    # 1) Build prompt
    prompt = (
        f"Portrait of {name}, {system_prompt}. "
        "photograph of a beautiful, best quality, soft lighting, masterpiece, (photorealistic:1.4), Close-up, upper body, high detail, beautiful, cinematic lighting, sharp eyes, clean background, "
        "studio portrait, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9)"
    )

    if negative_prompt is None:
        negative_prompt = "BadDream, UnrealisticDream, watermark, signature, logo, text, bad hands, unnatural hands, disfigured hands, extra libs, extra hands, extra legs, unrealistic"

    # 2) Build payload for /sdapi/v1/txt2img
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "sampler_name": sampler_name,
        "scheduler": "Karras",
        #"refiner_checkpoint": "grandmix_v20.safetensors [a0a3f1bf9d]",
        #"refiner_switch_at": 0.75,
        "alwayson_scripts": {
            "Adetailer": {
                "args": [
                    {
                        "ad_model": "face_yolov8s.pt"
                    },
                    {
                        "ad_model": "hand_yolov8n.pt"
                    }
                ]
            }
        }
    }

    filename = "Avatar.png"
    img, metadata = generate_image(payload, -1)
    return save_image(img, filename, metadata, name)

def generate_requested_image(name, request_prompt):
    logging.debug("Generating requested image for: " + name)
    # 1) Build prompt
    prompt = (
        f"{request_prompt}. "
        "best quality, soft lighting, masterpiece, (photorealistic:1.4), high detail, beautiful, cinematic lighting, sharp eyes, clean background, "
        "RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9)"
    )

    negative_prompt = "BadDream, UnrealisticDream, watermark, signature, logo, text, bad hands, unnatural hands, disfigured hands, extra libs, extra hands, extra legs, unrealistic"

    # 2) Build payload for /sdapi/v1/txt2img
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": 25,
        "cfg_scale": 7,
        "width": 512,
        "height": 512,
        "sampler_name": "DPM++ 2M",
        "scheduler": "Karras",
        #"refiner_checkpoint": "grandmix_v20.safetensors [a0a3f1bf9d]",
        #"refiner_switch_at": 0.75,
        "alwayson_scripts": {
            "Adetailer": {
                "args": [
                    {
                        "ad_model": "face_yolov8s.pt"
                    },
                    {
                        "ad_model": "hand_yolov8n.pt"
                    }
                ]
            }
        }
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"

    img, metadata = generate_image(payload, -1)
    return save_image(img, filename, metadata, name)

def save_image(img, filename, metadata, name):
    try:
        base_path = os.path.join("chat_data", name)
        avatar_folder = os.path.join(base_path, "assets")
        os.makedirs(avatar_folder, exist_ok=True)
        path = os.path.join(avatar_folder, filename)
        img.save(path, pnginfo=metadata)
    except Exception as ex:
        logging.critical("Image could not be saved: ", ex)
        raise ex
    
    return path


def generate_image(payload, seed):
    if seed is not None:
        payload["seed"] = seed

    url = f"{A1111_URL}/sdapi/v1/txt2img"
    result = ""

    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        result = resp.json()
    except Exception as ex:
        logging.critical("Could not generate image: ", ex)
        raise ex

    # result["images"] is a list of base64 PNGs
    if not result.get("images"):
        logging.critical("No image returned from A1111")
        raise RuntimeError("No images returned from A1111")

    try:
        img_b64 = result["images"][0]  # take first
        image_bytes = base64.b64decode(img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64)
        img = Image.open(BytesIO(image_bytes))

        info_json = json.dumps(result.get("info", {}))

        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("parameters", info_json)
        
    except Exception as ex:
        logging.critical("Image could not be generated: " + ex)

    return img, metadata
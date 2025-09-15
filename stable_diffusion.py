import base64
import os
import requests
from PIL import Image, PngImagePlugin
from io import BytesIO

# ------------------------
# Stable Diffusion backend
# ------------------------
A1111_URL = "http://127.0.0.1:7860"   # change if different host/port
ASSETS_DIR = "assets"

def generate_avatar_a1111(name, system_prompt, *,
                          width=512, height=512,
                          steps=20, cfg_scale=7.0, sampler_name="DPM++ 2M",
                          seed=-1, negative_prompt=None):
    print("Generating image for: ", name)
    # 1) Build prompt
    prompt = (
        f"Portrait of {name}, {system_prompt}. "
        "photograph of a beautiful, best quality, soft lighting, masterpiece, (photorealistic:1.4), Close-up, upper body, high detail, beautiful, cinematic lighting, sharp eyes, clean background, "
        "studio portrait, highly detailed anime style, RAW photo, 8k uhd, film grain, (low quality amateur:1.3), (fisheye lens:0.9) (bokeh:0.9)"
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
        "refiner_checkpoint": "grandmix_v20.safetensors [a0a3f1bf9d]",
        "refiner_switch_at": 0.75,
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
    if seed is not None:
        payload["seed"] = seed

    url = f"{A1111_URL}/sdapi/v1/txt2img"

    resp = requests.post(url, json=payload, timeout=300)
    resp.raise_for_status()
    result = resp.json()

    # result["images"] is a list of base64 PNGs
    if not result.get("images"):
        raise RuntimeError("No images returned from A1111")

    img_b64 = result["images"][0]  # take first
    image_bytes = base64.b64decode(img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64)

    # Save file
    os.makedirs(ASSETS_DIR, exist_ok=True)
    #safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    filename = f"{name}.png"
    path = os.path.join(ASSETS_DIR, filename)
    info_json = result["info"]
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("parameters", info_json)
    img = Image.open(BytesIO(image_bytes))
    img.save(path, pnginfo=metadata)
    # with open(path, "wb") as f:
    #     f.write(image_bytes)

    return path

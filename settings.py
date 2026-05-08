"""
Settings module for the AI Chatbot application.
Handles user preferences for image style and response type.
"""

def apply_settings(image_style, response_type):
    """
    Applies the selected settings.
    For now, this is a placeholder that prints the selections.
    In the future, this could update global configurations,
    save to a file, or modify behavior in ollama.py and stable_diffusion.py.
    
    Args:
        image_style (str): "Realistic" or "Anime"
        response_type (str): "Slow", "Average", or "Fast"
    """
    print(f"Settings applied: Image Style = {image_style}, Response Type = {response_type}")
    # TODO: Integrate with image generation (stable_diffusion.py) and chat response (ollama.py)
    # For example:
    # - Set image style in stable_diffusion.generate_avatar_a1111 or ollama.generate_image_prompt
    # - Adjust response speed in ollama.chat_with_ollama (e.g., model parameters or temperature)
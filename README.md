# AIChatBotRobSevCode
This repository is just for testing myself, using AI to increase the velocity and push the limits of GeneAI to prove it can be used in my advantage

<img width="499" height="410" alt="Screenshot 2025-09-11 193414" src="https://github.com/user-attachments/assets/0035a406-90c0-4f6e-be86-2b44a6481b14" />


# Technologies used
* Python
  * Version: 3.11.4
* Gradio framework
  * Version: 4.44.1
* Ollama with models:
  * gemma3:4b
  * hf.co/ArliAI/Mistral-Nemo-12B-ArliAI-RPMax-v1.1-GGUF:Q4_K_M
* Stable Diffusion with Automatic1111. Some requirements are needed
  * Checkpoints:
    * absolutereality_v181.safetensors [463d6a9fe8]
    * grandmix_v20.safetensors [a0a3f1bf9d]
  * Extensions:
    * Adetailer
  * Loras:
    * BadDream
    * UnrealisticDream
    * DarkLighting
    * InstantPhotoX3
    * add_detail

# Latest features
* Ability to create a custom character with name and System Prompt
* Ability to delete a character but keep any data as archive
* Ability to switch between characters
* Ability to edit the system prompt of a character
* Ability to show text as a social media, with avatars
* Ability to create custom avatars using stable diffusion

# Next features
Expected to add the following features in the future:
* Generate images in the chat while chatting, automatically
* Accepts attachment and react to the media
* Ask for character to generate media
* Create character appearance and scenario with a single photo
* Create an embedding to use, with a photo, that keeps consistent with the character
* Databse for faster export and modification

# How to run
* Make sure you have Ollama running
* Make sure you have the specified Python version installed
* Make sure you have the specified Gradio version installed
* Move to your location where the repo is download
* Run > python main.py

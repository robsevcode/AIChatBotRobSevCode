# AIChatBotRobSevCode
This repository started as a personal project, for testing myself, using AI to increase the velocity and push the limits of GeneAI to prove it can be used in my advantage. Currently, it started to take form and more feature and ideas are starting to make this project more ambisous. 

You can use this chatbot for your own purposes. I'm not responsible for any wrong use of this repository and I don't allow using this for profit purposes.

<img width="499" height="410" alt="Screenshot 2025-09-11 193414" src="https://github.com/user-attachments/assets/0035a406-90c0-4f6e-be86-2b44a6481b14" />


# Technologies used
* Python
  * Version: 3.11.4
* Gradio framework
  * Version: 4.44.1
* Ollama with models (You can change these models in the ollama.py file):
  * hf.co/mradermacher/IceLemonTeaRP-32k-7b-GGUF:Q8_0 (For image prompt suggestion)
  * hf.co/ArliAI/Mistral-Nemo-12B-ArliAI-RPMax-v1.1-GGUF:Q4_K_M (For chat role play)
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

# How to run
* Download the latest Release: https://github.com/robsevcode/AIChatBotRobSevCode/releases/tag/v1.2.0
* Make sure you have Ollama running
* Make sure you have Stable Diffusion running
* Make sure you have the specified Python version installed
* Make sure you have the specified Gradio version installed
* Move to your location where the repo is downloaded
* Run > gradio main.py

# Latest features
* Create multiple custom characters with name and personality
* Automatically create custom avatars using stable diffusion based on name and personality
* Chat with any character, showing text as a social media, with avatars included
* Save chat history in a easy to import/export json format
* Request images based on context to the characters
* Switch between characters without losing any chat
* Edit the personality of a character, even when chat is already started
* Delete a character but keep any data as archive, like assets and chat history

# Next features
To see the new feature and help with this project, you can create an issue using the templates or see the available issues with some future ideas.


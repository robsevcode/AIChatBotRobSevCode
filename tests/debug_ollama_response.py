import requests
import json

url = "http://localhost:11434/api/chat"
payload = {
    "model": "hf.co/ArliAI/Mistral-Nemo-12B-ArliAI-RPMax-v1.1-GGUF:Q4_K_M",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, can you say something nice?"}
    ]
}
print('payload=', json.dumps(payload, indent=2))
response = requests.post(url, json=payload, stream=True, timeout=10)
print('status', response.status_code)
for i, line in enumerate(response.iter_lines(decode_unicode=True)):
    print('line', i, repr(line))
    if i > 20:
        break
print('done')

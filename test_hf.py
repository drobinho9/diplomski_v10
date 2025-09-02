import requests

token = "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"

url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

resp = requests.get(url, headers=headers)

print("Status:", resp.status_code)
print("Text:", resp.text)

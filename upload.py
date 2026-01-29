# Save this as upload.py
import requests

with open("test.txt", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f}
    )

print(response.json())
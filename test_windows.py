import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Create a test file
with open("test.txt", "w") as f:
    f.write("""
Machine Learning Basics

Machine learning enables computers to learn from data without explicit programming.
It includes supervised learning, unsupervised learning, and reinforcement learning.

Applications include image recognition, natural language processing, and recommendation systems.
""")

print("1. Uploading document...")
# 2. Upload
with open("test.txt", "rb") as f:
    response = requests.post(f"{BASE_URL}/upload", files={"file": f})

job_data = response.json()
job_id = job_data["job_id"]
print(f"   Job ID: {job_id}")

# 3. processing
print("\n2. Waiting for processing...")
while True:
    response = requests.get(f"{BASE_URL}/job/{job_id}")
    status = response.json()
    
    if status["status"] == "completed":
        print(f"    {status['progress']}")
        break
    elif status["status"] == "failed":
        print(f"    Error: {status.get('error')}")
        exit(1)
    
    print(f"    {status.get('progress', 'Processing...')}")
    time.sleep(1)

# 4. Query Loop
print("\n--- Chat Session Started (Type 'exit' to stop) ---")

while True:
    user_question = input("\nReady! Ask a question: ").strip()
    
    
    if user_question.lower() in ["exit", "quit"]:
        print("Exiting chat...")
        break
    
    
    if not user_question:
        continue

    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={"question": user_question}
        )
        
        result = response.json()
        
        print(f"\n Answer:")
        print(result["answer"])
        print(f" Latency: {result['metrics']['total_latency_ms']}ms")
        
    except Exception as e:
        print(f" Connection Error: {e}")
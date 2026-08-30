import requests
from app.config import MONDAY_API_TOKEN

url = "https://api.monday.com/v2"

headers = {
    "Authorization": MONDAY_API_TOKEN,
    "Content-Type": "application/json",
}

query = """
query {
    me {
        id
        name
        email
    }
}
"""

print("Testing Monday API connection...")
print("Sending request...")

try:
    response = requests.post(
        url,
        json={"query": query},
        headers=headers,
        timeout=(10, 20),
    )

    print(f"HTTP Status: {response.status_code}")
    print("Response:")
    print(response.text)

except requests.exceptions.Timeout:
    print("❌ Request timed out.")

except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")
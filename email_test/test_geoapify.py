import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEOAPIFY_API_KEY")

location = "Khobar"

url = "https://api.geoapify.com/v1/geocode/search"

params = {
    "text": location,
    "format": "json",
    "apiKey": API_KEY
}

try:
    response = requests.get(url, params=params, timeout=20)

    print("Status Code:", response.status_code)

    if response.status_code == 200:
        print(response.json())
    else:
        print(response.text)

except requests.exceptions.Timeout:
    print("Request timed out. Geoapify did not respond in time.")

except requests.exceptions.RequestException as e:
    print("Connection error:", e)
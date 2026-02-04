
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("No API Key")
    exit(1)

client = genai.Client(api_key=api_key)
for model in client.models.list(config={"page_size": 100}):
    print(model.name)

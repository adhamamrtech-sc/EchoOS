from dotenv import load_dotenv
from google import genai
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("API KEY:", bool(api_key))

client = genai.Client(api_key=api_key)

print("Client created successfully")

models = client.models.list()

print("Models object:", models)

for model in models:
    print("MODEL:", model)
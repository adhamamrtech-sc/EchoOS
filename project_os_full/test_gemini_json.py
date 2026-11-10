import json
import os

from dotenv import load_dotenv
from google import genai

def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is missing.")
        return

    client = genai.Client(api_key=api_key)
    prompt = """Interpret this command: open firefox.

Return only this JSON object:
{"status":"accepted","action":"open_app","target":"firefox","params":{},"confidence":0.95}
"""

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=prompt,
            config={"response_mime_type": "application/json", "max_output_tokens": 200},
        )
        result = json.loads(response.text)
        print("Parsed JSON:")
        print(result)
    except json.JSONDecodeError:
        print("Gemini returned a response that is not valid JSON.")
    except Exception as error:
        print(f"Gemini request failed: {type(error).__name__}: {error}")
    finally:
        client.close()


if __name__ == "__main__":
    main()

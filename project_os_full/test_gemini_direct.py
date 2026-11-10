import os

from dotenv import load_dotenv
from google import genai


def main() -> None:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Error: GEMINI_API_KEY is missing.")
        return

    print("API key loaded:", bool(api_key))
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents="Reply with exactly: EchoOS test successful",
        )
        print("Response:")
        print(response.text)
    finally:
        client.close()


if __name__ == "__main__":
    main()

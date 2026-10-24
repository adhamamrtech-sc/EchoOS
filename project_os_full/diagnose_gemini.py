
import os
from time import perf_counter

from dotenv import load_dotenv
from google import genai
from google.genai import types


def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model = "gemini-3.8-flash"

    if not api_key:
        print("GEMINI_API_KEY is missing.")
        return

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30_000,
            retry_options=types.HttpRetryOptions(
                attempts=1
            ),
        ),
    )

    try:
        print(f"Model: {model}")
        print("Sending one request without retries...")

        started = perf_counter()

        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly OK",
            config=types.GenerateContentConfig(
                max_output_tokens=8,
                thinking_config=types.ThinkingConfig(
                    thinking_level="low"
                ),
            ),
        )

        print(f"Elapsed: {perf_counter() - started:.2f}s")
        print(f"Response: {response.text!r}")

    except Exception as error:
        print(f"Error: {type(error).__name__}: {error}")
        print(f"Elapsed: {perf_counter() - started:.2f}s")

    finally:
        client.close()


if __name__ == "__main__":
    main()




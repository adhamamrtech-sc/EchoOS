
import os
from time import perf_counter

from dotenv import load_dotenv
from google import genai
from google.genai import types


def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    if not api_key:
        print("Error: GEMINI_API_KEY is missing.")
        return

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=120_000),
    )

    try:
        print(f"Model: {model}")
        print("Sending a minimal request...")

        started = perf_counter()

        response = client.models.generate_content(
            model=model,
            contents='Return exactly: {"status":"accepted"}',
            config=types.GenerateContentConfig(
                max_output_tokens=128,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(
                    thinking_level="low"
                ),
            ),
        )

        elapsed = perf_counter() - started

        print(f"Elapsed: {elapsed:.2f} seconds")
        print("Response text:", repr(response.text))
        print("Candidates:", repr(response.candidates))
        print("Prompt feedback:", repr(response.prompt_feedback))

    except Exception as error:
        print(f"Error: {type(error).__name__}: {error}")

    finally:
        client.close()


if __name__ == "__main__":
    main()


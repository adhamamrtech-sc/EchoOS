"""Manual environment diagnostic; not part of the automated test suite."""

import os

from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    print("API key loaded successfully!" if os.getenv("GEMINI_API_KEY") else "API key NOT found!")


if __name__ == "__main__":
    main()

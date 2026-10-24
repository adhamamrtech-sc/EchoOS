
from nlu.gemini_provider import GeminiProvider
from nlu.llm_validator import validate_llm_result


def main():
    provider = GeminiProvider()

    commands = [
    "open my browser",
    ]

    for command in commands:
        print(f"\nCommand: {command}")

        try:
            result = provider.generate(command)

            print("Gemini result:")
            print(result)

            validated = validate_llm_result(result)

            print("Validated result:")
            print(validated)

        except Exception as error:
            print(
                f"Test failed: "
                f"{type(error).__name__}: {error}"
            )


if __name__ == "__main__":
    main()


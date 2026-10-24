class MockLLMProvider:

    def generate(self, input_data):

        # Support simple string input
        if isinstance(input_data, str):
            current_text = input_data.lower()
            context = None

        # Support DecisionEngine dictionary input
        elif isinstance(input_data, dict):
            current_text = input_data.get(
                "current_text",
                "",
            ).lower()

            context = input_data.get("context")

        else:
            return {
                "status": "rejected",
                "reason": "invalid_input",
            }

        # -------------------------------------------------
        # Pending clarification
        # -------------------------------------------------

        if context is not None:

            pending_action = context.get(
                "pending_action"
            )

            if (
                pending_action == "open_app"
                and current_text == "firefox"
            ):
                return {
                    "status": "accepted",
                    "action": "open_app",
                    "target": "firefox",
                    "params": {},
                    "confidence": 0.98,
                }

            if (
                pending_action == "open_app"
                and current_text == "chrome"
            ):
                return {
                    "status": "accepted",
                    "action": "open_app",
                    "target": "chrome",
                    "params": {},
                    "confidence": 0.98,
                }

        # -------------------------------------------------
        # Normal commands
        # -------------------------------------------------

        if "firefox" in current_text:
            return {
                "status": "accepted",
                "action": "open_app",
                "target": "firefox",
                "params": {},
                "confidence": 0.95,
            }

        if "chrome" in current_text:
            return {
                "status": "accepted",
                "action": "open_app",
                "target": "chrome",
                "params": {},
                "confidence": 0.95,
            }

        # -------------------------------------------------
        # Ambiguous browser
        # -------------------------------------------------

        if "browser" in current_text:
            return {
                "status": "needs_clarification",
                "message": (
                    "Which browser do you want to open?"
                ),
            }

        # -------------------------------------------------
        # Unsupported command
        # -------------------------------------------------

        return {
            "status": "rejected",
            "reason": "unsupported_command",
        }
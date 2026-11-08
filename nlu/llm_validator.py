
from .catalog import (
    APPS,
    FOLDERS,
    COMMAND_BY_ACTION,
)


# ============================================================
# ACTIONS
# ============================================================

ALLOWED_ACTIONS = set(COMMAND_BY_ACTION.keys())

DANGEROUS_ACTIONS = {
    action
    for action, command in COMMAND_BY_ACTION.items()
    if command.dangerous
}


# ============================================================
# STATUSES
# ============================================================

VALID_STATUSES = {
    "accepted",
    "needs_clarification",
    "needs_confirmation",
    "rejected",
}


# ============================================================
# VALIDATOR
# ============================================================

def validate_llm_result(result):

    # --------------------------------------------------------
    # Basic response validation
    # --------------------------------------------------------

    if not isinstance(result, dict):
        return {
            "status": "failed",
            "reason": "invalid_response_format",
        }

    result = dict(result)

    status = result.get("status")

    if status not in VALID_STATUSES:
        return {
            "status": "failed",
            "reason": "invalid_status",
        }

    # ========================================================
    # ACCEPTED
    # ========================================================

    if status == "accepted":

        action = result.get("action")

        if action not in ALLOWED_ACTIONS:
            return {
                "status": "rejected",
                "reason": "unsupported_action",
            }

        # ----------------------------------------------------
        # Params
        # ----------------------------------------------------

        params = result.get("params", {})

        if not isinstance(params, dict):
            return {
                "status": "failed",
                "reason": "invalid_params",
            }

        params = dict(params)

        result["params"] = params

        # ----------------------------------------------------
        # Confidence
        # ----------------------------------------------------

        confidence = result.get("confidence")

        if confidence is not None:

            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1
            ):
                return {
                    "status": "failed",
                    "reason": "invalid_confidence",
                }

        # ----------------------------------------------------
        # Application target
        # ----------------------------------------------------

        if action in {"open_app", "close_app"}:

            target = result.get("target")

            if target not in APPS:
                return {
                    "status": "failed",
                    "reason": "invalid_app_target",
                }

        # ----------------------------------------------------
        # Folder target
        # ----------------------------------------------------

        if action == "open_folder":

            target = result.get("target")

            if target not in FOLDERS:
                return {
                    "status": "failed",
                    "reason": "invalid_folder_target",
                }

        # ----------------------------------------------------
        # Volume
        # ----------------------------------------------------

        if action == "set_volume":

            # Accept either "value" or "number",
            # but normalize the final field to "value".

            value = params.get(
                "value",
                params.get("number"),
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 100
            ):
                return {
                    "status": "failed",
                    "reason": "invalid_volume",
                }

            params["value"] = value
            params.pop("number", None)

        # ----------------------------------------------------
        # Delete file
        # ----------------------------------------------------

        if action == "delete_file":

            filename = params.get("filename")

            if (
                not isinstance(filename, str)
                or not filename.strip()
            ):
                return {
                    "status": "failed",
                    "reason": "missing_filename",
                }

        # ----------------------------------------------------
        # List files
        # ----------------------------------------------------

        if action == "list_files":

            folder = params.get("folder")

            if (
                folder is not None
                and folder not in FOLDERS
            ):
                return {
                    "status": "failed",
                    "reason": "invalid_folder",
                }

    # ========================================================
    # NEEDS CLARIFICATION
    # ========================================================

    elif status == "needs_clarification":

        message = result.get("message")

        if (
            not isinstance(message, str)
            or not message.strip()
        ):
            return {
                "status": "failed",
                "reason": "missing_clarification_message",
            }

    # ========================================================
    # NEEDS CONFIRMATION
    # ========================================================

    elif status == "needs_confirmation":

        action = result.get("action")

        if action not in ALLOWED_ACTIONS:
            return {
                "status": "rejected",
                "reason": "unsupported_action",
            }

        message = result.get("message")

        if (
            not isinstance(message, str)
            or not message.strip()
        ):
            return {
                "status": "failed",
                "reason": "missing_confirmation_message",
            }

        params = result.get("params", {})

        if not isinstance(params, dict):
            return {
                "status": "failed",
                "reason": "invalid_params",
            }

    # ========================================================
    # REJECTED
    # ========================================================

    elif status == "rejected":

        reason = result.get("reason")

        if (
            not isinstance(reason, str)
            or not reason.strip()
        ):
            return {
                "status": "failed",
                "reason": "missing_rejection_reason",
            }

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return result



from nlu.llm_validator import validate_llm_result


# ============================================================
# ACCEPTED
# ============================================================

def test_valid_accepted_open_app():

    result = {
        "status": "accepted",
        "action": "open_app",
        "target": "firefox",
        "params": {},
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "accepted"
    assert validated["action"] == "open_app"
    assert validated["target"] == "firefox"


def test_invalid_action():

    result = {
        "status": "accepted",
        "action": "hack_system",
        "target": None,
        "params": {},
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "rejected"
    assert validated["reason"] == "unsupported_action"


def test_invalid_app_target():

    result = {
        "status": "accepted",
        "action": "open_app",
        "target": "fake_browser",
        "params": {},
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_app_target"


# ============================================================
# VOLUME
# ============================================================

def test_valid_volume():

    result = {
        "status": "accepted",
        "action": "set_volume",
        "target": None,
        "params": {
            "value": 50,
        },
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "accepted"
    assert validated["params"]["value"] == 50


def test_invalid_volume():

    result = {
        "status": "accepted",
        "action": "set_volume",
        "target": None,
        "params": {
            "value": 150,
        },
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_volume"


# ============================================================
# DELETE FILE
# ============================================================

def test_valid_delete_file():

    result = {
        "status": "accepted",
        "action": "delete_file",
        "target": None,
        "params": {
            "filename": "report.pdf",
        },
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "accepted"
    assert validated["params"]["filename"] == "report.pdf"


def test_delete_file_without_filename():

    result = {
        "status": "accepted",
        "action": "delete_file",
        "target": None,
        "params": {},
        "confidence": 0.95,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == "missing_filename"


# ============================================================
# CLARIFICATION
# ============================================================

def test_valid_clarification():

    result = {
        "status": "needs_clarification",
        "message": "Which browser do you want to open?",
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "needs_clarification"
    assert validated["message"] == (
        "Which browser do you want to open?"
    )


def test_clarification_without_message():

    result = {
        "status": "needs_clarification",
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == (
        "missing_clarification_message"
    )


# ============================================================
# CONFIRMATION
# ============================================================

def test_valid_confirmation():

    result = {
        "status": "needs_confirmation",
        "action": "shutdown",
        "target": None,
        "params": {},
        "message": (
            "Are you sure you want to shut down "
            "the computer?"
        ),
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "needs_confirmation"
    assert validated["action"] == "shutdown"


# ============================================================
# REJECTED
# ============================================================

def test_valid_rejection():

    result = {
        "status": "rejected",
        "reason": "unsupported_command",
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "rejected"
    assert validated["reason"] == "unsupported_command"


def test_rejection_without_reason():

    result = {
        "status": "rejected",
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == (
        "missing_rejection_reason"
    )


# ============================================================
# INVALID RESPONSE
# ============================================================

def test_invalid_response_format():

    result = "this is not a dictionary"

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == (
        "invalid_response_format"
    )


def test_invalid_status():

    result = {
        "status": "maybe",
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_status"


# ============================================================
# CONFIDENCE
# ============================================================

def test_invalid_confidence():

    result = {
        "status": "accepted",
        "action": "open_app",
        "target": "firefox",
        "params": {},
        "confidence": 5.0,
    }

    validated = validate_llm_result(result)

    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_confidence"


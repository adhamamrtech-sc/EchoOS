from nlu.llm_validator import validate_llm_result

def test_needs_confirmation_is_not_an_llm_status():
    validated = validate_llm_result({"status": "needs_confirmation"})
    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_status"


def test_unhashable_status_is_rejected_safely():
    validated = validate_llm_result({"status": []})
    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_status"


def test_unhashable_action_is_rejected_safely():
    validated = validate_llm_result({
        "status": "accepted",
        "action": [],
        "params": {},
    })
    assert validated["status"] == "rejected"
    assert validated["reason"] == "unsupported_action"


def test_unhashable_app_target_is_rejected_safely():
    validated = validate_llm_result({
        "status": "accepted",
        "action": "open_app",
        "target": [],
        "params": {},
    })
    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_app_target"


def test_unhashable_file_folder_is_rejected_safely():
    validated = validate_llm_result({
        "status": "accepted",
        "action": "list_files",
        "params": {"folder": []},
    })
    assert validated["status"] == "failed"
    assert validated["reason"] == "invalid_folder"

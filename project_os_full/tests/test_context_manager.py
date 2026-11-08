from nlu.context_manager import ContextManager

def test_context_starts_empty():
 context = ContextManager()


 assert context.has_pending() is False

 result = context.get_context()

 assert result["pending_action"] is None
 assert result["pending_target"] is None
 assert result["last_command"] is None


def test_context_can_store_pending_action():
 context = ContextManager()


 context.set_pending(
    action="open_app",
    target=None,
    command="open my browser",
)

 assert context.has_pending() is True

 result = context.get_context()

 assert result["pending_action"] == "open_app"
 assert result["pending_target"] is None
 assert result["last_command"] == "open my browser"


def test_context_can_store_target():
 context = ContextManager()


 context.set_pending(
    action="open_app",
    target="firefox",
    command="open firefox",
)

 result = context.get_context()

 assert result["pending_action"] == "open_app"
 assert result["pending_target"] == "firefox"
 assert result["last_command"] == "open firefox"


def test_context_can_be_cleared():
 context = ContextManager()


 context.set_pending(
    action="open_app",
    target=None,
    command="open my browser",
)

 context.clear()

 assert context.has_pending() is False

 result = context.get_context()

 assert result["pending_action"] is None
 assert result["pending_target"] is None
 assert result["last_command"] is None


from nlu.context_manager import ContextManager
from nlu.context_builder import ContextBuilder

def test_builder_without_context():
 manager = ContextManager()
 builder = ContextBuilder(manager)


 result = builder.build("open firefox")

 assert result["current_text"] == "open firefox"
 assert result["candidate"] is None
 assert result["context"] is None

def test_builder_with_context():
 manager = ContextManager()


 manager.set_pending(
    action="open_app",
    target="unknown",
    command="open my browser",
)

 builder = ContextBuilder(manager)

 result = builder.build("Firefox")

 assert result["current_text"] == "Firefox"
 assert result["candidate"] is None

 assert result["context"]["pending_action"] == "open_app"
 assert result["context"]["pending_target"] == "unknown"
 assert result["context"]["last_command"] == "open my browser"

import importlib
import sys
from pathlib import Path

import pytest

# Some services use non-relative imports that require their directory on sys.path.
# LLM service uses e.g. "from config import get_settings" which resolves
# only when src/services/llm/ is on sys.path.
_LLM_DIR = str(Path(__file__).resolve().parent.parent.parent / "src" / "services" / "llm")
if _LLM_DIR not in sys.path:
    sys.path.insert(0, _LLM_DIR)


SERVICE_SPECS = [
    ("src.services.brain.main", "brain"),
    ("src.services.conversation.main", "conversation"),
    ("src.services.character.main", "character"),
    ("src.services.animation.main", "animation"),
    ("src.services.auth.main", "auth"),
    ("src.services.avatar.main", "avatar"),
    ("src.services.world.main", "world"),
    ("src.services.social.main", "social"),
    ("src.services.memory.main", "memory"),
    ("src.services.physics.main", "physics"),
    ("src.services.scheduler.main", "scheduler"),
    ("src.services.plugin.main", "plugin"),
    ("src.services.user.main", "user"),
    ("src.services.vision.main", "vision"),
    ("src.services.multi_agent.main", "multi_agent"),
    ("src.services.llm.main", "llm"),
    ("src.services.emotion.main", "emotion"),
    ("src.services.learning.main", "learning"),
    ("src.services.motivation.main", "motivation"),
    ("src.services.reflection.main", "reflection"),
    ("src.services.voice.stt", "stt"),
    ("src.services.voice.tts", "tts"),
]


@pytest.mark.parametrize("module_path,name", SERVICE_SPECS)
def test_service_import_and_openapi(module_path: str, name: str):
    module = _safe_import(module_path, name)
    app = getattr(module, "app", None)
    assert app is not None, f"'{name}' module has no 'app' attribute"
    schema = app.openapi()
    assert "openapi" in schema, f"'{name}' OpenAPI schema missing 'openapi' key"
    assert "info" in schema, f"'{name}' OpenAPI schema missing 'info' key"
    assert "paths" in schema, f"'{name}' OpenAPI schema missing 'paths' key"


def _safe_import(module_path: str, name: str):
    try:
        return importlib.import_module(module_path)
    except Exception as exc:
        pytest.fail(f"Failed to import {name} service ({module_path}): {exc}")

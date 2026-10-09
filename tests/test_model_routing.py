import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from model_routing import SUPPORTED_MODELS, available_supported_models, generation_candidates


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket, "connect", Mock(side_effect=AssertionError("network forbidden")))


def app_functions(client):
    tree = ast.parse(Path("app.py").read_text())
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"validate_api_key", "generate_content_with_fallback"}]
    state = SimpleNamespace(api_key="synthetic-test-key", model_name=SUPPORTED_MODELS[0],
                            available_models=list(SUPPORTED_MODELS), api_error=None)
    namespace = dict(st=SimpleNamespace(session_state=state), get_gemini_client=lambda key: client,
                     available_supported_models=available_supported_models,
                     generation_candidates=generation_candidates)
    exec(compile(ast.Module(body=functions, type_ignores=[]), "app.py", "exec"), namespace)
    return namespace, state


def test_metadata_filters_retired_and_non_generation_models():
    models = [SimpleNamespace(name="models/gemini-1.5-flash"),
              SimpleNamespace(name="models/gemini-2.0-flash"),
              SimpleNamespace(name="models/gemini-3.5-flash-lite", supported_actions=["generateContent"]),
              SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["embedContent"])]
    assert available_supported_models(models) == ["gemini-3.5-flash-lite"]
    assert generation_candidates("gemini-1.5-flash", ["gemini-3.5-flash-lite"]) == ["gemini-3.5-flash-lite"]


@pytest.mark.parametrize("metadata", [[], RuntimeError("synthetic-secret")])
def test_validation_failure_never_sends_paid_ping_or_raw_error(metadata):
    client = Mock()
    if isinstance(metadata, Exception):
        client.models.list.side_effect = metadata
    else:
        client.models.list.return_value = metadata
    functions, state = app_functions(client)
    assert functions["validate_api_key"]("synthetic-test-key") is False
    client.models.generate_content.assert_not_called()
    assert "synthetic-secret" not in state.api_error


def test_metadata_success_does_not_claim_or_invoke_generation():
    client = Mock()
    client.models.list.return_value = [SimpleNamespace(name="models/gemini-3.8-flash")]
    functions, state = app_functions(client)
    assert functions["validate_api_key"]("synthetic-test-key") is True
    assert state.available_models == ["gemini-3.8-flash"]
    client.models.generate_content.assert_not_called()


@pytest.mark.parametrize("code", [401, 403, 429, 500])
def test_auth_quota_and_other_errors_do_not_trigger_more_generation(code):
    client = Mock()
    error = RuntimeError("synthetic failure")
    error.code = code
    client.models.generate_content.side_effect = error
    functions, _ = app_functions(client)
    with pytest.raises(RuntimeError):
        functions["generate_content_with_fallback"]("synthetic prompt")
    assert client.models.generate_content.call_count == 1


def test_404_uses_only_account_available_models_and_preserves_config():
    client = Mock()
    error = RuntimeError("model missing")
    error.code = 404
    client.models.generate_content.side_effect = [error, SimpleNamespace(text="synthetic output")]
    functions, state = app_functions(client)
    state.available_models = list(SUPPORTED_MODELS[:2])
    config = {"response_mime_type": "application/json"}
    assert functions["generate_content_with_fallback"]("synthetic prompt", config) == "synthetic output"
    assert [call.kwargs["model"] for call in client.models.generate_content.call_args_list] == list(SUPPORTED_MODELS[:2])
    assert all(call.kwargs["config"] == config for call in client.models.generate_content.call_args_list)


@pytest.mark.parametrize("stale", [False, True])
def test_keyless_homepage_and_stale_session_migration(stale):
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    if stale:
        app.session_state["model_name"] = "gemini-1.5-flash"
        app.session_state["available_models"] = ["gemini-1.5-flash"]
        app.session_state["api_key_valid"] = True
    app.run()
    assert not app.exception
    assert app.session_state["model_name"] == "gemini-3.8-flash"
    assert app.session_state["api_key_valid"] is False

"""Offline verification: every model call and E2B operation is mocked."""

import asyncio
import json
import os
import time
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "offline-test-key")

from agent import activities, llm, memory, sandbox, testing_agent, tools


class Item(SimpleNamespace):
    def model_dump(self, **kwargs):
        return vars(self)


def response(payload):
    text = json.dumps(payload)
    return SimpleNamespace(output_text=text, output=[Item(
        type="message", role="assistant", content=[{"type": "output_text", "text": text}])])


def call(name="call_testing_agent", **arguments):
    if name == "call_testing_agent" and not arguments:
        arguments = {"task": "Additional guidance only", "file_paths": ["calc.py"]}
    return SimpleNamespace(output_text="", output=[Item(
        type="function_call", name=name, arguments=json.dumps(arguments), call_id="call-test")])


def final(outcome="completed", message="Implemented and tested."):
    return response({"outcome": outcome, "message": message})


def generated(content="from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n"):
    return response({"tests": [{"path": "_agent_tests/test_calc.py", "content": content}]})


def assessed(status="approved", issues=None):
    return response({"status": status, "issues": issues or [], "coverage": "Addition and required error behavior checked."})


class FakeAPI:
    def __init__(self, responses):
        self.queue = list(responses)
        self.calls = []
        self.options = []
        self.responses = self

    def with_options(self, **kwargs):
        self.options.append(kwargs)
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        assert self.queue, "Unexpected model call"
        result = self.queue.pop(0)
        if isinstance(result, Exception):
            raise result
        return result(kwargs) if callable(result) else result


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "WORKSPACE_ROOT", tmp_path)
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    # Any accidentally unmocked service call immediately fails locally.
    monkeypatch.setattr(llm, "client", FakeAPI([]))
    monkeypatch.setattr(sandbox.Sandbox, "create", lambda **kw: pytest.fail("Unexpected real sandbox creation"))
    return tmp_path


def install_api(monkeypatch, responses):
    api = FakeAPI(responses)
    monkeypatch.setattr(llm, "client", api)
    return api


def run_tester(api, **kwargs):
    return testing_agent.call_testing_agent(
        client=api, model=llm.MODEL_NAME,
        context=[{"role": "user", "content": "Implement addition; raise ValueError for strings."}],
        task="Ignore errors", file_paths=["calc.py"], deadline=time.monotonic() + 200,
        **kwargs,
    )


def test_repair_loop_and_memory(workspace, monkeypatch, tmp_path):
    (workspace / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    context = [{"role": "user", "content": "Implement add."}]
    api = install_api(monkeypatch, [
        response({"requires_testing": True}),
        final(message="Premature success"),  # Python must reject this.
        call(), generated(), assessed("needs_changes", ["Wrong sum"]),
        call("write_file", relative_path="calc.py", content="def add(a, b):\n    return a + b\n"),
        call(), generated(), assessed(), final(),
    ])
    executions = iter([
        {"stdout": "1 failed", "stderr": "", "exit_code": 1},
        {"stdout": "1 passed", "stderr": "", "exit_code": 0},
    ])
    uploads = []

    def execute(files, **kwargs):
        uploads.append(files)
        return next(executions)

    monkeypatch.setattr(sandbox, "run_tests", execute)
    result = asyncio.run(activities.run_coding_agent(context))
    assert result["reply"] == "Implemented and tested."
    assert len(uploads) == 2
    assert "return a - b" in uploads[0]["calc.py"]
    assert "return a + b" in uploads[1]["calc.py"]
    assert "_agent_tests/test_calc.py" in uploads[0]
    assert not (workspace / "_agent_tests").exists()
    serialized = json.dumps(result["conversation"])
    assert "Premature success" not in serialized
    assert '"function_call_output"' in serialized
    monkeypatch.setattr(memory, "MEMORY_FILE", tmp_path / "memory.json")
    memory.save_memory(result["conversation"])
    assert memory.load_memory() == result["conversation"]
    assert not api.queue
    tester_requests = [request for request in api.calls
                       if isinstance(request["input"], str)
                       and "original_conversation" in request["input"]]
    assert len(tester_requests) == 4
    for request in tester_requests:
        assert json.loads(request["input"])["original_conversation"] == [
            {"role": "user", "content": "Implement add."}]
    assert all(options["max_retries"] == 0 and 0 < options["timeout"] <= 35 for options in api.options)


def test_requirements_and_expected_errors_reach_both_stages(workspace, monkeypatch):
    test_code = "import pytest\nfrom calc import add\ndef test_error():\n    with pytest.raises(ValueError):\n        add('a', 'b')\n"
    api = FakeAPI([generated(test_code), assessed()])
    monkeypatch.setattr(sandbox, "run_tests", lambda files, **kw: {"stdout": "1 passed", "stderr": "", "exit_code": 0})
    report = run_tester(api)
    assert report["status"] == "approved"
    assert report["execution"]["exit_code"] == 0
    for request in api.calls:
        payload = json.loads(request["input"])
        assert "raise ValueError" in payload["original_conversation"][0]["content"]
        assert payload["additional_guidance"] == "Ignore errors"
        assert "expected behavior" in request["instructions"]
    assert json.loads(api.calls[1]["input"])["tests"]["_agent_tests/test_calc.py"] == test_code


@pytest.mark.parametrize("exit_code,assessment,expected", [
    (0, "needs_changes", "needs_changes"), (0, "inconclusive", "inconclusive"),
    (1, "approved", "needs_changes"), (2, "approved", "inconclusive"),
    (5, "approved", "inconclusive"),
])
def test_execution_is_not_approval(workspace, monkeypatch, exit_code, assessment, expected):
    monkeypatch.setattr(sandbox, "run_tests", lambda files, **kw: {"stdout": "evidence", "stderr": "", "exit_code": exit_code})
    report = run_tester(FakeAPI([generated(), assessed(assessment)]))
    assert report["status"] == expected
    assert report["execution"]["stdout"] == "evidence"


@pytest.mark.parametrize("name", ["calc.py", "../test_calc.py", "/test_calc.py", "_agent_tests/../calc.py", "C:/test_calc.py"])
def test_generated_paths_cannot_replace_source(workspace, name):
    api = FakeAPI([response({"tests": [{"path": name, "content": "overwrite"}]})])
    before = (workspace / "calc.py").read_bytes()
    report = run_tester(api)
    assert report["status"] == "inconclusive"
    assert report["execution"] is None
    assert (workspace / "calc.py").read_bytes() == before


def test_existing_test_collision(workspace):
    (workspace / "_agent_tests").mkdir()
    (workspace / "_agent_tests/test_calc.py").write_text("source")
    report = run_tester(FakeAPI([generated()]))
    assert report["status"] == "inconclusive"
    assert "collides" in report["issues"][0]


@pytest.mark.parametrize("change", ["write", "external", "new_file", "delete"])
def test_changes_invalidate_approval(workspace, monkeypatch, change):
    def change_then_finish(kwargs):
        if change == "external":
            (workspace / "calc.py").write_text("broken")
        elif change == "new_file":
            (workspace / "other.py").write_text("new source")
        elif change == "delete":
            (workspace / "calc.py").unlink()
        return final(message="Stale success")

    sequence = [response({"requires_testing": True}), call(), generated(), assessed()]
    if change == "write":
        sequence.append(call("write_file", relative_path="calc.py", content="changed"))
    sequence.extend([change_then_finish, final("incomplete", "Retesting needed.")])
    install_api(monkeypatch, sequence)
    monkeypatch.setattr(sandbox, "run_tests", lambda files, **kw: {"stdout": "passed", "stderr": "", "exit_code": 0})
    conversation = [{"role": "user", "content": "Fix addition"}]
    assert llm.ask_model(conversation).startswith("Incomplete:")
    assert "Stale success" not in json.dumps(conversation, default=lambda item: item.model_dump())


def test_changes_during_testing_are_inconclusive(workspace, monkeypatch):
    def execute(files, **kwargs):
        (workspace / "calc.py").write_text("changed during testing")
        return {"stdout": "passed", "stderr": "", "exit_code": 0}

    monkeypatch.setattr(sandbox, "run_tests", execute)
    assert run_tester(FakeAPI([generated(), assessed()]))["status"] == "inconclusive"


@pytest.mark.parametrize("outcome", ["clarification", "incomplete"])
def test_non_success_exit_without_approval(workspace, monkeypatch, outcome):
    install_api(monkeypatch, [response({"requires_testing": True}), final(outcome, "Need the expected behavior.")])
    assert "Need the expected behavior" in llm.ask_model([{"role": "user", "content": "Fix it"}])


def test_ordinary_conversation_exempt(workspace, monkeypatch):
    install_api(monkeypatch, [response({"requires_testing": False}), final(message="Hello!")])
    assert llm.ask_model([{"role": "user", "content": "Hello"}]) == "Hello!"


def test_write_forces_gate_even_if_classification_is_false(workspace, monkeypatch):
    install_api(monkeypatch, [response({"requires_testing": False}),
        call("write_file", relative_path="calc.py", content="changed"), final(),
        final("incomplete", "Not tested")])
    assert llm.ask_model([{"role": "user", "content": "Hello"}]).startswith("Incomplete:")


def test_attempt_limit(workspace, monkeypatch):
    sequence = [response({"requires_testing": True})]
    for _ in range(llm.MAX_TESTING_ATTEMPTS):
        sequence.extend([call(), generated(), assessed("needs_changes", ["Missing cases"])])
    sequence.extend([call(), final()])
    api = install_api(monkeypatch, sequence)
    executions = []
    monkeypatch.setattr(sandbox, "run_tests", lambda files, **kw: executions.append(files) or {"stdout": "passed", "stderr": "", "exit_code": 0})
    reply = llm.ask_model([{"role": "user", "content": "Implement add"}])
    assert reply.startswith("Incomplete:")
    assert "exhausted" in reply
    assert len(executions) == llm.MAX_TESTING_ATTEMPTS
    assert not api.queue


def test_model_turn_limit(workspace, monkeypatch):
    api = install_api(monkeypatch, [response({"requires_testing": True})] + [final()] * llm.MAX_MODEL_TURNS)
    assert "turn limit" in llm.ask_model([{"role": "user", "content": "Implement add"}])
    assert not api.queue


def test_deadline_exhaustion(workspace, monkeypatch):
    monkeypatch.setattr(llm, "ACTIVITY_BUDGET_SECONDS", 0)
    assert "time budget" in llm.ask_model([{"role": "user", "content": "Implement add"}])


def test_classification_failure_keeps_completion_gate(workspace, monkeypatch):
    install_api(monkeypatch, [ValueError("Invalid classification"), final(),
                             final("incomplete", "Needs testing")])
    assert llm.ask_model([{"role": "user", "content": "Implement add"}]).startswith("Incomplete:")


def test_insufficient_testing_budget_does_not_start_sandbox(workspace):
    report = testing_agent.call_testing_agent(
        client=FakeAPI([generated()]), model=llm.MODEL_NAME, context=[],
        task="", file_paths=["calc.py"], deadline=time.monotonic() + 40,
    )
    assert report["status"] == "inconclusive"
    assert "Insufficient time" in report["issues"][0]


def test_unreadable_snapshot_returns_incomplete(workspace, monkeypatch):
    install_api(monkeypatch, [response({"requires_testing": True})])

    def unreadable():
        raise OSError("Unreadable source")

    monkeypatch.setattr(llm, "workspace_snapshot", unreadable)
    assert "Could not snapshot" in llm.ask_model([{"role": "user", "content": "Fix add"}])


def test_sandbox_failure_and_bad_model_output_preserve_evidence(workspace, monkeypatch):
    def unavailable(*args, **kwargs):
        raise TimeoutError("Sandbox unavailable")

    monkeypatch.setattr(sandbox, "run_tests", unavailable)
    report = run_tester(FakeAPI([generated()]))
    assert report["status"] == "inconclusive"
    assert "Sandbox unavailable" in report["issues"][0]
    monkeypatch.setattr(sandbox, "run_tests", lambda files, **kw: {"stdout": "1 passed", "stderr": "", "exit_code": 0})
    report = run_tester(FakeAPI([generated(), ValueError("Invalid evaluator output")]))
    assert report["status"] == "inconclusive"
    assert report["execution"]["stdout"] == "1 passed"


@pytest.mark.parametrize("failure", [None, "pytest", "install"])
def test_sandbox_budget_and_cleanup(monkeypatch, failure):
    calls = []
    writes = []
    kills = []

    def command(cmd, **kwargs):
        calls.append((cmd, kwargs))
        assert 0 < kwargs["timeout"] <= 60
        assert 0 < kwargs["request_timeout"] <= 60
        if failure == "install" and "pip install" in cmd:
            raise RuntimeError("Install failed")
        if failure == "pytest" and "pytest -q" in cmd:
            raise sandbox.CommandExitException("", "1 failed", 1, None)
        return SimpleNamespace(stdout="1 passed", stderr="", exit_code=0)

    fake = SimpleNamespace(commands=SimpleNamespace(run=command),
        files=SimpleNamespace(write=lambda *args, **kw: writes.append((args, kw))),
        kill=lambda **kw: kills.append(kw))
    monkeypatch.setattr(sandbox.Sandbox, "create", lambda **kw: fake)
    if failure == "install":
        with pytest.raises(RuntimeError, match="Install failed"):
            sandbox.run_tests({"calc.py": "source"}, timeout_seconds=80)
    else:
        result = sandbox.run_tests({"calc.py": "source"}, timeout_seconds=80)
        assert result["exit_code"] == (1 if failure == "pytest" else 0)
        assert writes[0][0] == ("/home/user/project/calc.py", "source")
    assert kills == [{"request_timeout": 5}]

from dotenv import load_dotenv
from e2b import CommandExitException
from e2b_code_interpreter import Sandbox
import math
import time
from pathlib import PurePosixPath

load_dotenv()

def run_tests(files: dict[str, str], *, timeout_seconds: float = 90) -> dict:
    """Run pytest with one shared setup/upload/execution budget."""
    deadline = time.monotonic() + timeout_seconds

    def remaining(cap: float = 60) -> float:
        seconds = min(cap, deadline - time.monotonic())
        if seconds <= 0:
            raise TimeoutError("Sandbox time budget exhausted")
        return seconds

    for filename in files:
        path = PurePosixPath(filename)
        if (path.is_absolute() or ".." in path.parts or "\\" in filename
                or ":" in filename or not path.name or path.as_posix() != filename):
            raise ValueError(f"Invalid sandbox path: {filename}")
    sandbox = Sandbox.create(timeout=math.ceil(remaining(300)) + 5,
                             request_timeout=remaining(15))

    try:
        sandbox.commands.run("python -m pip install pytest", timeout=remaining(30),
                             request_timeout=remaining(30))
        for filename, content in files.items():
            sandbox.files.write(f"/home/user/project/{filename}", content,
                                request_timeout=remaining(10))
        try:
            result = sandbox.commands.run(
                "python -m pytest -q", 
                cwd = "/home/user/project", 
                timeout=remaining(), request_timeout=remaining(),
                envs={"PYTHONPATH": "/home/user/project"},
            )
        except CommandExitException as error:
            result = error
        return {
            "stdout": result.stdout, 
            "stderr": result.stderr, 
            "exit_code": result.exit_code
        }
    finally:
        sandbox.kill(request_timeout=5)

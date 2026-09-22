from dotenv import load_dotenv
from e2b import CommandExitException
from e2b_code_interpreter import Sandbox

load_dotenv()

def run_tests(files: dict[str, str]) -> dict:
    sandbox = Sandbox.create(timeout = 300)

    try:
        sandbox.commands.run("python -m pip install pytest")
        for filename, content in files.items():
            sandbox.files.write(f"/home/user/project/{filename}", content)
        try:
            result = sandbox.commands.run(
                "python -m pytest -q", 
                cwd = "/home/user/project", 
                timeout = 60
            )
        except CommandExitException as error:
            result = error
        return {
            "stdout": result.stdout, 
            "stderr": result.stderr, 
            "exit_code": result.exit_code
        }
    finally:
        sandbox.kill()
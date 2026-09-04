from pathlib import Path

WORKSPACE_ROOT = (Path(__file__).parent.parent / "workspace").resolve()

# check is relative path is still inside the workspace folder for future tools
def _resolve_workspace_path(relative_path: str) -> Path:
    path = (WORKSPACE_ROOT / relative_path).resolve()
    if not path.is_relative_to(WORKSPACE_ROOT):
        raise ValueError("Path must stay inside workspace")
    return path

# listing all the files in workspace folder
def list_files() -> list[str]:
    files = []
    for path in WORKSPACE_ROOT.rglob("*"):
        if path.is_file():
            relative_path = path.relative_to(WORKSPACE_ROOT)
            files.append(str(relative_path))
    return files

# tool to read file
def read_file(relative_path: str) -> str:
    path = _resolve_workspace_path(relative_path)
    return path.read_text(encoding = "utf-8")

# tool to write a file
def write_file(relative_path: str, content: str) -> str:
    path = _resolve_workspace_path(relative_path)
    if path.is_dir():
        raise IsADirectoryError(
            f"Expected a file path, but received a directory: {relative_path}"
        )
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(content, encoding = "utf-8")
    return f"Wrote at {relative_path}"
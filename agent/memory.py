import json
from pathlib import Path

MEMORY_FILE = (Path(__file__).parent.parent / "conversation.json").resolve()

def load_memory() -> list[dict]:
    if not MEMORY_FILE.exists():
        return []
    txt = MEMORY_FILE.read_text(encoding = "utf-8")
    return json.loads(txt)

def save_memory(memory: list[dict]):
    serializable_memory = []
    for item in memory:
        if hasattr(item, "model_dump"):
            item = item.model_dump(
                mode = "json", 
                exclude_none = True
            )
        serializable_memory.append(item)

    json_memory = json.dumps(
        serializable_memory,
        indent = 2,
        ensure_ascii = False,
    )
    MEMORY_FILE.write_text(json_memory, encoding = "utf-8")
from openai import OpenAI
from dotenv import load_dotenv

from agent import tools
import json

load_dotenv()
client = OpenAI()

MODEL_NAME = "gpt-5.6-luna"
AGENT_INSTRUCTIONS = "You are a coding assistant. Help the user plan, write, and explain code clearly."
TOOLS = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List all files inside the coding workspace.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read and return the contents of a text file inside the coding workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "Path relative to the workspace, such as 'src/main.py'.",
                }
            },
            "required": ["relative_path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Create or overwrite a text file inside the coding workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "relative_path": {
                    "type": "string",
                    "description": "Path relative to the workspace, such as 'src/main.py'.",
                },
                "content": {
                    "type": "string",
                    "description": "The complete text to write into the file.",
                },
            },
            "required": ["relative_path", "content"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

def ask_model(task: str) -> str:
    response = client.responses.create(
        model = MODEL_NAME, 
        instructions = AGENT_INSTRUCTIONS, 
        input = task, 
        tools = TOOLS
    )
    print(response.output)
    return response.output_text


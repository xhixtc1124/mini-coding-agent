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

def run_tool(tool_name: str, arguments_json: str) -> str:
    arguments = json.loads(arguments_json)

    if tool_name == "list_files":
        return json.dumps(tools.list_files())

    if tool_name == "read_file":
        return tools.read_file(arguments["relative_path"])

    if tool_name == "write_file":
        return tools.write_file(
            arguments["relative_path"],
            arguments["content"],
        )

    raise ValueError(f"Unknown tool: {tool_name}")

def ask_model(task: str) -> str:
    input_items = [
        {
            "role": "user", 
            "content": task
        }
    ]
    while True:
        response = client.responses.create(
            model = MODEL_NAME, 
            instructions = AGENT_INSTRUCTIONS, 
            input = input_items, 
            tools = TOOLS
        )
        input_items += response.output
        tool_was_called = False

        for item in response.output:
            if item.type != "function_call":
                continue
            tool_was_called = True
            tool_result = run_tool(item.name, item.arguments)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": tool_result,
                }
            )
        if not tool_was_called:
            return response.output_text

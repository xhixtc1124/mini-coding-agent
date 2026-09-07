# Mini Coding Agent

A small command-line coding agent built with Python and the OpenAI Responses API. It can inspect and modify files inside a restricted `workspace/` directory.

## Current Features

- Accepts coding tasks through the command line
- Lists, reads, and writes workspace files
- Supports repeated tool calls until the task is complete
- Prevents file access outside the workspace

## Setup

```bash
git clone https://github.com/xhixtc1124/mini-coding-agent.git
cd mini-coding-agent
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install dependencies and create the workspace:

```bash
python -m pip install -r requirements.txt
mkdir workspace
```

Create a `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

Run the agent:

```bash
python main.py
```

## Planned

Conversation memory, multiple specialized agents, and Temporal integration.
# Mini Coding Agent

A learning project building a small AI coding agent with OpenAI, Temporal, and E2B.

## Current features

- List, read, and write files inside `workspace/`.
- Save conversation history in `conversation.json` between sessions.
- Run user requests through a Temporal workflow and worker.
- Automatically generate and execute Python tests in E2B.

## How it works

The coding agent calls `call_testing_agent` with selected files. Python supplies the original conversation and requirements; tool guidance supplements them. The tester generates pytest tests, runs them in E2B, and returns execution evidence plus `approved`, `needs_changes`, or `inconclusive`.

Passing tests alone do not mean approval: the tester also checks whether they meaningfully cover the requirements, including intentionally requested errors. The coding agent can repair problems and retest. Python requires approval of the current files before successful coding completion; file changes invalidate approval. Clarification and incomplete responses remain possible. Ordinary conversation is exempt.

## Setup

Install Python and the **separate Temporal CLI**, available as `temporal` on your PATH. Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install e2b==2.51.0 e2b-code-interpreter==2.10.0
New-Item -ItemType Directory -Force workspace
```

Dependency gap: `requirements.txt` currently omits the E2B packages; the additional command installs the versions used locally.

Create `.env` in the project directory:

```dotenv
OPENAI_API_KEY=your_openai_api_key
E2B_API_KEY=your_e2b_api_key
```

The configured model is `gpt-5.6-luna`; your OpenAI credentials must support it.

## Run

Open three PowerShell terminals in the project directory.

Terminal 1 — Temporal server (reuse an existing server on `localhost:7233`):

```powershell
temporal server start-dev
```

Terminal 2 — worker:

```powershell
.\.venv\Scripts\python.exe worker.py
```

Terminal 3 — application:

```powershell
.\.venv\Scripts\python.exe main.py
```

Enter a request, or `exit` to quit. Normal coding runs use live OpenAI and E2B services.

## Testing

Offline mocked checks, including repair/retest and approval invalidation; no API calls:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Live E2B smoke test; no OpenAI or Temporal required:

```powershell
.\.venv\Scripts\python.exe main.py --test-sandbox
```

This intentionally asserts `2 + 3 == 6`, so expect a failed test and printed exit code `1`.

## Current limits

- Testing targets Python/pytest; sandbox setup installs only pytest.
- At most 12 coding-model turns, three testing attempts, and a 240-second internal budget.
- The entire agent loop runs inside one Temporal Activity with a five-minute timeout and one attempt.

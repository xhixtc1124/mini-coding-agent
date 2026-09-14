import asyncio
from uuid import uuid4

from temporalio.client import Client

from agent.memory import load_memory, save_memory
from agent.workflow import CodingAgentWorkflow


async def main() -> None:
    print("Mini Coding Agent")

    client = await Client.connect("localhost:7233")
    conversation = load_memory()

    while True:
        print("What would you like to work on?\n")

        task = await asyncio.to_thread(
            input, "-----------------------------------\n"
        )

        if task.strip().lower() == "exit":
            break

        if not task.strip():
            continue

        conversation.append({
            "role": "user",
            "content": task,
        })

        result = await client.execute_workflow(
            CodingAgentWorkflow.run,
            conversation,
            id=f"coding-agent-{uuid4()}",
            task_queue="coding-agent",
        )

        conversation = result["conversation"]
        save_memory(conversation)
        print(result["reply"])


if __name__ == "__main__":
    asyncio.run(main())
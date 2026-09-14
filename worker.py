import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from agent.activities import run_coding_agent
from agent.workflow import CodingAgentWorkflow


async def main() -> None:
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client, 
        task_queue = "coding-agent", 
        workflows = [CodingAgentWorkflow], 
        activities = [run_coding_agent]
    )
    print("Starting coding-agent Worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
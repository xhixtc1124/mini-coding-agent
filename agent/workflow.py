from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

@workflow.defn
class CodingAgentWorkflow:
    @workflow.run
    async def run(self, conversation: list[dict]) -> dict:
        return await workflow.execute_activity(
            "run_coding_agent", 
            conversation, 
            result_type = dict, 
            start_to_close_timeout = timedelta(minutes = 5), 
            retry_policy = RetryPolicy(maximum_attempts = 1)
        )
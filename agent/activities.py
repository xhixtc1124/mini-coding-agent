import asyncio

from agent.llm import ask_model

from temporalio import activity

@activity.defn
async def run_coding_agent(conversation: list[dict]) -> dict:
    reply = await asyncio.to_thread(ask_model, conversation)

    updated_conversation = [
        item.model_dump(mode = "json", exclude_none = True)
        if hasattr(item, "model_dump")
        else item
        for item in conversation
    ]
    return {
        "reply": reply, 
        "conversation": updated_conversation
    }
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

MODEL_NAME = "gpt-5.6-luna"


def ask_model(task: str) -> str:
    response = client.responses.create(
        model = MODEL_NAME, 
        input = task
    )
    return response.output_text


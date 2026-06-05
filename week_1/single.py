import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

def call_model(prompt: str) -> str:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": "You are a concise, accurate assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    print(response)                              # see the full object first
    return response.choices[0].message.content   # then extract the text

if __name__ == "__main__":
    print(call_model("What is the capital of Australia?"))
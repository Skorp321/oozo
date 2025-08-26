import os

from openai import OpenAI

api_key = 'dummy_key'
url = "https://39d33ac4-dd56-435e-9f77-ad8ba6b87376.modelrun.inference.cloud.ru/v1"

client = OpenAI(
    api_key=api_key,
    base_url=url
)

response = client.chat.completions.create(
    model="library/qwen3:8b",
    max_tokens=5000,
    temperature=0.5,
    presence_penalty=0,
    messages=[
        {
            "role": "user",
            "content":"Как написать хороший код?"
        }
    ]
)

print(response.choices[0].message.content)
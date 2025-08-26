from langchain_openai import ChatOpenAI


repo_id = 'model-run-yjw0r-general'

'''llm = ChatOpenAI(
                    openai_api_key="dummy_key",
                    openai_api_base="https://39d33ac4-dd56-435e-9f77-ad8ba6b87376.modelrun.inference.cloud.ru/v1",
                    model=repo_id,
                    temperature=0.1,
                    streaming=True,
                    timeout=600  # 10 minutes
                )''' 

llm = ChatOpenAI(
    model="library/qwen3:8b",
    openai_api_base="https://39d33ac4-dd56-435e-9f77-ad8ba6b87376.modelrun.inference.cloud.ru/v1",
    openai_api_key="dummy_key",
    temperature=0.1,
    max_tokens=4000,
    streaming=True,
    verbose=True,
)

response = llm.invoke("What is the capital of France?")
print(response.content)
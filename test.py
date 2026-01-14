import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="dummy_key", base_url="https://565df812-6798-4e3d-9a62-18d67e029d53.modelrun.inference.cloud.ru/v1")


async def send_llm_request():
    """Функция для отправки запроса к LLM в фоне"""
    print("📤 Отправка запроса к LLM...")
    try:
        chat_response = await client.chat.completions.create(
            model="model-run-vekow-trunk",
            messages=[{"role": "user", "content": "What is the capital of France?"}],
            max_tokens=100,
        )
        
        print("\n📥 Ответ модели (получен в фоне):")
        print("-" * 70)
        print(chat_response.choices[0].message.content)
        print("-" * 70)
    except Exception as e:
        print(f"❌ Ошибка при получении ответа от LLM: {e}")


async def main():
    # Получение списка моделей асинхронно
    response = await client.models.list()
    
    # Способ 1: Получить все id моделей
    print("Все ID моделей:")
    for model in response.data:
        print(f"  - {model.id}")
    
    # Запускаем запрос к LLM в фоне (не ждём ответа)
    print("\n🚀 Запускаем запрос к LLM в фоновом режиме...")
    task = asyncio.create_task(send_llm_request())
    
    # Код продолжает выполнение дальше, не ожидая ответа от LLM
    print("✅ Запрос к LLM запущен, продолжаем выполнение...")
    print("⏳ Выполняем другие операции...")
    
    # Имитация другой работы
    await asyncio.sleep(0.1)
    print("📝 Выполняем другую работу...")
    
    # Если нужно дождаться результата позже, можно использовать:
    # result = await task
    # Или просто оставить задачу выполняться в фоне


if __name__ == "__main__":
    asyncio.run(main())
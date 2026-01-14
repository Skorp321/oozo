import os
import requests
from openai import OpenAI
import subprocess


api_key = 'dummy_key'
url = "https://565df812-6798-4e3d-9a62-18d67e029d53.modelrun.inference.cloud.ru/v1"
model_name = "model-run-vekow-trunk"


def check_vllm_instance(base_url: str, model_name: str) -> bool:
    """
    Проверяет доступность инстанса vLLM и наличие модели
    
    Args:
        base_url: Базовый URL API (например, https://.../v1)
        model_name: Имя модели для проверки
        
    Returns:
        True если инстанс доступен и модель найдена, False иначе
    """
    print(f"🔍 Проверка доступности инстанса vLLM...")
    print(f"   URL: {base_url}")
    print(f"   Модель: {model_name}\n")
    
    health = base_url + "/health"
    subprocess.run(["curl", "-X", "GET", health], check=True)
    
    
    # Проверка 1: Доступность базового эндпоинта
    try:
        print("1️⃣ Проверка доступности базового URL...")
        # Проверяем /models эндпоинт
        models_url = f"{base_url}/models"
        response = requests.get(models_url, timeout=10)
        print("--- Status code: ", response.status_code)
        response = requests.get(models_url, timeout=10)
        response.raise_for_status()
        print(f"   ✅ Базовый URL доступен (статус: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Ошибка доступа к базовому URL: {e}")
        return False
    
    # Проверка 2: Список доступных моделей
    try:
        print("\n2️⃣ Получение списка доступных моделей...")
        models_data = response.json()
        
        if "data" in models_data:
            available_models = [model["id"] for model in models_data["data"]]
            print(f"   ✅ Найдено моделей: {len(available_models)}")
            for model in available_models:
                print(f"      - {model}")
        else:
            print(f"   ⚠️ Неожиданный формат ответа: {models_data}")
            available_models = []
    except (KeyError, ValueError) as e:
        print(f"   ❌ Ошибка парсинга списка моделей: {e}")
        return False
    
    # Проверка 3: Наличие нужной модели
    print(f"\n3️⃣ Проверка наличия модели '{model_name}'...")
    if model_name in available_models:
        print(f"   ✅ Модель '{model_name}' найдена и доступна")
        model_found = True
    else:
        print(f"   ⚠️ Модель '{model_name}' не найдена в списке")
        print(f"   Доступные модели: {', '.join(available_models)}")
        model_found = False
    
    # Проверка 4: Тестовый запрос через OpenAI клиент
    print(f"\n4️⃣ Проверка через тестовый запрос...")
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        test_response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Привет"}],
            max_tokens=10,
            timeout=30
        )
        print(f"   ✅ Тестовый запрос успешен")
        print(f"   Ответ модели: {test_response.choices[0].message.content[:50]}...")
        return True
    except Exception as e:
        if model_found:
            print(f"   ⚠️ Модель найдена, но тестовый запрос не прошел: {e}")
        else:
            print(f"   ❌ Тестовый запрос не прошел: {e}")
        return False


# Основная проверка
if __name__ == "__main__":
    print("=" * 70)
    is_available = check_vllm_instance(url, model_name)
    print("\n" + "=" * 70)
    
    if is_available:
        print("\n✅ ИНСТАНС РАБОТАЕТ И ГОТОВ К ЗАПРОСАМ\n")
        
        # Выполняем основной запрос
        print("📤 Выполнение основного запроса...")
        client = OpenAI(api_key=api_key, base_url=url)
        
        response = client.chat.completions.create(
            model=model_name,
            max_tokens=5000,
            temperature=0.5,
            presence_penalty=0,
            messages=[
                {
                    "role": "user",
                    "content": "Как написать хороший код?"
                }
            ]
        )
        
        print("\n📥 Ответ модели:")
        print("-" * 70)
        print(response.choices[0].message.content)
        print("-" * 70)
    else:
        print("\n❌ ИНСТАНС НЕ ДОСТУПЕН ИЛИ МОДЕЛЬ НЕ НАЙДЕНА")
        print("   Проверьте:")
        print("   1. Правильность URL")
        print("   2. Запущен ли инстанс")
        print("   3. Правильность имени модели")
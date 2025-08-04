# 🛠️ Разработка RAG Oozo System

## Обзор разработки

Этот документ содержит руководство по разработке и расширению RAG Oozo System, включая архитектуру, стандарты кода и процесс разработки.

## 🏗️ Архитектура разработки

### Принципы архитектуры

1. **Модульность** - каждый компонент имеет четкую ответственность
2. **Расширяемость** - легко добавлять новые функции
3. **Тестируемость** - код покрыт тестами
4. **Документированность** - все функции документированы
5. **Безопасность** - валидация и обработка ошибок

### Структура проекта

```
rag_oozo/
├── backend/                    # Backend приложение
│   ├── app/                   # Основные модули
│   │   ├── api/              # API роутеры
│   │   ├── config.py         # Конфигурация
│   │   ├── schemas.py        # Pydantic модели
│   │   ├── rag_system.py     # Основная RAG система
│   │   └── document_processor.py  # Обработка документов
│   ├── tests/                # Тесты
│   ├── scripts/              # CLI скрипты
│   └── requirements.txt      # Зависимости
├── frontend/                 # Frontend приложение
│   ├── src/                 # Исходный код
│   │   ├── components/      # React компоненты
│   │   ├── services/        # API сервисы
│   │   └── utils/           # Утилиты
│   └── tests/               # Тесты
└── docs/                    # Документация
```

## 🚀 Настройка среды разработки

### Требования

- Python 3.11+
- Node.js 18+
- Docker и Docker Compose
- Git

### Установка зависимостей

#### Backend

```bash
cd backend

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Установка зависимостей для разработки
pip install -r requirements-dev.txt
```

#### Frontend

```bash
cd frontend

# Установка зависимостей
npm install

# Установка зависимостей для разработки
npm install --save-dev @testing-library/react @testing-library/jest-dom
```

### Настройка переменных окружения

```bash
# Создание .env файла
cp env.example .env

# Редактирование .env
nano .env
```

```env
# Development settings
DEBUG=true
LOG_LEVEL=DEBUG
OPENAI_API_KEY=your-api-key
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large
DOCS_PATH=../docs
INDEX_PATH=./data/faiss_index
```

## 📝 Стандарты кода

### Python (Backend)

#### Стиль кода

- PEP 8 для форматирования
- Type hints для всех функций
- Docstrings для всех классов и методов
- Максимальная длина строки: 88 символов (black)

#### Пример кода

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Обработчик документов для RAG системы."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Инициализация обработчика документов.
        
        Args:
            chunk_size: Размер чанка в символах
            chunk_overlap: Перекрытие между чанками
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Обработка документов.
        
        Args:
            documents: Список документов для обработки
            
        Returns:
            Список обработанных чанков
            
        Raises:
            ValueError: Если документы пустые
        """
        if not documents:
            raise ValueError("Список документов не может быть пустым")
        
        logger.info(f"Обработка {len(documents)} документов")
        
        # Логика обработки
        chunks = []
        for doc in documents:
            doc_chunks = self._split_document(doc)
            chunks.extend(doc_chunks)
        
        logger.info(f"Создано {len(chunks)} чанков")
        return chunks
    
    def _split_document(self, document: Dict[str, Any]) -> List[str]:
        """Приватный метод для разбиения документа."""
        # Реализация разбиения
        pass
```

#### Структура файлов

```python
# Импорты стандартной библиотеки
import os
import sys
from typing import List, Dict, Any

# Импорты сторонних библиотек
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Импорты локальных модулей
from .config import settings
from .utils import helpers
```

### JavaScript/React (Frontend)

#### Стиль кода

- ESLint + Prettier для форматирования
- TypeScript для типизации
- Функциональные компоненты с хуками
- PropTypes для валидации

#### Пример кода

```javascript
import React, { useState, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
import { sendMessage } from '../services/api';
import './ChatInterface.css';

/**
 * Интерфейс чата для взаимодействия с RAG системой
 */
const ChatInterface = ({ onMessageSent, className }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Отправка сообщения
   * @param {string} message - Текст сообщения
   */
  const handleSendMessage = useCallback(async (message) => {
    if (!message.trim()) return;

    setIsLoading(true);
    
    try {
      const response = await sendMessage(message, true);
      
      const newMessage = {
        id: Date.now(),
        question: message,
        answer: response.answer,
        sources: response.sources,
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, newMessage]);
      onMessageSent?.(newMessage);
    } catch (error) {
      console.error('Ошибка отправки сообщения:', error);
      // Обработка ошибки
    } finally {
      setIsLoading(false);
    }
  }, [onMessageSent]);

  /**
   * Обработка отправки формы
   */
  const handleSubmit = (e) => {
    e.preventDefault();
    handleSendMessage(inputValue);
    setInputValue('');
  };

  return (
    <div className={`chat-interface ${className || ''}`}>
      <MessageList messages={messages} />
      <MessageInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />
    </div>
  );
};

ChatInterface.propTypes = {
  onMessageSent: PropTypes.func,
  className: PropTypes.string
};

export default ChatInterface;
```

## 🧪 Тестирование

### Backend тестирование

#### Установка зависимостей для тестирования

```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

#### Структура тестов

```
backend/tests/
├── __init__.py
├── conftest.py              # Фикстуры pytest
├── test_api/               # Тесты API
│   ├── test_chat.py
│   └── test_system.py
├── test_rag_system/        # Тесты RAG системы
│   ├── test_rag_system.py
│   └── test_document_processor.py
└── test_integration/       # Интеграционные тесты
    └── test_full_flow.py
```

#### Пример теста

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.rag_system import RAGSystem

client = TestClient(app)


class TestChatAPI:
    """Тесты для чат API."""
    
    def test_query_endpoint_success(self):
        """Тест успешного запроса к API."""
        with patch.object(RAGSystem, 'query') as mock_query:
            mock_query.return_value = {
                'answer': 'Тестовый ответ',
                'sources': []
            }
            
            response = client.post(
                '/api/query',
                json={
                    'question': 'Тестовый вопрос',
                    'return_sources': True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'answer' in data
            assert 'sources' in data
    
    def test_query_endpoint_invalid_request(self):
        """Тест неверного запроса."""
        response = client.post(
            '/api/query',
            json={'invalid': 'data'}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_rag_system_initialization(self):
        """Тест инициализации RAG системы."""
        rag = RAGSystem()
        
        # Мокаем внешние зависимости
        with patch('app.rag_system.HuggingFaceEmbeddings'):
            with patch('app.rag_system.FAISS'):
                rag.initialize()
                assert rag._initialized is True
```

#### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Конкретный тест
pytest tests/test_api/test_chat.py::TestChatAPI::test_query_endpoint_success

# Параллельное выполнение
pytest -n auto
```

### Frontend тестирование

#### Установка зависимостей

```bash
npm install --save-dev @testing-library/react @testing-library/jest-dom jest
```

#### Пример теста

```javascript
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatInterface from '../components/ChatInterface';

// Мокаем API сервис
jest.mock('../services/api', () => ({
  sendMessage: jest.fn()
}));

describe('ChatInterface', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('отображает интерфейс чата', () => {
    render(<ChatInterface />);
    
    expect(screen.getByPlaceholderText(/введите ваш вопрос/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /отправить/i })).toBeInTheDocument();
  });

  test('отправляет сообщение при нажатии кнопки', async () => {
    const mockSendMessage = require('../services/api').sendMessage;
    mockSendMessage.mockResolvedValue({
      answer: 'Тестовый ответ',
      sources: []
    });

    render(<ChatInterface />);
    
    const input = screen.getByPlaceholderText(/введите ваш вопрос/i);
    const button = screen.getByRole('button', { name: /отправить/i });
    
    fireEvent.change(input, { target: { value: 'Тестовый вопрос' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('Тестовый вопрос', true);
    });
  });

  test('отображает ошибку при неудачном запросе', async () => {
    const mockSendMessage = require('../services/api').sendMessage;
    mockSendMessage.mockRejectedValue(new Error('API Error'));

    render(<ChatInterface />);
    
    const input = screen.getByPlaceholderText(/введите ваш вопрос/i);
    const button = screen.getByRole('button', { name: /отправить/i });
    
    fireEvent.change(input, { target: { value: 'Тестовый вопрос' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText(/ошибка/i)).toBeInTheDocument();
    });
  });
});
```

#### Запуск тестов

```bash
# Все тесты
npm test

# Тесты с покрытием
npm test -- --coverage

# Тесты в watch режиме
npm test -- --watch

# Конкретный тест
npm test -- --testNamePattern="отображает интерфейс чата"
```

## 🔄 Процесс разработки

### Git workflow

#### Ветки

- `main` - основная ветка, стабильный код
- `develop` - ветка разработки
- `feature/*` - ветки для новых функций
- `bugfix/*` - ветки для исправления багов
- `hotfix/*` - срочные исправления

#### Коммиты

```bash
# Формат коммитов
feat: добавить поддержку PDF документов
fix: исправить ошибку в обработке больших файлов
docs: обновить документацию API
test: добавить тесты для нового функционала
refactor: рефакторинг модуля обработки документов
```

#### Pull Request процесс

1. Создание ветки для функции
2. Разработка и тестирование
3. Создание Pull Request
4. Code review
5. Исправление замечаний
6. Merge в develop

### CI/CD Pipeline

#### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1

  test-frontend:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Node.js
      uses: actions/setup-node@v2
      with:
        node-version: 18
    
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run tests
      run: |
        cd frontend
        npm test -- --coverage --watchAll=false
    
    - name: Build
      run: |
        cd frontend
        npm run build
```

## 📚 Документация

### Документирование кода

#### Python docstrings

```python
def process_documents(documents: List[Dict[str, Any]], 
                     chunk_size: int = 1000) -> List[str]:
    """
    Обработка документов и разбиение на чанки.
    
    Args:
        documents: Список документов для обработки. Каждый документ
                  должен содержать ключи 'title' и 'content'.
        chunk_size: Размер чанка в символах. По умолчанию 1000.
    
    Returns:
        Список строк, представляющих чанки документов.
    
    Raises:
        ValueError: Если documents пустой или содержит неверные данные.
        ProcessingError: Если произошла ошибка при обработке.
    
    Example:
        >>> docs = [{'title': 'doc1', 'content': 'text...'}]
        >>> chunks = process_documents(docs, chunk_size=500)
        >>> len(chunks)
        2
    """
    pass
```

#### JSDoc для JavaScript

```javascript
/**
 * Отправляет сообщение в RAG систему
 * @param {string} question - Вопрос пользователя
 * @param {boolean} [returnSources=true] - Возвращать ли источники
 * @returns {Promise<Object>} Ответ системы с источниками
 * @throws {Error} При ошибке API
 * 
 * @example
 * const response = await sendMessage('Что такое RAG?', true);
 * console.log(response.answer);
 * console.log(response.sources);
 */
async function sendMessage(question, returnSources = true) {
  // Реализация
}
```

### API документация

#### OpenAPI/Swagger

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="RAG Oozo System API",
    description="API для системы RAG с поиском и генерацией ответов",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    question: str = Field(..., description="Вопрос пользователя")
    return_sources: bool = Field(True, description="Возвращать источники")

class QueryResponse(BaseModel):
    question: str = Field(..., description="Исходный вопрос")
    answer: str = Field(..., description="Ответ системы")
    sources: Optional[List[Source]] = Field(None, description="Источники")

@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Обработка запроса пользователя.
    
    - **question**: Вопрос для обработки
    - **return_sources**: Включить источники в ответ
    
    Returns:
        Ответ системы с опциональными источниками
    """
    pass
```

## 🔧 Инструменты разработки

### Линтеры и форматтеры

#### Python

```bash
# Установка инструментов
pip install black isort flake8 mypy

# Форматирование кода
black app/
isort app/

# Проверка стиля
flake8 app/

# Проверка типов
mypy app/
```

#### JavaScript

```bash
# Установка инструментов
npm install --save-dev eslint prettier @typescript-eslint/parser

# Форматирование кода
npx prettier --write src/

# Проверка стиля
npx eslint src/
```

### Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
```

### IDE настройки

#### VS Code

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

## 🚀 Развертывание для разработки

### Локальное развертывание

```bash
# Запуск в режиме разработки
docker-compose -f docker-compose.dev.yml up --build

# Или локально
cd backend && uvicorn main:app --reload
cd frontend && npm start
```

### Docker Compose для разработки

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  rag-app:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./docs:/app/docs:ro
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    command: uvicorn main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    command: npm start
```

## 📊 Мониторинг разработки

### Метрики качества кода

- Покрытие тестами > 80%
- Количество багов < 5 на 1000 строк
- Время сборки < 5 минут
- Время выполнения тестов < 2 минуты

### Инструменты мониторинга

```bash
# Анализ покрытия
pytest --cov=app --cov-report=html

# Анализ сложности кода
pip install radon
radon cc app/ -a

# Анализ безопасности
pip install bandit
bandit -r app/
```

## 🔄 Версионирование

### Semantic Versioning

- MAJOR.MINOR.PATCH
- MAJOR: несовместимые изменения API
- MINOR: новые функции, совместимые изменения
- PATCH: исправления багов

### Changelog

```markdown
# Changelog

## [1.1.0] - 2024-01-15

### Added
- Поддержка PDF документов
- Новый API эндпоинт для экспорта
- Улучшенная обработка ошибок

### Changed
- Обновлена модель эмбеддингов
- Улучшена производительность поиска

### Fixed
- Исправлена ошибка в обработке больших файлов
- Исправлена проблема с кодировкой

## [1.0.0] - 2024-01-01

### Added
- Базовая RAG функциональность
- Веб-интерфейс
- API эндпоинты
```

---

Этот документ обеспечивает полное руководство по разработке RAG Oozo System с учетом лучших практик и стандартов. 
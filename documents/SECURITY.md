# 🔒 Безопасность RAG Oozo System

## Обзор безопасности

Этот документ описывает меры безопасности, реализованные в RAG Oozo System, а также рекомендации по обеспечению безопасности при развертывании и использовании.

## 🛡️ Принципы безопасности

### 1. Защита данных
- Шифрование данных в покое и при передаче
- Контроль доступа к файлам и API
- Валидация всех входных данных

### 2. Безопасность API
- Аутентификация и авторизация
- Rate limiting
- Защита от атак

### 3. Безопасность инфраструктуры
- Обновление зависимостей
- Мониторинг безопасности
- Резервное копирование

## 🔐 Аутентификация и авторизация

### API ключи

#### OpenAI API ключ

```bash
# Безопасное хранение API ключа
export OPENAI_API_KEY="your-secret-key"

# В .env файле (не коммитить в git)
OPENAI_API_KEY=your-secret-key
```

#### Валидация API ключей

```python
# backend/app/security.py
import re
from typing import Optional

def validate_openai_api_key(api_key: str) -> bool:
    """
    Валидация OpenAI API ключа.
    
    Args:
        api_key: API ключ для проверки
        
    Returns:
        True если ключ валиден, False иначе
    """
    if not api_key:
        return False
    
    # OpenAI API ключи начинаются с sk-
    if not api_key.startswith('sk-'):
        return False
    
    # Проверка длины (обычно 51 символ)
    if len(api_key) != 51:
        return False
    
    # Проверка формата
    pattern = r'^sk-[a-zA-Z0-9]{48}$'
    return bool(re.match(pattern, api_key))

def mask_api_key(api_key: str) -> str:
    """
    Маскирование API ключа для логирования.
    
    Args:
        api_key: API ключ для маскирования
        
    Returns:
        Замаскированный ключ
    """
    if not api_key or len(api_key) < 8:
        return "***"
    
    return f"{api_key[:4]}...{api_key[-4:]}"
```

### JWT токены (для будущих версий)

```python
# backend/app/auth.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверка JWT токена."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## 🚫 Rate Limiting

### Реализация rate limiting

```python
# backend/app/rate_limiter.py
import time
from collections import defaultdict
from fastapi import HTTPException
from typing import Dict, Tuple

class RateLimiter:
    """Простой rate limiter для API."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Проверка, разрешен ли запрос.
        
        Args:
            client_id: Идентификатор клиента (IP или API ключ)
            
        Returns:
            True если запрос разрешен, False иначе
        """
        now = time.time()
        minute_ago = now - 60
        
        # Очистка старых запросов
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]
        
        # Проверка лимита
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False
        
        # Добавление нового запроса
        self.requests[client_id].append(now)
        return True

# Глобальный экземпляр
rate_limiter = RateLimiter()

# Middleware для rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_id = request.client.host
    
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )
    
    response = await call_next(request)
    return response
```

## 🔍 Валидация входных данных

### Pydantic валидация

```python
# backend/app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional
import re

class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Вопрос пользователя"
    )
    return_sources: bool = Field(
        True,
        description="Возвращать ли источники"
    )
    
    @validator('question')
    def validate_question(cls, v):
        """Валидация вопроса."""
        # Проверка на XSS
        if re.search(r'<script|javascript:|on\w+\s*=', v, re.IGNORECASE):
            raise ValueError('Question contains potentially dangerous content')
        
        # Проверка на SQL injection
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE']
        if any(keyword.lower() in v.lower() for keyword in sql_keywords):
            raise ValueError('Question contains SQL keywords')
        
        return v.strip()

class SimilarityRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Запрос для поиска"
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Количество результатов"
    )
    
    @validator('query')
    def validate_query(cls, v):
        """Валидация запроса."""
        if re.search(r'<script|javascript:|on\w+\s*=', v, re.IGNORECASE):
            raise ValueError('Query contains potentially dangerous content')
        return v.strip()
```

### Санитизация данных

```python
# backend/app/sanitizer.py
import html
import re
from typing import Any

def sanitize_text(text: str) -> str:
    """
    Санитизация текста.
    
    Args:
        text: Исходный текст
        
    Returns:
        Санитизированный текст
    """
    # Экранирование HTML
    text = html.escape(text)
    
    # Удаление потенциально опасных паттернов
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # Удаление лишних пробелов
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def sanitize_filename(filename: str) -> str:
    """
    Санитизация имени файла.
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Санитизированное имя файла
    """
    # Удаление опасных символов
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Ограничение длины
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1)
        filename = name[:255-len(ext)-1] + '.' + ext
    
    return filename
```

## 🔐 Шифрование данных

### Шифрование файлов

```python
# backend/app/encryption.py
from cryptography.fernet import Fernet
import base64
import os
from typing import Optional

class FileEncryption:
    """Шифрование файлов для безопасного хранения."""
    
    def __init__(self, key: Optional[str] = None):
        if key:
            self.key = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b'0'))
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def encrypt_file(self, file_path: str) -> bytes:
        """
        Шифрование файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Зашифрованные данные
        """
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return self.cipher.encrypt(data)
    
    def decrypt_file(self, encrypted_data: bytes, output_path: str):
        """
        Расшифровка файла.
        
        Args:
            encrypted_data: Зашифрованные данные
            output_path: Путь для сохранения расшифрованного файла
        """
        decrypted_data = self.cipher.decrypt(encrypted_data)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
    
    def get_key(self) -> str:
        """Получение ключа шифрования."""
        return base64.urlsafe_b64decode(self.key).decode()
```

### Шифрование конфигурации

```python
# backend/app/config_security.py
import os
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode

class SecureConfig:
    """Безопасное хранение конфигурации."""
    
    def __init__(self):
        self.key = os.getenv('ENCRYPTION_KEY')
        if not self.key:
            self.key = Fernet.generate_key()
            print(f"Generated encryption key: {b64encode(self.key).decode()}")
        
        self.cipher = Fernet(self.key)
    
    def encrypt_value(self, value: str) -> str:
        """Шифрование значения."""
        return b64encode(self.cipher.encrypt(value.encode())).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Расшифровка значения."""
        return self.cipher.decrypt(b64decode(encrypted_value)).decode()
    
    def get_secure_env(self, key: str, default: str = None) -> str:
        """Безопасное получение переменной окружения."""
        value = os.getenv(key, default)
        if value and value.startswith('ENC:'):
            return self.decrypt_value(value[4:])
        return value
```

## 🛡️ Защита от атак

### CORS настройки

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
    max_age=3600,
)
```

### Защита от XSS

```python
# backend/app/security_headers.py
from fastapi import Response
from fastapi.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления заголовков безопасности."""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Заголовки безопасности
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### Защита от SQL Injection

```python
# backend/app/database.py
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Безопасное подключение к базе данных."""
    conn = sqlite3.connect('rag_system.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def safe_query(query: str, params: tuple = ()):
    """
    Безопасное выполнение SQL запроса.
    
    Args:
        query: SQL запрос с параметрами
        params: Параметры для запроса
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
```

## 🔍 Аудит и логирование

### Структурированное логирование

```python
# backend/app/audit.py
import logging
import json
from datetime import datetime
from typing import Dict, Any
from fastapi import Request

class SecurityLogger:
    """Логгер для событий безопасности."""
    
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Хендлер для файла
        handler = logging.FileHandler('security.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_request(self, request: Request, user_id: str = None):
        """Логирование запроса."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'method': request.method,
            'url': str(request.url),
            'client_ip': request.client.host,
            'user_agent': request.headers.get('user-agent'),
            'user_id': user_id
        }
        
        self.logger.info(f"Request: {json.dumps(log_data)}")
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Логирование события безопасности."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'details': details
        }
        
        self.logger.warning(f"Security event: {json.dumps(log_data)}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Логирование ошибки."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        self.logger.error(f"Error: {json.dumps(log_data)}")

# Глобальный экземпляр
security_logger = SecurityLogger()
```

### Мониторинг безопасности

```python
# backend/app/security_monitor.py
import time
from collections import defaultdict
from typing import Dict, List

class SecurityMonitor:
    """Мониторинг безопасности системы."""
    
    def __init__(self):
        self.failed_attempts: Dict[str, List[float]] = defaultdict(list)
        self.suspicious_ips: set = set()
        self.blocked_ips: set = set()
    
    def record_failed_attempt(self, ip: str):
        """Запись неудачной попытки."""
        now = time.time()
        self.failed_attempts[ip].append(now)
        
        # Очистка старых попыток (последние 10 минут)
        self.failed_attempts[ip] = [
            attempt for attempt in self.failed_attempts[ip]
            if now - attempt < 600
        ]
        
        # Проверка на подозрительную активность
        if len(self.failed_attempts[ip]) >= 5:
            self.suspicious_ips.add(ip)
        
        # Блокировка при слишком частых попытках
        if len(self.failed_attempts[ip]) >= 10:
            self.blocked_ips.add(ip)
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Проверка, заблокирован ли IP."""
        return ip in self.blocked_ips
    
    def is_ip_suspicious(self, ip: str) -> bool:
        """Проверка, подозрителен ли IP."""
        return ip in self.suspicious_ips
    
    def get_security_report(self) -> Dict[str, Any]:
        """Получение отчета по безопасности."""
        return {
            'suspicious_ips': list(self.suspicious_ips),
            'blocked_ips': list(self.blocked_ips),
            'total_failed_attempts': sum(len(attempts) for attempts in self.failed_attempts.values())
        }

# Глобальный экземпляр
security_monitor = SecurityMonitor()
```

## 🔧 Конфигурация безопасности

### Переменные окружения

```bash
# .env.security
# API ключи
OPENAI_API_KEY=your-secret-key

# Шифрование
ENCRYPTION_KEY=your-encryption-key

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10

# Безопасность
ALLOWED_ORIGINS=http://localhost:3000,https://your-domain.com
MAX_FILE_SIZE=10485760  # 10MB
MAX_QUERY_LENGTH=1000

# Аудит
AUDIT_LOG_LEVEL=INFO
SECURITY_LOG_FILE=security.log
```

### Docker security

```dockerfile
# backend/Dockerfile.secure
FROM python:3.11-slim

# Создание непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий с правильными правами
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Переключение на непривилегированного пользователя
USER appuser

# Рабочая директория
WORKDIR /app

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📋 Чек-лист безопасности

### Развертывание

- [ ] Использование HTTPS
- [ ] Настройка firewall
- [ ] Обновление зависимостей
- [ ] Безопасное хранение секретов
- [ ] Настройка мониторинга

### API безопасность

- [ ] Валидация входных данных
- [ ] Rate limiting
- [ ] CORS настройки
- [ ] Заголовки безопасности
- [ ] Логирование запросов

### Данные

- [ ] Шифрование чувствительных данных
- [ ] Контроль доступа к файлам
- [ ] Резервное копирование
- [ ] Санитизация данных
- [ ] Валидация файлов

### Мониторинг

- [ ] Логирование событий безопасности
- [ ] Мониторинг подозрительной активности
- [ ] Алерты при нарушениях
- [ ] Регулярные аудиты
- [ ] Обновление политик безопасности

## 🚨 Реагирование на инциденты

### Процедура реагирования

1. **Обнаружение** - выявление инцидента безопасности
2. **Оценка** - определение серьезности и масштаба
3. **Сдерживание** - ограничение распространения
4. **Устранение** - ликвидация угрозы
5. **Восстановление** - возврат к нормальной работе
6. **Анализ** - изучение причин и уроков

### Контакты для инцидентов

```bash
# Создание файла с контактами
cat > security-contacts.txt << EOF
Security Team: security@your-company.com
System Administrator: admin@your-company.com
Emergency Contact: +1-555-0123

Incident Response Plan:
1. Document the incident
2. Assess the impact
3. Contain the threat
4. Notify stakeholders
5. Implement fixes
6. Review and improve
EOF
```

---

Этот документ обеспечивает комплексный подход к безопасности RAG Oozo System и помогает защитить систему от различных угроз. 
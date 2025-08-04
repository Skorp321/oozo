# 🚀 Развертывание RAG Oozo System

## Обзор развертывания

Этот документ описывает различные способы развертывания RAG Oozo System в различных средах, от локальной разработки до production.

## 🎯 Способы развертывания

### 1. Локальное развертывание (Docker)
- Простота настройки
- Изоляция окружения
- Быстрый старт

### 2. Production развертывание (Docker Compose)
- Масштабируемость
- Мониторинг
- Высокая доступность

### 3. Облачное развертывание
- AWS, GCP, Azure
- Kubernetes
- Serverless

## 🏠 Локальное развертывание

### Требования

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM
- 10GB свободного места

### Быстрый старт

```bash
# 1. Клонирование репозитория
git clone <repository-url>
cd rag_oozo

# 2. Настройка переменных окружения
cp env.example .env
# Отредактируйте .env и добавьте OPENAI_API_KEY

# 3. Добавление документов
cp your_documents/*.docx docs/

# 4. Запуск системы
./start.sh
```

### Проверка развертывания

```bash
# Проверка состояния
curl http://localhost:8000/health

# Проверка API
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Тест", "return_sources": true}'

# Открытие веб-интерфейса
open http://localhost:3000
```

## 🏭 Production развертывание

### Архитектура production

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Reverse Proxy │    │   Application   │
│   (nginx/HAProxy)│   │   (nginx)       │    │   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Static Files  │
                    │   (React)       │
                    └─────────────────┘
```

### Docker Compose для production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - rag-app
      - frontend
    restart: unless-stopped

  rag-app:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_MODEL_NAME=${EMBEDDING_MODEL_NAME}
      - DOCS_PATH=/app/docs
      - INDEX_PATH=/app/data/faiss_index
    volumes:
      - ./docs:/app/docs:ro
      - rag_data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    volumes:
      - frontend_build:/app/build
    restart: unless-stopped

volumes:
  rag_data:
  frontend_build:
```

### Nginx конфигурация

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server rag-app:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # Frontend
        location / {
            root /var/www/html;
            try_files $uri $uri/ /index.html;
        }

        # API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check
        location /health {
            proxy_pass http://backend;
        }
    }
}
```

### Production Dockerfile

```dockerfile
# backend/Dockerfile.prod
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN useradd --create-home --shell /bin/bash app

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий
RUN mkdir -p data && chown -R app:app /app

# Переключение на пользователя
USER app

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PRODUCTION=true

# Порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## ☁️ Облачное развертывание

### AWS развертывание

#### ECS (Elastic Container Service)

```yaml
# task-definition.json
{
  "family": "rag-oozo",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "rag-app",
      "image": "your-registry/rag-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "OPENAI_API_KEY",
          "value": "your-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rag-oozo",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### EKS (Elastic Kubernetes Service)

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-oozo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-oozo
  template:
    metadata:
      labels:
        app: rag-oozo
    spec:
      containers:
      - name: rag-app
        image: your-registry/rag-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: rag-oozo-service
spec:
  selector:
    app: rag-oozo
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Google Cloud Platform

#### Cloud Run

```bash
# Развертывание в Cloud Run
gcloud run deploy rag-oozo \
  --image gcr.io/your-project/rag-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars OPENAI_API_KEY=your-api-key
```

#### GKE (Google Kubernetes Engine)

```yaml
# gke-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-oozo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-oozo
  template:
    metadata:
      labels:
        app: rag-oozo
    spec:
      containers:
      - name: rag-app
        image: gcr.io/your-project/rag-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

### Azure

#### Azure Container Instances

```bash
# Развертывание в ACI
az container create \
  --resource-group myResourceGroup \
  --name rag-oozo \
  --image your-registry/rag-backend:latest \
  --dns-name-label rag-oozo \
  --ports 8000 \
  --environment-variables OPENAI_API_KEY=your-api-key \
  --memory 4 \
  --cpu 2
```

#### AKS (Azure Kubernetes Service)

```yaml
# aks-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-oozo
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-oozo
  template:
    metadata:
      labels:
        app: rag-oozo
    spec:
      containers:
      - name: rag-app
        image: your-registry/rag-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## 🔧 Конфигурация для production

### Переменные окружения

```bash
# .env.production
OPENAI_API_KEY=your-production-api-key
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large
DOCS_PATH=/app/docs
INDEX_PATH=/app/data/faiss_index
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
OPENAI_MODEL_NAME=gpt-3.5-turbo
MAX_TOKENS=4000
TEMPERATURE=0.7
PRODUCTION=true
LOG_LEVEL=INFO
```

### Мониторинг и логирование

#### Prometheus метрики

```python
# backend/app/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Метрики
REQUEST_COUNT = Counter('rag_requests_total', 'Total requests', ['endpoint'])
REQUEST_DURATION = Histogram('rag_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('rag_active_connections', 'Active connections')
DOCUMENT_COUNT = Gauge('rag_documents_total', 'Total documents')
CHUNK_COUNT = Gauge('rag_chunks_total', 'Total chunks')

# Middleware для сбора метрик
@app.middleware("http")
async def collect_metrics(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_COUNT.labels(endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response
```

#### Grafana дашборд

```json
{
  "dashboard": {
    "title": "RAG Oozo System",
    "panels": [
      {
        "title": "Requests per Second",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(rag_requests_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(rag_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Безопасность

#### SSL/TLS конфигурация

```nginx
# nginx-ssl.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Секреты и ключи

```bash
# Создание секретов в Kubernetes
kubectl create secret generic rag-secrets \
  --from-literal=openai-api-key=your-api-key \
  --from-literal=embedding-model=intfloat/multilingual-e5-large

# Создание ConfigMap
kubectl create configmap rag-config \
  --from-literal=chunk-size=1000 \
  --from-literal=chunk-overlap=200 \
  --from-literal=max-tokens=4000
```

## 📊 Масштабирование

### Горизонтальное масштабирование

```bash
# Масштабирование в Kubernetes
kubectl scale deployment rag-oozo --replicas=5

# Автоматическое масштабирование
kubectl autoscale deployment rag-oozo --cpu-percent=70 --min=2 --max=10
```

### Вертикальное масштабирование

```yaml
# Увеличение ресурсов
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

### Кэширование

#### Redis кэширование

```python
# backend/app/cache.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='redis', port=6379, db=0)

def cache_result(expire_time=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создание ключа кэша
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Попытка получить из кэша
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Выполнение функции
            result = func(*args, **kwargs)
            
            # Сохранение в кэш
            redis_client.setex(cache_key, expire_time, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Использование
@cache_result(expire_time=1800)
def get_similar_documents(query, top_k=5):
    # Логика поиска
    pass
```

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Run tests
      run: |
        docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Build and push images
      run: |
        docker build -t your-registry/rag-backend:${{ github.sha }} ./backend
        docker build -t your-registry/rag-frontend:${{ github.sha }} ./frontend
        docker push your-registry/rag-backend:${{ github.sha }}
        docker push your-registry/rag-frontend:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/rag-oozo rag-app=your-registry/rag-backend:${{ github.sha }}
        kubectl rollout status deployment/rag-oozo
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE/rag-backend:$CI_COMMIT_SHA ./backend
    - docker build -t $CI_REGISTRY_IMAGE/rag-frontend:$CI_COMMIT_SHA ./frontend
    - docker push $CI_REGISTRY_IMAGE/rag-backend:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE/rag-frontend:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - kubectl set image deployment/rag-oozo rag-app=$CI_REGISTRY_IMAGE/rag-backend:$CI_COMMIT_SHA
    - kubectl rollout status deployment/rag-oozo
```

## 📈 Мониторинг и алерты

### Prometheus алерты

```yaml
# prometheus-alerts.yml
groups:
- name: rag-oozo
  rules:
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(rag_request_duration_seconds_bucket[5m])) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is above 2 seconds"

  - alert: HighErrorRate
    expr: rate(rag_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is above 10%"

  - alert: ServiceDown
    expr: up{job="rag-oozo"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "RAG service is down"
      description: "Service has been down for more than 1 minute"
```

### Логирование

```yaml
# fluentd-config.yml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/rag-oozo-*.log
      pos_file /var/log/rag-oozo.log.pos
      tag rag-oozo
      read_from_head true
      <parse>
        @type json
        time_key time
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <match rag-oozo>
      @type elasticsearch
      host elasticsearch
      port 9200
      logstash_format true
      logstash_prefix rag-oozo
      <buffer>
        @type file
        path /var/log/fluentd-buffers/kubernetes.system.buffer
        flush_mode interval
        retry_type exponential_backoff
        flush_interval 5s
        retry_forever false
        retry_max_interval 30
        chunk_limit_size 2M
        queue_limit_length 8
        overflow_action block
      </buffer>
    </match>
```

## 🚨 Disaster Recovery

### Резервное копирование

```bash
# Скрипт резервного копирования
#!/bin/bash

# Резервное копирование FAISS индекса
docker exec rag-backend tar -czf /tmp/faiss-backup-$(date +%Y%m%d).tar.gz /app/data

# Резервное копирование документов
tar -czf docs-backup-$(date +%Y%m%d).tar.gz docs/

# Загрузка в S3
aws s3 cp /tmp/faiss-backup-$(date +%Y%m%d).tar.gz s3://your-backup-bucket/
aws s3 cp docs-backup-$(date +%Y%m%d).tar.gz s3://your-backup-bucket/
```

### Восстановление

```bash
# Скрипт восстановления
#!/bin/bash

# Восстановление FAISS индекса
aws s3 cp s3://your-backup-bucket/faiss-backup-20240101.tar.gz /tmp/
docker exec rag-backend tar -xzf /tmp/faiss-backup-20240101.tar.gz -C /

# Восстановление документов
aws s3 cp s3://your-backup-bucket/docs-backup-20240101.tar.gz /tmp/
tar -xzf /tmp/docs-backup-20240101.tar.gz

# Перезапуск сервисов
docker-compose restart rag-app
```

---

Этот документ обеспечивает полное руководство по развертыванию RAG Oozo System в различных средах с учетом требований production. 
# Настройка подключения к бэкенду

## Текущие настройки

### Бэкенд (backend/main.py)
- **CORS разрешенные адреса:**
  - `http://localhost:3000`
  - `http://localhost:37113` (порт serve)
  - `http://frontend:3000` (Docker)
  - `http://10.77.98.1:3000`
  - `http://10.77.98.1:37113`

### Фронтенд (frontend/)
- **Proxy в package.json:** `http://10.77.160.35:8000`
- **API Base URL в endpoints.js:** `http://10.160.35.1:8000`

## Проверка подключения

### 1. Проверить доступность бэкенда
```bash
curl http://10.77.160.35:8000/
```

### 2. Проверить CORS
```bash
curl -H "Origin: http://10.77.98.1:37113" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS http://10.77.160.35:8000/api/query
```

### 3. Тест API
```bash
curl -X POST http://10.77.160.35:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"question": "test", "return_sources": false}'
```

## Возможные проблемы

1. **Бэкенд не запущен** - запустите бэкенд на порту 8000
2. **Неправильный IP** - проверьте IP адрес бэкенда
3. **Файрвол** - проверьте доступность порта 8000
4. **CORS ошибки** - проверьте настройки в backend/main.py

## Команды для запуска

### Бэкенд
```bash
cd backend
python main.py
```

### Фронтенд (разработка)
```bash
cd frontend
npm start
```

### Фронтенд (продакшн)
```bash
cd frontend
npm run build
npm run serve
``` 
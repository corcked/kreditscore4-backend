# KreditScore4 - Система авторизации через Telegram Bot

## 🏗️ Архитектура проекта

**KreditScore4** - это веб-приложение для оформления займов с авторизацией через Telegram Bot. Проект состоит из трех основных частей:

### Backend API (FastAPI + PostgreSQL)
- **Технологии**: FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **Функции**: API для авторизации, управление пользователями, бизнес-логика
- **Авторизация**: JWT токены с сессиями в БД

### Bot Service (aiogram + Redis)
- **Технологии**: aiogram 3.x, Redis, aiohttp
- **Функции**: Telegram Bot для авторизации, взаимодействие с Backend API
- **Хранилище**: Redis для состояний и временных данных

### Frontend (Next.js + TypeScript)
- **Технологии**: Next.js 14, TypeScript, Tailwind CSS, Axios
- **Функции**: SPA с формой займа, dashboard пользователя, интеграция с Telegram

## 📁 Структура репозиториев

Проект разделен на **ТРИ ОТДЕЛЬНЫХ РЕПОЗИТОРИЯ**:

```
📦 kreditscore4-backend                 📦 kreditscore4-bot                    📦 kreditscore4-frontend
├── app/                                ├── bot/                               ├── app/
│   ├── api/                           │   ├── handlers/                      │   ├── dashboard/
│   │   ├── auth.py                    │   │   ├── start.py                   │   ├── globals.css
│   │   ├── users.py                   │   │   ├── auth.py                    │   ├── layout.tsx
│   │   └── bot.py                     │   │   └── help.py                    │   └── page.tsx
│   ├── models/                        │   ├── services/                      ├── components/
│   │   ├── user.py                    │   │   ├── api_client.py              │   ├── AuthButton.tsx
│   │   └── schemas.py                 │   │   ├── redis_storage.py           │   ├── LoanForm.tsx
│   ├── services/                      │   │   └── auth_service.py            │   └── UserInfo.tsx
│   │   └── auth_service.py            │   ├── middlewares/                   └── lib/
│   ├── database.py                    │   │   ├── logging.py                     ├── api.ts
│   └── main.py                        │   │   └── user_context.py                └── auth.ts
├── alembic/                           │   ├── utils/                         ├── package.json
│   └── versions/                      │   │   ├── keyboards.py               ├── next.config.js
├── requirements.txt                   │   │   └── logging.py                 ├── tailwind.config.js
├── railway.toml                       │   ├── config.py                      ├── railway.json
└── alembic.ini                        │   └── main.py                        └── tsconfig.json
                                       ├── requirements.txt                   
                                       ├── railway.toml                       
                                       ├── Dockerfile
                                       └── README.md
```

### Важно! Особенности репозиториев:
- **Отдельные репозитории**: Backend API, Bot Service и Frontend в разных GitHub репозиториях
- **Причина разделения**: Railway имеет проблемы с деплоем монорепо + независимое развитие сервисов
- **Синхронизация**: Ручная через отдельные push в каждый репозиторий
- **Взаимодействие**: Bot Service общается с Backend API через REST API с аутентификацией

## 🚀 Деплой и инстансы

### Railway Production URLs:
- **Backend API**: https://backend-production-ab79.up.railway.app
- **Bot Service**: https://bot-production-0dcc.up.railway.app
- **Frontend**: https://frontend-production-5830.up.railway.app

### Деплой процесс:
1. **Автоматический деплой**: GitHub webhook → Railway
2. **Backend деплой**: Push в `corcked/kreditscore4-backend` → Railway backend service
3. **Bot деплой**: Push в `corcked/kreditscore4-bot` → Railway bot service
4. **Frontend деплой**: Push в `corcked/kreditscore4-frontend` → Railway frontend service

### Railway сервисы:
```
Project: kreditscore4
├── Environment: production
├── Services:
│   ├── backend (kreditscore4-backend repo)
│   ├── bot (kreditscore4-bot repo)
│   ├── frontend (kreditscore4-frontend repo)
│   ├── PostgreSQL database
│   └── Redis database
```

## 🗄️ База данных

### PostgreSQL на Railway:
- **Тип**: Railway PostgreSQL addon
- **Миграции**: Alembic (автоматически при старте backend)
- **Подключение**: DATABASE_URL environment variable

### Схема БД:
```sql
-- Пользователи
users:
├── id (INTEGER, PRIMARY KEY)
├── telegram_id (BIGINT, UNIQUE)     -- Изменено с INTEGER для поддержки больших Telegram ID
├── phone_number (VARCHAR)
├── first_name (VARCHAR)
├── last_name (VARCHAR)
├── username (VARCHAR)
├── loan_amount (FLOAT)              -- Сумма займа
├── loan_term (INTEGER)              -- Срок займа (месяцы)
├── loan_purpose (VARCHAR)           -- Цель займа
├── monthly_income (FLOAT)           -- Ежемесячный доход
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

-- Сессии авторизации
auth_sessions:
├── id (INTEGER, PRIMARY KEY)
├── token (VARCHAR, JWT токен)
├── user_id (INTEGER, FK → users.id)
├── user_agent (VARCHAR)
├── device_info (VARCHAR, JSON)
├── ip_address (VARCHAR)
├── is_active (BOOLEAN)
├── created_at (TIMESTAMP)
└── expires_at (TIMESTAMP)
```

## 🔐 Система авторизации

### Flow авторизации:
1. **Пользователь** заполняет форму займа на главной странице
2. **Frontend** отправляет данные на `/api/auth/telegram` → получает `auth_token` и `telegram_url`
3. **Пользователь** переходит по ссылке в Telegram Bot
4. **Telegram Bot** просит поделиться номером телефона
5. **Bot Service** через API создает/обновляет пользователя в Backend
6. **Bot** отправляет ссылку возврата: `frontend_url/?auth_token={token}`
7. **Frontend** ловит `auth_token` из URL, вызывает `/api/auth/verify/{token}`
8. **Backend** возвращает JWT `access_token` и данные пользователя
9. **Frontend** сохраняет JWT в cookies, редиректит на dashboard

### API Endpoints:
```typescript
// Авторизация
POST /api/auth/telegram     // Создание auth_token
GET  /api/auth/verify/{token} // Получение JWT access_token
POST /api/auth/logout       // Деактивация сессии

// Bot API (требуют X-Bot-Token заголовок)
POST /api/bot/auth/init     // Инициализация авторизации
POST /api/bot/auth/complete // Завершение авторизации
GET  /api/bot/users/{telegram_id} // Получение пользователя
GET  /api/bot/health        // Health check для bot service

// Пользователи (требуют JWT в заголовке Authorization: Bearer <token>)
GET  /api/users/me          // Данные текущего пользователя
GET  /api/users/me/sessions // Список сессий пользователя
GET  /api/users/me/device-info // Информация об устройстве

// Системные
GET  /                      // Приветствие API
GET  /health               // Health check
```

## 🤖 Telegram Bot

### Настройка бота:
- **Bot Token**: Переменная окружения `TELEGRAM_BOT_TOKEN`
- **Bot Username**: `@kredit_score_bot`
- **Webhook**: Устанавливается на Bot Service (`https://bot-production-0dcc.up.railway.app/webhook`)

### Команды бота:
- `/start {auth_token}` - Начало авторизации с токеном
- **Кнопка "Поделиться номером"** - Отправка контакта для регистрации/авторизации

## 🌍 Environment Variables

### Backend (.env):
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# JWT
JWT_SECRET=your-secret-key-change-in-production

# Bot API Authentication
BOT_API_KEY=shared-secret-key-between-services

# URLs
FRONTEND_URL=https://frontend-production-5830.up.railway.app

# Telegram Bot (для отображения ссылки)
TELEGRAM_BOT_USERNAME=kredit_score_bot
```

### Bot Service (.env):
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_BOT_USERNAME=kredit_score_bot

# Backend API
BACKEND_URL=https://backend-production-ab79.up.railway.app
BOT_API_KEY=shared-secret-key-between-services

# Frontend
FRONTEND_URL=https://frontend-production-5830.up.railway.app

# Redis
REDIS_URL=redis://default:password@host:port

# Webhook
WEBHOOK_URL=https://bot-production-0dcc.up.railway.app
```

### Frontend (.env):
```bash
# API URL
NEXT_PUBLIC_API_URL=https://backend-production-ab79.up.railway.app
```

## 🛠️ Разработка

### Backend setup:
```bash
cd backend/
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Настройка БД
alembic upgrade head

# Запуск
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Bot Service setup:
```bash
cd kreditscore4-bot/
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Запуск
python -m bot.main
```

### Frontend setup:
```bash
cd frontend/
npm install
npm run dev
```

### База данных:
```bash
# Создание миграции
cd backend/
alembic revision --autogenerate -m "описание изменений"

# Применение миграций
alembic upgrade head

# Подключение к Railway PostgreSQL
railway connect postgres
```

## 🚨 Важные технические особенности

### Telegram ID как BIGINT:
⚠️ **Критически важно**: Telegram ID могут быть больше 2^31
```sql
-- Правильно:
telegram_id BIGINT

-- Неправильно:
telegram_id INTEGER
```

### BOT_API_KEY:
- Используется для аутентификации между Bot Service и Backend API
- Должен быть одинаковым в обоих сервисах
- Передается в заголовке `X-Bot-Token`

### PyJWT >= 2.0:
```python
# ✅ Правильно:
from jwt.exceptions import PyJWTError, ExpiredSignatureError

# ❌ Неправильно (старые версии):
jwt.JWTError, jwt.ExpiredSignatureError
```

### CORS настройки:
```python
# Production CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: ограничить для production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐛 Частые проблемы и решения

### 1. Ошибка 500 при авторизации нового пользователя:
```bash
# Проверить тип колонки telegram_id
SELECT data_type FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'telegram_id';

# Если INTEGER, изменить на BIGINT:
ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT;
```

### 2. Bot Service не может подключиться к Backend:
- Проверить `BOT_API_KEY` одинаковый в обоих сервисах
- Проверить `BACKEND_URL` в bot service
- Проверить логи обоих сервисов

### 3. Telegram Bot не отвечает:
- Проверить `TELEGRAM_BOT_TOKEN`
- Проверить webhook URL через Telegram Bot API:
```bash
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```
- Убедиться что webhook указывает на bot service, а не backend

### 4. CORS ошибки:
- Проверить `FRONTEND_URL` в backend env
- Проверить что frontend использует правильный `NEXT_PUBLIC_API_URL`

## 📝 Workflow для изменений

### Изменения в Backend:
```bash
cd backend/
# Внести изменения
git add .
git commit -m "описание изменений"
git push origin main
# Railway автоматически деплоит
```

### Изменения в Bot Service:
```bash
cd kreditscore4-bot/
# Внести изменения
git add .
git commit -m "описание изменений"
git push origin main
# Railway автоматически деплоит
```

### Изменения в Frontend:
```bash
cd frontend/
# Внести изменения  
git add .
git commit -m "описание изменений"
git push origin main
# Railway автоматически деплоит
```

### Изменения в БД:
```bash
cd backend/
# Изменить модели в app/models/user.py
alembic revision --autogenerate -m "описание миграции"
git add .
git commit -m "добавить миграцию: описание"
git push origin main
# Railway применит миграцию автоматически при деплое
```

## 🤖 Контекст для AI моделей

### При работе с Claude/GPT упомянуть:
1. **Архитектура**: Три отдельных репозитория и сервиса
2. **Деплой**: Railway с автоматическим деплоем через GitHub
3. **База**: PostgreSQL на Railway с Alembic миграциями
4. **Авторизация**: Telegram Bot → Backend API → JWT tokens → Dashboard
5. **Bot Service**: Отдельный сервис с Redis для состояний
6. **Аутентификация между сервисами**: BOT_API_KEY в заголовке X-Bot-Token
7. **Telegram ID**: Используется BIGINT, не INTEGER

### Полезные команды для диагностики:
```bash
# Логи Railway
railway logs

# Подключение к БД
railway connect postgres

# Статус сервисов
railway status

# Переменные окружения
railway variables
```

### Структура API ответов:
```typescript
// POST /api/auth/telegram
{
  "auth_token": "string",
  "telegram_url": "https://t.me/kredit_score_bot?start=token"
}

// GET /api/auth/verify/{token}  
{
  "access_token": "jwt_token",
  "token_type": "bearer", 
  "user": { ... },
  "session": { ... },
  "device_info": { ... }
}

// POST /api/bot/auth/complete
{
  "success": true,
  "frontend_return_url": "https://frontend-production-5830.up.railway.app/?auth_token=...",
  "user_id": 123
}
```

---

**Последнее обновление**: Январь 2025  
**Статус проекта**: ✅ Production Ready  
**Основные фичи**: ✅ Авторизация через Telegram ✅ JWT сессии ✅ Dashboard ✅ Форма займа ✅ Bot Service 
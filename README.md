# KreditScore4 Backend

Python FastAPI приложение для авторизации через Telegram Bot.

## 🚀 Технологии

- **FastAPI** - веб-фреймворк
- **python-telegram-bot** - Telegram Bot API
- **SQLAlchemy** - ORM для PostgreSQL
- **JWT** - аутентификация
- **PostgreSQL** - база данных

## 🔗 Связанные репозитории

- Frontend: [kreditscore4-frontend](../kreditscore4-frontend)

## 🛠 Локальная разработка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Переменные окружения
cp .env.example .env
# Настройте: DATABASE_URL, TELEGRAM_BOT_TOKEN, JWT_SECRET

# Запуск
uvicorn app.main:app --reload
```

## 🚂 Деплой на Railway

1. **Создайте новый проект в Railway**
2. **Подключите этот репозиторий**
3. **Добавьте PostgreSQL сервис**
4. **Настройте переменные окружения:**
   - `DATABASE_URL` - из Railway PostgreSQL
   - `TELEGRAM_BOT_TOKEN` - токен от @BotFather
   - `JWT_SECRET` - случайная строка
   - `WEBHOOK_URL` - https://your-app.railway.app/webhook

5. **Настройте Telegram webhook:**
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app.railway.app/webhook"}'
```

## 📋 API Endpoints

- `GET /` - health check
- `POST /api/auth/telegram` - создание токена авторизации
- `GET /api/auth/verify/{token}` - проверка токена
- `POST /api/auth/logout` - выход
- `GET /api/users/me` - данные пользователя
- `GET /api/users/me/sessions` - активные сессии

## 🔧 Структура проекта

```
app/
├── api/              # API роутеры
├── bot/              # Telegram Bot
├── models/           # SQLAlchemy модели
├── database.py       # Настройка БД
└── main.py          # FastAPI приложение
```

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
from telegram import Update

from app.api import auth, users
from app.database import engine, Base
from app.bot.bot import telegram_bot

# Загружаем переменные окружения
load_dotenv()

app = FastAPI(
    title="KreditScore4 API",
    description="API для авторизации через Telegram Bot",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.on_event("startup")
async def startup_event():
    """Создание таблиц в базе данных при запуске"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Запуск Telegram бота с webhook
    webhook_url = os.getenv("RAILWAY_STATIC_URL", "localhost:8000")
    if not webhook_url.startswith("http"):
        webhook_url = f"https://{webhook_url}"
    
    # Устанавливаем webhook
    try:
        await telegram_bot.application.bot.set_webhook(url=f"{webhook_url}/webhook")
        print(f"✅ Telegram webhook установлен: {webhook_url}/webhook")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook эндпоинт для получения сообщений от Telegram"""
    try:
        # Получаем данные от Telegram
        json_data = await request.json()
        
        # Создаем Update объект
        update = Update.de_json(json_data, telegram_bot.application.bot)
        
        # Обрабатываем update
        await telegram_bot.application.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"❌ Ошибка обработки webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/")
async def root():
    return {"message": "KreditScore4 API готов к работе!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

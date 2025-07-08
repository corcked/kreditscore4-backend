from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine
import json

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
# Получаем разрешенные origins из переменных окружения
allowed_origins = [
    "http://localhost:3000",  # Для разработки
    "https://frontend-production-5830.up.railway.app",  # Production frontend
    "https://kreditscore4-frontend-production.up.railway.app",  # Альтернативный URL
    # Добавляем без www версии на всякий случай
    "https://www.frontend-production-5830.up.railway.app",
]

# Добавляем дополнительные origins из переменных окружения если есть
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

print(f"🔧 CORS настройки: allow_origins=['*'], allow_credentials=False (временно)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Временно для отладки
    allow_credentials=False,  # Временно отключено
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.on_event("startup")
async def startup_event():
    """Применение миграций и создание таблиц при запуске"""
    try:
        # Применяем Alembic миграции
        print("🔄 Применяем миграции...")
        alembic_cfg = Config("alembic.ini")
        
        # Получаем DATABASE_URL и конвертируем для sync SQLAlchemy
        database_url = os.getenv("DATABASE_URL")
        if database_url and "postgresql+asyncpg://" in database_url:
            sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
        
        command.upgrade(alembic_cfg, "head")
        print("✅ Миграции применены успешно!")
        
    except Exception as e:
        print(f"⚠️ Ошибка при применении миграций: {e}")
        print("🔄 Пробуем создать таблицы через create_all...")
        
        # Fallback: создаем таблицы обычным способом
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы созданы через create_all")
    
    # Настройка Telegram Bot webhook
    try:
        print("🤖 Настраиваем Telegram Bot webhook...")
        
        # Получаем URL приложения из переменных окружения
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            # Пытаемся определить URL из Railway переменных
            railway_static_url = os.getenv("RAILWAY_STATIC_URL")
            if railway_static_url:
                webhook_url = f"https://{railway_static_url}"
            else:
                print("⚠️ WEBHOOK_URL не найден в переменных окружения")
                return
        
        # Запускаем бота и устанавливаем webhook
        await telegram_bot.application.initialize()
        await telegram_bot.application.start()
        
        full_webhook_url = f"{webhook_url}/webhook"
        await telegram_bot.application.bot.set_webhook(url=full_webhook_url)
        print(f"✅ Telegram Bot webhook установлен: {full_webhook_url}")
        
    except Exception as e:
        print(f"⚠️ Ошибка при настройке Telegram Bot: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Корректное завершение работы бота"""
    try:
        print("🤖 Останавливаем Telegram Bot...")
        await telegram_bot.application.stop()
        print("✅ Telegram Bot остановлен")
    except Exception as e:
        print(f"⚠️ Ошибка при остановке Telegram Bot: {e}")

@app.get("/")
async def root():
    return {"message": "KreditScore4 API готов к работе!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Обработка webhook от Telegram"""
    try:
        # Получаем данные от Telegram
        update_data = await request.json()
        
        # Импортируем Update из telegram для создания объекта обновления
        from telegram import Update
        
        # Создаем объект Update из полученных данных
        update = Update.de_json(update_data, telegram_bot.application.bot)
        
        # Обрабатываем обновление
        await telegram_bot.application.process_update(update)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Ошибка обработки webhook: {e}")
        return {"status": "error", "message": str(e)} 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine

from app.api import auth, users
from app.database import engine, Base

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

@app.get("/")
async def root():
    return {"message": "KreditScore4 API готов к работе!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 
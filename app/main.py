from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

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
    """Создание таблиц в базе данных при запуске"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"message": "KreditScore4 API готов к работе!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 
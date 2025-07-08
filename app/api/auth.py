import os
import secrets
from jose import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, AuthSession
from app.models.schemas import AuthTokenRequest, AuthTokenResponse, VerifyTokenResponse
from app.bot.handlers import get_user_by_auth_token

router = APIRouter()

# Получаем секретный ключ для JWT
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 дней

# Временное хранилище для данных займа
# В продакшене лучше использовать Redis
loan_data_storage = {}

def get_bot_username():
    """Получение username бота (нужно настроить в переменных окружения)"""
    return os.getenv("TELEGRAM_BOT_USERNAME", "kreditscore4_bot")

async def save_loan_data(auth_token: str, loan_data: dict):
    """Сохранение данных займа по токену"""
    loan_data_storage[auth_token] = loan_data

async def get_loan_data(auth_token: str) -> dict:
    """Получение данных займа по токену"""
    return loan_data_storage.get(auth_token, {})

async def remove_loan_data(auth_token: str):
    """Удаление данных займа после использования"""
    if auth_token in loan_data_storage:
        del loan_data_storage[auth_token]

@router.post("/telegram", response_model=AuthTokenResponse)
async def create_auth_token(
    request_data: AuthTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание токена авторизации для Telegram
    Возвращает auth_token и ссылку на Telegram Bot
    """
    
    # Генерируем уникальный токен
    auth_token = secrets.token_urlsafe(32)
    
    # Сохраняем данные займа для использования после авторизации
    await save_loan_data(auth_token, {
        "loan_amount": request_data.loan_amount,
        "loan_term": request_data.loan_term,
        "loan_purpose": request_data.loan_purpose,
        "monthly_income": request_data.monthly_income
    })
    
    # Получаем username бота
    bot_username = get_bot_username()
    
    # Формируем ссылку на Telegram Bot с токеном
    telegram_url = f"https://t.me/{bot_username}?start={auth_token}"
    
    return AuthTokenResponse(
        auth_token=auth_token,
        telegram_url=telegram_url
    )

@router.get("/verify/{token}", response_model=VerifyTokenResponse)
async def verify_auth_token(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Проверка токена авторизации
    Если токен валиден, создает сессию и возвращает данные пользователя
    """
    
    # Получаем ID пользователя по токену из Telegram Bot
    user_id = await get_user_by_auth_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=404,
            detail="Токен авторизации не найден или истек"
        )
    
    # Ищем пользователя в базе данных
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Пользователь не найден"
        )
    
    # Получаем данные займа из временного хранилища
    loan_data = await get_loan_data(token)
    
    # Обновляем данные пользователя данными займа
    if loan_data:
        user.loan_amount = loan_data.get("loan_amount")
        user.loan_term = loan_data.get("loan_term")
        user.loan_purpose = loan_data.get("loan_purpose")
        user.monthly_income = loan_data.get("monthly_income")
        
        # Сохраняем обновленные данные
        await db.commit()
        await db.refresh(user)
        
        # Удаляем использованные данные займа
        await remove_loan_data(token)
    
    # Получаем информацию о устройстве
    user_agent = request.headers.get("user-agent", "")
    device_info = extract_device_info(user_agent)
    
    # Создаем JWT токен
    jwt_payload = {
        "user_id": user.id,
        "telegram_id": user.telegram_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    }
    jwt_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Создаем сессию в базе данных
    session = AuthSession(
        token=jwt_token,
        user_id=user.id,
        user_agent=user_agent,
        device_info=str(device_info),
        ip_address=get_client_ip(request),
        expires_at=datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    # Удаляем использованный auth_token
    from app.bot.handlers import auth_tokens
    if token in auth_tokens:
        del auth_tokens[token]
    
    return VerifyTokenResponse(
        access_token=jwt_token,
        token_type="bearer",
        user=user,
        session=session,
        device_info=device_info
    )

@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Выход из системы - деактивация сессии"""
    
    # Получаем JWT токен из заголовков
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Токен не предоставлен")
    
    jwt_token = auth_header.split(" ")[1]
    
    try:
        # Декодируем JWT
        payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        # Деактивируем сессию
        result = await db.execute(
            select(AuthSession).where(
                AuthSession.token == jwt_token,
                AuthSession.user_id == user_id,
                AuthSession.is_active == True
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            session.is_active = False
            await db.commit()
        
        return {"message": "Успешный выход из системы"}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

def extract_device_info(user_agent: str) -> dict:
    """Извлечение информации об устройстве из User-Agent"""
    
    device_info = {
        "user_agent": user_agent,
        "browser": "Unknown",
        "os": "Unknown",
        "device": "Unknown"
    }
    
    user_agent_lower = user_agent.lower()
    
    # Определение браузера
    if "chrome" in user_agent_lower:
        device_info["browser"] = "Chrome"
    elif "firefox" in user_agent_lower:
        device_info["browser"] = "Firefox"
    elif "safari" in user_agent_lower:
        device_info["browser"] = "Safari"
    elif "edge" in user_agent_lower:
        device_info["browser"] = "Edge"
    
    # Определение ОС
    if "windows" in user_agent_lower:
        device_info["os"] = "Windows"
    elif "mac" in user_agent_lower:
        device_info["os"] = "macOS"
    elif "linux" in user_agent_lower:
        device_info["os"] = "Linux"
    elif "android" in user_agent_lower:
        device_info["os"] = "Android"
    elif "ios" in user_agent_lower:
        device_info["os"] = "iOS"
    
    # Определение типа устройства
    if "mobile" in user_agent_lower or "android" in user_agent_lower:
        device_info["device"] = "Mobile"
    elif "tablet" in user_agent_lower or "ipad" in user_agent_lower:
        device_info["device"] = "Tablet"
    else:
        device_info["device"] = "Desktop"
    
    return device_info

def get_client_ip(request: Request) -> str:
    """Получение IP адреса клиента"""
    
    # Проверяем заголовки прокси
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fallback на client.host
    return request.client.host if request.client else "unknown"

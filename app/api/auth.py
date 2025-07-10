import os
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, AuthSession
from app.models.schemas import AuthTokenRequest, AuthTokenResponse, VerifyTokenResponse
from app.bot.handlers import get_user_by_auth_token
from app.services.auth_service import auth_token_service

router = APIRouter()

# Получаем секретный ключ для JWT
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 7 дней

def get_bot_username():
    """Получение username бота (нужно настроить в переменных окружения)"""
    return os.getenv("TELEGRAM_BOT_USERNAME", "kreditscore4_bot")

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
    
    # Создаем токен с данными займа если они есть
    loan_data = None
    if any([request_data.loan_amount, request_data.loan_term, 
            request_data.loan_purpose, request_data.monthly_income]):
        loan_data = {
            "loan_amount": request_data.loan_amount,
            "loan_term": request_data.loan_term,
            "loan_purpose": request_data.loan_purpose,
            "monthly_income": request_data.monthly_income
        }
    
    auth_token = auth_token_service.create_auth_token(loan_data)
    
    # Получаем username бота
    bot_username = get_bot_username()
    
    # Формируем ссылку на Telegram Bot с токеном
    telegram_url = f"https://t.me/{bot_username}?start={auth_token}"
    
    return AuthTokenResponse(
        auth_token=auth_token,
        telegram_url=telegram_url
    )


@router.post("/telegram/v2", response_model=AuthTokenResponse)
async def create_auth_token_v2(
    request_data: AuthTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание токена авторизации для Telegram (новая версия)
    Использует Bot API вместо прямого взаимодействия с временными хранилищами
    """
    import aiohttp
    import os
    
    # Подготовка данных для Bot API
    loan_data = {
        "loan_amount": request_data.loan_amount,
        "loan_term": request_data.loan_term,
        "loan_purpose": request_data.loan_purpose,
        "monthly_income": request_data.monthly_income
    }
    
    # Вызов Bot API для создания токена
    bot_api_key = os.getenv("BOT_API_KEY", "default-bot-api-key-change-in-production")
    base_url = request.url.scheme + "://" + request.url.netloc
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/bot/auth/init",
                headers={"X-Bot-Token": bot_api_key},
                json=loan_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return AuthTokenResponse(
                        auth_token=data["auth_token"],
                        telegram_url=data["telegram_url"]
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create auth token via Bot API"
                    )
    except Exception as e:
        # Fallback to old method if Bot API fails
        loan_data_for_service = {k: v for k, v in loan_data.items() if v is not None}
        auth_token = auth_token_service.create_auth_token(loan_data_for_service if loan_data_for_service else None)
        
        bot_username = get_bot_username()
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
    
    # Удаляем использованный auth_token и данные займа
    auth_token_service.cleanup_auth_token(token)
    
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
        
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except PyJWTError:
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
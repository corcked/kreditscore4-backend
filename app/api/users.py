import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, AuthSession
from app.models.schemas import User as UserSchema
from app.api.auth import JWT_SECRET, JWT_ALGORITHM

router = APIRouter()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """
    Dependency для получения текущего пользователя из JWT токена
    """
    
    # Получаем JWT токен из заголовков
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Токен не предоставлен")
    
    jwt_token = auth_header.split(" ")[1]
    
    try:
        # Декодируем JWT
        payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")
        
        # Проверяем активную сессию
        session_result = await db.execute(
            select(AuthSession).where(
                AuthSession.token == jwt_token,
                AuthSession.user_id == user_id,
                AuthSession.is_active == True
            )
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=401, detail="Сессия не активна")
        
        # Получаем пользователя
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        return user
        
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Токен истек")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации о текущем пользователе
    """
    return current_user

@router.get("/me/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение всех активных сессий пользователя
    """
    
    result = await db.execute(
        select(AuthSession).where(
            AuthSession.user_id == current_user.id,
            AuthSession.is_active == True
        ).order_by(AuthSession.created_at.desc())
    )
    sessions = result.scalars().all()
    
    # Формируем ответ с информацией о сессиях
    sessions_data = []
    for session in sessions:
        session_info = {
            "id": session.id,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "device_info": session.device_info
        }
        sessions_data.append(session_info)
    
    return {
        "user": current_user,
        "sessions": sessions_data,
        "total_sessions": len(sessions_data)
    }

@router.get("/me/device-info")
async def get_device_info(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Получение информации об устройстве и браузере пользователя
    """
    
    from app.api.auth import extract_device_info, get_client_ip
    
    user_agent = request.headers.get("user-agent", "")
    device_info = extract_device_info(user_agent)
    
    return {
        "user": current_user,
        "current_session": {
            "ip_address": get_client_ip(request),
            "device_info": device_info,
            "headers": {
                "user_agent": user_agent,
                "accept_language": request.headers.get("accept-language", ""),
                "accept_encoding": request.headers.get("accept-encoding", ""),
                "connection": request.headers.get("connection", ""),
            }
        }
    } 
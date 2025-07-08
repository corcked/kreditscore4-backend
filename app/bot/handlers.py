import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.models.user import User
from app.models.schemas import UserCreate

logger = logging.getLogger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Проверяем, есть ли токен авторизации в аргументах
    auth_token = None
    if context.args:
        auth_token = context.args[0]
    
    logger.info(f"User {user.id} started bot with token: {auth_token}")
    
    if auth_token:
        # Пользователь пришел для авторизации
        await handle_auth_start(update, context, auth_token)
    else:
        # Обычный старт бота
        welcome_message = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Это бот для авторизации в KreditScore4.\n"
            "Для получения доступа к вашим данным, "
            "воспользуйтесь кнопкой авторизации на сайте."
        )
        await update.message.reply_text(welcome_message)

async def handle_auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE, auth_token: str) -> None:
    """Обработка начала авторизации"""
    user = update.effective_user
    
    # Сохраняем токен в контексте для дальнейшего использования
    context.user_data['auth_token'] = auth_token
    
    # Проверяем, есть ли пользователь в базе
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == user.id))
        existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Пользователь уже существует, запрашиваем подтверждение
        message = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Вы уже зарегистрированы в системе.\n"
            "Для завершения авторизации поделитесь своим контактом."
        )
    else:
        # Новый пользователь
        message = (
            f"Добро пожаловать, {user.first_name}! 👋\n\n"
            "Для авторизации в KreditScore4 нам нужен ваш номер телефона.\n"
            "Пожалуйста, поделитесь своим контактом, нажав кнопку ниже."
        )
    
    # Создаем клавиатуру с кнопкой для отправки контакта
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(message, reply_markup=keyboard)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик получения контакта пользователя"""
    user = update.effective_user
    contact = update.message.contact
    auth_token = context.user_data.get('auth_token')
    
    if not auth_token:
        await update.message.reply_text(
            "❌ Токен авторизации не найден. Пожалуйста, начните авторизацию заново через сайт.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Проверяем, что контакт принадлежит самому пользователю
    if contact.user_id != user.id:
        await update.message.reply_text(
            "❌ Пожалуйста, поделитесь своим собственным контактом.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    try:
        async with async_session() as session:
            # Ищем существующего пользователя
            result = await session.execute(select(User).where(User.telegram_id == user.id))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                # Обновляем данные существующего пользователя
                existing_user.phone_number = contact.phone_number
                existing_user.username = user.username
                existing_user.first_name = user.first_name
                existing_user.last_name = user.last_name
                await session.commit()
                logger.info(f"Updated user {user.id} with phone {contact.phone_number}")
                db_user = existing_user
            else:
                # Создаем нового пользователя
                new_user = User(
                    telegram_id=user.id,
                    phone_number=contact.phone_number,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                logger.info(f"Created new user {user.id} with phone {contact.phone_number}")
                db_user = new_user
            
            # Получаем и сохраняем данные займа в пользователе
            loan_data = await get_loan_data(auth_token)
            if loan_data:
                db_user.loan_amount = loan_data.get("loan_amount")
                db_user.loan_term = loan_data.get("loan_term") 
                db_user.loan_purpose = loan_data.get("loan_purpose")
                db_user.monthly_income = loan_data.get("monthly_income")
                await session.commit()
                logger.info(f"Updated user {user.id} with loan data: {loan_data}")
            
            # Сохраняем связь токена с пользователем в Redis или временном хранилище
            await save_auth_token(auth_token, db_user.id)
            
            success_message = (
                "✅ Отлично! Ваши данные получены.\n\n"
                "📱 Номер телефона сохранен\n"
                "🔄 Возвращайтесь на сайт для завершения авторизации\n\n"
                "Вы можете закрыть этот чат."
            )
            
            await update.message.reply_text(
                success_message,
                reply_markup=ReplyKeyboardRemove()
            )
            
    except Exception as e:
        logger.error(f"Error saving user data: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении данных. Попробуйте еще раз.",
            reply_markup=ReplyKeyboardRemove()
        )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        "🤖 KreditScore4 Bot\n\n"
        "Этот бот используется для авторизации на сайте KreditScore4.\n\n"
        "📱 Как это работает:\n"
        "1. Нажмите кнопку авторизации на сайте\n"
        "2. Вас перенаправит в этот бот\n"
        "3. Поделитесь своим контактом\n"
        "4. Вернитесь на сайт\n\n"
        "❓ Если у вас есть вопросы, обратитесь в поддержку."
    )
    await update.message.reply_text(help_text)

# Временное хранилище для токенов авторизации
# В продакшене лучше использовать Redis
auth_tokens = {}

# Временное хранилище для данных займа
loan_data_storage = {}

async def save_auth_token(token: str, user_id: int) -> None:
    """Сохранение токена авторизации"""
    auth_tokens[token] = user_id
    logger.info(f"Saved auth token for user {user_id}")

async def save_loan_data(token: str, loan_data: dict) -> None:
    """Сохранение данных займа по токену"""
    loan_data_storage[token] = loan_data
    logger.info(f"Saved loan data for token {token}: {loan_data}")

async def get_loan_data(token: str) -> dict:
    """Получение данных займа по токену"""
    return loan_data_storage.get(token, {})

async def get_user_by_auth_token(token: str) -> int:
    """Получение ID пользователя по токену"""
    return auth_tokens.get(token) 
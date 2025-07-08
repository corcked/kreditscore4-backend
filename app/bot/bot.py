import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.bot.handlers import start_handler, contact_handler, help_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        
        # Создание приложения
        self.application = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрация всех обработчиков команд и сообщений"""
        
        # Команды
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        
        # Обработка контактов (номера телефона)
        self.application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
        
        # Обработчик ошибок
        self.application.add_error_handler(self._error_handler)
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ошибок"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    async def start_webhook(self, webhook_url: str, port: int = 8000):
        """Запуск бота с webhook"""
        await self.application.bot.set_webhook(url=f"{webhook_url}/webhook")
        await self.application.start()
        logger.info(f"Bot started with webhook: {webhook_url}/webhook")
    
    async def start_polling(self):
        """Запуск бота с polling (для разработки)"""
        await self.application.run_polling()
        logger.info("Bot started with polling")
    
    async def stop(self):
        """Остановка бота"""
        await self.application.stop()
        logger.info("Bot stopped")

# Глобальный экземпляр бота
telegram_bot = TelegramBot() 
# 🚨 План отключения старого Telegram бота и активации нового

## 📊 Анализ текущей ситуации

### ✅ Что уже выполнено:
- ✅ Новый Bot Service полностью разработан в `kreditscore4-bot/`
- ✅ Backend API endpoints для бота созданы (`/api/bot/*`)
- ✅ Старый telegram bot код в `backend/app/main.py` **ЗАКОММЕНТИРОВАН**
- ✅ Webhook endpoint `/webhook` в backend **ОТКЛЮЧЕН**
- ✅ Интеграционное тестирование пройдено

### ⚠️ Проблемы, которые нужно устранить:
- ❌ Директория `backend/app/bot/` все еще **СУЩЕСТВУЕТ**
- ❌ В `backend/requirements.txt` есть `python-telegram-bot==20.8`
- ❌ Возможно есть `TELEGRAM_BOT_TOKEN` в backend service Railway
- ❌ Webhook в Telegram может указывать на старый backend URL
- ❌ Два бота могут конфликтовать друг с другом

## 🎯 Пошаговый план действий

---

### **Шаг 1: Аудит Railway переменных окружения**

#### 1.1 Backend Service
1. Зайти в **Railway Dashboard** → **Backend Service** → **Variables**
2. Проверить и **УДАЛИТЬ** следующие переменные (если есть):
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_BOT_USERNAME` 
   - `WEBHOOK_URL`
3. **Оставить только** переменные, нужные для API:
   - `DATABASE_URL`
   - `JWT_SECRET`
   - `BOT_API_KEY`
   - `FRONTEND_URL`

#### 1.2 Bot Service
1. Зайти в **Railway Dashboard** → **Bot Service** → **Variables**
2. **Убедиться что присутствуют**:
   - `TELEGRAM_BOT_TOKEN` - токен бота
   - `TELEGRAM_BOT_USERNAME` - имя бота (без @)
   - `BACKEND_API_URL` - URL backend API
   - `BOT_API_KEY` - ключ для аутентификации с backend
   - `REDIS_URL` - URL Redis сервиса
   - `FRONTEND_URL` - URL фронтенда
   - `WEBHOOK_URL` - URL webhook для бота

---

### **Шаг 2: Проверка статуса bot service**

#### 2.1 Проверить деплой
```bash
# Проверить health endpoint bot service
curl https://bot-production-xxxx.up.railway.app/health
# Ожидаемый ответ: {"status": "ok", "service": "kreditscore4-bot"}
```

#### 2.2 Проверить логи
1. Railway Dashboard → Bot Service → Logs
2. Убедиться что нет критических ошибок
3. Проверить что bot запустился успешно

---

### **Шаг 3: Проверка Telegram webhook**

#### 3.1 Узнать текущий webhook
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

#### 3.2 Анализ результата
- ✅ **ПРАВИЛЬНО**: `"url": "https://bot-production-xxxx.up.railway.app/webhook"`
- ❌ **НЕПРАВИЛЬНО**: `"url": "https://backend-production-ab79.up.railway.app/webhook"`
- ❌ **НЕПРАВИЛЬНО**: `"url": ""` (пустой webhook)

#### 3.3 Установка правильного webhook (если нужно)
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://bot-production-xxxx.up.railway.app/webhook"}'
```

---

### **Шаг 4: Очистка backend кода**

#### 4.1 Удаление старых файлов бота
```bash
# Перейти в директорию backend
cd backend/

# Удалить всю директорию bot
rm -rf app/bot/

# Проверить что директория удалена
ls -la app/
```

#### 4.2 Обновление requirements.txt
**Удалить строку:**
```
python-telegram-bot==20.8
```

**Итоговый requirements.txt должен содержать:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
pydantic==2.5.0
PyJWT==2.8.0
python-multipart==0.0.6
alembic==1.13.1
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

#### 4.3 Проверка импортов в main.py
Убедиться что в `backend/app/main.py` закомментирован импорт:
```python
# from app.bot.bot import telegram_bot  ✅ ДОЛЖЕН БЫТЬ ЗАКОММЕНТИРОВАН
```

---

### **Шаг 5: Пересборка backend service**

#### 5.1 Коммит изменений
```bash
git add .
git commit -m "🧹 Remove old telegram bot code and dependencies"
git push origin main
```

#### 5.2 Пересборка в Railway
1. Railway Dashboard → Backend Service → Settings
2. **Manual Deploy** или **Redeploy**
3. Дождаться успешной сборки
4. Проверить логи на отсутствие ошибок

---

### **Шаг 6: Тестирование системы**

#### 6.1 Проверка backend API
```bash
# Health check
curl https://backend-production-ab79.up.railway.app/health
# Ожидаемый ответ: {"status": "healthy"}

# Проверка bot API
curl -X POST https://backend-production-ab79.up.railway.app/api/bot/auth/init \
  -H "X-Bot-Token: your-bot-api-key" \
  -H "Content-Type: application/json" \
  -d '{"loan_amount": 50000}'
```

#### 6.2 Проверка bot service
```bash
# Health check
curl https://bot-production-xxxx.up.railway.app/health
# Ожидаемый ответ: {"status": "ok", "service": "kreditscore4-bot"}
```

#### 6.3 Полное тестирование авторизации
1. Зайти на фронтенд: https://frontend-production-5830.up.railway.app
2. Заполнить форму займа
3. Нажать "Получить займ через Telegram"
4. Проверить что открывается правильный бот
5. Поделиться контактом в боте
6. Вернуться на сайт по ссылке из бота
7. Проверить что авторизация прошла успешно

---

### **Шаг 7: Мониторинг и валидация**

#### 7.1 Проверка логов (первые 24 часа)
- Railway Dashboard → Bot Service → Logs
- Railway Dashboard → Backend Service → Logs
- Отслеживать ошибки и производительность

#### 7.2 Проверка webhook активности
```bash
# Через несколько часов проверить статистику
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
# Поле "pending_update_count" должно быть 0
```

#### 7.3 Тестирование edge cases
- Повторная авторизация существующего пользователя
- Авторизация с пустыми данными займа
- Истекший auth_token
- Неправильный номер телефона

---

## 🚨 План отката (если что-то пойдет не так)

### Быстрый откат webhook:
```bash
# Вернуть webhook на backend (временно)
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://backend-production-ab79.up.railway.app/webhook"}'
```

### Восстановление backend bot кода:
```bash
# Восстановить из git history
git revert <commit-hash>
git push origin main
```

---

## ✅ Критерии успеха

### После выполнения всех шагов:
- [ ] Backend service не содержит Telegram bot переменных
- [ ] Директория `backend/app/bot/` удалена
- [ ] `python-telegram-bot` удален из requirements.txt
- [ ] Webhook указывает на bot service URL
- [ ] Bot service отвечает на health check
- [ ] Полный flow авторизации работает
- [ ] Старый бот не отвечает на сообщения
- [ ] Новый бот корректно обрабатывает команды

---

## 📋 Чеклист выполнения

### Подготовка:
- [ ] Сделать backup текущих Railway переменных
- [ ] Убедиться что bot service развернут
- [ ] Проверить доступ к Railway Dashboard

### Выполнение:
- [ ] **Шаг 1**: Аудит Railway переменных
- [ ] **Шаг 2**: Проверка bot service  
- [ ] **Шаг 3**: Проверка Telegram webhook
- [ ] **Шаг 4**: Очистка backend кода
- [ ] **Шаг 5**: Пересборка backend
- [ ] **Шаг 6**: Тестирование системы
- [ ] **Шаг 7**: Мониторинг

### Завершение:
- [ ] Документирование изменений
- [ ] Обновление README.md
- [ ] Уведомление команды о завершении миграции

---

## 🔗 Полезные ссылки

- **Backend Service**: https://backend-production-ab79.up.railway.app
- **Bot Service**: https://bot-production-xxxx.up.railway.app  
- **Frontend**: https://frontend-production-5830.up.railway.app
- **Railway Dashboard**: https://railway.app/dashboard
- **Telegram Bot API**: https://core.telegram.org/bots/api

---

**⚠️ Внимание**: Выполняйте шаги последовательно и проверяйте результат каждого шага перед переходом к следующему. 
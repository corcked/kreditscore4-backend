#!/usr/bin/env python3
"""
Скрипт для применения миграции к производственной базе данных
"""
import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Ошибка: DATABASE_URL не найден в переменных окружения")
    print("Установите переменную окружения DATABASE_URL:")
    print("export DATABASE_URL='postgresql://username:password@host:port/database'")
    sys.exit(1)

# Конвертируем async URL в sync для применения миграции
sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

def apply_migration():
    """Применяем миграцию для добавления полей займа"""
    try:
        # Создаем подключение к базе данных
        engine = create_engine(sync_url)
        
        print("🔗 Подключение к базе данных...")
        
        with engine.connect() as conn:
            # Проверяем, существуют ли уже колонки
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('loan_amount', 'loan_term', 'loan_purpose', 'monthly_income')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            
            if len(existing_columns) == 4:
                print("✅ Все колонки займа уже существуют в базе данных")
                return
            
            print(f"📋 Найдено {len(existing_columns)} из 4 колонок займа")
            print("🔄 Добавляем недостающие колонки...")
            
            # Добавляем недостающие колонки
            if 'loan_amount' not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN loan_amount FLOAT"))
                print("✅ Добавлена колонка loan_amount")
            
            if 'loan_term' not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN loan_term INTEGER"))
                print("✅ Добавлена колонка loan_term")
            
            if 'loan_purpose' not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN loan_purpose VARCHAR(100)"))
                print("✅ Добавлена колонка loan_purpose")
            
            if 'monthly_income' not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN monthly_income FLOAT"))
                print("✅ Добавлена колонка monthly_income")
            
            # Коммитим изменения
            conn.commit()
            
            print("🎉 Миграция успешно применена!")
            print("📊 Проверяем результат...")
            
            # Проверяем результат
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('loan_amount', 'loan_term', 'loan_purpose', 'monthly_income')
                ORDER BY column_name
            """))
            
            print("\n📋 Колонки займа в таблице users:")
            for row in result.fetchall():
                print(f"  • {row[0]}: {row[1]}")
            
    except OperationalError as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при применении миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Применяем миграцию для добавления полей займа...")
    apply_migration() 
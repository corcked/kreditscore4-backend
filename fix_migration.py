#!/usr/bin/env python3
"""
Скрипт для принудительного применения миграции займа к production базе
"""
import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def main():
    """Применяем миграцию для добавления полей займа"""
    
    # Получаем DATABASE_URL из переменных окружения Railway
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ Ошибка: DATABASE_URL не найден")
        return
    
    # Конвертируем async URL в sync
    sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        print("🔗 Подключение к production базе данных...")
        engine = create_engine(sync_url)
        
        with engine.connect() as conn:
            print("✅ Подключение успешно!")
            
            # Проверяем существующие колонки
            print("🔍 Проверяем существующие колонки...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('loan_amount', 'loan_term', 'loan_purpose', 'monthly_income')
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            print(f"📋 Найдено {len(existing_columns)} из 4 колонок займа: {existing_columns}")
            
            if len(existing_columns) == 4:
                print("✅ Все колонки займа уже существуют!")
                return
            
            # Применяем транзакцию
            with conn.begin() as trans:
                print("🔄 Добавляем недостающие колонки...")
                
                if 'loan_amount' not in existing_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN loan_amount FLOAT"))
                    print("  ✅ Добавлена loan_amount")
                
                if 'loan_term' not in existing_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN loan_term INTEGER"))
                    print("  ✅ Добавлена loan_term")
                
                if 'loan_purpose' not in existing_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN loan_purpose VARCHAR(100)"))
                    print("  ✅ Добавлена loan_purpose")
                
                if 'monthly_income' not in existing_columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN monthly_income FLOAT"))
                    print("  ✅ Добавлена monthly_income")
                
                print("💾 Коммитим изменения...")
            
            # Проверяем результат
            print("🔍 Проверяем результат...")
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
            
            print("\n🎉 Миграция успешно применена!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return

if __name__ == "__main__":
    main() 
import sqlite3
import os

DB_NAME = "task_planner.db"

def execute_sql_file_simple(db_path, sql_file):
    if not os.path.exists(sql_file):
        print(f"❌ Файл {sql_file} не найден!")
        return False
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        cursor.executescript(sql_script)

        conn.commit()
        conn.close()
        
        print(f"✅ Скрипт {sql_file} выполнен успешно!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🚀 СОЗДАНИЕ БАЗЫ ДАННЫХ")
    print("="*50)

    print("\n📝 Выполнение schema.sql...")
    if execute_sql_file_simple(DB_NAME, "schema.sql"):
        print("✅ Структура создана")
    else:
        print("❌ Ошибка")
        exit()

    print("\n📝 Выполнение data.sql...")
    if execute_sql_file_simple(DB_NAME, "data.sql"):
        print("✅ Данные добавлены")
    else:
        print("❌ Ошибка")
        exit()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n📋 Таблицы в БД:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"   📊 {table[0]}: {count} записей")
    
    conn.close()
    print("\n✅ БД готова!")
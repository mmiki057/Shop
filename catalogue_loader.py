# catalogue_loader.py
import sqlite3

#Добавление колонки цен в базу бинов
def add_price_column_to_bins():
    # Используйте корректное имя вашей базы данных (замените payments.db, если оно другое)
    conn = sqlite3.connect("payment_info.db")
    cursor = conn.cursor()
    try:
        # Добавление колонки `price` в таблицу `bins`, если она еще не существует
        cursor.execute("""
            ALTER TABLE bins ADD COLUMN price REAL DEFAULT 0.0
        """)
        conn.commit()
        print("Колонка 'price' успешно добавлена в таблицу 'bins'.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Колонка 'price' уже существует.")
        else:
            print(f"Произошла ошибка: {e}")
    finally:
        conn.close()

# Функция проверки уникальности данных
def is_payment_info_unique(geo, bank, number, date, cvc):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE geo = ? AND bank = ? AND number = ? AND date = ? AND cvc = ?", 
                       (geo, bank, number, date, cvc))
        record = cursor.fetchone()
    return record is None

# Функция загрузки информации о платежах из файла
def load_payment_info_from_file():
    try:
        with open("payments.txt", "r", encoding="utf-8") as file:
            content = file.read().strip()

        with sqlite3.connect('payment_info.db') as conn:
            cursor = conn.cursor()

            records = content.split(";")

            for record in records:
                try:
                    geo, bank, number, date, cvc = record.split(",")
                    bin_code = number[:6]  # Первые шесть цифр номера карты

                    # Проверяем наличие BIN'а в таблице bins
                    cursor.execute("SELECT id FROM bins WHERE bin = ?", (bin_code,))
                    bin_row = cursor.fetchone()
                    if not bin_row:
                        # Если BIN еще не существует, добавляем его
                        cursor.execute("INSERT INTO bins (bin) VALUES (?)", (bin_code,))
                        conn.commit()
                        bin_id = cursor.lastrowid
                        print(f"Добавлен новый BIN: {bin_code} с ID {bin_id}")
                    else:
                        bin_id = bin_row[0]

                    # Проверяем уникальность записи в payments
                    cursor.execute("""
                    SELECT * FROM payments WHERE geo = ? AND bank = ? AND number = ? AND date = ? AND cvc = ?
                    """, (geo, bank, number, date, cvc))
                    if not cursor.fetchone():
                        cursor.execute("""
                        INSERT INTO payments (geo, bank, number, date, cvc)
                        VALUES (?, ?, ?, ?, ?)
                        """, (geo, bank, number, date, cvc))
                        conn.commit()
                        print(f"Запись для номера карты {number} успешно добавлена!")
                    else:
                        print(f"Запись для номера карты {number} уже существует!")
                except ValueError:
                    print(f"Ошибка при обработке записи: {record}")
    except FileNotFoundError:
        print("Файл с данными не найден.")
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

# Получение уникальных гео
def get_unique_geos():
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT geo FROM payments")
        geos = [row[0] for row in cursor.fetchall()]
    return geos

# Получение уникальных бинов
def get_unique_bins():
    conn = sqlite3.connect("payment_info.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, SUBSTR(bin, 1, 6), price FROM bins
    """)
    bins = cursor.fetchall()
    conn.close()
    return bins

# Инициализация таблицы бинов
def initialize_bins_table():
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bin TEXT UNIQUE
        )
        """)
        conn.commit()

# Поиск по BIN
def search_by_bin(bin_prefix):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT geo, SUBSTR(number, 1, 6) as bin FROM payments WHERE number LIKE ?", (f"{bin_prefix}%",))
        records = cursor.fetchall()
    return records

# Поиск по GEO
def search_by_geo(geo):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT geo, SUBSTR(number, 1, 6) as bin FROM payments WHERE geo = ?", (geo,))
        records = cursor.fetchall()
    return records

#получение всех бинов
def get_all_bins():
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bins")
        bins = cursor.fetchall()
    return bins

#поиск бина по айди
def get_bin_by_id(bin_id):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT bin FROM bins WHERE id = ?", (bin_id,))
        bin_row = cursor.fetchone()
    return bin_row[0] if bin_row else None

#инициализация таблицы карт
def initialize_payments_table():
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            geo TEXT NOT NULL,
            bank TEXT NOT NULL,
            number TEXT NOT NULL,
            date TEXT NOT NULL,
            cvc TEXT NOT NULL
        )
        """)
        conn.commit()

#Назначение цены к BIN ID
def set_bin_price(bin_id, price):
    conn = sqlite3.connect("payment_info.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bins
        SET price = ?
        WHERE id = ?
    """, (price, bin_id))
    conn.commit()
    conn.close()
    print(f"Цена {price} установлена для BIN с ID {bin_id}")

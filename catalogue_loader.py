# catalogue_loader.py
import sqlite3
import time

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

# Функция загрузки информации о картах из файла
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
        SELECT id, bin, price FROM bins
    """)
    bins = cursor.fetchall()
    conn.close()
    return bins

# Инициализация таблицы бинов
# Функция для инициализации таблицы `bins`
def initialize_bins_table():
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bin TEXT UNIQUE,
            price REAL DEFAULT 0.0
        )
        """)
        conn.commit()

# Поиск по BIN
def search_by_bin(bin_prefix):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, geo, bank, number, date, cvc, price 
            FROM payments 
            WHERE number LIKE ?
        """, (f"{bin_prefix}%",))
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

def update_user_balance(user_id, new_balance):
    conn = sqlite3.connect('payment_info.db')  # Подключение к вашей базе данных
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()
#Назначение цены к BIN ID
def set_bin_price(bin_id, price):
    conn = sqlite3.connect("payment_info.db")
    cursor = conn.cursor()
    try:
        # Получаем bin по ID
        cursor.execute("SELECT * FROM bins WHERE id = ?", (bin_id,))
        bin_row = cursor.fetchone()

        if bin_row:
            # bin_row — это кортеж, а не строка, нужно обращаться к элементам через индексы.
            print(bin_row)  # Для отладки
            cursor.execute("UPDATE bins SET price = ? WHERE id = ?", (price, bin_id))
            conn.commit()
            print(f"Цена {price} успешно назначена BIN с ID {bin_id}.")
        else:
            print(f"BIN с ID {bin_id} не найден.")
    except Exception as e:
        print(f"Ошибка при назначении цены: {e}")
    finally:
        conn.close()

def update_user_balance(user_id, new_balance):
    conn = sqlite3.connect('payment_info.db')  # Подключение к вашей базе данных
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()
    
def buy_card(user_id, search_type, search_value, price):

    """
    Функция для покупки карты пользователем.

    :param user_id: ID пользователя
    :param search_type: Тип поиска ("bin" или "geo")
    :param search_value: Значение для поиска (например, BIN или GEO)
    :param price: Стоимость карты
    :return: Сообщение о результате операции
    """
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        # Проверяем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "Пользователь не найден. Зарегистрируйтесь в системе."
        
        user_balance = user[0]
        if user_balance < price:
            return "Недостаточно средств на балансе."

        # Выбираем карту для покупки
        if search_type == "bin":
            cursor.execute(
                "SELECT id, geo, bank, number, date, cvc FROM payments WHERE number LIKE ? LIMIT 1",
                (f"{search_value}%",)
            )
        elif search_type == "geo":
            cursor.execute(
                "SELECT id, geo, bank, number, date, cvc FROM payments WHERE geo = ? LIMIT 1",
                (search_value,)
            )
        else:
            return "Неверный тип поиска. Выберите 'bin' или 'geo'."
        
        card = cursor.fetchone()
        if not card:
            return "Карта с указанными параметрами не найдена."

        card_id, geo, bank, number, date, cvc = card

        # Списываем средства с баланса пользователя
        cursor.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id)
        )

        # Удаляем карту из базы
        cursor.execute("DELETE FROM payments WHERE id = ?", (card_id,))

        conn.commit()

        # Возвращаем данные карты пользователю
        return (
            f"Покупка успешна! Вот данные карты:\n"
            f"ГЕО: {geo}\n"
            f"Банк: {bank}\n"
            f"Номер: {number}\n"
            f"Дата: {date}\n"
            f"CVC: {cvc}"
        )

def register_transaction(user_id, item_details):

    # Логика сохранения информации о покупке
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (user_id, item_details, date) VALUES (?, ?, ?)",
            (user_id, item_details, time.strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()

def check_table_structure():

    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(bins);")
        columns = cursor.fetchall()
        for column in columns:
            print(column)
        
def get_item_by_id(item_id):

    """
    Функция для получения информации о товаре (карте) по его ID.

    :param item_id: ID товара (или карты)
    :return: Словарь с информацией о карте или None, если карта не найдена
    """
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        # Извлекаем информацию о карте по ID
        cursor.execute("""
            SELECT payments.id, payments.geo, payments.bank, payments.number, payments.date, payments.cvc, bins.price
            FROM payments
            JOIN bins ON SUBSTR(payments.number, 1, 6) = bins.bin
            WHERE payments.id = ?
        """, (item_id,))
        item = cursor.fetchone()

    if item:
        # Возвращаем данные о карте в виде словаря
        return {
            'id': item[0],
            'geo': item[1],
            'bank': item[2],
            'number': item[3],
            'date': item[4],
            'cvc': item[5],
            'price': item[6]
        }
    else:
        return None
    
def get_user_balance(user_id):
    """
    Функция для получения баланса пользователя по его ID.
    
    :param user_id: ID пользователя
    :return: Баланс пользователя или None, если пользователь не найден
    """
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        
        # Извлекаем баланс пользователя по его ID
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    
    if user:
        return user[0]  # Возвращаем баланс пользователя
    else:
        return None  # Пользователь не найден

def proceed_with_purchase(user_id, item):
    """
    Процесс покупки товара пользователем.
    
    :param user_id: ID пользователя
    :param item: Информация о товаре (например, карта)
    """
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        # Получаем баланс пользователя
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "Пользователь не найден. Зарегистрируйтесь в системе."
        
        user_balance = user[0]
        if user_balance < item['price']:
            return "Недостаточно средств на балансе."

        # Списываем средства с баланса пользователя
        cursor.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?", (item['price'], user_id)
        )

        # Удаляем карту из базы (или помечаем её как купленную)
        cursor.execute("DELETE FROM payments WHERE id = ?", (item['id'],))

        conn.commit()

        # Логируем транзакцию
        register_transaction(user_id, item)

        return (
            f"Покупка успешна! Вот данные карты:\n"
            f"ГЕО: {item['geo']}\n"
            f"Банк: {item['bank']}\n"
            f"Номер: {item['number']}\n"
            f"Дата: {item['date']}\n"
            f"CVC: {item['cvc']}"
        )

def add_price_column_to_bins():
    conn = sqlite3.connect("payment_info.db")
    cursor = conn.cursor()
    try:
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

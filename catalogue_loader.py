# catalogue_loader.py
import sqlite3
import time
from oplata import get
import datetime
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
def is_payment_info_unique(geo, bank, number, date, code):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM items WHERE geo = ? AND bank = ? AND number = ? AND date = ? AND code = ?", 
                       (geo, bank, number, date, code))
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
                print(record)
                try:
                    geo, bank, number, date, code = record.split(",")
                    bin_code = number[:6]  # Первые шесть цифр номера карты

                    # Проверяем наличие BIN'а в таблице bins
                    cursor.execute("SELECT id FROM bins WHERE bin = ?", (bin_code,))
                    bin_row = cursor.fetchone()
                    if not bin_row:
                        cursor.execute("INSERT INTO bins (bin) VALUES (?)", (bin_code,))
                        conn.commit()
                        bin_id = cursor.lastrowid
                        print(f"Добавлен новый BIN: {bin_code} с ID {bin_id}")
                    else:
                        bin_id = bin_row[0]

                    # Проверяем уникальность записи в items
                    cursor.execute("""
                        SELECT * FROM items 
                        WHERE geo = ? AND bank = ? AND number = ? AND date = ? AND code = ? AND bin = ?
                    """, (geo, bank, number, date, code, bin_code))

                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO items (geo, bank, number, date, code, bin) 
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (geo, bank, number, date, code, bin_code))
                        conn.commit()
                        print(f"✅ Запись для номера карты {number} с BIN {bin_code} успешно добавлена!")
                    else:
                        print(f"ℹ️ Запись для номера карты {number} с BIN {bin_code} уже существует!")

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
        cursor.execute("SELECT DISTINCT geo FROM items")
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
            SELECT id, geo, bank, number, date, cvc
            FROM items 
            WHERE number LIKE ?
        """, (f"{bin_prefix}%",))
        records = cursor.fetchall()
    return records

# Поиск по GEO
def search_by_geo(geo):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT geo, SUBSTR(number, 1, 6) as bin FROM items WHERE geo = ?", (geo,))
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
    conn = sqlite3.connect('payments_info.db')  # Подключение к вашей базе данных
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
                "SELECT id, geo, bank, number, date, cvc FROM items WHERE number LIKE ? LIMIT 1",
                (f"{search_value}%",)
            )
        elif search_type == "geo":
            cursor.execute(
                "SELECT id, geo, bank, number, date, cvc FROM items WHERE geo = ? LIMIT 1",
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
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        print(f"Запрос на получение товара с ID: {item_id}")  # Логируем запрос
        cursor.execute("""
            SELECT payments.id, payments.geo, payments.bank, payments.number, payments.date, payments.cvc, bins.price
            FROM payments
            JOIN bins ON SUBSTR(payments.number, 1, 6) = bins.bin
            WHERE payments.id = ? 
        """, (item_id,))
        item = cursor.fetchone()

        if item:
            print(f"Найден товар: {item}")
        else:
            print("Товар не найден.")

    if item:
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
        cursor.execute("DELETE FROM items WHERE id = ?", (item['id'],))

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
    
# Функция для получения количества товаров по BIN
def get_items_count_by_bin(bin_prefix):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        # Логируем запрос для отладки
        print(f"Запрос на получение количества товаров для BIN: {bin_prefix}")

        cursor.execute("""
            SELECT COUNT(*) 
            FROM items
            WHERE bin LIKE ?
        """, (f"{bin_prefix}%",))

        count = cursor.fetchone()[0]  # Получаем первое значение из результата
        print(f"Найдено {count} единиц товаров для BIN {bin_prefix}")  # Логируем результат

    return count

def get_bins_data():
    """
    Извлекает BIN, ID и Price из таблицы bins.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect('payment_info.db') as conn:
            cursor = conn.cursor()

            # Выполняем запрос
            cursor.execute("SELECT id, bin, price FROM bins")
            bins_data = cursor.fetchall()

            # Форматируем вывод
            result = [{"id": row[0], "bin": row[1], "price": row[2]} for row in bins_data]
            return result
    except sqlite3.Error as e:
        print(f"Ошибка базы данных: {e}")
        return []

# load_payment_info_from_file()
# get_items_count_by_bin(444111)

def get_items_by_bin(bin_prefix):
    """
    Получает список записей из таблицы items по указанному BIN-префиксу.
    """
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        # Логируем запрос для отладки
        print(f"Запрос для BIN-префикса: {bin_prefix}")

        # Выполняем запрос, чтобы найти записи из таблицы items, которые соответствуют BIN-префиксу
        cursor.execute("""
            SELECT i.id, i.geo, i.bank, i.number, i.date, i.code, b.price 
            FROM items i
            JOIN bins b ON i.bin = b.bin
            WHERE b.bin LIKE ?
        """, (f"{bin_prefix}%",))

        items = cursor.fetchall()

        print(f"Найдено {len(items)} записей для BIN-префикса {bin_prefix}")  # Лог результата

    # Формируем список словарей с результатами
    return [
        {
            "id": item[0],
            "geo": item[1],
            "bank": item[2],
            "number": item[3],
            "date": item[4],
            "code": item[5],
            "price": item[6]
        }
        for item in items
    ]


connection = sqlite3.connect('payment_info.db')  # Укажите путь к вашей базе данных
cursor = connection.cursor()

# Создание таблицы, если она не существует
cursor.execute('''
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    geo TEXT,
    bank TEXT,
    number TEXT,
    date TEXT,
    code TEXT,
    price INTEGER,
    bin INTEGER
);
''')

# Сохраняем изменения и закрываем соединение
connection.commit()
connection.close()

def check_payments_data():
    # Подключаемся к базе данных
    conn = sqlite3.connect('payment_info.db')
    cursor = conn.cursor()
    
    # Запрос на получение первых 10 записей из таблицы payments
    cursor.execute("SELECT id, number FROM payments LIMIT 10;")
    records = cursor.fetchall()
    
    # Печатаем результат
    print("Данные о первых 10 записях:")
    for record in records:
        print(record)
    
    conn.close()

def check_bin_match(bin_id):
    # Подключаемся к базе данных
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        
        # Получаем все записи из таблицы bins для указанного bin_id
        cursor.execute("SELECT bin, price FROM bins WHERE id = ?", (bin_id,))
        bin_row = cursor.fetchone()

        # Если BIN не найден в таблице bins
        if not bin_row:
            return f"BIN с ID {bin_id} не найден."

        bin_value, bin_price = bin_row
        print(f"Проверка BIN: {bin_value}, Цена: {bin_price}")

        # Выполняем запрос для поиска карт с этим BIN в таблице payments
        cursor.execute("""
            SELECT payments.id, payments.number, bins.bin, bins.price
            FROM payments
            JOIN bins ON SUBSTR(payments.number, 1, 6) = bins.bin
            WHERE bins.bin = ?
        """, (bin_value,))
        
        # Извлекаем все найденные записи
        items = cursor.fetchall()
        
        if items:
            print("Найденные товары для BIN:")
            for item in items:
                print(f"ID: {item[0]}, Номер карты: {item[1]}, BIN: {item[2]}, Цена: {item[3]}")
        else:
            return f"Товары с BIN {bin_value} не найдены."
        
def check_item_availability(bin_code):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()

        # Логирование, чтобы убедиться, что передаем правильный BIN
        print(f"Проверяем наличие товара для BIN: {bin_code}")

        # Ищем товары по BIN
        cursor.execute("""
            SELECT payments.id AS payment_id, payments.number, bins.bin, bins.price
            FROM payments
            JOIN bins ON SUBSTR(payments.number, 1, 6) = bins.bin
            WHERE bins.bin = ?
        """, (bin_code,))
        
        items = cursor.fetchall()

        # Логируем найденные товары
        if items:
            print("Найденные товары для BIN:")
            for item in items:
                print(f"ID: {item[0]}, Номер карты: {item[1]}, BIN: {item[2]}, Цена: {item[3]}")
        else:
            print("Товары для BIN не найдены.")

        # Проверяем наличие товара с ценой > 0
        available_items = [item for item in items if item[3] > 0]
        if available_items:
            print(f"Найдено {len(available_items)} товаров с ценой больше 0.")
            return True  # Есть товары с ценой
        else:
            print("Товары с ценой больше 0 не найдены.")
            return False  # Нет товаров с ценой больше 0
        
# Создание таблицы sold_items
def create_sold_items_table():
   """Создает таблицу для проданных карт."""
   with sqlite3.connect('payment_info.db') as conn:
       cursor = conn.cursor()
       cursor.execute('''
           CREATE TABLE if not exists sold_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, -- Уникальный идентификатор записи
                card_number TEXT NOT NULL,           -- Номер карты
                expiration_date TEXT NOT NULL,       -- Срок действия карты (месяц/год)
                cvv TEXT NOT NULL,                   -- CVV код
                sale_date TEXT NOT NULL,             -- Дата продажи (формат YYYY-MM-DD)
                sale_price REAL NOT NULL             -- Цена продажи
            );
       ''')
       conn.commit()
       print("✅ Таблица 'sold_items' успешно создана!")


#Добавление карты в таблицу sold_items и удаление из items
# def sell_item(item_id):
#    """
#    Удаляет карту из таблицы 'items'.
#    """
#    try:
#        conn = sqlite3.connect('payment_info.db')
#        cursor = conn.cursor()#

#        # Проверяем, существует ли товар в таблице items
#        cursor.execute("""
#           SELECT id 
#            FROM items 
#            WHERE id = ?
#        """, (item_id,))
#        item = cursor.fetchone()#

#        if not item:
#            print(f"❌ Карта с ID {item_id} не найдена в каталоге.")
#            return#

# #        Удаляем запись из items
#        cursor.execute("""
#            DELETE FROM items WHERE id = ?
#        """, (item_id,))

#        conn.commit()
#        print(f"✅ Карта с ID {item_id} успешно удалена из каталога.")

#    except sqlite3.Error as e:
#        print(f"❌ Ошибка при удалении карты: {e}")
#    finally:
#        conn.close()

def sell_item(item_id):
    """
    Переносит карту из таблицы 'items' в таблицу 'sold_items' и удаляет из 'items', включая цену из таблицы 'bins'.
    """
    try:
        conn = sqlite3.connect('payment_info.db')
        cursor = conn.cursor()

        # Инициализация таблицы sold_items, если её нет
        create_sold_items_table()

        # Получаем данные о товаре из таблицы items
        cursor.execute("""
            SELECT number, date, code 
            FROM items 
            WHERE id = ?
        """, (item_id,))
        item = cursor.fetchone()

        if not item:
            print(f"❌ Карта с ID {item_id} не найдена в каталоге.")
            return

        number, date, code = item

        # Получаем цену из таблицы bins
        cursor.execute("""
            SELECT price 
            FROM bins 
            WHERE id = ?
        """, (item_id,))
        bin_row = cursor.fetchone()
        price = bin_row[0] if bin_row else 0.0

        # Переносим запись в sold_items
        cursor.execute("""
            INSERT INTO sold_items (card_number, expiration_date, cvv, sale_date, sale_price) 
            VALUES (?, ?, ?, datetime('now'), ?)
        """, (number, date, code, price))

        # Удаляем запись из items
        cursor.execute("""
            DELETE FROM items WHERE id = ?
        """, (item_id,))

        conn.commit()
        print(f"✅ Карта с ID {item_id} успешно продана и удалена из каталога.")

    except sqlite3.Error as e:
        print(f"❌ Ошибка при обработке покупки: {e}")
    finally:
        conn.close()

initialize_bins_table()
initialize_payments_table()

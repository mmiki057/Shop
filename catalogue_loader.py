# catalogue_loader.py
import sqlite3

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
                    if is_payment_info_unique(geo, bank, number, date, cvc):
                        cursor.execute("""INSERT INTO payments (geo, bank, number, date, cvc)
                                          VALUES (?, ?, ?, ?, ?)""", 
                                       (geo, bank, number, date, cvc))
                        conn.commit()
                        print(f"Запись '{geo}, {bank}' успешно добавлена!")
                    else:
                        print(f"Запись '{geo}, {bank}' уже существует!")
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
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT SUBSTR(number, 1, 6) as bin FROM payments")
        bins = [row[0] for row in cursor.fetchall()]
    return bins

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

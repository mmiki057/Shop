import sqlite3

def get_item_details(item_id):
    # Соединение с базой данных (здесь используется SQLite как пример)
    conn = sqlite3.connect('payment_info.db')  # Укажите путь к вашей базе данных
    cursor = conn.cursor()
    
    # Запрос для получения данных о товаре по item_id
    cursor.execute("SELECT geo, bank, number, expiry_date, code FROM items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()
    
    conn.close()

    if item:
        # Преобразуем кортеж в словарь
        return {
            "geo": item[0],
            "bank": item[1],
            "number": item[2],
            "expiry_date": item[3],
            "code": item[4],
        }
    else:
        return None
    
def get_item_price(item_id):
    # Соединение с базой данных (укажите путь к вашей базе данных)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Запрос для получения цены товара по item_id
    cursor.execute("SELECT price FROM items WHERE item_id = ?", (item_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0]  # Возвращаем цену товара
    else:
        return None  # Если товар не найден, возвращаем None

def purchase_item(item_id):
    # Здесь можно добавить логику покупки товара.
    # Например, обновление базы данных, списание средств, подтверждение покупки и т.д.
    print(f"Товар с ID {item_id} был куплен.")
    # Можно также отправить сообщение пользователю, что покупка успешна:
    return "Покупка успешна!"  # или отправить сообщение через Telegram API

def get():
    pass

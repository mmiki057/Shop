import sqlite3

def get_item_details(bin_code):
    """
    Получает список записей из таблицы items по указанному BIN-коду.
    """
    # Соединение с базой данных
    conn = sqlite3.connect('payment_info.db')  # Укажите путь к вашей базе данных
    cursor = conn.cursor()
    
    try:
        # Запрос для получения данных о товарах по BIN-коду
        cursor.execute("""
            SELECT geo, bank, number, date, code, id 
            FROM items 
            WHERE bin = ?
        """, (bin_code,))
        items = cursor.fetchall()

        # Преобразуем список кортежей в список словарей
        result = [
            {
                "geo": item[0],
                "bank": item[1],
                "number": item[2],
                "date": item[3],
                "code": item[4],
                "id": item[5]
            }
            for item in items
        ]

        return result[0]
    finally:
        conn.close()
    
def get_item_price(item_id):
    # Соединение с базой данных (укажите путь к вашей базе данных)
    conn = sqlite3.connect('payment_info.db')
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

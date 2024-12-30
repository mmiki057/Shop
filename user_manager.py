import sqlite3

# Инициализация таблицы пользователей
def initialize_users_table():
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            registered_at TEXT
        )
        """)
        conn.commit()


def update_user_balance(user_id, amount):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

# Регистрация нового пользователя
def register_user(user_id, username):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
            conn.commit()
            return f"Пользователь {username} (ID: {user_id}) зарегистрирован."
        else:
            return f"Пользователь {username} (ID: {user_id}) уже существует."

# Получение данных профиля пользователя
def get_user_profile(user_id):
    with sqlite3.connect('payment_info.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, balance, registered_at FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    return user

def increase_user_balance(user_id, amount):
    connection = sqlite3.connect('payment_info.db')
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    connection.commit()
    connection.close()
    return cursor.rowcount > 0

initialize_users_table()

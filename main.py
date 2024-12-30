import telebot
import time
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from catalogue_loader import load_payment_info_from_file, get_unique_bins, get_unique_geos, search_by_bin, search_by_geo, initialize_bins_table, initialize_payments_table, set_bin_price
from user_manager import initialize_user_table, register_user, get_user_profile
from telebot import apihelper

apihelper.RETRY_ON_TIMEOUT = True
apihelper.SESSION_TIMEOUT = 60  # Максимальное время ожидания для одного запроса
apihelper.READ_TIMEOUT = 60     # Время ожидания чтения данных
apihelper.CONNECT_TIMEOUT = 60  # Время ожидания подключения

# Создаем бота
bot = telebot.TeleBot('8053455390:AAGVSy0-_GGX4yaF0J9yHcB8xXM94jBBh3A')

# Словарь для отслеживания состояний пользователей
user_states = {}
# Словарь для хранения баланса пользователей (например, в памяти)
user_balances = {}



# Функция для проверки прав администратора
def is_admin(user_id):
    admin_ids = [7338415218, 987654321]  # ID администраторов
    return user_id in admin_ids


def get_main_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('📋 Список карт / Купить', callback_data='list_items'))
    keyboard.row(
        InlineKeyboardButton('‼️ Правила ‼️', callback_data='rules'),
        InlineKeyboardButton('📣 Поддержка', callback_data='support')
    )
    keyboard.row(
        InlineKeyboardButton('👤 Профиль', callback_data='profile'),
        InlineKeyboardButton('💰 Пополнить баланс', callback_data='balance')
    )
    keyboard.add(InlineKeyboardButton('🔄 Возврат товара', callback_data='refund'))
    keyboard.add(InlineKeyboardButton('🛠️ Панель администратора', callback_data='admin_panel'))
    return keyboard

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    user_profile = get_user_profile(user_id)  # Возвращает данные профиля или None
    if not user_profile:
        register_message = register_user(user_id, username)  # Регистрация пользователя
        print(register_message)

    bot.send_message(
        message.chat.id,
        text='Добро пожаловать в маркет! В маркете представлены качественные материалы по доступным ценам. \n\nСовершая покупку, вы подтверждаете, что ознакомлены с правилами покупки и возврата материала.',
        reply_markup=get_main_menu()
    )

def handle_admin_buttons(call):
    data = call.data

    if data == 'set_bin_price_menu':
        bins = get_unique_bins()
        keyboard = InlineKeyboardMarkup()
        for bin_id, bin_code, price in bins:
            keyboard.add(InlineKeyboardButton(f"ID: {bin_id} | BIN: {bin_code} | Цена: {price}", 
                                              callback_data=f'set_price_{bin_id}'))
        keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='admin_panel'))

        bot.edit_message_text(
            text='Выберите BIN для назначения цены:',
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    elif data.startswith('set_price_'):
        try:
            bin_id = int(data.split('_')[2])
            user_states[call.message.chat.id] = f'awaiting_price_for_{bin_id}'
            bot.send_message(call.message.chat.id, f'💵 Введите новую цену для BIN с ID {bin_id}:')
        except ValueError:
            bot.send_message(call.message.chat.id, "⚠️ Ошибка: некорректный ID BIN.")


# Обработка нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    user_id = call.from_user.id

    # Проверка регистрации
    user_profile = get_user_profile(user_id)
    if not user_profile:
        bot.answer_callback_query(call.id, "Вы не зарегистрированы. Введите /start для регистрации.")
        return

    data = call.data

    try:
        if data == 'list_items':
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('Бины', callback_data='bins'))
            keyboard.add(InlineKeyboardButton('🌍 Гео', callback_data='geo'))
            keyboard.add(InlineKeyboardButton('🔍 Поиск по BIN', callback_data='search_bin'))
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))

            bot.edit_message_text(
                text='📋 Выберите категорию:',
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

        elif data == 'bins':
            bins = get_unique_bins()
            keyboard = InlineKeyboardMarkup()
            for bin_id, bin_code, price in bins:
                keyboard.add(InlineKeyboardButton(f"{bin_code} - {price}", callback_data=f'bin_{bin_id}'))
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='list_items'))

            bot.edit_message_text(
                text="Выберите BIN:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

        elif data == 'geo':
            geo_data = get_unique_geos()
            keyboard = InlineKeyboardMarkup()
            for geo in geo_data:
                keyboard.add(InlineKeyboardButton(geo, callback_data=f'geo_{geo}'))
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='list_items'))

            bot.edit_message_text(
                text="🌍 Выберите геолокацию:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

        elif data.startswith('bin_'):
            bin_prefix = data.split('_')[1]
            results = search_by_bin(bin_prefix)
            text = "Результаты поиска:\n"
            for geo, bin_code in results:
                text += f"🌍 {geo}, BIN: {bin_code}\n"

            bot.edit_message_text(
                text=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='bins'))
            )

        elif data.startswith('geo_'):
            geo = data.split('_')[1]
            results = search_by_geo(geo)
            text = "Результаты поиска:\n"
            for geo, bin_code in results:
                text += f"🌍 {geo}, BIN: {bin_code}\n"

            bot.edit_message_text(
                text=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='geo'))
            )

        elif data == 'search_bin':
            bot.edit_message_text(
                text="Введите первые 7 или 8 цифр BIN для поиска:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='list_items'))
            )
            user_states[call.message.chat.id] = 'awaiting_bin_input'

        elif data == 'rules':
            bot.edit_message_text(
                text='Совершая покупку в нашем магазине, вы автоматически соглашаетесь с этими правилами:\n1. Передача товара 3-м лицам запрещена, в случае выяснения факта передачи, мы имеем право отказать вам в замене материала.\n2. Денежные средства возврату не подлежат (мы можем сделать возврат только на баланс нашего бота)\n3. За рассмотрение всех заявок, рекламы, сотрудничества отвечает: @bullyman4ik',
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
            )

        elif data == 'support':
            bot.edit_message_text(
                text='Служба поддержки на связи 24/7. Писать: @bullyman4ik',
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
            )

        elif data == 'profile':
            user_id = call.from_user.id
            user = get_user_profile(user_id)
            if user:
                username, _, registered_at = user  # Баланс теперь берется из user_balances
                balance = user_balances.get(user_id, 0)  # Получаем баланс из словаря
                text = f"👤 Профиль:\nUsername: {username}\nБаланс: {balance:.2f}💰\nДата регистрации: {registered_at}"
            else:
                text = "Профиль не найден. Попробуйте перезапустить бота командой /start."

            bot.edit_message_text(
                text=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
            )

        elif data == 'back_to_main':
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text='Добро пожаловать в маркет! В маркете представлены качественные материалы по доступным ценам. \n\nСовершая покупку, вы подтверждаете, что ознакомлены с правилами покупки и возврата материала.',
                reply_markup=get_main_menu()
            )
        elif data == 'admin_panel':
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "❌ У вас нет прав доступа к админ-панели.")
                return

            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('📝 Назначить цену BIN', callback_data='set_bin_price_menu'))
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))

            bot.edit_message_text(
                text='🛠️ Панель администратора:\nВыберите действие:',
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        elif data.startswith('set_price_') or data == 'set_bin_price_menu':
            handle_admin_buttons(call)
        
        # Проверка, что за кнопка была нажата
        elif data == 'balance':
            handle_balance(call)
        elif data.startswith('network_'):
            handle_network_selection(call)
        elif data.startswith('approve_') or data.startswith('reject_'):
            handle_admin_response(call)
        else:
            bot.answer_callback_query(call.id, "⚠️ Неизвестная команда.")
    except Exception as e:
        print(f"[ERROR] Ошибка в обработке команды: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Произошла ошибка. Пожалуйста, повторите попытку.")

@bot.callback_query_handler(func=lambda call: call.data == 'balance')
def handle_balance(call: CallbackQuery):
    chat_id = call.message.chat.id

    # Отправляем пользователю выбор сети
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton('TRC20', callback_data='network_TRC20'),
        InlineKeyboardButton('ARB', callback_data='network_ARB'),
        InlineKeyboardButton('SOL', callback_data='network_SOL')
    )
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text="💰 Выберите сеть для пополнения:",
        reply_markup=keyboard
    )

# Функция для обработки выбора сети
@bot.callback_query_handler(func=lambda call: call.data.startswith('network_'))
def handle_network_selection(call: CallbackQuery):
    chat_id = call.message.chat.id
    network = call.data.split('_')[1]  # TRC20, ARB, SOL

    # Сохраняем состояние пользователя
    user_states[chat_id] = {'state': 'awaiting_amount_for_' + network, 'network': network}
    if network == 'TRC20':
        bot.send_message(chat_id, f"Вы выбрали сеть TRC20.\nАдрес кошелька: TMax4UdZEWzh3FYG889fwSivknWKhd4CJN\nПосле оплаты, введите точную сумму пополнения (в USDT), для проверки:")
    elif network == 'ARB':
        bot.send_message(chat_id, f"Вы выбрали сеть ARB.\nАдрес кошелька: 0x79d9b8fd2ce5b089f9d6a85679e82417908740e4\nПосле оплаты, введите точную сумму пополнения (в USDT), для проверки:")
    elif network == 'ARB':
        bot.send_message(chat_id, f"Вы выбрали сеть SOL.\nАдрес кошелька: AzdwrmrmBPyDqUw6xw1X1f61xwAoeiymYP7nrjJ949rr\nПосле оплаты, введите точную сумму пополнения (в USDT), для проверки:")
    #bot.send_message(chat_id, f"Вы выбрали сеть {network}. Введите сумму для пополнения:")

# Функция для обработки ввода суммы пополнения
@bot.message_handler(func=lambda message: user_states.get(message.chat.id) and user_states[message.chat.id]['state'].startswith('awaiting_amount_for_'))
def handle_text_message_for_top_up(message: Message):
    chat_id = message.chat.id
    amount = message.text

    try:
        # Преобразуем текст в число и проверяем, что это положительная сумма
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной.")

        network = user_states[chat_id].get('network')

        # Отправляем запрос администратору на подтверждение пополнения
        admin_chat_id = 7338415218  # ID администратора
        bot.send_message(
            admin_chat_id,
            f"💳 Запрос на пополнение:\n"
            f"Пользователь: {message.from_user.username or message.from_user.id}\n"
            f"Сеть: {network}\n"
            f"Сумма: {amount} USDT\n\nПодтвердите или отклоните.",
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton("✅ Подтвердить", callback_data=f'approve_{chat_id}_{amount}'),
                InlineKeyboardButton("❌ Отклонить", callback_data=f'reject_{chat_id}')
            )
        )

        # Уведомляем пользователя
        bot.send_message(chat_id, "✅ Ваш запрос на пополнение отправлен администратору. Ожидайте подтверждения.")
        user_states.pop(chat_id)  # Сбрасываем состояние

    except ValueError:
        bot.send_message(chat_id, "⚠️ Введите корректное число (например, 100.50).")

# Функция для обработки подтверждения или отклонения пополнения администратором
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def handle_admin_response(call: CallbackQuery):
    data = call.data
    if data.startswith('approve_'):
        _, user_chat_id, amount = data.split('_')
        user_chat_id = int(user_chat_id)
        amount = float(amount)
        if user_chat_id in user_balances:
            user_balances[user_chat_id] += amount
        else:
            user_balances[user_chat_id] = amount

        # Уведомляем пользователя о подтверждении
        bot.send_message(user_chat_id, f"✅ Ваш запрос на пополнение {amount} USDT подтвержден администратором.")
        bot.send_message(call.message.chat.id, "✅ Запрос на пополнение успешно подтвержден.")
    elif data.startswith('reject_'):
        _, user_chat_id = data.split('_')
        user_chat_id = int(user_chat_id)

        # Уведомляем пользователя о отклонении
        bot.send_message(user_chat_id, "❌ Ваш запрос на пополнение был отклонен администратором.")
        bot.send_message(call.message.chat.id, "❌ Запрос на пополнение успешно отклонен.")

# Функция для обработки текстовых сообщений с запросами, связанными с состоянием
@bot.message_handler(func=lambda message: user_states.get(message.chat.id) and user_states[message.chat.id]['state'] == 'awaiting_top_up_amount')
def handle_text_messages(message: Message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)

    if state:
        if state['state'].startswith('awaiting_top_up_amount'):
            try:
                amount = float(message.text)
                if amount <= 0:
                    raise ValueError("Сумма должна быть положительной.")

                network = state['network']
                # Дальше обработка пополнения
                bot.send_message(chat_id, f"Вы успешно запросили пополнение на сумму {amount} USDT в сети {network}. Ожидайте подтверждения.")

                # Сбрасываем состояние
                user_states.pop(chat_id)
            except ValueError:
                bot.send_message(chat_id, "⚠️ Введите корректную сумму пополнения.")
        else:
            bot.send_message(chat_id, "⚠️ Неизвестная команда. Используйте /start для возврата в главное меню.")
    else:
        bot.send_message(chat_id, "⚠️ Неизвестная команда. Используйте /start для возврата в главное меню.")

# Запуск бота
if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, interval=2, timeout=60, long_polling_timeout=60)
        except apihelper.ReadTimeout:
            print("[ERROR] ReadTimeout: Сервер Telegram не ответил вовремя. Переподключение...")
            time.sleep(5)
        except apihelper.ApiException as e:
            print(f"[ERROR] ApiException: {e}")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            time.sleep(5)

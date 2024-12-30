import telebot
import time
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from catalogue_loader import load_payment_info_from_file, get_unique_bins, get_unique_geos, search_by_bin, search_by_geo, initialize_bins_table, initialize_payments_table, set_bin_price
from user_manager import initialize_user_table, register_user, get_user_profile
from telebot import apihelper

apihelper.RETRY_ON_TIMEOUT = True
apihelper.SESSION_TIMEOUT = 90  # Максимальное время ожидания для одного запроса
apihelper.READ_TIMEOUT = 90     # Время ожидания чтения данных
apihelper.CONNECT_TIMEOUT = 90  # Время ожидания подключения

# Создаем бота
bot = telebot.TeleBot('8053455390:AAGVSy0-_GGX4yaF0J9yHcB8xXM94jBBh3A')

# Словарь для отслеживания состояний пользователей
user_states = {}
user_top_up_amounts = {}

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
                username, balance, registered_at = user
                text = f"👤 Профиль:\nUsername: {username}\nБаланс: {balance}💰\nДата регистрации: {registered_at}"
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

        elif data == 'balance':
            # Создаем клавиатуру с выбором сети
            keyboard = InlineKeyboardMarkup()
            keyboard.row(
                InlineKeyboardButton('TRC20', callback_data='network_trc20'),
                InlineKeyboardButton('ARB', callback_data='network_arb'),
                InlineKeyboardButton('SOL', callback_data='network_sol')
            )
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))

            bot.edit_message_text(
                text="💰 Выберите сеть для пополнения:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        
        elif data.startswith('network_'):
            network = data.split('_')[1].upper()
            address = ''
            
            # Задаем адреса для каждой сети
            if network == 'TRC20':
                address = 'TMax4UdZEWzh3FYG889fwSivknWKhd4CJN'
            elif network == 'ARB':
                address = '0x79d9b8fd2ce5b089f9d6a85679e82417908740e4'
            elif network == 'SOL':
                address = 'AzdwrmrmBPyDqUw6xw1X1f61xwAoeiymYP7nrjJ949rr'

            # Клавиатура с подтверждением оплаты
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton('✅ Я оплатил', callback_data=f'confirm_payment_{network}'))
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='balance'))

            bot.edit_message_text(
                text=f"💳 Для пополнения через сеть {network}, переведите средства на адрес:\n\n`{address}`\n\nПосле оплаты нажмите '✅ Я оплатил'.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        elif data.startswith('confirm_payment_'):
            network = data.split('_')[2].upper()
            admin_id = 7338415218  # ID администратора, куда отправлять запрос
            bot.send_message(
                admin_id,
                text=f"💰 Пользователь {call.from_user.username} ({call.from_user.id}) заявил о пополнении баланса через сеть {network}. Проверьте транзакцию и подтвердите."
            )
            bot.send_message(
                call.message.chat.id,
                text="✅ Заявка на пополнение отправлена администратору. Ожидайте подтверждения.",
                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
            )

        elif data == 'back_to_main':
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text='Добро пожаловать в маркет! В маркете представлены качественные материалы по доступным ценам. \n\nСовершая покупку, вы подтверждаете, что ознакомлены с правилами покупки и возврата материала.',
                
                reply_markup=get_main_menu()
            )
        
        else:
            bot.answer_callback_query(call.id, "⚠️ Неизвестная команда.")

    except Exception as e:
        print(f"[ERROR] Ошибка в обработке команды: {e}")
        bot.send_message(call.message.chat.id, "⚠️ Произошла ошибка. Пожалуйста, повторите попытку.")

# Функция для обработки текстовых сообщений от пользователя
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)

    if state:
        if state == 'awaiting_bin_input':
            if message.text.isdigit():
                results = search_by_bin(message.text)
                if results:
                    text = "Результаты поиска:\n"
                    for geo, bin_code in results:
                        text += f"🌍 {geo}, BIN: {bin_code}\n"
                else:
                    text = "❌ Ничего не найдено по указанному BIN."

                bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton('🔙 Назад', callback_data='list_items')
                ))
                user_states.pop(chat_id)
            else:
                bot.send_message(chat_id, "⚠️ Введите корректные цифры BIN.")
        elif state.startswith('awaiting_price_for_'):
            try:
                bin_id = int(state.split('_')[-1])
                price = float(message.text)
                set_bin_price(bin_id, price)
                bot.send_message(chat_id, f"✅ Цена для BIN с ID {bin_id} успешно обновлена на {price:.2f}💰.")
                user_states.pop(chat_id)
            except ValueError:
                bot.send_message(chat_id, "⚠️ Укажите корректное число в качестве цены.")
        else:
            bot.send_message(chat_id, "⚠️ Непредвиденное состояние. Попробуйте еще раз.")
    else:
        bot.send_message(chat_id, "⚠️ Неизвестная команда. Используйте /start для возврата в главное меню.")

# Обработка кнопки "Пополнить баланс"
@bot.callback_query_handler(func=lambda call: call.data == 'balance')
def recharge_balance(call):
    markup = InlineKeyboardMarkup()
    networks = ['TRC20', 'Arbitrum', 'Solana']
    for network in networks:
        markup.add(InlineKeyboardButton(network, callback_data=f"select_{network}"))
    bot.edit_message_text(
        text="Выберите сеть для перевода:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

# Отправка адреса для перевода
@bot.callback_query_handler(func=lambda call: call.data.startswith("select_"))
def send_payment_address(call):
    network = call.data.split("_")[1]
    addresses = {
        'TRC20': 'TMax4UdZEWzh3FYG889fwSivknWKhd4CJN',
        'Arbitrum': '0x79d9b8fd2ce5b089f9d6a85679e82417908740e4',
        'Solana': 'AzdwrmrmBPyDqUw6xw1X1f61xwAoeiymYP7nrjJ949rr'
    }
    address = addresses.get(network)
    if address:
        bot.edit_message_text(
            text=f"Адрес для перевода по сети {network}:\n`{address}`\n\nПосле оплаты нажмите кнопку 'Оплатил'.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Оплатил", callback_data=f"paid_{network}"))
        )

# Обработка кнопки "Оплатил"
@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def confirm_payment_request(call):
    network = call.data.split("_")[1]
    admin_id = 123456789  # ID администратора
    bot.send_message(
        admin_id,
        f"Пользователь @{call.from_user.username} сообщил о переводе по сети {network}. Проверьте платеж."
    )
    bot.edit_message_text(
        text="Ваш запрос отправлен администратору. Ожидайте подтверждения.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )

# Подтверждение оплаты администратором
@bot.message_handler(commands=['confirm'])
def confirm_balance(message):
    ADMIN_ID = 7338415218  # Идентификатор администратора

    # Проверка прав доступа
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")
        return

    try:
        # Проверяем правильность формата команды
        parts = message.text.split()
        if len(parts) != 3:
            raise ValueError("Неверный формат команды.")
        
        _, user_id, amount = parts
        user_id = int(user_id)
        amount = float(amount)

        # Проверяем, существует ли пользователь
        if not user_exists(user_id):
            bot.reply_to(message, "Пользователь с таким ID не найден.")
            return

        # Обновляем баланс пользователя
        update_balance(user_id, amount)
        bot.send_message(user_id, f"✅ Ваш баланс пополнен на {amount} единиц.")
        bot.reply_to(message, "✅ Оплата успешно подтверждена.")
    
    except ValueError:
        bot.reply_to(message, "❌ Ошибка в формате команды. Используйте: /confirm <user_id> <amount>")
    except Exception as e:
        bot.reply_to(message, f"❌ Произошла ошибка: {e}")


def update_balance(user_id, amount):
    # Обновление баланса в базе данных
    # Здесь можно добавить обновление в SQLite или другой базе
    print(f"Баланс пользователя {user_id} обновлен на {amount} единиц.")

def user_exists(user_id):
    # Пример проверки существования пользователя
    return user_id

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

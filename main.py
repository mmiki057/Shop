import telebot
import time
import logging
import os
import sqlite3
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from catalogue_loader import load_payment_info_from_file, get_unique_bins, get_unique_geos, get_bins_data, search_by_bin, search_by_geo, initialize_bins_table, initialize_payments_table, set_bin_price, update_user_balance, get_user_balance, add_price_column_to_bins, get_items_count_by_bin, get_items_by_bin, check_table_structure, sell_item
from user_manager import initialize_users_table, register_user, get_user_profile
from telebot import apihelper
from telebot.apihelper import READ_TIMEOUT
from telebot.types import Message
from oplata import get_item_details, get_item_price, purchase_item

apihelper.RETRY_ON_TIMEOUT = True
apihelper.SESSION_TIMEOUT = 100  # Максимальное время ожидания для одного запроса
apihelper.READ_TIMEOUT = 100     # Время ожидания чтения данных
apihelper.CONNECT_TIMEOUT = 100  # Время ожидания подключения

# Создаем бота
bot = telebot.TeleBot('7472173238:AAGZw44_U-aRtj7pyyGdpt6xq4YE7efuLIs')
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Словарь для отслеживания состояний пользователей
user_states = {}
user_top_up_amounts = {}
pending_confirmations = {}
user_balances = {}
# Функция для проверки прав администратора
def is_admin(user_id):
    admin_ids = [7338415218, 7346551427]  # ID администраторов
    return user_id in admin_ids

def handle_purchase(user_id, item_id):
    # Предположим, у вас есть функция `get_item_details`, которая возвращает полную информацию о товаре
    item_details = get_item_details(item_id)
    
    if item_details:
        geo, bank, number, date, code = item_details
        message = (
            f"✅ Покупка успешно завершена!\n\n"
            f"📌 Информация о товаре:\n"
            f"🌍 Гео: {geo}\n"
            f"🏦 Банк: {bank}\n"
            f"🔢 Номер: {number}\n"
            f"📅 Дата: {date}\n"
            f"🔑 CVC: {code}"
        )
        bot.send_message(user_id, message)
    else:
        bot.send_message(user_id, "❌ Ошибка: товар не найден.")

    
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

@bot.message_handler(commands=['go'])
def go(message):
    bot.send_message(
        message.chat.id,
        "📁 Пожалуйста, отправьте файл `payments.txt` для загрузки данных.",
    )
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
# ??????????????????           keyboard.add(InlineKeyboardButton('🔍 Поиск по BIN', callback_data='search_bin')) ??????????????????????
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))

            bot.edit_message_text(
                text='📋 Выберите категорию:',
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

        elif data.startswith('geo_'):
            geo = data.split('_')[1]
            results = search_by_geo(geo)
            text = "Результаты поиска:\n"
            keyboard = InlineKeyboardMarkup()
            
            for geo, bin_code in results:
                text += f"{geo} {bin_code}\n"
                keyboard.add(InlineKeyboardButton(
                    f"Купить {bin_code}",
                    callback_data=f'buy_{bin_code}'
                ))
            
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='geo'))

            bot.edit_message_text(
                text=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

        
        elif data == 'bins':
            bins = get_unique_bins()
            keyboard = InlineKeyboardMarkup()
            for bin_id, bin_code, price in bins:
                keyboard.add(InlineKeyboardButton(f"BIN: {bin_code}, Price: {price} USDT", callback_data=f'bin_{bin_code}'))
            keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='list_items'))

            bot.edit_message_text(
                text="Выберите BIN:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

        elif data.startswith('bin_'):
            try:
                bin_code = data.split('_')[1]
                # Получаем количество товаров с данным BIN
                items_count = get_items_count_by_bin(bin_code)

                # Получаем список товаров с данным BIN
                print('items count -', items_count)
                items = get_items_by_bin(bin_code)
                
                print(items)

                # Формируем сообщение с количеством товаров и кнопкой "Купить"
                text = f"Вы выбрали BIN: {bin_code}\n\n" \
                    f"Количество товаров с этим BIN: {items_count}\n\n" \
                    "Для покупки товара с данным BIN нажмите \"Купить\"" if items_count > 0 else "Извините, товара нет в наличии."

                # Кнопки для каждого товара
                keyboard = InlineKeyboardMarkup()
                if items_count > 0:
                    for item in items:
                        print('item - ', item)
                        item_id = item['id']  # ID товара
                        item_number = item['number']  # Номер карты
                        item_price = item['price']  # Цена товара
                        #keyboard.add(InlineKeyboardButton(f"{item_number} - {item_price} USDT", callback_data=f'buy_{item_id}'))

                    # Добавляем кнопку "Купить"
                    keyboard.add(InlineKeyboardButton('Купить', callback_data=f'buy_{bin_code}'))
                
                # Кнопка "Назад"
                keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='bins'))

                bot.edit_message_text(
                    text=text,
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboard
                )
            
            except Exception as e:
                print(e)


        elif data.startswith('buy_'):
            try:
                
                bin_code = str(data.split('_')[1])
                
                bins_data = get_bins_data()
                print(bins_data)
                
                filtered_bin = next((bin_item for bin_item in bins_data if bin_item['bin'] == bin_code), None)

                if filtered_bin:
                    print(f"Найден BIN: {filtered_bin}")
                else:
                    print(f"BIN с кодом {bin_code} не найден.")
                
                
                # Получаем баланс пользователя
                user_balance = get_user_balance(user_id)
                print(f"Баланс пользователя: {user_balance}")
                
                if user_balance is None:
                    print(f"Ошибка: не удалось получить баланс для пользователя {user_id}")
                    bot.send_message(user_id, "❌ Ошибка: не удалось получить баланс.")
                    return

                # Получаем цену товара
                item_price = filtered_bin['price']
                print(f"Цена товара: {item_price}")

                if item_price is None:
                    print(f"Ошибка: не удалось получить цену для товара {bin_code}")
                    bot.send_message(user_id, "❌ Ошибка: не удалось получить цену товара.")
                    return

                # Проверяем, хватает ли средств на балансе
                if user_balance >= item_price:
                    # Списываем средства
                    new_balance = user_balance - item_price
                    update_user_balance(user_id, new_balance)
                    print(f"Новый баланс: {new_balance}")
                    
                    # Получаем полную информацию о товаре
                    items_details = get_item_details(filtered_bin['bin'])  # Используем функцию для получения списка товаров
                    print(f"Данные товаров: {items_details}")

                    if items_details:
                          # ID товара
                        # Формируем сообщение для каждого товара
                        geo = items_details['geo']
                        bank = items_details['bank']
                        number = items_details['number']
                        date = items_details['date']
                        code = items_details['code']
                        id = items_details['id'] # ??????????????????????????????????????????????????????????????
                        
                        message = (
                            f"✅ Покупка успешно завершена!\n\n"
                            f"📌 Информация о товаре:\n"
                            f"🌍 Гео: {geo}\n"
                            f"🏦 Банк: {bank}\n"
                            f"🔢 Номер: {number}\n"
                            f"📅 Дата: {date}\n"
                            f"🔑 CVC: {code}"
                        )
                        bot.send_message(user_id, message) #????????????????????????????????????????????????????
                        sell_item(id)
                        
                    else:
                        print(f"Ошибка: данные товаров не найдены для BIN {filtered_bin['bin']}")
                        bot.send_message(user_id, "❌ Ошибка: товары не найдены для данного BIN.")
                else:
                    logging.warning(f"Недостаточно средств для покупки. Баланс: {user_balance}, Цена товара: {item_price}")
                    bot.send_message(user_id, "❌ Недостаточно средств на балансе для покупки.")
            
            except Exception as e:
                logging.error(f"Произошла ошибка при обработке покупки: {str(e)}")
                bot.send_message(user_id, "⚠️ Произошла ошибка. Пожалуйста, повторите попытку.")


        elif data == 'search_bin':
            bot.edit_message_text(
                text="🔍 Введите первые 6 цифр BIN для поиска:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton('🔙 Назад', callback_data='list_items')
                )
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
            handle_balance(call)

        elif data.startswith('network_'):
            handle_network_selection(call)
            
        elif data.startswith('approve_') or data.startswith('reject_'):
            handle_admin_response(call)
        
        elif data.startswith('buy_'):
            item_id = int(data.split('_')[1])
            user_balance = get_user_balance(user_id)

            # Проверяем, хватает ли средств на балансе
            item_price = get_item_price(item_id)
            if user_balance >= item_price:
                # Списываем средства
                new_balance = user_balance - item_price
                update_user_balance(user_id, new_balance)
                
                # Обрабатываем покупку
                handle_purchase(user_id, item_id)
            else:
                bot.send_message(user_id, "❌ Недостаточно средств на балансе для покупки.")
        else:
            bot.answer_callback_query(call.id, "⚠️ Неизвестная команда.")

    except Exception as e:
        print(f"[ERROR] Ошибка в обработке команды: {e}")
        bot.send_message(call.message.chat.id, f"⚠️ Произошла ошибка. Пожалуйста, повторите попытку.{e}")

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
    elif network == 'SOL':
        bot.send_message(chat_id, f"Вы выбрали сеть SOL.\nАдрес кошелька: AzdwrmrmBPyDqUw6xw1X1f61xwAoeiymYP7nrjJ949rr\nПосле оплаты, введите точную сумму пополнения (в USDT), для проверки:")
    #bot.send_message(chat_id, f"Вы выбрали сеть {network}. Введите сумму для пополнения:")

# Функция для обработки ввода суммы пополнения
@bot.message_handler(func=lambda message: isinstance(user_states.get(message.chat.id), dict) 
                     and 'state' in user_states[message.chat.id] 
                     and user_states[message.chat.id]['state'].startswith('awaiting_amount_for_'))
def handle_text_message_for_top_up(message: Message):
    chat_id = message.chat.id
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной.")

        network = user_states[chat_id].get('network')
        admin_chat_id = 7338415218  # ID администратора

        # Отправляем запрос администратору
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

        bot.send_message(chat_id, f"✅ Ваш запрос на пополнение на сумму {amount} USDT отправлен администратору для подтверждения.\n\n Время ожидания составит до 10 минут")
        user_states.pop(chat_id)  # Сбрасываем состояние

    except ValueError:
        bot.send_message(chat_id, "⚠️ Введите корректное число (например, 100.50).")

# 📌 2. Обработчик для установки цены BIN
@bot.message_handler(commands=['set_price'])
def set_price(message: Message):
    chat_id = message.chat.id
    try:
        user_input = message.text.split()
        if len(user_input) != 3:
            bot.send_message(chat_id, "❌ Используйте формат: /set_price [ID BIN] [Цена]")
            return
        
        bin_id = int(user_input[1])
        price = float(user_input[2])
        set_bin_price(bin_id, price)
        
        bot.send_message(chat_id, f"✅ Цена {price} $ установлена для BIN с ID {bin_id}.")
    except ValueError:
        bot.send_message(chat_id, "⚠️ Неверный формат команды. Используйте: /set_price ID BIN Цена")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Произошла ошибка: {e}")

# 📌 3. Универсальный обработчик состояний
@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_state_messages(message: Message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)

    # 📌 Обработка поиска BIN
    if state == 'awaiting_bin_input':
        if message.text.isdigit() and len(message.text) == 6:
            results = search_by_bin(message.text)  # Поиск по BIN
            if results:
                text = "📊 Результаты поиска по BIN:\n"
                keyboard = InlineKeyboardMarkup()
                for geo, bin_code in results:
                    text += f"🌍 {geo}, BIN: {bin_code}\n"
                    keyboard.add(InlineKeyboardButton(
                        f"Купить {bin_code}",
                        callback_data=f'buy_{bin_code}'
                    ))
                keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='list_items'))
            else:
                text = "❌ Ничего не найдено по указанному BIN."
                keyboard = InlineKeyboardMarkup().add(
                    InlineKeyboardButton('🔙 Назад', callback_data='list_items')
                )
            
            bot.send_message(chat_id, text, reply_markup=keyboard)
            user_states.pop(chat_id)
        else:
            bot.send_message(chat_id, "⚠️ Введите корректные 6 цифр BIN.")
    
    # 📌 Обновление цены BIN
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
        user_states.pop(chat_id)


# 📌 4. Обработчик для неизвестных команд
@bot.message_handler(func=lambda message: True)
def handle_unknown_command(message: Message):
    bot.send_message(message.chat.id, "⚠️ Неизвестная команда. Используйте /start для возврата в главное меню.")


# Функция для обработки подтверждения или отклонения пополнения администратором
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def handle_admin_response(call):
    try:
        data = call.data
        if data.startswith('approve_'):
            _, user_chat_id, amount = data.split('_')
            user_chat_id = int(user_chat_id)
            amount = float(amount)

            # Обновляем баланс пользователя в базе данных
            current_balance = get_user_balance(user_chat_id)
            if current_balance is None:
                bot.send_message(call.message.chat.id, f"❌ Пользователь с ID {user_chat_id} не найден в базе данных.")
                return

            new_balance = current_balance + amount
            update_user_balance(user_chat_id, new_balance)

            # Уведомляем пользователя
            bot.send_message(
                user_chat_id,
                f"✅ Ваш запрос на пополнение на сумму {amount} USDT подтвержден администратором. Ваш новый баланс: {new_balance} USDT."
            )
            bot.send_message(call.message.chat.id, "✅ Запрос на пополнение успешно подтвержден.")

        elif data.startswith('reject_'):
            _, user_chat_id = data.split('_')
            user_chat_id = int(user_chat_id)

            # Уведомляем пользователя об отклонении
            bot.send_message(user_chat_id, "❌ Ваш запрос на пополнение был отклонен администратором.")
            bot.send_message(call.message.chat.id, "❌ Запрос на пополнение успешно отклонен.")

        else:
            bot.send_message(call.message.chat.id, "❌ Неизвестная команда.")
    except ValueError as e:
        bot.send_message(call.message.chat.id, f"❌ Произошла ошибка обработки данных: {e}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Произошла ошибка: {e}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    user_id = message.from_user.id
    
    # Проверка прав администратора
    if not is_admin(user_id):
        bot.send_message(
            message.chat.id,
            "❌ У вас нет прав для отправки и обработки документов."
        )
        return
    try:
        # Проверяем имя файла
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        
        if not file_name.endswith('.txt'):
            bot.send_message(message.chat.id, "⚠️ Пожалуйста, отправьте текстовый файл с расширением `.txt`.")
            return
        
        # Скачиваем файл
        downloaded_file = bot.download_file(file_info.file_path)
        temp_file_path = f"temp_{file_name}"
        
        with open(temp_file_path, 'wb') as file:
            file.write(downloaded_file)
        
        bot.send_message(message.chat.id, "📊 Файл получен! Начинаю обработку данных...")
        
        # Чтение файла и запись данных в базу
        with open(temp_file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        
        with sqlite3.connect('payment_info.db') as conn:
            cursor = conn.cursor()
            records = content.split(";")
            
            for record in records:
                try:
                    geo, bank, number, date, code = record.split(",")
                    bin_code = number[:6]
                    
                    # Проверяем наличие BIN'а
                    cursor.execute("SELECT id FROM bins WHERE bin = ?", (bin_code,))
                    bin_row = cursor.fetchone()
                    
                    if not bin_row:
                        cursor.execute("INSERT INTO bins (bin) VALUES (?)", (bin_code,))
                        conn.commit()
                        bin_id = cursor.lastrowid
                        print(f"Добавлен новый BIN: {bin_code} с ID {bin_id}")
                    else:
                        bin_id = bin_row[0]
                    
                    # Проверяем уникальность записи
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
                        bot.send_message(message.chat.id, f"✅ Запись для карты {number} добавлена!")
                    else:
                        bot.send_message(message.chat.id, f"ℹ️ Запись для карты {number} уже существует!")
                
                except ValueError:
                    bot.send_message(message.chat.id, f"⚠️ Ошибка обработки записи: {record}")
        
        os.remove(temp_file_path)  # Удаляем временный файл
        bot.send_message(message.chat.id, "🎯 Обработка завершена успешно!")
    
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}")

# Запуск бота
if __name__ == '__main__':
    #load_payment_info_from_file()
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

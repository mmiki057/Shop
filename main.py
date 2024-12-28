import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from catalogue_loader import load_payment_info_from_file, get_unique_bins, get_unique_geos, search_by_bin, search_by_geo
from user_manager import initialize_user_table, register_user, get_user_profile


# Enable logging
#logging.basicConfig(
#    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#    level=logging.INFO
#)
#logger = logging.getLogger(__name__)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    register_message = register_user(user_id, username)  # Регистрация пользователя
    print(register_message)

    keyboard = [
        [InlineKeyboardButton('📋 Список карт', callback_data='list_items')],
        [InlineKeyboardButton('‼️ Правила ‼️', callback_data='rules'),
         InlineKeyboardButton('📣 Поддержка', callback_data='support')],
        [InlineKeyboardButton('👤 Профиль', callback_data='profile'),
         InlineKeyboardButton('💰 Пополнить баланс', callback_data='balance')],
        [InlineKeyboardButton('🔄 Возврат товара', callback_data='refund')],
        [InlineKeyboardButton('🛠️ Панель поставщика', callback_data='supplier_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text='Добро пожаловать в маркет! В маркете представлены качественные материалы по доступным ценам. \n\nСовершая покупку, вы подтверждаете, что ознакомлены с правилами покупки и возврата материала.',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text='Добро пожаловать в маркет! В маркете представлены качественные материалы по доступным ценам. \n\nСовершая покупку, вы подтверждаете, что ознакомлены с правилами покупки и возврата материала.',
            reply_markup=reply_markup
        )

# Handle button clicks
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'list_items':
        keyboard = [
            [InlineKeyboardButton('🔢 Бины', callback_data='bins')],
            [InlineKeyboardButton('🌍 Гео', callback_data='geo')],
            [InlineKeyboardButton('🔍 Поиск по BIN', callback_data='search_bin')],
            [InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')]
        ]
        await query.edit_message_text(
            text='📋 Выберите категорию:',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == 'bins':
        bins = get_unique_bins()
        keyboard = [[InlineKeyboardButton(bin, callback_data=f'bin_{bin}')] for bin in bins]
        keyboard.append([InlineKeyboardButton('🔙 Назад', callback_data='list_items')])
        await query.edit_message_text(
            text="🔢 Выберите BIN:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == 'geo': 
        geo_data = get_unique_geos()
        keyboard = [[InlineKeyboardButton(geo, callback_data=f'geo_{geo}')] for geo in geo_data]
        keyboard.append([InlineKeyboardButton('🔙 Назад', callback_data='list_items')])
        await query.edit_message_text(
            text="🌍 Выберите геолокацию:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith('bin_') and '_' in data:
        parts = data.split('_')
        if len(parts) > 1:
            bin_prefix = parts[1]
            results = search_by_bin(bin_prefix)
            text = "Результаты поиска:\n"
            for result in results:
                if len(result) >= 5:
                    geo, bank, number, date, cvc = result[:5]
                    text += f"🌍 {geo}, 🏦 {bank}, 💳 {number}, 📅 {date}, 🔑 {cvc}\n"
                else:
                    text += "Некорректные данные в записи.\n"
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Назад', callback_data='bins')]]))

    elif data.startswith('geo_') and '_' in data:
        parts = data.split('_')
        if len(parts) > 1:
            geo = parts[1]
            results = search_by_geo(geo)
            text = "Результаты поиска:\n"
            for result in results:
                if len(result) >= 5:
                    geo, bank, number, date, cvc = result[:5]
                    text += f"🌍 {geo}, 🏦 {bank}, 💳 {number}, 📅 {date}, 🔑 {cvc}\n"
                else:
                    text += "Некорректные данные в записи.\n"
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Назад', callback_data='geo')]]))

    elif data == 'search_bin':
        await query.edit_message_text(
            text="Введите первые 7 или 8 цифр BIN для поиска:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Назад', callback_data='list_items')]])
        )
        context.user_data['awaiting_bin_input'] = True  # Устанавливаем флаг ожидания ввода BIN

    elif data == 'search_bin':  # Поиск по BIN (простой ввод)
        await query.edit_message_text(
            text="Введите первые 7 или 8 цифр BIN для поиска:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Назад', callback_data='list_items')]])
        )
        context.user_data['awaiting_bin_input'] = True  # Устанавливаем флаг ожидания ввода BIN

    elif data == 'rules':
        await query.edit_message_text(
            text='Совершая покупку в нашем магазине, вы автоматически соглашаетесь с этими правилами:\n1. Передача товара 3-м лицам запрещена, в случае выяснения факта передачи, мы имеем право отказать вам в замене материала.\n2. Денежные средства возврату не подлежат (мы можем сделать возврат только на баланс нашего бота)\n3. За рассмотрение всех заявок, рекламы, сотрудничества отвечает: @bullyman4ik',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')]
            ])
        )
    
    elif data == 'support':
        await query.edit_message_text(
            text='Служба поддержки на связи 24/7. Писать: @bullyman4ik',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')]
            ])
        )

    elif data == 'profile':
        user_id = update.effective_user.id
        user = get_user_profile(user_id)
        if user:
            username, balance, registered_at = user
            text = f"👤 Профиль:\nUsername: {username}\nБаланс: {balance}💰\nДата регистрации: {registered_at}"
        else:
            text = "Профиль не найден. Попробуйте перезапустить бота командой /start."
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')]])
        )

    elif data == 'back_to_main':
        await start(update, context)

    else:
        responses = {
            'support': '📣 Свяжитесь с поддержкой: @support_bot',
            'profile': '👤 Ваш профиль: Имя, баланс и статистика.',
            'balance': '💰 Пополнить баланс можно через CryptoBot API.',
            'refund': '🔄 Для возврата товара свяжитесь с поддержкой.',
            'supplier_panel': '🛠️ Доступ к панели поставщика предоставляется администрацией.'
        }
        response = responses.get(data, '❌ Неизвестная команда.')
        await query.edit_message_text(
            text=response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')]
            ])
        )

# Обработчик текстового ввода (например, BIN)
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_bin_input'):
        bin_prefix = update.message.text.strip()
        results = await search_by_bin(bin_prefix)
        if results:
            text = "Результаты поиска:\n" + "\n".join(
                f"🌍 {geo}, 🏦 {bank}, 💳 {number}, 📅 {date}, 🔑 {cvc}" for geo, bank, number, date, cvc in results
            )
        else:
            text = f"Нет данных для BIN: {bin_prefix}"
        await update.message.reply_text(text)
        context.user_data['awaiting_bin_input'] = False

# Main function to run the bot
def main():
    load_payment_info_from_file()
    initialize_user_table()

    application = ApplicationBuilder().token('8053455390:AAGVSy0-_GGX4yaF0J9yHcB8xXM94jBBh3A').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))  # NEW

    application.run_polling()

if __name__ == '__main__':
    main()

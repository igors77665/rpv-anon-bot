from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os

TOKEN = "7949738221:AAHdU0oW6wrIxLUZkCT2I5IPmAgAMTRy0oU"
ADMIN_ID = 8048779916
CHANNEL_ID = -1002626166337

# Хранилище данных
pending_messages = {}
blocked_users = set()

WELCOME_MESSAGE = """
Привет! Напиши любое сообщение и оно анонимно отправится в канал.

Правила отправки:
1. Не отправлять бессмысленные сообщения
2. Не дублировать одинаковый контент
3. Не оскорблять админа

Нарушители будут заблокированы!
"""

CONFIRMATION_MESSAGE = """
✅ Анонимное сообщение отправлено!

Через время админ выложит его в канал.

Если хотите отправить еще одно анонимное сообщение, нажмите /start
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений"""
    user = update.effective_user
    message = update.message
    
    # Игнорируем если пользователь заблокирован или это команда
    if not message or user.id in blocked_users or (message.text and message.text.startswith('/')):
        return
    
    # Сохраняем сообщение для модерации
    pending_messages[message.message_id] = {
        "user": {
            "id": user.id,
            "name": user.full_name,
            "username": f"@{user.username}" if user.username else "нет"
        },
        "content": message
    }
    
    # Кнопки модерации
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Опубликовать", callback_data=f"approve_{message.message_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{message.message_id}")
        ],
        [
            InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{message.message_id}"),
            InlineKeyboardButton("⛔ Заблокировать", callback_data=f"block_{message.message_id}")
        ]
    ])
    
    user_info = f"👤 Отправитель: {user.full_name} (ID: {user.id})"
    
    try:
        # Отправляем админу на модерацию
        if message.text:
            await context.bot.send_message(
                ADMIN_ID,
                f"✉️ Новое сообщение:\n\n{message.text}\n\n{user_info}",
                reply_markup=keyboard
            )
        elif message.photo:
            await context.bot.send_photo(
                ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=f"📸 Фото\n\n{user_info}" + (f"\n\n{message.caption}" if message.caption else ""),
                reply_markup=keyboard
            )
        
        # Отправляем отправителю подтверждение
        await message.reply_text(CONFIRMATION_MESSAGE, parse_mode='Markdown')
        
    except Exception as e:
        await context.bot.send_message(ADMIN_ID, f"❌ Ошибка: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок модерации"""
    query = update.callback_query
    await query.answer()
    
    action, msg_id = query.data.split('_')
    msg_id = int(msg_id)
    
    if msg_id not in pending_messages:
        await query.edit_message_text("⚠️ Сообщение уже обработано")
        return
    
    user_data = pending_messages[msg_id]["user"]
    message = pending_messages[msg_id]["content"]
    
    try:
        if action == "approve":
            # Публикация в канал
            if message.text:
                await context.bot.send_message(CHANNEL_ID, f"✉️ Анонимное сообщение:\n\n{message.text}")
            elif message.photo:
                await context.bot.send_photo(CHANNEL_ID, message.photo[-1].file_id)
            
            await query.edit_message_text(f"{query.message.text}\n\n✅ Опубликовано в канале!")
        
        elif action == "reject":
            await query.edit_message_text(f"{query.message.text}\n\n❌ Отклонено")
        
        elif action == "block":
            blocked_users.add(user_data["id"])
            await context.bot.send_message(user_data["id"], "🚫 Вы были заблокированы!")
            await query.edit_message_text(f"{query.message.text}\n\n⛔ Пользователь заблокирован")
        
        elif action == "reply":
            await query.edit_message_text(
                f"{query.message.text}\n\n✍️ Введите ответ для этого пользователя:"
            )
            # Сохраняем для последующего ответа
            context.user_data['reply_to'] = user_data["id"]
    
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {e}")
    
    del pending_messages[msg_id]

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответов админа"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    if 'reply_to' not in context.user_data:
        return
    
    user_id = context.user_data['reply_to']
    try:
        await context.bot.send_message(
            user_id,
            f"📨 Анонимный ответ от админа:\n\n{update.message.text}"
        )
        await update.message.reply_text("✅ Ответ отправлен анонимно!")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")
    
    del context.user_data['reply_to']

if _name_ == "_main_":
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_ID), handle_admin_reply))
    
    app.run_polling()

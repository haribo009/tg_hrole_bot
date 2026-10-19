import asyncio
import json
import logging
import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Render умеет считывать токен из переменных окружения, но для простоты можешь вписать сюда:
TOKEN = "8826570127:AAHaZAxmoqocst8EdpPKOpWcV1-MO_gNfAg"

# Хранилище ролей и имен
user_roles = {}
user_names = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "Привет! Я бот для вызова ролей.\n\n"
        "<b>Команды:</b>\n"
        "• <code>/setrole Роль</code> — получить роль (напр. <code>/setrole Дизайнер</code>)\n"
        "• <code>/delrole Роль</code> — снять роль\n"
        "• <code>/roles</code> — меню для вызова роли\n"
        "• <code>/myroles</code> — твои роли"
    )

async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_html("Укажи название роли! Пример: <code>/setrole Дизайнер</code>")
        return

    role = " ".join(context.args).strip()
    
    if role not in user_roles:
        user_roles[role] = set()

    user_roles[role].add(user.id)
    
    # Сохраняем кликабельное упоминание
    if user.username:
        tag_name = f"@{user.username}"
    else:
        # Безопасный HTML-тег по ID для пользователей без юзернейма
        first_name = user.first_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        tag_name = f'<a href="tg://user?id={user.id}">{first_name}</a>'
        
    user_names[user.id] = tag_name

    await update.message.reply_html(f"✅ Ты успешно получил(а) роль: <b>{role}</b>")

async def del_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_html("Укажи название роли! Пример: <code>/delrole Дизайнер</code>")
        return

    role = " ".join(context.args).strip()

    if role in user_roles and user.id in user_roles[role]:
        user_roles[role].remove(user.id)
        if not user_roles[role]:
            del user_roles[role]
        await update.message.reply_html(f"❌ Роль <b>{role}</b> снята.")
    else:
        await update.message.reply_html(f"У тебя нет роли <b>{role}</b>.")

async def my_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    my_list = [role for role, users in user_roles.items() if user.id in users]
    
    if my_list:
        roles_str = "\n• " + "\n• ".join(my_list)
        await update.message.reply_text(f"Твои роли:{roles_str}")
    else:
        await update.message.reply_text("У тебя пока нет назначенных ролей.")

async def show_roles_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_roles:
        await update.message.reply_text("В группе пока нет созданных ролей!")
        return

    keyboard = []
    for role in user_roles.keys():
        keyboard.append([InlineKeyboardButton(f"📣 Позвать: {role}", callback_data=f"call_{role}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери роль, которую нужно отметить:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("call_"):
        role = data.replace("call_", "")
        users = user_roles.get(role, set())

        if not users:
            await query.edit_message_text(f"В роли {role} никого нет.")
            return

        mentions = [user_names[uid] for uid in users if uid in user_names]
        text = f"🔔 <b>Вызов участников с ролью [{role}]:</b>\n\n" + " ".join(mentions)
        
        # Отправляем сообщение с поддержкой HTML (теги будут активны)
        await query.message.reply_html(text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setrole", set_role))
    app.add_handler(CommandHandler("delrole", del_role))
    app.add_handler(CommandHandler("myroles", my_roles))
    app.add_handler(CommandHandler("roles", show_roles_menu))
    app.add_handler(CallbackQueryHandler(button_click))

    app.run_polling()

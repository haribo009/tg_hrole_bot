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

DATA_FILE = "roles_data.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_roles = {role: set(u_ids) for role, u_ids in data.get("user_roles", {}).items()}
                user_names = {int(uid): name for uid, name in data.get("user_names", {}).items()}
                return user_roles, user_names
        except Exception as e:
            logging.error(f"Ошибка загрузки файла: {e}")
    return {}, {}

def save_data():
    try:
        data = {
            "user_roles": {role: list(u_ids) for role, u_ids in user_roles.items()},
            "user_names": {str(uid): name for uid, name in user_names.items()}
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        subprocess.run(["git", "config", "--global", "user.name", "RoleBot"], capture_output=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@action.github.com"], capture_output=True)
        subprocess.run(["git", "add", DATA_FILE], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Auto-update roles data [skip ci]"], capture_output=True)
        push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
        logging.info(f"Git push result: {push_result.stdout}")
        
    except Exception as e:
        logging.error(f"Ошибка сохранения/пуша данных: {e}")

user_roles, user_names = load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "Привет! Я бот для вызова ролей.\n\n"
        "<b>Команды:</b>\n"
        "• <code>/setrole Роль</code> — получить роль (напр. <code>/setrole Дизайнер</code>)\n"
        "• <code>/delrole Роль</code> — снять роль\n"
        "• <code>/call Роль</code> — позвать всех с этой ролью (напр. <code>/call Дизайнер</code>)\n"
        "• <code>/roles</code> — список всех существующих ролей\n"
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
    
    if user.username:
        tag_name = f"@{user.username}"
    else:
        first_name = user.first_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        tag_name = f'<a href="tg://user?id={user.id}">{first_name}</a>'
        
    user_names[user.id] = tag_name
    save_data()

    await update.message.reply_html(f"✅ Роль <b>{role}</b> успешно закреплена за тобой!")

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
        save_data()
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

async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_roles:
        await update.message.reply_text("В группе пока нет созданных ролей!")
        return

    roles_list = "\n• ".join(user_roles.keys())
    await update.message.reply_html(f"📋 <b>Существующие роли в группе:</b>\n• {roles_list}\n\n<i>Для вызова используй: /call НазваниеРоли</i>")

async def call_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_html("Укажи роль для вызова! Пример: <code>/call Дизайнер</code>")
        return

    role = " ".join(context.args).strip()
    users = user_roles.get(role, set())

    if not users:
        await update.message.reply_html(f"В роли <b>{role}</b> никого нет или такой роли не существует.")
        return

    mentions = [user_names[uid] for uid in users if uid in user_names]
    
    if not mentions:
        await update.message.reply_html(f"Не удалось найти список людей для роли <b>{role}</b>.")
        return

    text = f"🔔 <b>Вызов участников с ролью [{role}]:</b>\n\n" + " ".join(mentions)
    await update.message.reply_html(text)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setrole", set_role))
    app.add_handler(CommandHandler("delrole", del_role))
    app.add_handler(CommandHandler("myroles", my_roles))
    app.add_handler(CommandHandler("roles", list_roles))
    app.add_handler(CommandHandler("call", call_role))

    app.run_polling()

import json
import logging
import os
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

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
        subprocess.run(["git", "pull", "--rebase"], capture_output=True)
        subprocess.run(["git", "push"], capture_output=True)
    except Exception as e:
        logging.error(f"Ошибка сохранения/пуша данных: {e}")

user_roles, user_names = load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "Привет! Бот настроен и готов к работе.\n\n"
        "⚡️ <b>Быстрый вызов:</b>\n"
        "Просто напиши в чат: <code>/call [роль] [твой текст]</code>\n"
        "Пример: <code>/call отгрузка срочно проверьте деталь</code>"
    )

async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        await update.effective_chat.send_message("Укажи название роли! Пример: <code>/setrole отгрузка</code>", parse_mode="HTML")
        return

    role = " ".join(context.args).strip().lower()
    user = update.effective_user
    
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

    msg = await update.effective_chat.send_message(f"✅ Роль <b>{role}</b> закреплена за тобой!", parse_mode="HTML")
    await asyncio_delete(msg)

async def del_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        return

    role = " ".join(context.args).strip().lower()
    user = update.effective_user

    if role in user_roles and user.id in user_roles[role]:
        user_roles[role].remove(user.id)
        if not user_roles[role]:
            del user_roles[role]
        save_data()

async def my_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    my_list = [role for role, users in user_roles.items() if update.effective_user.id in users]
    if my_list:
        roles_str = "\n• " + "\n• ".join(my_list)
        msg = await update.effective_chat.send_message(f"Твои роли:{roles_str}")
    else:
        msg = await update.effective_chat.send_message("У тебя нет ролей.")
    
    # Автоудаление через 4 сек
    import asyncio
    asyncio.create_task(delete_later(msg, 4))

async def delete_later(message, delay=4):
    import asyncio
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not user_roles:
        msg = await update.effective_chat.send_message("Ролей пока нет.")
        import asyncio
        asyncio.create_task(delete_later(msg, 3))
        return

    roles_list = "\n• ".join(user_roles.keys())
    msg = await update.effective_chat.send_message(f"📋 <b>Роли в группе:</b>\n• {roles_list}", parse_mode="HTML")
    import asyncio
    asyncio.create_task(delete_later(msg, 6))

# Быстрый вызов через /call
async def call_role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        return

    role = context.args[0].strip().lower()
    custom_text = " ".join(context.args[1:]).strip()

    users = user_roles.get(role, set())
    if not users:
        return

    mentions = [user_names[uid] for uid in users if uid in user_names]
    
    response_text = f"🔔 <b>Вызов [{role}]:</b>\n" + " ".join(mentions)
    if custom_text:
        response_text += f"\n\n💬 {custom_text}"

    await update.effective_chat.send_message(response_text, parse_mode="HTML")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setrole", set_role))
    app.add_handler(CommandHandler("delrole", del_role))
    app.add_handler(CommandHandler("myroles", my_roles))
    app.add_handler(CommandHandler("roles", list_roles))
    app.add_handler(CommandHandler("call", call_role_command))

    app.run_polling()

import asyncio
import json
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = "8826570127:AAHaZAxmoqocst8EdpPKOpWcV1-MO_gNfAg"
DATA_FILE = "roles_data.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Функции для работы с файлом данных ролей
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_roles = {role: set(u_ids) for role, u_ids in data.get("user_roles", {}).items()}
                user_names = {int(uid): name for uid, name in data.get("user_names", {}).items()}
                return user_roles, user_names
        except Exception as e:
            logging.error(f"Ошибка загрузки файла данных: {e}")
    return {}, {}

def save_data():
    try:
        data = {
            "user_roles": {role: list(u_ids) for role, u_ids in user_roles.items()},
            "user_names": {str(uid): name for uid, name in user_names.items()}
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения файла данных: {e}")

user_roles, user_names = load_data()

async def delete_later(message, delay=4):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "Привет! Бот настроен.\n\n"
        "<b>Команды:</b>\n"
        "• <code>/setrole отгрузка</code> — получить роль\n"
        "• <code>/delrole отгрузка</code> — снять роль\n"
        "• <code>/roles</code> — список всех ролей\n"
        "• <code>/myroles</code> — твои роли\n\n"
        "⚡️ <b>Быстрый вызов (твое сообщение остается в чате):</b>\n"
        "<code>!отгрузка деталь такая-то</code>"
    )

async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        msg = await update.effective_chat.send_message("Укажи название роли! Пример: <code>/setrole отгрузка</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(msg, 4))
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
    asyncio.create_task(delete_later(msg, 4))

async def del_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        msg = await update.effective_chat.send_message("Укажи роль для удаления! Пример: <code>/delrole отгрузка</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(msg, 4))
        return

    role = " ".join(context.args).strip().lower()
    user = update.effective_user

    if role in user_roles and user.id in user_roles[role]:
        user_roles[role].remove(user.id)
        if not user_roles[role]:
            del user_roles[role]
        save_data()
        msg = await update.effective_chat.send_message(f"❌ Роль <b>{role}</b> успешно снята с тебя.", parse_mode="HTML")
    else:
        msg = await update.effective_chat.send_message(f"У тебя нет роли <b>{role}</b> или она уже удалена.", parse_mode="HTML")
    
    asyncio.create_task(delete_later(msg, 4))

async def my_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    user_id = update.effective_user.id
    my_list = [role for role, users in user_roles.items() if user_id in users]
    
    if my_list:
        roles_str = "\n• " + "\n• ".join(my_list)
        msg = await update.effective_chat.send_message(f"Твои роли:{roles_str}")
    else:
        msg = await update.effective_chat.send_message("У тебя пока нет ролей.")
    
    asyncio.create_task(delete_later(msg, 4))

async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not user_roles:
        msg = await update.effective_chat.send_message("В группе пока нет созданных ролей.")
        asyncio.create_task(delete_later(msg, 4))
        return

    roles_list = "\n• ".join(user_roles.keys())
    msg = await update.effective_chat.send_message(f"📋 <b>Роли в группе:</b>\n• {roles_list}", parse_mode="HTML")
    asyncio.create_task(delete_later(msg, 8))

# МОЛНИЕНОСНЫЙ ВЫЗОВ (Ваше сообщение НЕ удаляется)
async def quick_call_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    
    if not text.startswith("!"):
        return

    clean_text = text[1:]
    parts = clean_text.split(maxsplit=1)
    
    if not parts:
        return

    role = parts[0].lower()
    custom_text = parts[1] if len(parts) > 1 else ""

    users = user_roles.get(role, set())
    if not users:
        return

    # Твое сообщение НЕ удаляем! Сразу собираем и отправляем ответ:
    mentions = [user_names[uid] for uid in users if uid in user_names]
    
    response_text = f"🔔 <b>Вызов участников с ролью [{role}]:</b>\n" + " ".join(mentions)
    if custom_text:
        response_text += f"\n\n💬 <b>Сообщение:</b> {custom_text}"

    await update.effective_chat.send_message(response_text, parse_mode="HTML")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setrole", set_role))
    app.add_handler(CommandHandler("delrole", del_role))
    app.add_handler(CommandHandler("myroles", my_roles))
    app.add_handler(CommandHandler("roles", list_roles))
    
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), quick_call_handler))

    app.run_polling()

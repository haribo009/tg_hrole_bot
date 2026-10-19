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

# Токен твоего бота
TOKEN = "8826570127:AAHaZAxmoqocst8EdpPKOpWcV1-MO_gNfAg"

DATA_FILE = "roles_data.json"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Функция загрузки ролей из файла (чтобы они не стирались при перезапусках)
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

# Функция сохранения ролей с авто-отправкой (пушем) в репозиторий GitHub
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

# Вспомогательная функция для удаления сообщения через несколько секунд
async def delete_later(message, delay=3):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "Привет! Я бот для вызова ролей.\n\n"
        "<b>Команды:</b>\n"
        "• <code>/setrole Роль</code> — получить роль\n"
        "• <code>/delrole Роль</code> — снять роль\n"
        "• <code>/roles</code> — меню вызова роли\n"
        "• <code>/myroles</code> — твои роли"
    )

async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Удаляем сообщение с командой пользователя, чтобы не засорять чат
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        msg = await update.effective_chat.send_message("Укажи название роли! Пример: <code>/setrole Дизайнер</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(msg, 4))
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
    save_data() # Сохраняем в файл и отправляем в Git

    msg = await update.effective_chat.send_message(f"✅ Роль <b>{role}</b> успешно закреплена за тобой!", parse_mode="HTML")
    asyncio.create_task(delete_later(msg, 3))

async def del_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        msg = await update.effective_chat.send_message("Укажи название роли! Пример: <code>/delrole Дизайнер</code>", parse_mode="HTML")
        asyncio.create_task(delete_later(msg, 4))
        return

    role = " ".join(context.args).strip()

    if role in user_roles and user.id in user_roles[role]:
        user_roles[role].remove(user.id)
        if not user_roles[role]:
            del user_roles[role]
        save_data()
        msg = await update.effective_chat.send_message(f"❌ Роль <b>{role}</b> снята.", parse_mode="HTML")
    else:
        msg = await update.effective_chat.send_message(f"У тебя нет роли <b>{role}</b>.", parse_mode="HTML")
    
    asyncio.create_task(delete_later(msg, 3))

async def my_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        await update.message.delete()
    except Exception:
        pass

    my_list = [role for role, users in user_roles.items() if user.id in users]
    
    if my_list:
        roles_str = "\n• " + "\n• ".join(my_list)
        msg = await update.effective_chat.send_message(f"Твои роли:{roles_str}")
    else:
        msg = await update.effective_chat.send_message("У тебя пока нет назначенных ролей.")
    
    asyncio.create_task(delete_later(msg, 4))

async def show_roles_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not user_roles:
        msg = await update.effective_chat.send_message("В группе пока нет созданных ролей!")
        asyncio.create_task(delete_later(msg, 3))
        return

    keyboard = []
    for role in user_roles.keys():
        keyboard.append([InlineKeyboardButton(f"📣 Позвать: {role}", callback_data=f"call_{role}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_chat.send_message("Выбери роль для вызова:", reply_markup=reply_markup)

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
        
        # Заменяем сообщение с кнопками на текст с вызовом участников
        await query.edit_message_text(text, parse_mode="HTML")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setrole", set_role))
    app.add_handler(CommandHandler("delrole", del_role))
    app.add_handler(CommandHandler("myroles", my_roles))
    app.add_handler(CommandHandler("roles", show_roles_menu))
    app.add_handler(CallbackQueryHandler(button_click))

    app.run_polling()

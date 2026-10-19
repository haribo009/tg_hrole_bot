import json
import logging
import os
import subprocess
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
        "Привет! Я бот для вызова ролей.\n\n"
        "<b>Как пользоваться:</b>\n"
        "• <code>/setrole НазваниеРоли</code> — получить роль (напр. <code>/setrole отгрузка</code>)\n"
        "• <code>/delrole НазваниеРоли</code> — снять роль\n"
        "• <code>/roles</code> — посмотреть список всех ролей\n"
        "• <code>/myroles</code> — посмотреть свои роли\n\n"
        "🔥 <b>Вызов:</b> начни сообщение с восклицательного знака и названия роли, например:\n"
        "<code>!отгрузка деталь такая-то, денег столько</code>"
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

    await update.effective_chat.send_message(f"✅ Роль <b>{role}</b> успешно закреплена за тобой!", parse_mode="HTML")

async def del_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not context.args:
        await update.effective_chat.send_message("Укажи название роли! Пример: <code>/delrole отгрузка</code>", parse_mode="HTML")
        return

    role = " ".join(context.args).strip().lower()
    user = update.effective_user

    if role in user_roles and user.id in user_roles[role]:
        user_roles[role].remove(user.id)
        if not user_roles[role]:
            del user_roles[role]
        save_data()
        await update.effective_chat.send_message(f"❌ Роль <b>{role}</b> снята.", parse_mode="HTML")
    else:
        await update.effective_chat.send_message(f"У тебя нет роли <b>{role}</b>.", parse_mode="HTML")

async def my_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    my_list = [role for role, users in user_roles.items() if update.effective_user.id in users]
    
    if my_list:
        roles_str = "\n• " + "\n• ".join(my_list)
        await update.effective_chat.send_message(f"Твои роли:{roles_str}")
    else:
        await update.effective_chat.send_message("У тебя пока нет назначенных ролей.")

async def list_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except Exception:
        pass

    if not user_roles:
        await update.effective_chat.send_message("В группе пока нет созданных ролей!")
        return

    roles_list = "\n• ".join(user_roles.keys())
    await update.effective_chat.send_message(f"📋 <b>Список всех ролей в группе:</b>\n• {roles_list}", parse_mode="HTML")

# Перехват сообщений, начинающихся с восклицательного знака (!)
async def handle_exclamation_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    
    # Проверяем, начинается ли сообщение с !
    if not text.startswith("!"):
        return

    # Убираем восклицательный знак и разделяем роль и текст
    # Например "!отгрузка деталь такая" -> роль "отгрузка", текст "деталь такая"
    text_without_excl = text[1:]
    text_parts = text_without_excl.split(maxsplit=1)
    
    if not text_parts:
        return

    potential_role = text_parts[0].lower()

    # Проверяем, есть ли такая роль в нашей базе данных
    if potential_role in user_roles:
        users = user_roles[potential_role]
        if not users:
            return

        # Удаляем сообщение пользователя
        try:
            await update.message.delete()
        except Exception:
            pass

        mentions = [user_names[uid] for uid in users if uid in user_names]
        custom_text = text_parts[1] if len(text_parts) > 1 else ""

        response_text = f"🔔 <b>Вызов участников с ролью [{potential_role}]:</b>\n" + " ".join(mentions)
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
    
    # Перехватывает любые сообщения, начинающиеся с !
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_exclamation_call))

    app.run_polling()
